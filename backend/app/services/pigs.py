"""Reserved piggy-bank funds and parent-approved closing, in atomic transactions."""

from contextlib import contextmanager
from datetime import UTC, datetime

from sqlalchemy import func, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models import (
    Account, ChaildProfile, FamilyAccount, FamilyMember,
    Pig, PigBreakRequest, PigState, Transaction, User,
)
from app.schemas.pigs import (
    FamilyMemberView, PigContribution, PigContributionReceipt, PigCreate, PigRename, PigView, RequestView,
)
from app.schemas.wire_models import MAX_JS_INTEGER
from app.services.banking import period_window
from app.services.family_access import (
    actor, child_account_allowed, child_profile, family_id, readable_account,
    require_same_family, visible_account_ids,
)


@contextmanager
def _write(db: Session):
    try:
        with db.begin():
            if db.get_bind().dialect.name == "sqlite":
                db.execute(text("BEGIN IMMEDIATE"))
            yield
    except OperationalError as exc:
        if db.get_bind().dialect.name == "sqlite" and "locked" in str(exc.orig).lower():
            raise ApiError(503, "DATABASE_BUSY", "Сервер занят, проверьте состояние перед повтором") from exc
        raise


def _lock_accounts(db: Session, *account_ids: int) -> dict[int, Account]:
    rows = db.scalars(select(Account).where(Account.id.in_(set(account_ids)))
                      .order_by(Account.id).with_for_update()).all()
    accounts = {account.id: account for account in rows}
    if len(accounts) != len(set(account_ids)):
        raise ApiError(404, "NOT_FOUND", "Счёт не найден")
    return accounts


def _pig(db: Session, pig_id: int, *, lock: bool = False) -> tuple[Pig, PigState, ChaildProfile]:
    statement = select(Pig, PigState).join(PigState, PigState.pig_id == Pig.id).where(Pig.id == pig_id)
    if lock:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    row = db.execute(statement).one_or_none()
    if row is None:
        raise ApiError(404, "NOT_FOUND", "Копилка не найдена")
    pig, state = row
    profile = child_profile(db, state.child_user_id)
    return pig, state, profile


def _check_family_pig(db: Session, user: User, pig: Pig, state: PigState) -> None:
    require_same_family(db, user.id, state.child_user_id)
    account = db.get(Account, pig.account_id)
    if account is None or not child_account_allowed(db, state.child_user_id, account):
        raise ApiError(403, "ACCESS_DENIED", "Счёт копилки не подключён к ребёнку и экосемье")


def _check_visible(db: Session, user: User, pig: Pig, state: PigState) -> None:
    _check_family_pig(db, user, pig, state)
    if user.role == "child" and state.child_user_id != user.id:
        raise ApiError(403, "ACCESS_DENIED", "Доступны только свои копилки")


def _check_manager(user: User, state: PigState, profile: ChaildProfile) -> None:
    if user.id not in (state.child_user_id, profile.parent_id):
        raise ApiError(403, "ACCESS_DENIED", "Изменять копилку могут ребёнок и его parent_id")


def _check_parent(user: User, profile: ChaildProfile) -> None:
    if user.role != "parent" or user.id != profile.parent_id:
        raise ApiError(403, "ACCESS_DENIED", "Разбить копилку может только назначенный parent_id")
    if not profile.agree_pig:
        raise ApiError(403, "ACCESS_DENIED", "Разрешение на разбитие копилки отключено")


def _open(state: PigState) -> None:
    if state.closed:
        raise ApiError(409, "PIG_CLOSED", "Копилка уже разбита")


def _active(*accounts: Account) -> None:
    if any(not account.active for account in accounts):
        raise ApiError(409, "ACCOUNT_FROZEN", "Один из счетов заморожен")


def _reserve(db: Session, account_id: int) -> int:
    return db.scalar(select(func.coalesce(func.sum(Pig.current_balance), 0)).where(Pig.account_id == account_id))


def _consistent_reserve(db: Session, account: Account) -> int:
    reserved = _reserve(db, account.id)
    if reserved > account.balance:
        raise ApiError(409, "INVALID_RESERVE", "Резерв копилок превышает остаток счёта")
    return reserved


def _view(db: Session, pig: Pig, state: PigState, profile: ChaildProfile) -> PigView:
    pending = db.scalar(select(PigBreakRequest.id).where(
        PigBreakRequest.pig_id == pig.id, PigBreakRequest.status == "pending",
    ).order_by(PigBreakRequest.id))
    return PigView(id=pig.id, account_id=pig.account_id, name=pig.name,
                   current_balance=pig.current_balance, goal_balance=pig.goal_balance,
                   child_user_id=state.child_user_id, parent_id=profile.parent_id,
                   closed=state.closed, pending_request_id=pending)


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _request_view(request: PigBreakRequest) -> RequestView:
    return RequestView(id=request.id, pig_id=request.pig_id,
                       child_user_id=request.child_user_id, parent_id=request.parent_id,
                       status=request.status, created_at=_utc(request.created_at),
                       resolved_at=_utc(request.resolved_at))


