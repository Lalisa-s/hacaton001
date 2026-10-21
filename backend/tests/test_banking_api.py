"""The first integration scenario: demo parent, account, transfer and history."""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.core.config import Settings
from app.main import create_app
from app.models.banking import Account, Transaction, User
from app.schemas.wire_models import MAX_JS_INTEGER, TransferCreate


pytestmark = pytest.mark.anyio
PREFIX = "/api/v1"


@pytest.fixture
def anyio_backend():
    return "asyncio"


def demo_settings(database_path, **changes):
    values = {
        "database_url": f"sqlite:///{database_path.as_posix()}",
        "demo_mode": True,
        "demo_user_id": 10,
        "cors_origins": ["http://localhost:5173"],
    }
    values.update(changes)
    return Settings(_env_file=None, **values)


@pytest.fixture
async def bank_app(tmp_path):
    application = create_app(demo_settings(tmp_path / "banking.db"))
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def bank_client(bank_app):
    async with AsyncClient(
        transport=ASGITransport(app=bank_app), base_url="http://testserver"
    ) as client:
        yield client


def update_account(application, account_id, **values):
    with application.state.session_factory() as session:
        account = session.get(Account, account_id)
        assert account is not None
        for name, value in values.items():
            setattr(account, name, value)
        session.commit()


def database_snapshot(application):
    with application.state.session_factory() as session:
        balances = list(
            session.execute(select(Account.id, Account.balance).order_by(Account.id))
        )
        transfers = session.scalar(select(func.count()).select_from(Transaction))
        return balances, transfers


def add_other_parent(application):
    with application.state.session_factory() as session:
        session.add(User(id=40, login="other-parent", role="parent"))
        session.flush()
        session.add(
            Account(
                id=200,
                user_id=40,
                balance=10000,
                active=True,
                limit=None,
                limit_period=None,
            )
        )
        session.commit()


def assert_error(response, status, code):
    assert response.status_code == status, response.text
    error = response.json()["error"]
    assert error["code"] == code
    assert isinstance(error["message"], str) and error["message"]
    assert isinstance(error["details"], list)
    assert set(response.json()) == {"error"}


async def test_demo_profile_and_account_balances_are_public(bank_client):
    profile = await bank_client.get(f"{PREFIX}/me")
    assert profile.status_code == 200
    assert profile.json()["id"] == 10
    assert profile.json()["role"] == "parent"
    assert set(profile.json()["accounts"]) == {100, 101}
    assert "password" not in profile.text

    response = await bank_client.get(f"{PREFIX}/accounts")
    assert response.status_code == 200
    assert set(response.json()) == {"items"}
    accounts = {account["id"]: account for account in response.json()["items"]}
    assert set(accounts) == {100, 101}
    assert accounts[100]["balance"] == accounts[100]["active_balance"] == 20000
    assert accounts[100]["limit"] == 15000
    assert accounts[101]["balance"] == 10000
    assert accounts[101]["active_balance"] == 7000
    assert accounts[101]["pigs"] == [500]
    assert all(account["user_id"] == 10 for account in accounts.values())
    assert all(account["transactions_history"] == [] for account in accounts.values())


async def test_transfer_updates_both_balances_and_one_shared_history_record(bank_client):
    started = datetime.now(timezone.utc)
    response = await bank_client.post(
        f"{PREFIX}/transactions",
        json={"cender": 100, "recipient": 101, "amount": 2500},
    )
    assert response.status_code == 201, response.text
    transfer = response.json()
    assert set(transfer) == {"id", "cender", "recipient", "amount", "data"}
    assert transfer["id"] > 0
    assert transfer["cender"] == 100
    assert transfer["recipient"] == 101
    assert transfer["amount"] == 2500
    recorded = datetime.fromisoformat(transfer["data"].replace("Z", "+00:00"))
    assert recorded.utcoffset() == timedelta(0)
    assert started <= recorded <= datetime.now(timezone.utc)

    source = (await bank_client.get(f"{PREFIX}/accounts/100")).json()
    target = (await bank_client.get(f"{PREFIX}/accounts/101")).json()
    assert source["balance"] == source["active_balance"] == 17500
    assert target["balance"] == 12500
    assert target["active_balance"] == 9500
    assert source["balance"] + target["balance"] == 30000
    assert source["transactions_history"] == target["transactions_history"] == [
        transfer["id"]
    ]
    for account_id in (100, 101):
        history = await bank_client.get(f"{PREFIX}/accounts/{account_id}/transactions")
        assert history.status_code == 200
        assert history.json() == {"items": [transfer]}


