"""Read permissions shared by accounts and piggy banks."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models import Account, ChaildProfile, ChildAccountAccess, FamilyAccount, FamilyMember, User


def actor(db: Session, actor_id: int) -> User:
    user = db.get(User, actor_id)
    if user is None:
        raise ApiError(401, "DEMO_USER_NOT_FOUND", "Демо-пользователь не найден")
    if user.role == "child" and db.get(ChaildProfile, user.id) is None:
        raise ApiError(403, "ACCESS_DENIED", "Профиль ребёнка и права доступа не настроены")
    return user


def family_id(db: Session, user_id: int) -> int | None:
    membership = db.get(FamilyMember, user_id)
    return None if membership is None else membership.family_id


def require_same_family(db: Session, *user_ids: int) -> int:
    families = [family_id(db, user_id) for user_id in user_ids]
    if not families or families[0] is None or any(value != families[0] for value in families):
        raise ApiError(403, "ACCESS_DENIED", "Участники должны состоять в одной экосемье")
    return families[0]


def child_profile(db: Session, child_user_id: int) -> ChaildProfile:
    profile = db.get(ChaildProfile, child_user_id)
    child = db.get(User, child_user_id)
    if profile is None or child is None or child.role != "child":
        raise ApiError(404, "NOT_FOUND", "Профиль ребёнка не найден")
    parent = db.get(User, profile.parent_id)
    if parent is None or parent.role != "parent":
        raise ApiError(403, "ACCESS_DENIED", "Законный представитель не настроен")
    require_same_family(db, child_user_id, profile.parent_id)
    return profile


def child_account_allowed(db: Session, child_user_id: int, account: Account) -> bool:
    profile = child_profile(db, child_user_id)
    family = family_id(db, child_user_id)
    link = db.get(FamilyAccount, account.id)
    return (account.user_id == profile.parent_id
            and db.get(ChildAccountAccess, (child_user_id, account.id)) is not None
            and link is not None and link.family_id == family)


def visible_account_ids(db: Session, user: User) -> list[int]:
    if user.role == "parent":
        return list(db.scalars(select(Account.id).where(Account.user_id == user.id).order_by(Account.id)))
    accounts = db.scalars(select(Account).join(
        ChildAccountAccess, ChildAccountAccess.account_id == Account.id,
    ).where(ChildAccountAccess.child_user_id == user.id).order_by(Account.id))
    return [account.id for account in accounts if child_account_allowed(db, user.id, account)]


def readable_account(db: Session, user: User, account_id: int, *, history: bool = False) -> Account:
    account = db.get(Account, account_id)
    if account is None:
        raise ApiError(404, "NOT_FOUND", "Счёт не найден")
    allowed = account.user_id == user.id if user.role == "parent" else child_account_allowed(db, user.id, account)
    if not allowed:
        raise ApiError(403, "ACCESS_DENIED", "Нет доступа к этому счёту")
    if history and user.role == "child" and not child_profile(db, user.id).agree_history:
        raise ApiError(403, "ACCESS_DENIED", "Просмотр истории отключён родителем")
    return account
