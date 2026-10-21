"""Small banking demo: own accounts, atomic transfers, and transfer history."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models import Account, PigState, Transaction, User
from app.schemas.wire_models import (
    MAX_JS_INTEGER, AccountRead, PigRead, TransactionRead, TransferCreate,
    UserRead, account_response,
)
from app.services.family_access import (
    actor, child_profile, family_id, readable_account, visible_account_ids,
)

UTC = timezone.utc
DEMO_TIMEZONE = timezone(timedelta(hours=3))


def _actor(db: Session, actor_id: int) -> User:
    user = db.get(User, actor_id)
    if user is None:
        raise ApiError(401, "DEMO_USER_NOT_FOUND", "Демо-пользователь не найден")
    if user.role != "parent":
        raise ApiError(403, "ACCESS_DENIED", "На этом этапе доступны только счета родителя")
    return user


def _own_account(db: Session, actor_id: int, account_id: int) -> Account:
    account = db.get(Account, account_id)
    if account is None:
        raise ApiError(404, "NOT_FOUND", "Счёт не найден")
    if account.user_id != actor_id:
        raise ApiError(403, "ACCESS_DENIED", "Нет доступа к этому счёту")
    return account


def _transaction_response(transaction: Transaction) -> TransactionRead:
    timestamp = transaction.data
    # SQLite drops timezone information. Every stored timestamp originates in UTC.
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return TransactionRead(id=transaction.id, cender=transaction.cender,
                           recipient=transaction.recipient, amount=transaction.amount,
                           data=timestamp.astimezone(UTC))


def _account_response(db: Session, account: Account) -> AccountRead:
    history = list(db.scalars(select(Transaction.id).where(or_(
        Transaction.cender == account.id, Transaction.recipient == account.id,
    )).order_by(Transaction.data.desc(), Transaction.id.desc())))
    pigs = [PigRead(id=p.id, account_id=p.account_id, name=p.name,
                    current_balance=p.current_balance, goal_balance=p.goal_balance)
            for p in account.pigs]
    return account_response({
        "id": account.id, "user_id": account.user_id, "balance": account.balance,
        "active": account.active, "transactions_history": history,
        "limit": account.limit, "limit_period": account.limit_period,
    }, pigs)


def get_me(db: Session, actor_id: int) -> UserRead:
    user = actor(db, actor_id)
    accounts = visible_account_ids(db, user)
    return UserRead(id=user.id, login=user.login, role=user.role, accounts=accounts,
                    ECOfamily_id=family_id(db, user.id), newses_id=[], test_id=[], auto_transaction=[])


def list_accounts(db: Session, actor_id: int) -> list[AccountRead]:
    user = actor(db, actor_id)
    return [get_account(db, actor_id, account_id) for account_id in visible_account_ids(db, user)]


def get_account(db: Session, actor_id: int, account_id: int) -> AccountRead:
    user = actor(db, actor_id)
    result = _account_response(db, readable_account(db, user, account_id))
    if user.role == "child":
        # The available balance includes every reserve; the pig ID list exposes only this child's pigs.
        result.pigs = list(db.scalars(select(PigState.pig_id).where(
            PigState.child_user_id == user.id, PigState.pig_id.in_(result.pigs),
        ).order_by(PigState.pig_id)))
        if not child_profile(db, user.id).agree_history:
            result.transactions_history = []
    return result


def get_history(db: Session, actor_id: int, account_id: int,
                limit: int = 50, offset: int = 0) -> list[TransactionRead]:
    user = actor(db, actor_id)
    readable_account(db, user, account_id, history=True)
    rows = db.scalars(select(Transaction).where(or_(
        Transaction.cender == account_id, Transaction.recipient == account_id,
    )).order_by(Transaction.data.desc(), Transaction.id.desc()).offset(offset).limit(limit))
    return [_transaction_response(row) for row in rows]


def period_window(period: str, now: datetime) -> tuple[datetime, datetime]:
    """Calendar limits use the explicitly chosen fixed UTC+03 demo timezone."""
    local_day = now.astimezone(DEMO_TIMEZONE).replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "daily":
        start, end = local_day, local_day + timedelta(days=1)
    elif period == "weekly":
        start = local_day - timedelta(days=local_day.weekday())
        end = start + timedelta(days=7)
    elif period == "monthly":
        start = local_day.replace(day=1)
        end = (start.replace(year=start.year + 1, month=1) if start.month == 12
               else start.replace(month=start.month + 1))
    else:
        raise ValueError("Unsupported account limit period")
    return start.astimezone(UTC), end.astimezone(UTC)


def create_transfer(db: Session, actor_id: int, command: TransferCreate, *,
                    now: datetime | None = None) -> TransactionRead:
    """Debit, credit and history commit together, after locking both accounts."""
    if now is not None and (now.tzinfo is None or now.utcoffset() is None):
        raise ValueError("now must include a timezone")
    try:
        with db.begin():
            if db.get_bind().dialect.name == "sqlite":
                # Acquire the writer lock BEFORE reads; SELECT FOR UPDATE is ignored by SQLite.
                db.execute(text("BEGIN IMMEDIATE"))
            _actor(db, actor_id)
            rows = db.scalars(select(Account).where(Account.id.in_(
                [command.cender, command.recipient],
            )).order_by(Account.id).with_for_update()).all()
            accounts = {row.id: row for row in rows}
            if len(accounts) != 2:
                raise ApiError(404, "NOT_FOUND", "Счёт не найден")
            source, recipient = accounts[command.cender], accounts[command.recipient]
            if source.user_id != actor_id or recipient.user_id != actor_id:
                raise ApiError(403, "ACCESS_DENIED", "Разрешены переводы только между своими счетами")
            if not source.active or not recipient.active:
                raise ApiError(409, "ACCOUNT_FROZEN", "Один из счетов заморожен")
            reserved = sum(pig.current_balance for pig in source.pigs)
            if command.amount > source.balance - reserved:
                raise ApiError(409, "INSUFFICIENT_FUNDS", "Недостаточно доступных средств")
            if recipient.balance > MAX_JS_INTEGER - command.amount:
                raise ApiError(409, "BALANCE_OVERFLOW", "Превышен допустимый остаток счёта")
            timestamp = datetime.now(UTC) if now is None else now.astimezone(UTC)
            if source.limit is not None:
                start, end = period_window(source.limit_period, timestamp)
                used = db.scalar(select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                    Transaction.cender == source.id, Transaction.data >= start, Transaction.data < end,
                ))
                if command.amount > source.limit - used:
                    raise ApiError(409, "LIMIT_EXCEEDED", "Превышен лимит переводов за период")
            source.balance -= command.amount
            recipient.balance += command.amount
            transaction = Transaction(cender=source.id, recipient=recipient.id,
                                      amount=command.amount, data=timestamp)
            db.add(transaction)
            db.flush()
            result = _transaction_response(transaction)
        return result
    except OperationalError as exc:
        if db.get_bind().dialect.name == "sqlite" and "locked" in str(exc.orig).lower():
            raise ApiError(503, "DATABASE_BUSY", "Сервер занят, проверьте историю перед повтором") from exc
        raise