@pytest.mark.parametrize(
    "change",
    [
        {"amount": 0},
        {"amount": -1},
        {"amount": True},
        {"amount": "2500"},
        {"amount": 1.5},
        {"amount": MAX_JS_INTEGER + 1},
        {"cender": "100"},
        {"cender": True},
        {"recipient": 100},
    ],
)
async def test_transfer_rejects_invalid_ids_or_money_without_writes(
    bank_app, bank_client, change
):
    before = database_snapshot(bank_app)
    response = await bank_client.post(
        f"{PREFIX}/transactions",
        json={"cender": 100, "recipient": 101, "amount": 2500, **change},
    )
    assert_error(response, 422, "VALIDATION_ERROR")
    assert database_snapshot(bank_app) == before


async def test_malformed_json_uses_same_error_envelope(bank_app, bank_client):
    before = database_snapshot(bank_app)
    response = await bank_client.post(
        f"{PREFIX}/transactions",
        content='{"cender":100,"recipient":101,"amount":',
        headers={"Content-Type": "application/json"},
    )
    assert_error(response, 422, "VALIDATION_ERROR")
    assert database_snapshot(bank_app) == before


@pytest.mark.parametrize("field", ["id", "data", "balance", "user_id", "password"])
async def test_server_owned_fields_are_rejected_and_values_not_echoed(
    bank_app, bank_client, field
):
    before = database_snapshot(bank_app)
    secret = "sensitive-value-not-to-echo"
    response = await bank_client.post(
        f"{PREFIX}/transactions",
        json={"cender": 100, "recipient": 101, "amount": 1, field: secret},
    )
    assert_error(response, 422, "VALIDATION_ERROR")
    assert secret not in response.text
    assert database_snapshot(bank_app) == before


async def test_demo_mode_off_keeps_health_but_denies_demo_api(tmp_path):
    application = create_app(demo_settings(tmp_path / "disabled.db", demo_mode=False))
    async with application.router.lifespan_context(application):
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://testserver"
        ) as client:
            assert (await client.get(f"{PREFIX}/health")).json() == {"status": "ok"}
            response = await client.get(f"{PREFIX}/me")
            assert_error(response, 403, "DEMO_MODE_DISABLED")


async def test_unknown_demo_user_is_rejected(bank_app, bank_client):
    before = database_snapshot(bank_app)
    response = await bank_client.get(
        f"{PREFIX}/me", headers={"X-Demo-User-Id": "999999"}
    )
    assert_error(response, 401, "DEMO_USER_NOT_FOUND")
    assert database_snapshot(bank_app) == before


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("GET", "/accounts/999999", None),
        ("GET", "/accounts/999999/transactions", None),
        ("POST", "/transactions", {"cender": 999999, "recipient": 101, "amount": 1}),
        ("POST", "/transactions", {"cender": 100, "recipient": 999999, "amount": 1}),
    ],
)
async def test_nonexistent_account_is_not_found_without_writes(
    bank_app, bank_client, method, path, body
):
    before = database_snapshot(bank_app)
    kwargs = {} if body is None else {"json": body}
    response = await bank_client.request(method, PREFIX + path, **kwargs)
    assert_error(response, 404, "NOT_FOUND")
    assert database_snapshot(bank_app) == before


async def test_other_parent_accounts_cannot_be_read_or_used_for_transfers(
    bank_app, bank_client
):
    add_other_parent(bank_app)
    listed = (await bank_client.get(f"{PREFIX}/accounts")).json()["items"]
    assert {account["id"] for account in listed} == {100, 101}
    before = database_snapshot(bank_app)
    for path in ("/accounts/200", "/accounts/200/transactions"):
        assert_error(await bank_client.get(PREFIX + path), 403, "ACCESS_DENIED")
    for source, target in ((100, 200), (200, 100)):
        response = await bank_client.post(
            f"{PREFIX}/transactions",
            json={"cender": source, "recipient": target, "amount": 1},
        )
        assert_error(response, 403, "ACCESS_DENIED")
    assert database_snapshot(bank_app) == before


