"""Pig reserves, family contributions and parent-approved release of savings."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Barrier

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, func, select

from app.core.config import Settings
from app.main import create_app
from app.models import (
    Account,
    ChaildProfile,
    ChildAccountAccess,
    EcoFamily,
    FamilyAccount,
    FamilyMember,
    Pig,
    PigBreakRequest,
    PigState,
    Transaction,
    User,
)
from app.schemas.wire_models import MAX_JS_INTEGER


pytestmark = pytest.mark.anyio
PREFIX = "/api/v1"


@pytest.fixture
def anyio_backend():
    return "asyncio"


def settings_for(database_path):
    return Settings(
        _env_file=None,
        database_url=f"sqlite:///{database_path.as_posix()}",
        demo_mode=True,
        demo_user_id=10,
        cors_origins=["http://localhost:5173"],
    )


@pytest.fixture
async def pig_app(tmp_path):
    application = create_app(settings_for(tmp_path / "pigs.db"))
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def pig_client(pig_app):
    async with AsyncClient(
        transport=ASGITransport(app=pig_app), base_url="http://testserver"
    ) as client:
        yield client


def actor(user_id):
    return {"X-Demo-User-Id": str(user_id)}


def snapshot(application):
    """All money and approval state, so rejected commands cannot write partially."""
    with application.state.session_factory() as db:
        return (
            list(db.execute(select(Account.id, Account.balance).order_by(Account.id))),
            list(db.execute(select(Pig.id, Pig.name, Pig.current_balance).order_by(Pig.id))),
            list(db.execute(select(PigState.pig_id, PigState.closed).order_by(PigState.pig_id))),
            list(db.execute(select(
                PigBreakRequest.id,
                PigBreakRequest.pig_id,
                PigBreakRequest.status,
                PigBreakRequest.resolved_at,
            ).order_by(PigBreakRequest.id))),
            db.scalar(select(func.count()).select_from(Transaction)),
        )


def update_account(application, account_id, **values):
    with application.state.session_factory() as db, db.begin():
        account = db.get(Account, account_id)
        assert account is not None
        for name, value in values.items():
            setattr(account, name, value)


def add_second_child(application):
    with application.state.session_factory() as db, db.begin():
        db.add(User(id=21, login="other-child", role="child"))
        db.flush()
        db.add(FamilyMember(user_id=21, family_id=1))
        db.add(ChaildProfile(user_id=21, parent_id=10))
        db.add(Account(id=102, user_id=10, balance=5000, active=True,
                       limit=None, limit_period=None))
        db.flush()
        db.add(FamilyAccount(account_id=102, family_id=1))
        db.add(ChildAccountAccess(child_user_id=21, account_id=102))
        db.add(Pig(id=501, account_id=102, name="Другая копилка",
                   current_balance=1000, goal_balance=10000))
        db.flush()
        db.add(PigState(pig_id=501, child_user_id=21, closed=False))


def add_stranger_family(application):
    with application.state.session_factory() as db, db.begin():
        db.add(User(id=40, login="stranger-parent", role="parent"))
        db.flush()
        db.add(EcoFamily(id=2, name="Другая семья", user_admin_id=40))
        db.add(Account(id=400, user_id=40, balance=5000, active=True,
                       limit=None, limit_period=None))
        db.flush()
        db.add(FamilyMember(user_id=40, family_id=2))
        db.add(FamilyAccount(account_id=400, family_id=2))


def add_stranger_child(application):
    add_stranger_family(application)
    with application.state.session_factory() as db, db.begin():
        db.add(User(id=41, login="stranger-child", role="child"))
        db.flush()
        db.add(FamilyMember(user_id=41, family_id=2))
        db.add(ChaildProfile(user_id=41, parent_id=40))
        db.flush()
        db.add(ChildAccountAccess(child_user_id=41, account_id=400))
        db.add(Pig(id=600, account_id=400, name="Чужая семейная цель",
                   current_balance=1000, goal_balance=10000))
        db.flush()
        db.add(PigState(pig_id=600, child_user_id=41, closed=False))


async def account(client, account_id=101, user_id=10):
    response = await client.get(f"{PREFIX}/accounts/{account_id}", headers=actor(user_id))
    assert response.status_code == 200, response.text
    return response.json()


async def pig(client, pig_id=500, user_id=20):
    response = await client.get(f"{PREFIX}/pigs", headers=actor(user_id))
    assert response.status_code == 200, response.text
    return next(item for item in response.json()["items"] if item["id"] == pig_id)


async def request_break(client, pig_id=500, user_id=20):
    response = await client.post(
        f"{PREFIX}/pigs/{pig_id}/break-requests", json={}, headers=actor(user_id)
    )
    assert response.status_code == 201, response.text
    return response.json()


def assert_error(response, status):
    assert response.status_code == status, response.text
    assert set(response.json()) == {"error"}
    assert isinstance(response.json()["error"]["code"], str)


async def simultaneous_posts(application, commands):
    """Separate event loops/clients hit the same file database simultaneously."""
    ready = Barrier(len(commands))

    async def send(command):
        path, body, user_id = command
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://testserver"
        ) as client:
            return await client.post(PREFIX + path, json=body, headers=actor(user_id))

    def execute(command):
        ready.wait(timeout=10)
        return asyncio.run(send(command))

    def run_all():
        with ThreadPoolExecutor(max_workers=len(commands)) as executor:
            return list(executor.map(execute, commands))

    return await asyncio.to_thread(run_all)


async def test_seed_pig_shows_one_reserved_balance_and_assigned_parent(pig_client):
    saved = await pig(pig_client)
    assert set(saved) == {
        "id", "account_id", "name", "current_balance", "goal_balance",
        "child_user_id", "parent_id", "closed", "pending_request_id",
    }
    assert saved == {
        "id": 500, "account_id": 101, "name": "Велосипед",
        "current_balance": 3000, "goal_balance": 30000,
        "child_user_id": 20, "parent_id": 10,
        "closed": False, "pending_request_id": None,
    }
    owner_account = await account(pig_client)
    assert owner_account["user_id"] == 10
    assert owner_account["balance"] == 10000
    assert owner_account["active_balance"] == 7000


async def test_child_lists_only_own_pigs_and_cannot_request_siblings_pig(pig_app, pig_client):
    add_second_child(pig_app)
    listed = await pig_client.get(f"{PREFIX}/pigs", headers=actor(20))
    assert listed.status_code == 200, listed.text
    assert [item["id"] for item in listed.json()["items"]] == [500]
    before = snapshot(pig_app)
    denied = await pig_client.post(
        f"{PREFIX}/pigs/501/break-requests", json={}, headers=actor(20)
    )
    assert_error(denied, 403)
    assert snapshot(pig_app) == before


async def test_child_cannot_break_pig_directly(pig_app, pig_client):
    before = snapshot(pig_app)
    response = await pig_client.post(f"{PREFIX}/pigs/500/break", json={}, headers=actor(20))
    assert_error(response, 403)
    assert snapshot(pig_app) == before


async def test_break_request_is_pending_idempotent_and_does_not_release_money(pig_app, pig_client):
    original = await account(pig_client)
    first = await request_break(pig_client)
    duplicate = await request_break(pig_client)
    assert duplicate["id"] == first["id"]
    assert first["pig_id"] == 500
    assert first["child_user_id"] == 20
    assert first["parent_id"] == 10
    assert first["status"] == "pending"
    assert first["resolved_at"] is None
    assert datetime.fromisoformat(first["created_at"].replace("Z", "+00:00")).utcoffset() is not None
    assert await account(pig_client) == original
    assert (await pig(pig_client))["current_balance"] == 3000
    assert (await pig(pig_client))["pending_request_id"] == first["id"]
    with pig_app.state.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(PigBreakRequest)) == 1


async def test_only_assigned_parent_sees_and_approves_request(pig_app, pig_client):
    pending = await request_break(pig_client)
    for user_id in (10, 20):
        response = await pig_client.get(f"{PREFIX}/pig-break-requests", headers=actor(user_id))
        assert response.status_code == 200, response.text
        assert [item["id"] for item in response.json()["items"]] == [pending["id"]]
    other_parent = await pig_client.get(f"{PREFIX}/pig-break-requests", headers=actor(11))
    assert other_parent.status_code == 200, other_parent.text
    assert other_parent.json() == {"items": []}
    before = snapshot(pig_app)
    for user_id in (11, 20):
        denied = await pig_client.post(
            f"{PREFIX}/pig-break-requests/{pending['id']}/approve", json={}, headers=actor(user_id)
        )
        assert_error(denied, 403)
    assert snapshot(pig_app) == before


async def test_approval_releases_only_reserve_and_preserves_owner_balance(pig_app, pig_client):
    pending = await request_break(pig_client)
    approved = await pig_client.post(
        f"{PREFIX}/pig-break-requests/{pending['id']}/approve", json={}, headers=actor(10)
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert approved.json()["resolved_at"] is not None
    result = await account(pig_client)
    assert result["balance"] == result["active_balance"] == 10000
    assert result["transactions_history"] == []
    closed = await pig(pig_client)
    assert closed["closed"] is True
    assert closed["current_balance"] == 0
    assert closed["pending_request_id"] is None
    after = snapshot(pig_app)
    repeated = await pig_client.post(
        f"{PREFIX}/pig-break-requests/{pending['id']}/approve", json={}, headers=actor(10)
    )
    assert repeated.status_code in (200, 409), repeated.text
    assert snapshot(pig_app) == after


async def test_rejection_keeps_savings_and_child_can_make_new_request(pig_client):
    first = await request_break(pig_client)
    denied_parent = await pig_client.post(
        f"{PREFIX}/pig-break-requests/{first['id']}/reject", json={}, headers=actor(11)
    )
    assert_error(denied_parent, 403)
    response = await pig_client.post(
        f"{PREFIX}/pig-break-requests/{first['id']}/reject", json={}, headers=actor(10)
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "rejected"
    assert response.json()["resolved_at"] is not None
    saved = await pig(pig_client)
    assert saved["closed"] is False
    assert saved["current_balance"] == 3000
    assert saved["pending_request_id"] is None
    assert (await account(pig_client))["active_balance"] == 7000
    second = await request_break(pig_client)
    assert second["id"] != first["id"]


async def test_assigned_parent_can_break_directly_but_other_parent_cannot(pig_app, pig_client):
    before = snapshot(pig_app)
    denied = await pig_client.post(f"{PREFIX}/pigs/500/break", json={}, headers=actor(11))
    assert_error(denied, 403)
    assert snapshot(pig_app) == before
    response = await pig_client.post(f"{PREFIX}/pigs/500/break", json={}, headers=actor(10))
    assert response.status_code == 200, response.text
    assert response.json()["closed"] is True
    result = await account(pig_client)
    assert result["balance"] == result["active_balance"] == 10000


async def test_direct_parent_break_also_approves_existing_child_request(pig_client):
    pending = await request_break(pig_client)
    response = await pig_client.post(f"{PREFIX}/pigs/500/break", json={}, headers=actor(10))
    assert response.status_code == 200, response.text
    requests = (await pig_client.get(f"{PREFIX}/pig-break-requests", headers=actor(20))).json()["items"]
    assert requests[0]["id"] == pending["id"]
    assert requests[0]["status"] == "approved"
    assert (await account(pig_client))["balance"] == 10000


async def test_family_member_contribution_moves_money_to_owner_and_reserves_it(pig_client):
    response = await pig_client.post(
        f"{PREFIX}/pigs/500/contributions", json={"account_id": 110, "amount": 1250},
        headers=actor(11),
    )
    assert response.status_code == 200, response.text
    assert response.json()["current_balance"] == 4250
    source = await account(pig_client, 110, 11)
    destination = await account(pig_client)
    assert source["balance"] == source["active_balance"] == 13750
    assert destination["balance"] == 11250
    assert destination["active_balance"] == 7000
    assert len(source["transactions_history"]) == 1
    assert source["transactions_history"] == destination["transactions_history"]
    history = await pig_client.get(f"{PREFIX}/accounts/110/transactions", headers=actor(11))
    assert history.status_code == 200, history.text
    transfer = history.json()["items"][0]
    assert (transfer["cender"], transfer["recipient"], transfer["amount"]) == (110, 101, 1250)


async def test_same_account_contribution_only_reserves_money_without_transfer(pig_client):
    response = await pig_client.post(
        f"{PREFIX}/pigs/500/contributions", json={"account_id": 101, "amount": 500},
        headers=actor(10),
    )
    assert response.status_code == 200, response.text
    assert response.json()["current_balance"] == 3500
    result = await account(pig_client)
    assert result["balance"] == 10000
    assert result["active_balance"] == 6500
    assert result["transactions_history"] == []


async def test_child_can_contribute_from_explicitly_assigned_account(pig_client):
    response = await pig_client.post(
        f"{PREFIX}/pigs/500/contributions", json={"account_id": 101, "amount": 500},
        headers=actor(20),
    )
    assert response.status_code == 200, response.text
    assert response.json()["current_balance"] == 3500
    assert (await account(pig_client))["balance"] == 10000


async def test_child_can_contribute_to_hidden_family_pig_without_reading_its_details(
    pig_app, pig_client
):
    add_second_child(pig_app)
    listed = await pig_client.get(f"{PREFIX}/pigs", headers=actor(20))
    assert listed.status_code == 200, listed.text
    assert [item["id"] for item in listed.json()["items"]] == [500]

    contributed = await pig_client.post(
        f"{PREFIX}/pigs/501/contributions", headers=actor(20),
        json={"account_id": 101, "amount": 500},
    )
    assert contributed.status_code == 200, contributed.text
    assert contributed.json() == {"pig_id": 501, "amount": 500}
    assert (await pig(pig_client, 501, 21))["current_balance"] == 1500
    source = await account(pig_client, 101)
    destination = await account(pig_client, 102)
    assert source["balance"] == 9500
    assert source["active_balance"] == 6500
    assert destination["balance"] == 5500
    assert destination["active_balance"] == 4000
    assert len(source["transactions_history"]) == 1
    assert source["transactions_history"] == destination["transactions_history"]
    listed_after = await pig_client.get(f"{PREFIX}/pigs", headers=actor(20))
    assert [item["id"] for item in listed_after.json()["items"]] == [500]

    add_stranger_child(pig_app)
    before = snapshot(pig_app)
    for user_id, pig_id, source_id in ((20, 600, 101), (41, 500, 400)):
        denied = await pig_client.post(
            f"{PREFIX}/pigs/{pig_id}/contributions", headers=actor(user_id),
            json={"account_id": source_id, "amount": 500},
        )
        assert_error(denied, 403)
    assert snapshot(pig_app) == before


async def test_family_members_cannot_spend_someone_elses_source_account(pig_app, pig_client):
    before = snapshot(pig_app)
    response = await pig_client.post(
        f"{PREFIX}/pigs/500/contributions", json={"account_id": 100, "amount": 500},
        headers=actor(11),
    )
    assert_error(response, 403)
    assert snapshot(pig_app) == before


async def test_stranger_family_cannot_contribute_even_from_owned_account(pig_app, pig_client):
    add_stranger_family(pig_app)
    before = snapshot(pig_app)
    response = await pig_client.post(
        f"{PREFIX}/pigs/500/contributions", json={"account_id": 400, "amount": 500},
        headers=actor(40),
    )
    assert_error(response, 403)
    assert snapshot(pig_app) == before


async def test_contribution_cannot_spend_existing_pig_reserve(pig_app, pig_client):
    update_account(pig_app, 101, limit=None, limit_period=None)
    before = snapshot(pig_app)
    response = await pig_client.post(
        f"{PREFIX}/pigs/500/contributions", json={"account_id": 101, "amount": 7001},
        headers=actor(10),
    )
    assert_error(response, 409)
    assert snapshot(pig_app) == before


@pytest.mark.parametrize("frozen_account", [110, 101])
async def test_freeze_on_source_or_owner_blocks_contribution(pig_app, pig_client, frozen_account):
    update_account(pig_app, frozen_account, active=False)
    before = snapshot(pig_app)
    response = await pig_client.post(
        f"{PREFIX}/pigs/500/contributions", json={"account_id": 110, "amount": 500},
        headers=actor(11),
    )
    assert_error(response, 409)
    assert snapshot(pig_app) == before


async def test_closed_pig_cannot_receive_money_or_get_new_break_request(pig_app, pig_client):
    response = await pig_client.post(f"{PREFIX}/pigs/500/break", json={}, headers=actor(10))
    assert response.status_code == 200, response.text
    before = snapshot(pig_app)
    response = await pig_client.post(
        f"{PREFIX}/pigs/500/contributions", json={"account_id": 110, "amount": 500},
        headers=actor(11),
    )
    assert_error(response, 409)
    request = await pig_client.post(
        f"{PREFIX}/pigs/500/break-requests", json={}, headers=actor(20)
    )
    assert_error(request, 409)
    assert snapshot(pig_app) == before


async def test_own_child_and_assigned_parent_can_rename_other_parent_cannot(pig_app, pig_client):
    for user_id, name in ((20, "  На велосипед  "), (10, "Летняя поездка")):
        response = await pig_client.patch(
            f"{PREFIX}/pigs/500", json={"name": name}, headers=actor(user_id)
        )
        assert response.status_code == 200, response.text
        assert response.json()["name"] == name.strip()
    before = snapshot(pig_app)
    response = await pig_client.patch(
        f"{PREFIX}/pigs/500", json={"name": "Чужое имя"}, headers=actor(11)
    )
    assert_error(response, 403)
    assert snapshot(pig_app) == before


async def test_create_pig_trims_name_and_starts_without_reserved_money(pig_client):
    response = await pig_client.post(
        f"{PREFIX}/pigs", headers=actor(10), json={
            "account_id": 101, "child_user_id": 20,
            "name": "  Путешествие  ", "goal_balance": 50000,
        },
    )
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["id"] != 500
    assert created["name"] == "Путешествие"
    assert created["current_balance"] == 0
    assert created["goal_balance"] == 50000
    assert created["child_user_id"] == 20
    assert created["parent_id"] == 10
    assert created["closed"] is False
    assert (await account(pig_client))["active_balance"] == 7000


@pytest.mark.parametrize("name", ["", "   ", "x" * 101, None, 123])
async def test_empty_overlong_and_non_string_pig_names_are_rejected(pig_app, pig_client, name):
    before = snapshot(pig_app)
    response = await pig_client.post(
        f"{PREFIX}/pigs", headers=actor(10), json={
            "account_id": 101, "child_user_id": 20,
            "name": name, "goal_balance": 10000,
        },
    )
    assert_error(response, 422)
    rename = await pig_client.patch(
        f"{PREFIX}/pigs/500", headers=actor(20), json={"name": name}
    )
    assert_error(rename, 422)
    assert snapshot(pig_app) == before


@pytest.mark.parametrize("amount", [True, "100", 1.5, 0, -1, MAX_JS_INTEGER + 1])
async def test_money_inputs_are_positive_strict_safe_integers(pig_app, pig_client, amount):
    before = snapshot(pig_app)
    contribution = await pig_client.post(
        f"{PREFIX}/pigs/500/contributions", headers=actor(10),
        json={"account_id": 101, "amount": amount},
    )
    assert_error(contribution, 422)
    creation = await pig_client.post(
        f"{PREFIX}/pigs", headers=actor(10), json={
            "account_id": 101, "child_user_id": 20,
            "name": "Новая цель", "goal_balance": amount,
        },
    )
    assert_error(creation, 422)
    assert snapshot(pig_app) == before


async def test_client_cannot_set_reserve_or_approval_fields(pig_app, pig_client):
    before = snapshot(pig_app)
    response = await pig_client.patch(f"{PREFIX}/pigs/500", headers=actor(20), json={
        "name": "Попытка подмены", "current_balance": 0,
        "closed": True, "parent_id": 20,
    })
    assert_error(response, 422)
    assert snapshot(pig_app) == before


async def test_restart_preserves_closed_pig_and_does_not_restore_seed_reserve(tmp_path):
    settings = settings_for(tmp_path / "restart-pigs.db")
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://testserver"
        ) as client:
            pending = await request_break(client)
            approved = await client.post(
                f"{PREFIX}/pig-break-requests/{pending['id']}/approve", json={}, headers=actor(10)
            )
            assert approved.status_code == 200, approved.text
    restarted = create_app(settings)
    async with restarted.router.lifespan_context(restarted):
        async with AsyncClient(
            transport=ASGITransport(app=restarted), base_url="http://testserver"
        ) as client:
            saved = await pig(client)
            assert saved["closed"] is True
            assert saved["current_balance"] == 0
            result = await account(client)
            assert result["balance"] == result["active_balance"] == 10000
            requests = await client.get(f"{PREFIX}/pig-break-requests", headers=actor(10))
            assert [item["status"] for item in requests.json()["items"]] == ["approved"]


async def test_simultaneous_approvals_cannot_release_savings_twice(pig_app, pig_client):
    pending = await request_break(pig_client)
    command = (f"/pig-break-requests/{pending['id']}/approve", {}, 10)
    responses = await simultaneous_posts(pig_app, [command, command])
    assert any(response.status_code == 200 for response in responses)
    assert all(response.status_code in (200, 409) for response in responses)
    result = await account(pig_client)
    assert result["balance"] == result["active_balance"] == 10000
    assert result["transactions_history"] == []
    saved = await pig(pig_client)
    assert saved["closed"] is True
    assert saved["current_balance"] == 0
    with pig_app.state.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(PigBreakRequest)) == 1
        assert db.get(PigBreakRequest, pending["id"]).status == "approved"


@pytest.mark.parametrize("spending_limit,amount", [(None, 8000), (10000, 6000)])
async def test_simultaneous_contributions_cannot_exceed_source_funds_or_limit(
    pig_app, pig_client, spending_limit, amount
):
    update_account(pig_app, 110, limit=spending_limit,
                   limit_period="daily" if spending_limit is not None else None)
    command = ("/pigs/500/contributions", {"account_id": 110, "amount": amount}, 11)
    responses = await simultaneous_posts(pig_app, [command, command])
    assert sorted(response.status_code for response in responses) == [200, 409]
    source = await account(pig_client, 110, 11)
    destination = await account(pig_client)
    saved = await pig(pig_client)
    assert source["balance"] == 15000 - amount
    assert destination["balance"] == 10000 + amount
    assert destination["active_balance"] == 7000
    assert saved["current_balance"] == 3000 + amount
    assert len(source["transactions_history"]) == 1


async def test_simultaneous_family_credits_do_not_lose_money_or_reserve(pig_app, pig_client):
    responses = await simultaneous_posts(pig_app, [
        ("/pigs/500/contributions", {"account_id": 100, "amount": 1000}, 10),
        ("/pigs/500/contributions", {"account_id": 110, "amount": 1000}, 11),
    ])
    assert all(response.status_code == 200 for response in responses)
    assert (await account(pig_client, 100))["balance"] == 19000
    assert (await account(pig_client, 110, 11))["balance"] == 14000
    destination = await account(pig_client)
    assert destination["balance"] == 12000
    assert destination["active_balance"] == 7000
    assert len(destination["transactions_history"]) == 2
    assert (await pig(pig_client))["current_balance"] == 5000


async def test_storage_failure_rolls_back_contribution_balances_reserve_and_history(
    pig_app, pig_client
):
    before = snapshot(pig_app)
    engine = pig_app.state.db_engine

    def fail_after_transfer_insert(_connection, _cursor, _statement, _parameters, context, _many):
        statement = context.compiled.statement if context.compiled is not None else None
        if getattr(statement, "is_insert", False) and statement.table.name == "transactions":
            raise RuntimeError("simulated contribution storage failure")

    event.listen(engine, "after_cursor_execute", fail_after_transfer_insert)
    try:
        with pytest.raises(RuntimeError, match="simulated contribution storage failure"):
            await pig_client.post(
                f"{PREFIX}/pigs/500/contributions", headers=actor(11),
                json={"account_id": 110, "amount": 1250},
            )
    finally:
        event.remove(engine, "after_cursor_execute", fail_after_transfer_insert)
    assert snapshot(pig_app) == before
