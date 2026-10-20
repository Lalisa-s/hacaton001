"""Contract checks. No database, network, application mutations, or fake transfers."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.wire_models import (
    AccountRead, ExchangeFixtures, TestRead as PublicTestDTO, TestSubmit as SubmitDTO,
    TransactionRead, UserRead, account_response, parse_transfer_json,
    public_projection,
)

ROOT = Path(__file__).resolve().parents[2] / "docs" / "json-exchange"


def fixtures():
    return ExchangeFixtures.model_validate_json(
        (ROOT / "examples" / "entities.json").read_text(encoding="utf-8")
    )


def test_public_fixture_roundtrip_and_reserves():
    data = fixtures()
    again = ExchangeFixtures.model_validate_json(data.model_dump_json())
    assert data == again
    raw = json.loads(data.model_dump_json())
    for account in data.Account:
        reserves = [p for p in data.Pig if p.account_id == account.id]
        assert account_response(account.model_dump(), reserves) == account
    assert raw["Account"][1]["balance"] == 10000
    assert raw["Account"][1]["active_balance"] == 7000
    assert all(a.user_id == 10 for a in data.Account)


def test_public_whitelist_excludes_secrets():
    data = fixtures()
    user = public_projection(UserRead, {**data.User[0].model_dump(), "password": "private-hash"})
    public_test = public_projection(PublicTestDTO, {**data.Test[0].model_dump(), "right_answer": {"1": 0}})
    assert "password" not in json.loads(user.model_dump_json())
    assert "right_answer" not in json.loads(public_test.model_dump_json())
    serialized = data.model_dump_json()
    assert '"right_answer"' not in serialized
    assert '"password"' not in serialized


@pytest.mark.parametrize("amount", [0, -1, 1.5, "2500", True, 9_007_199_254_740_992])
def test_invalid_money_is_rejected(amount):
    with pytest.raises(ValidationError):
        parse_transfer_json(json.dumps({"cender": 100, "recipient": 101, "amount": amount}))


@pytest.mark.parametrize("extra", [{"balance": 99999}, {"id": 99}, {"MTcount": 500}])
def test_client_cannot_supply_server_owned_fields(extra):
    with pytest.raises(ValidationError):
        parse_transfer_json(json.dumps({"cender": 100, "recipient": 101, "amount": 2500, **extra}))


def test_sender_is_account_id_and_distinct_from_recipient():
    assert parse_transfer_json('{"cender":100,"recipient":101,"amount":2500}').cender == 100
    for sender, recipient in (("demo_parent", 101), (100, 100)):
        with pytest.raises(ValidationError):
            parse_transfer_json(json.dumps({"cender": sender, "recipient": recipient, "amount": 2500}))


def test_timestamp_retains_timezone_and_serializes_to_utc():
    transaction = TransactionRead.model_validate_json(
        '{"id":900,"cender":100,"recipient":101,"amount":2500,"data":"2026-10-20T13:30:00+03:00"}'
    )
    assert json.loads(transaction.model_dump_json())["data"] == "2026-10-20T10:30:00Z"
    with pytest.raises(ValidationError):
        TransactionRead.model_validate_json(
            '{"id":900,"cender":100,"recipient":101,"amount":2500,"data":"2026-10-20T10:30:00"}'
        )


def test_unlimited_and_zero_limit_are_different():
    account = fixtures().Account[0].model_dump()
    unlimited = AccountRead.model_validate({**account, "limit": None, "limit_period": None})
    blocked = AccountRead.model_validate({**account, "limit": 0, "limit_period": "daily"})
    assert unlimited.limit is None
    assert blocked.limit == 0
    with pytest.raises(ValidationError):
        AccountRead.model_validate({**account, "limit": 1000, "limit_period": None})


def test_test_submission_uses_string_keys_and_integer_indexes():
    submission = SubmitDTO.model_validate_json('{"answers":{"1":0}}')
    assert submission.answers == {"1": 0}
    with pytest.raises(ValidationError):
        SubmitDTO.model_validate_json('{"answers":{"1":"0"}}')


def test_response_builder_rejects_foreign_reserve():
    data = fixtures()
    with pytest.raises(ValueError, match="different account"):
        account_response(data.Account[0].model_dump(), data.Pig)


def test_invalid_json_is_rejected():
    with pytest.raises(ValidationError):
        parse_transfer_json('{"cender":100,}')
