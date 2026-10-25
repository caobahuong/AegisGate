"""Tests for hardened governance, fail-closed state machine, atomic approval and output masking."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlmodel import Session, SQLModel, create_engine

from core.config import settings
from core.database import PluginProfile, Rule
from core.engine.governance import GovernanceEngine, validate_rule_definition
from core.engine.output_masker import OutputMasker
from core.engine.state_machine import ExecutionStateMachine
from core.engine.timeout_guard import TimeoutGuard
from core.exceptions import ExecutionStateError, ExecutionTimeoutError
from plugins.plugin_contract import ExecuteResult
from plugins.sql_inspector import classify_query, is_unbounded_scan, joins_tables, statement_count


def _rule(rule_type: str, expression: str = "", rule_id: str = "r1") -> Rule:
    return Rule(id=rule_id, name=rule_id, rule_type=rule_type, expression=expression, is_active=True)


class TestSqlInspector:
    @pytest.mark.parametrize(
        "query",
        [
            "SELECT * FROM AuditLogs -- WHERE x = 1",
            "SELECT * FROM AuditLogs /* WHERE x = 1 */",
            "SELECT * FROM AuditLogs WHERE 1=1",
            "SELECT * FROM AuditLogs WHERE (1 = 1)",
            "SELECT * FROM AuditLogs WHERE 'a' = 'a'",
            "SELECT * FROM AuditLogs WHERE TRUE",
            "SELECT * FROM AuditLogs WHERE Id = 5 OR 1=1",
            "SELECT * FROM AuditLogs WHERE 1=1 AND 2=2",
            "SELECT * FROM (SELECT * FROM AuditLogs WHERE Id = 1) t, AuditLogs",
        ],
    )
    def test_unbounded_scan_cannot_be_dodged(self, query: str) -> None:
        assert is_unbounded_scan(query)

    @pytest.mark.parametrize(
        "query",
        [
            "SELECT * FROM AuditLogs WHERE LogID = 5",
            "SELECT * FROM AuditLogs WHERE 1=1 AND LogID = 5",
            "SELECT 1",
            "SELECT * FROM T WHERE a = 'WHERE' ORDER BY a",
        ],
    )
    def test_bounded_queries_pass(self, query: str) -> None:
        assert not is_unbounded_scan(query)

    def test_join_detection_alias_cte_comma_and_schema(self) -> None:
        tables = ["ORDERS", "AUDITLOGS"]
        assert joins_tables("SELECT 1 FROM dbo.Orders o JOIN [dbo].[AuditLogs] a ON o.Id=a.Id", tables)
        assert joins_tables("SELECT 1 FROM Orders o, AuditLogs a WHERE o.Id=a.Id", tables)
        assert joins_tables("WITH x AS (SELECT * FROM Orders) SELECT * FROM x JOIN AuditLogs a ON 1=1", tables)

    def test_join_not_flagged_when_only_mentioned(self) -> None:
        tables = ["ORDERS", "AUDITLOGS"]
        assert not joins_tables("SELECT 1 FROM Orders WHERE note = 'AuditLogs'", tables)
        assert not joins_tables("SELECT 1 FROM Orders -- AuditLogs", tables)
        assert not joins_tables("SELECT 1 FROM Orders WHERE Id IN (1,2)", tables)

    def test_classification_ignores_identifiers_comments_strings(self) -> None:
        assert classify_query("SELECT UPDATED_AT, deleted FROM T WHERE x = 'DROP TABLE'") == "READ"
        assert classify_query("SELECT 1 -- DELETE FROM x") == "READ"
        assert classify_query("SELECT * FROM [Update]") == "READ"
        assert classify_query("UPDATE T SET a = 1") == "WRITE"
        assert classify_query("SELECT * INTO NewT FROM T") == "WRITE"
        assert classify_query("WITH c AS (SELECT 1) DELETE FROM T") == "WRITE"
        assert classify_query("EXEC sp_who") == "WRITE"
        assert classify_query("") == "WRITE"

    def test_multi_statement_blocked(self) -> None:
        assert statement_count("SELECT 1; DROP TABLE T") == 2
        violations = GovernanceEngine.inspect_query_and_plan("SELECT 1; SELECT 2", [], {})
        assert violations and "Multiple" in violations[0]
        assert GovernanceEngine.inspect_query_and_plan("SELECT 1;", [], {}) == []


class TestCustomRuleSafety:
    def test_invalid_regex_fails_closed_instead_of_crashing(self) -> None:
        v = GovernanceEngine.inspect_query_and_plan("SELECT 1", [_rule("CUSTOM", "([unclosed")], {})
        assert v and "unusable" in v[0]

    def test_redos_pattern_rejected(self) -> None:
        assert validate_rule_definition("CUSTOM", "(a+)+$") is not None
        v = GovernanceEngine.inspect_query_and_plan("aaaaaaaaaaaaaaaaaaaaaaaa!", [_rule("CUSTOM", "(a+)+$")], {})
        assert v and "unusable" in v[0]

    def test_valid_custom_pattern_still_works(self) -> None:
        assert validate_rule_definition("CUSTOM", r"\bSALARY\b") is None
        v = GovernanceEngine.inspect_query_and_plan(
            "SELECT salary FROM T WHERE a=1", [_rule("CUSTOM", r"\bSALARY\b")], {}
        )
        assert v

    def test_rule_definition_validation(self) -> None:
        assert validate_rule_definition("NOPE", "x") is not None
        assert validate_rule_definition("FORBID_JOIN", "OnlyOne") is not None
        assert validate_rule_definition("REDACT_FIELD", " , ") is not None
        assert validate_rule_definition("REDACT_FIELD", "Password") is None


class TestOutputMasker:
    DATA = [
        {"id": 1, "Password": "secret", "profile": {"ssn": "123", "name": "A"}},
        {"id": 2, "password": "x", "items": [{"ssn": "9"}]},
    ]

    def test_redact_nulls_value_keeps_key(self) -> None:
        out, fields = OutputMasker.apply(self.DATA, [_rule("REDACT_FIELD", "password,dbo.Users.SSN")])
        assert out[0]["Password"] is None and out[0]["profile"]["ssn"] is None
        assert out[0]["profile"]["name"] == "A" and out[1]["password"] is None
        assert out[1]["items"][0]["ssn"] is None
        assert sorted(f.lower() for f in fields) == ["password", "ssn"]

    def test_remove_deletes_key(self) -> None:
        out, _ = OutputMasker.apply(self.DATA, [_rule("REMOVE_FIELD", "Password")])
        assert "Password" not in out[0] and "password" not in out[1]
        assert out[0]["id"] == 1

    def test_remove_wins_over_redact_and_input_not_mutated(self) -> None:
        out, _ = OutputMasker.apply(
            self.DATA, [_rule("REDACT_FIELD", "password"), _rule("REMOVE_FIELD", "password", "r2")]
        )
        assert "Password" not in out[0]
        assert self.DATA[0]["Password"] == "secret"

    def test_no_rules_returns_same_data(self) -> None:
        out, fields = OutputMasker.apply(self.DATA, [])
        assert out is self.DATA and fields == []

    def test_inactive_rule_ignored(self) -> None:
        rule = _rule("REMOVE_FIELD", "Password")
        rule.is_active = False
        out, fields = OutputMasker.apply(self.DATA, [rule])
        assert out is self.DATA and fields == []


@pytest.fixture(name="session")
def fixture_session(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'hard.db'}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(PluginProfile(id="t1", name="T1", driver="x", entrypoint="python x.py", status="active"))
        session.commit()
        yield session


class TestStateMachineHardening:
    async def test_dry_run_failure_is_fail_closed(self, session: Session) -> None:
        sm = ExecutionStateMachine(session)
        client = AsyncMock()
        client.dry_run.side_effect = RuntimeError("plugin down")
        sm.setting_store.set_auto_approval(True)
        with patch.object(sm.registry, "get_client", return_value=client):
            log = await sm.initiate_execution("t1", "SELECT 1")
        assert log.status == "REJECTED" and "fail-closed" in (log.error_message or "")
        client.execute.assert_not_called()

    async def test_dry_run_failure_open_mode_never_auto_executes(self, session: Session, monkeypatch) -> None:
        monkeypatch.setattr(settings, "FAIL_CLOSED_ON_DRY_RUN_ERROR", False)
        sm = ExecutionStateMachine(session)
        client = AsyncMock()
        client.dry_run.side_effect = RuntimeError("plugin down")
        sm.setting_store.set_auto_approval(True)
        with patch.object(sm.registry, "get_client", return_value=client):
            log = await sm.initiate_execution("t1", "SELECT 1")
        assert log.status == "PAUSED_FOR_REVIEW"
        client.execute.assert_not_called()

    async def test_double_approve_executes_once(self, session: Session) -> None:
        sm = ExecutionStateMachine(session)
        client = AsyncMock()
        client.dry_run.return_value = AsyncMock(explain_plan={}, violations=[], query_type="READ")
        client.execute.return_value = ExecuteResult(data=[{"a": 1}], rows_affected=1, execution_time_ms=1.0, spid=1)
        sm.setting_store.set_auto_approval(False)
        with patch.object(sm.registry, "get_client", return_value=client):
            log = await sm.initiate_execution("t1", "SELECT 1")
            assert log.status == "PAUSED_FOR_REVIEW"
            await sm.approve_and_resume(log.id)
            with pytest.raises(ExecutionStateError):
                await sm.approve_and_resume(log.id)
        assert client.execute.call_count == 1

    async def test_losing_race_is_refused(self, session: Session) -> None:
        sm = ExecutionStateMachine(session)
        client = AsyncMock()
        client.dry_run.return_value = AsyncMock(explain_plan={}, violations=[], query_type="READ")
        sm.setting_store.set_auto_approval(False)
        with patch.object(sm.registry, "get_client", return_value=client):
            log = await sm.initiate_execution("t1", "SELECT 1")
            # another request flips the state between the read and the update
            assert sm.log_store.transition_status(log.id, ("PAUSED_FOR_REVIEW",), {"status": "REJECTED"})
            with pytest.raises(ExecutionStateError):
                await sm.approve_and_resume(log.id)
        client.execute.assert_not_called()

    async def test_plugin_cannot_downgrade_write_to_read(self, session: Session) -> None:
        sm = ExecutionStateMachine(session)
        client = AsyncMock()
        client.dry_run.return_value = AsyncMock(explain_plan={}, violations=[], query_type="READ")
        sm.setting_store.set_auto_approval(False)
        with patch.object(sm.registry, "get_client", return_value=client):
            log = await sm.initiate_execution("t1", "DELETE FROM T WHERE Id = 1")
        assert log.query_type == "WRITE"

    async def test_output_fields_masked_before_storage(self, session: Session) -> None:
        sm = ExecutionStateMachine(session)
        sm.rule_store.create_rule(_rule("REDACT_FIELD", "Password", "mask1"))
        sm.rule_store.create_rule(_rule("REMOVE_FIELD", "Salary", "mask2"))
        client = AsyncMock()
        client.dry_run.return_value = AsyncMock(explain_plan={}, violations=[], query_type="READ")
        client.execute.return_value = ExecuteResult(
            data=[{"Name": "A", "Password": "secret", "Salary": 99}], rows_affected=1, execution_time_ms=1.0, spid=1
        )
        sm.setting_store.set_auto_approval(True)
        with patch.object(sm.registry, "get_client", return_value=client):
            log = await sm.initiate_execution("t1", "SELECT Name, Password, Salary FROM U WHERE Id = 1")
        assert log.status == "COMPLETED"
        assert "secret" not in log.result_summary and "99" not in log.result_summary
        import json

        summary = json.loads(log.result_summary)
        assert summary["data"] == [{"Name": "A", "Password": None}]
        assert sorted(summary["masked_fields"]) == ["Password", "Salary"]
        assert client.execute.call_args.args[0].read_only is True


class TestTimeoutGuardAbortReporting:
    async def test_failed_abort_is_reported(self) -> None:
        async def slow() -> None:
            await asyncio.sleep(5)

        async def bad_abort() -> None:
            raise RuntimeError("kill refused")

        with pytest.raises(ExecutionTimeoutError) as info:
            await TimeoutGuard.run_with_timeout(slow(), 0.05, on_timeout_abort=bad_abort)
        assert "abort FAILED" in info.value.message and "kill refused" in info.value.message
        assert info.value.details["abort_failed"] is True
