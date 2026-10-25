"""Unit tests for OutputMasker data redaction and field removal."""

from core.database import Rule
from core.engine.output_masker import OutputMasker


def test_output_masker_redact_field():
    """Verify REDACT_FIELD blanks sensitive field values while retaining keys."""
    rule = Rule(
        id="rule_redact_ssn",
        name="Redact SSN",
        rule_type="REDACT_FIELD",
        expression="ssn,credit_card",
        is_active=True,
    )
    data = [
        {"id": 1, "name": "Alice", "ssn": "123-45-6789", "credit_card": "4111-2222-3333"},
        {"id": 2, "name": "Bob", "ssn": "987-65-4321", "credit_card": "5500-0000-0000"},
    ]

    masked, hit_fields = OutputMasker.apply(data, [rule])

    assert len(masked) == 2
    assert masked[0]["ssn"] is None
    assert masked[0]["credit_card"] is None
    assert masked[0]["name"] == "Alice"
    assert "ssn" in hit_fields
    assert "credit_card" in hit_fields


def test_output_masker_remove_field():
    """Verify REMOVE_FIELD completely strips keys from output payloads."""
    rule = Rule(
        id="rule_remove_password",
        name="Remove Password",
        rule_type="REMOVE_FIELD",
        expression="password_hash,salt",
        is_active=True,
    )
    data = {"id": 10, "username": "admin", "password_hash": "secret", "salt": "random_bytes"}

    masked, hit_fields = OutputMasker.apply(data, [rule])

    assert "password_hash" not in masked
    assert "salt" not in masked
    assert masked["username"] == "admin"
    assert "password_hash" in hit_fields


def test_output_masker_remove_takes_precedence_over_redact():
    """Verify that REMOVE_FIELD takes priority over REDACT_FIELD if both match."""
    rule_redact = Rule(id="r1", name="R1", rule_type="REDACT_FIELD", expression="token", is_active=True)
    rule_remove = Rule(id="r2", name="R2", rule_type="REMOVE_FIELD", expression="token", is_active=True)

    data = {"token": "xyz123"}
    masked, hit_fields = OutputMasker.apply(data, [rule_redact, rule_remove])

    assert "token" not in masked


def test_output_masker_nested_structures():
    """Verify recursive field masking in nested dictionaries and lists."""
    rule = Rule(
        id="r_email",
        name="Redact Email",
        rule_type="REDACT_FIELD",
        expression="email",
        is_active=True,
    )
    data = {
        "org": "Corp",
        "members": [
            {"name": "Dev1", "contact": {"email": "dev1@corp.local", "phone": "123"}},
            {"name": "Dev2", "contact": {"email": "dev2@corp.local", "phone": "456"}},
        ],
    }

    masked, hit_fields = OutputMasker.apply(data, [rule])

    assert masked["members"][0]["contact"]["email"] is None
    assert masked["members"][0]["contact"]["phone"] == "123"
    assert masked["members"][1]["contact"]["email"] is None


def test_output_masker_inactive_rules_ignored():
    """Verify inactive masking rules are not applied."""
    rule = Rule(
        id="r_inactive",
        name="Inactive",
        rule_type="REDACT_FIELD",
        expression="secret",
        is_active=False,
    )
    data = {"secret": "visible"}
    masked, hit_fields = OutputMasker.apply(data, [rule])

    assert masked["secret"] == "visible"
    assert len(hit_fields) == 0
