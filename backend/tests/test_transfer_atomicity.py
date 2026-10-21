"""Money must remain consistent across simultaneous requests and storage faults."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.orm import sessionmaker

from app.core.errors import ApiError
from app.db.demo import initialize_demo_database
from app.db.session import create_db_engine
from app.models import Account, Transaction
from app.schemas.wire_models import TransferCreate
from app.services.banking import create_transfer


@pytest.fixture
def bank(tmp_path):
    engine = create_db_engine(f"sqlite:///{(tmp_path / 'atomicity.db').as_posix()}")
    initialize_demo_database(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    try:
        yield engine, factory
    finally:
        engine.dispose()


def snapshot(factory):
    with factory() as db:
        return dict(db.execute(select(Account.id, Account.balance)).all()), db.scalar(
            select(func.count()).select_from(Transaction)
        )


def simultaneous(factory, commands):
    ready = Barrier(len(commands))

    def execute(command):
        with factory() as db:
            ready.wait(timeout=10)
            try:
                return create_transfer(db, 10, TransferCreate(**command))
            except ApiError as exc:
                return exc.code

    with ThreadPoolExecutor(max_workers=len(commands)) as executor:
        return list(executor.map(execute, commands))


def test_concurrent_transfers_cannot_spend_the_same_money_twice(bank):
    _, factory = bank
    with factory() as db, db.begin():
        account = db.get(Account, 100)
        account.limit, account.limit_period = None, None
    result = simultaneous(factory, [
        {"cender": 100, "recipient": 101, "amount": 11000},
        {"cender": 100, "recipient": 101, "amount": 11000},
    ])
    assert sum(not isinstance(item, str) for item in result) == 1
    assert "INSUFFICIENT_FUNDS" in result
    assert snapshot(factory) == ({100: 9000, 101: 21000, 110: 15000}, 1)


def test_concurrent_transfers_cannot_exceed_the_combined_period_limit(bank):
    _, factory = bank
    result = simultaneous(factory, [
        {"cender": 100, "recipient": 101, "amount": 8000},
        {"cender": 100, "recipient": 101, "amount": 8000},
    ])
    assert sum(not isinstance(item, str) for item in result) == 1
    assert "LIMIT_EXCEEDED" in result
    assert snapshot(factory) == ({100: 12000, 101: 18000, 110: 15000}, 1)


def test_concurrent_credits_to_same_account_are_not_lost(bank):
    _, factory = bank
    with factory() as db, db.begin():
        db.add(Account(id=102, user_id=10, balance=5000, active=True,
                       limit=None, limit_period=None))
    result = simultaneous(factory, [
        {"cender": 100, "recipient": 101, "amount": 1000},
        {"cender": 102, "recipient": 101, "amount": 1000},
    ])
    assert all(not isinstance(item, str) for item in result)
    assert snapshot(factory) == ({100: 19000, 101: 12000, 102: 4000, 110: 15000}, 2)


def test_storage_failure_rolls_back_both_balances_and_history(bank):
    engine, factory = bank
    before = snapshot(factory)

    def fail_after_history_insert(_connection, _cursor, _statement, _parameters, context, _many):
        statement = context.compiled.statement if context.compiled is not None else None
        if getattr(statement, "is_insert", False) and statement.table.name == "transactions":
            raise RuntimeError("simulated storage failure")

    event.listen(engine, "after_cursor_execute", fail_after_history_insert)
    try:
        with factory() as db, pytest.raises(RuntimeError, match="simulated storage failure"):
            create_transfer(db, 10, TransferCreate(cender=100, recipient=101, amount=2500))
    finally:
        event.remove(engine, "after_cursor_execute", fail_after_history_insert)
    assert snapshot(factory) == before