def list_pigs(db: Session, actor_id: int) -> list[PigView]:
    user = actor(db, actor_id)
    family = family_id(db, user.id)
    if family is None:
        return []
    statement = (select(Pig.id).join(PigState, PigState.pig_id == Pig.id)
                 .join(FamilyMember, FamilyMember.user_id == PigState.child_user_id)
                 .where(FamilyMember.family_id == family).order_by(Pig.id))
    if user.role == "child":
        statement = statement.where(PigState.child_user_id == user.id)
    result = []
    for pig_id in db.scalars(statement):
        pig, state, profile = _pig(db, pig_id)
        _check_visible(db, user, pig, state)
        result.append(_view(db, pig, state, profile))
    return result


def create_pig(db: Session, actor_id: int, command: PigCreate) -> PigView:
    with _write(db):
        user = actor(db, actor_id)
        profile = child_profile(db, command.child_user_id)
        require_same_family(db, user.id, profile.user_id)
        if user.id not in (profile.user_id, profile.parent_id):
            raise ApiError(403, "ACCESS_DENIED", "Создать копилку могут ребёнок и его parent_id")
        account = _lock_accounts(db, command.account_id)[command.account_id]
        if not child_account_allowed(db, profile.user_id, account):
            raise ApiError(403, "ACCESS_DENIED", "Счёт не подключён к ребёнку")
        _active(account)
        _consistent_reserve(db, account)
        pig = Pig(account_id=account.id, name=command.name, current_balance=0,
                  goal_balance=command.goal_balance)
        db.add(pig)
        db.flush()
        state = PigState(pig_id=pig.id, child_user_id=profile.user_id, closed=False)
        db.add(state)
        db.flush()
        result = _view(db, pig, state, profile)
    return result


def rename_pig(db: Session, actor_id: int, pig_id: int, command: PigRename) -> PigView:
    with _write(db):
        user = actor(db, actor_id)
        pig, state, profile = _pig(db, pig_id, lock=True)
        _check_visible(db, user, pig, state)
        _check_manager(user, state, profile)
        _open(state)
        pig.name = command.name
        db.flush()
        result = _view(db, pig, state, profile)
    return result


def contribute(db: Session, actor_id: int, pig_id: int, command: PigContribution, *,
               now: datetime | None = None) -> PigView | PigContributionReceipt:
    if now is not None and (now.tzinfo is None or now.utcoffset() is None):
        raise ValueError("now must include a timezone")
    with _write(db):
        user = actor(db, actor_id)
        initial, _, _ = _pig(db, pig_id)
        accounts = _lock_accounts(db, command.account_id, initial.account_id)
        pig, state, profile = _pig(db, pig_id, lock=True)
        _check_family_pig(db, user, pig, state)
        _open(state)
        source, target = accounts[command.account_id], accounts[pig.account_id]
        # Family visibility never grants debit access to another member's account.
        readable_account(db, user, source.id)
        family = require_same_family(db, user.id, state.child_user_id, source.user_id)
        source_link = db.get(FamilyAccount, source.id)
        target_link = db.get(FamilyAccount, target.id)
        if (source_link is None or target_link is None
                or source_link.family_id != family or target_link.family_id != family):
            raise ApiError(403, "ACCESS_DENIED", "Оба счёта должны быть явно подключены к экосемье")
        if user.role == "child" and not child_profile(db, user.id).agree_transaction:
            raise ApiError(403, "ACCESS_DENIED", "Переводы отключены родителем")
        _active(source, target)
        source_reserved = _consistent_reserve(db, source)
        _consistent_reserve(db, target)
        if command.amount > source.balance - source_reserved:
            raise ApiError(409, "INSUFFICIENT_FUNDS", "Недостаточно доступных средств")
        if pig.current_balance > MAX_JS_INTEGER - command.amount:
            raise ApiError(409, "BALANCE_OVERFLOW", "Превышен допустимый остаток копилки")
        if source.id != target.id:
            if target.balance > MAX_JS_INTEGER - command.amount:
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
            target.balance += command.amount
            db.add(Transaction(cender=source.id, recipient=target.id, amount=command.amount, data=timestamp))
        # Reserving funds inside the same account changes no bank balance/history/transfer limit.
        pig.current_balance += command.amount
        db.flush()
        _consistent_reserve(db, source)
        _consistent_reserve(db, target)
        result = (PigContributionReceipt(pig_id=pig.id, amount=command.amount)
                  if user.role == "child" and state.child_user_id != user.id
                  else _view(db, pig, state, profile))
    return result


