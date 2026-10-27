"""Unit tests for SQL query classification and governance rule inspection."""

from core.database import Rule
from core.engine.governance import GovernanceEngine


class TestGovernanceEngine:
    """Test governance rule enforcement on SQL queries and execution plans."""

    def test_forbid_join_detection(self):
        """Verify FORBID_JOIN rule flags prohibited cross-table joins."""
        rule = Rule(
            id="rule_no_join",
            name="No Orders and AuditLogs Join",
            rule_type="FORBID_JOIN",
            expression="Orders,AuditLogs",
            description="Forbidden join on Orders and AuditLogs",
            severity="CRITICAL",
            is_active=True,
        )

        # Prohibited join query
        violating_query = """
        SELECT o.OrderID, a.LogID
        FROM Orders o
        JOIN AuditLogs a ON o.OrderID = a.OrderID
        """
        violations = GovernanceEngine.inspect_query_and_plan(violating_query, [rule])
        assert len(violations) >= 1
        assert "rule_no_join" in violations[0]

        # Allowed single table query
        safe_query = "SELECT OrderID, Amount FROM Orders WHERE OrderID = 101"
        assert len(GovernanceEngine.inspect_query_and_plan(safe_query, [rule])) == 0

    def test_table_scan_detection(self):
        """Verify FORBID_TABLE_SCAN rule flags unbounded table scans."""
        rule = Rule(
            id="rule_no_scan",
            name="No Large Table Scans",
            rule_type="FORBID_TABLE_SCAN",
            expression="Users",
            description="Prohibit scans on Users table",
            severity="HIGH",
            is_active=True,
        )

        plan_with_scan = {"PhysicalOp": "Table Scan", "EstimateRows": 1000000}
        violations = GovernanceEngine.inspect_query_and_plan("SELECT * FROM Users", [rule], plan_with_scan)
        assert len(violations) >= 1

    def test_query_type_determination(self):
        """Verify query classification into READ and WRITE categories."""
        assert GovernanceEngine.determine_query_type("SELECT * FROM Customers") == "READ"
        assert GovernanceEngine.determine_query_type("INSERT INTO Orders (Id) VALUES (1)") == "WRITE"
        assert GovernanceEngine.determine_query_type("UPDATE Orders SET Status = 'Done'") == "WRITE"
        assert GovernanceEngine.determine_query_type("DELETE FROM Orders WHERE Id = 1") == "WRITE"
