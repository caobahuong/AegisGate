"""Edge-case unit tests for OutputMasker.

Verifies:
- Edge cases: empty structures, None, primitives, unicode, very long strings
- Overlapping patterns where REMOVE overrides REDACT
- Table prefix dot notation (e.g. Users.Password)
- Recursive nested lists and dictionaries
- Input immutability
"""

import copy

from core.engine.output_masker import OutputMasker
from tests.factories import make_rule


def test_output_masker_empty_and_none():
    """Verify handling of None, empty list, empty dict, and primitive types."""
    rule = make_rule(rule_type="REDACT_FIELD", expression="password,token")

    # None input
    res, hit = OutputMasker.apply(None, [rule])
    assert res is None
    assert hit == []

    # Empty dict
    res_d, hit_d = OutputMasker.apply({}, [rule])
    assert res_d == {}
    assert hit_d == []

    # Empty list
    res_l, hit_l = OutputMasker.apply([], [rule])
    assert res_l == []
    assert hit_l == []

    # Primitive root values (int, string, bool)
    res_p, hit_p = OutputMasker.apply(42, [rule])
    assert res_p == 42
    assert hit_p == []


def test_output_masker_unicode_and_vietnamese():
    """Verify handling of unicode keys and values (Vietnamese diacritics, emoji, special symbols)."""
    rules = [
        make_rule(rule_type="REDACT_FIELD", expression="mật_khẩu,token_🔑"),
        make_rule(rule_type="REMOVE_FIELD", expression="số_cccd"),
    ]

    payload = {
        "tên_người_dùng": "Nguyễn Văn A",
        "mật_khẩu": "MậtKhẩuBảoMật123!@#",
        "token_🔑": "secret_key_abc_xyz",
        "số_cccd": "001200001234",
        "ghi_chú": "Dữ liệu hợp lệ với tiếng Việt: á, à, ả, ã, ạ, ê, ế, ơ, ư",
    }

    masked, hit = OutputMasker.apply(payload, rules)
    assert masked["tên_người_dùng"] == "Nguyễn Văn A"
    assert masked["mật_khẩu"] is None  # REDACTed
    assert masked["token_🔑"] is None  # REDACTed
    assert "số_cccd" not in masked  # REMOVEd
    assert "ghi_chú" in masked
    assert sorted(hit) == sorted(["mật_khẩu", "token_🔑", "số_cccd"])


def test_output_masker_very_long_strings():
    """Verify performance and stability with very large string payloads (> 1MB)."""
    large_token = "A" * (1024 * 1024)  # 1MB string
    payload = {
        "id": 1,
        "token": large_token,
        "data": "B" * 10000,
    }
    rule = make_rule(rule_type="REDACT_FIELD", expression="token")

    masked, hit = OutputMasker.apply(payload, [rule])
    assert masked["id"] == 1
    assert masked["token"] is None
    assert len(masked["data"]) == 10000
    assert hit == ["token"]


def test_output_masker_overlapping_patterns_remove_wins():
    """Verify that REMOVE_FIELD overrides REDACT_FIELD when both match the same field."""
    rules = [
        make_rule(id="r1", rule_type="REDACT_FIELD", expression="password,ssn,api_key"),
        make_rule(id="r2", rule_type="REMOVE_FIELD", expression="ssn,secret"),
        make_rule(id="r3", rule_type="REDACT_FIELD", expression="users.password,orders.secret"),
    ]

    payload = {
        "username": "admin",
        "password": "SuperSecretPassword!",  # Both REDACT and table-prefix REDACT -> None
        "ssn": "123-45-6789",  # Both REDACT and REMOVE -> REMOVE wins (key removed)
        "secret": "TopSecretValue",  # Both REMOVE and table-prefix REDACT -> REMOVE wins
        "api_key": "key_xyz_123",  # REDACT -> None
    }

    original = copy.deepcopy(payload)
    masked, hit = OutputMasker.apply(payload, rules)

    # Immutability check
    assert payload == original

    # Field transformations
    assert masked["username"] == "admin"
    assert masked["password"] is None
    assert "ssn" not in masked
    assert "secret" not in masked
    assert masked["api_key"] is None
    assert sorted(hit) == sorted(["api_key", "password", "secret", "ssn"])


def test_output_masker_deeply_nested_structures():
    """Verify recursive masking in deeply nested heterogeneous dicts and lists."""
    rule = make_rule(rule_type="REDACT_FIELD", expression="card_number,cvv")

    nested_payload = {
        "company": "Tech Corp",
        "departments": [
            {
                "name": "Finance",
                "employees": [
                    {
                        "name": "Bob",
                        "payment_info": {
                            "card_number": "4111-2222-3333-4444",
                            "cvv": "123",
                            "billing_address": {"city": "Hanoi", "country": "Vietnam"},
                        },
                    }
                ],
            }
        ],
    }

    masked, hit = OutputMasker.apply(nested_payload, [rule])
    bob_payment = masked["departments"][0]["employees"][0]["payment_info"]
    assert bob_payment["card_number"] is None
    assert bob_payment["cvv"] is None
    assert bob_payment["billing_address"]["city"] == "Hanoi"
    assert sorted(hit) == ["card_number", "cvv"]