@pytest.mark.parametrize("account_id", [100, 101])
async def test_frozen_source_or_destination_blocks_entire_transfer(
    bank_app, bank_client, account_id
):
    update_account(bank_app, account_id, active=False)
    before = database_snapshot(bank_app)
    response = await bank_client.post(
        f"{PREFIX}/transactions",
        json={"cender": 100, "recipient": 101, "amount": 2500},
    )
    assert_error(response, 409, "ACCOUNT_FROZEN")
    assert database_snapshot(bank_app) == before


@pytest.mark.parametrize("amount", [7001, 10001])
async def test_reserved_money_and_insufficient_balance_cannot_be_spent(
    bank_app, bank_client, amount
):
    update_account(bank_app, 101, limit=None, limit_period=None)
    before = database_snapshot(bank_app)
    response = await bank_client.post(
        f"{PREFIX}/transactions",
        json={"cender": 101, "recipient": 100, "amount": amount},
    )
    assert_error(response, 409, "INSUFFICIENT_FUNDS")
    assert database_snapshot(bank_app) == before


async def test_daily_limit_counts_cumulative_outgoing_transfers(bank_app, bank_client):
    for amount in (10000, 5000):
        response = await bank_client.post(
            f"{PREFIX}/transactions",
            json={"cender": 100, "recipient": 101, "amount": amount},
        )
        assert response.status_code == 201, response.text
    before = database_snapshot(bank_app)
    rejected = await bank_client.post(
        f"{PREFIX}/transactions",
        json={"cender": 100, "recipient": 101, "amount": 1},
    )
    assert_error(rejected, 409, "LIMIT_EXCEEDED")
    assert database_snapshot(bank_app) == before


@pytest.mark.parametrize("limit,period,amount,status", [(0, "daily", 1, 409), (None, None, 15001, 201)])
async def test_zero_limit_and_no_limit_have_different_meanings(
    bank_app, bank_client, limit, period, amount, status
):
    update_account(bank_app, 100, limit=limit, limit_period=period)
    before = database_snapshot(bank_app)
    response = await bank_client.post(
        f"{PREFIX}/transactions",
        json={"cender": 100, "recipient": 101, "amount": amount},
    )
    assert response.status_code == status, response.text
    if limit == 0:
        assert_error(response, 409, "LIMIT_EXCEEDED")
        assert database_snapshot(bank_app) == before


async def test_incoming_money_does_not_consume_destination_spending_limit(bank_client):
    for source, target, amount in ((100, 101, 2500), (101, 100, 5000)):
        response = await bank_client.post(
            f"{PREFIX}/transactions",
            json={"cender": source, "recipient": target, "amount": amount},
        )
        assert response.status_code == 201, response.text
    assert (await bank_client.get(f"{PREFIX}/accounts/101")).json()["balance"] == 7500


async def test_destination_balance_cannot_overflow_safe_json_integer(
    bank_app, bank_client
):
    update_account(bank_app, 101, balance=MAX_JS_INTEGER)
    before = database_snapshot(bank_app)
    response = await bank_client.post(
        f"{PREFIX}/transactions",
        json={"cender": 100, "recipient": 101, "amount": 1},
    )
    assert_error(response, 409, "BALANCE_OVERFLOW")
    assert database_snapshot(bank_app) == before


async def test_history_is_newest_first_with_bounded_pagination(bank_client):
    ids = []
    for amount in (100, 200, 300):
        response = await bank_client.post(
            f"{PREFIX}/transactions",
            json={"cender": 100, "recipient": 101, "amount": amount},
        )
        assert response.status_code == 201, response.text
        ids.append(response.json()["id"])
    history = await bank_client.get(f"{PREFIX}/accounts/100/transactions")
    assert [item["id"] for item in history.json()["items"]] == ids[::-1]
    page = await bank_client.get(f"{PREFIX}/accounts/100/transactions?limit=1&offset=1")
    assert page.status_code == 200
    assert [item["id"] for item in page.json()["items"]] == [ids[1]]
    for query in ("limit=0", "limit=101", "offset=-1"):
        response = await bank_client.get(f"{PREFIX}/accounts/100/transactions?{query}")
        assert_error(response, 422, "VALIDATION_ERROR")