def request_break(db: Session, actor_id: int, pig_id: int) -> RequestView:
    with _write(db):
        user = actor(db, actor_id)
        pig, state, profile = _pig(db, pig_id, lock=True)
        _check_visible(db, user, pig, state)
        if user.role != "child" or user.id != state.child_user_id:
            raise ApiError(403, "ACCESS_DENIED", "Запрос отправляет ребёнок для своей копилки")
        _open(state)
        existing = db.scalar(select(PigBreakRequest).where(
            PigBreakRequest.pig_id == pig.id, PigBreakRequest.status == "pending",
        ))
        if existing is None:
            existing = PigBreakRequest(pig_id=pig.id, child_user_id=user.id,
                                       parent_id=profile.parent_id, status="pending")
            db.add(existing)
            db.flush()
        result = _request_view(existing)
    return result


def _close(db: Session, pig: Pig, state: PigState, account: Account,
           *, approved_request_id: int | None = None) -> None:
    _open(state)
    _active(account)
    _consistent_reserve(db, account)
    pig.current_balance = 0
    state.closed = True
    resolved = datetime.now(UTC)
    for request in db.scalars(select(PigBreakRequest).where(
        PigBreakRequest.pig_id == pig.id, PigBreakRequest.status == "pending",
    ).with_for_update()):
        request.status = "approved" if approved_request_id is None or request.id == approved_request_id else "rejected"
        request.resolved_at = resolved
    # Legal account ownership and its total balance never change on closing.


def break_pig(db: Session, actor_id: int, pig_id: int) -> PigView:
    with _write(db):
        user = actor(db, actor_id)
        initial, _, _ = _pig(db, pig_id)
        account = _lock_accounts(db, initial.account_id)[initial.account_id]
        pig, state, profile = _pig(db, pig_id, lock=True)
        _check_visible(db, user, pig, state)
        _check_parent(user, profile)
        _close(db, pig, state, account)
        db.flush()
        result = _view(db, pig, state, profile)
    return result


def list_requests(db: Session, actor_id: int) -> list[RequestView]:
    user = actor(db, actor_id)
    statement = select(PigBreakRequest)
    if user.role == "child":
        statement = statement.where(PigBreakRequest.child_user_id == user.id)
    else:
        statement = statement.where(PigBreakRequest.parent_id == user.id)
    result = []
    for request in db.scalars(statement.order_by(PigBreakRequest.created_at.desc(), PigBreakRequest.id.desc())):
        if family_id(db, request.child_user_id) != family_id(db, user.id):
            continue
        pig, state, profile = _pig(db, request.pig_id)
        _check_visible(db, user, pig, state)
        if user.role == "parent" and profile.parent_id != user.id:
            continue
        result.append(_request_view(request))
    return result


def resolve_request(db: Session, actor_id: int, request_id: int, *, approve: bool) -> RequestView:
    with _write(db):
        user = actor(db, actor_id)
        initial = db.get(PigBreakRequest, request_id)
        if initial is None:
            raise ApiError(404, "NOT_FOUND", "Запрос не найден")
        initial_pig, _, _ = _pig(db, initial.pig_id)
        account = _lock_accounts(db, initial_pig.account_id)[initial_pig.account_id]
        pig, state, profile = _pig(db, initial.pig_id, lock=True)
        request = db.scalar(select(PigBreakRequest).where(PigBreakRequest.id == request_id)
                            .with_for_update().execution_options(populate_existing=True))
        _check_visible(db, user, pig, state)
        _check_parent(user, profile)
        if request.parent_id != user.id:
            raise ApiError(403, "ACCESS_DENIED", "Запрос адресован другому parent_id")
        if request.status != "pending":
            raise ApiError(409, "REQUEST_ALREADY_RESOLVED", "Запрос уже рассмотрен")
        if approve:
            _close(db, pig, state, account, approved_request_id=request.id)
        else:
            request.status = "rejected"
            request.resolved_at = datetime.now(UTC)
        db.flush()
        result = _request_view(request)
    return result


def family_members(db: Session, actor_id: int) -> list[FamilyMemberView]:
    user = actor(db, actor_id)
    family = family_id(db, user.id)
    if family is None:
        return []
    rows = db.scalars(select(User).join(FamilyMember, FamilyMember.user_id == User.id)
                      .where(FamilyMember.family_id == family).order_by(User.id))
    result = []
    for member in rows:
        profile = child_profile(db, member.id) if member.role == "child" else None
        # IDs and public names only: no balances, history, or credentials.
        result.append(FamilyMemberView(id=member.id, login=member.login, role=member.role,
                      parent_id=None if profile is None else profile.parent_id,
                      accounts=[account_id for account_id in visible_account_ids(db, member)
                                if (link := db.get(FamilyAccount, account_id)) is not None
                                and link.family_id == family]))
    return result