async def test_restart_preserves_balances_history_and_used_daily_limit(tmp_path):
    settings = demo_settings(tmp_path / "restart.db")
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://testserver"
        ) as client:
            response = await client.post(
                f"{PREFIX}/transactions",
                json={"cender": 100, "recipient": 101, "amount": 14000},
            )
            assert response.status_code == 201, response.text
            transfer_id = response.json()["id"]

    restarted = create_app(settings)
    async with restarted.router.lifespan_context(restarted):
        async with AsyncClient(
            transport=ASGITransport(app=restarted), base_url="http://testserver"
        ) as client:
            account = (await client.get(f"{PREFIX}/accounts/100")).json()
            assert account["balance"] == 6000
            assert account["transactions_history"] == [transfer_id]
            history = (await client.get(f"{PREFIX}/accounts/101/transactions")).json()
            assert [item["id"] for item in history["items"]] == [transfer_id]
            before = database_snapshot(restarted)
            response = await client.post(
                f"{PREFIX}/transactions",
                json={"cender": 100, "recipient": 101, "amount": 1001},
            )
            assert_error(response, 409, "LIMIT_EXCEEDED")
            assert database_snapshot(restarted) == before


async def test_demo_user_header_selects_only_that_parents_accounts(bank_app, bank_client):
    add_other_parent(bank_app)
    headers = {"X-Demo-User-Id": "40"}
    response = await bank_client.get(f"{PREFIX}/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == 40
    accounts = await bank_client.get(f"{PREFIX}/accounts", headers=headers)
    assert [account["id"] for account in accounts.json()["items"]] == [200]
    response = await bank_client.get(f"{PREFIX}/accounts/100", headers=headers)
    assert_error(response, 403, "ACCESS_DENIED")


async def test_child_profile_cannot_use_parent_banking_api(bank_app, bank_client):
    with bank_app.state.session_factory() as session:
        session.add(User(id=30, login="demo-child", role="child"))
        session.commit()
    before = database_snapshot(bank_app)
    response = await bank_client.get(
        f"{PREFIX}/accounts", headers={"X-Demo-User-Id": "30"}
    )
    assert_error(response, 403, "ACCESS_DENIED")
    assert database_snapshot(bank_app) == before


async def test_demo_header_is_allowed_by_explicit_origin_cors(bank_client):
    origin = "http://localhost:5173"
    response = await bank_client.options(
        f"{PREFIX}/transactions",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, X-Demo-User-Id",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"
    allowed = response.headers["access-control-allow-headers"].lower()
    assert "x-demo-user-id" in allowed


@pytest.mark.parametrize(
    "period,before_boundary,after_boundary",
    [
        ("daily", "2026-10-20T20:59:00+00:00", "2026-10-20T21:00:00+00:00"),
        ("weekly", "2026-10-18T20:59:00+00:00", "2026-10-18T21:00:00+00:00"),
        ("monthly", "2026-10-31T20:59:00+00:00", "2026-10-31T21:00:00+00:00"),
    ],
)
async def test_spending_limit_renews_on_belarus_calendar_boundary(
    bank_app, bank_client, period, before_boundary, after_boundary
):
    # The service clock is injectable for this check; HTTP clients cannot set it.
    from app.services.banking import create_transfer

    update_account(bank_app, 100, limit=100, limit_period=period)
    command = TransferCreate(cender=100, recipient=101, amount=100)
    for timestamp in (before_boundary, after_boundary):
        with bank_app.state.session_factory() as session:
            created = create_transfer(
                session, 10, command, now=datetime.fromisoformat(timestamp)
            )
            assert created.amount == 100
    source = (await bank_client.get(f"{PREFIX}/accounts/100")).json()
    assert source["balance"] == 19800
    history = (await bank_client.get(f"{PREFIX}/accounts/100/transactions")).json()
    assert len(history["items"]) == 2
