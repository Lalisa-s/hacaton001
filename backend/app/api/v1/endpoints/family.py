"""Family membership and explicitly shared resources; no personal balances."""
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from typing import Annotated

from fastapi import APIRouter, Depends, Path
from pydantic import StringConstraints
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_demo_actor_id
from app.core.errors import ApiError
from app.db.session import get_request_db
from app.models import Account, ChaildProfile, EcoFamily, FamilyMember, Pig, PigBreakRequest, PigState, User
from app.models.family import FamilyInvitation, FamilyRemoval, SharedFamilyAccount, SharedFamilyPig
from app.schemas.wire_models import DTO, MAX_JS_INTEGER
from app.services.family_access import actor, family_id
from app.services.pigs import _write

router = APIRouter(tags=["family-demo"])
Database = Annotated[Session, Depends(get_request_db)]
Actor = Annotated[int, Depends(get_demo_actor_id)]
EntityId = Annotated[int, Path(gt=0, le=MAX_JS_INTEGER)]


def family_for(db, actor_id, *, admin=False):
    user = actor(db, actor_id)
    family = db.get(EcoFamily, family_id(db, user.id)) if family_id(db, user.id) else None
    if family is None:
        raise ApiError(403, "FAMILY_NOT_FOUND", "Участник не подключён к семье")
    if admin and (user.role != "parent" or family.user_admin_id != user.id):
        raise ApiError(403, "ACCESS_DENIED", "Действие доступно только администратору семьи")
    return family


@router.get("/family")
def summary(db: Database, actor_id: Actor):
    family = family_for(db, actor_id)
    members = db.scalars(select(User).join(FamilyMember, FamilyMember.user_id == User.id)
                         .where(FamilyMember.family_id == family.id).order_by(User.id))
    accounts = db.scalars(select(Account).join(SharedFamilyAccount, SharedFamilyAccount.account_id == Account.id)
                          .join(FamilyMember, FamilyMember.user_id == Account.user_id)
                          .where(SharedFamilyAccount.family_id == family.id, FamilyMember.family_id == family.id))
    pigs = db.scalars(select(Pig).join(SharedFamilyPig, SharedFamilyPig.pig_id == Pig.id)
                      .join(Account, Account.id == Pig.account_id)
                      .join(FamilyMember, FamilyMember.user_id == Account.user_id)
                      .where(SharedFamilyPig.family_id == family.id, FamilyMember.family_id == family.id))
    return {"id": family.id, "name": family.name, "is_admin": family.user_admin_id == actor_id,
            "members": [{"id": u.id, "login": u.login, "role": u.role} for u in members],
            "accounts": [{"id": a.id, "balance": a.balance, "active": a.active} for a in accounts],
            "pigs": [{"id": p.id, "name": p.name, "current_balance": p.current_balance,
                      "goal_balance": p.goal_balance} for p in pigs if not (state := db.get(PigState, p.id)) or not state.closed]}


@router.post("/family/invitations", status_code=201)
def invite(db: Database, actor_id: Actor):
    with _write(db):
        family = family_for(db, actor_id, admin=True)
        token = token_urlsafe(24)
        expires = datetime.now(UTC) + timedelta(days=7)
        invitation = FamilyInvitation(family_id=family.id, token_hash=sha256(token.encode()).hexdigest(), expires_at=expires)
        db.add(invitation)
        db.flush()
        return {"id": invitation.id, "token": token, "expires_at": expires.isoformat().replace("+00:00", "Z")}


class InvitationAccept(DTO):
    token: Annotated[str, StringConstraints(strict=True, min_length=20, max_length=100)]


@router.post("/family/invitations/accept")
def accept(command: InvitationAccept, db: Database, actor_id: Actor):
    with _write(db):
        user = actor(db, actor_id)
        invitation = db.scalar(select(FamilyInvitation).where(FamilyInvitation.token_hash == sha256(command.token.encode()).hexdigest()).with_for_update())
        if invitation is None:
            raise ApiError(404, "NOT_FOUND", "Приглашение не найдено")
        expires = invitation.expires_at.replace(tzinfo=UTC) if invitation.expires_at.tzinfo is None else invitation.expires_at
        if invitation.accepted_by is not None or expires <= datetime.now(UTC):
            raise ApiError(409, "INVITATION_UNAVAILABLE", "Приглашение использовано или истекло")
        if db.get(FamilyMember, user.id) is not None:
            raise ApiError(409, "ALREADY_IN_FAMILY", "Участник уже состоит в семье")
        if user.role == "child":
            profile = db.get(ChaildProfile, user.id)
            if profile is None or family_id(db, profile.parent_id) != invitation.family_id:
                raise ApiError(403, "ACCESS_DENIED", "Ребёнок присоединяется к семье своего parent_id")
        db.add(FamilyMember(user_id=user.id, family_id=invitation.family_id))
        removed = db.get(FamilyRemoval, user.id)
        if removed is not None:
            db.delete(removed)
        invitation.accepted_by = user.id
        return {"family_id": invitation.family_id}


@router.delete("/family/members/{user_id}")
def remove_member(user_id: EntityId, db: Database, actor_id: Actor):
    with _write(db):
        family = family_for(db, actor_id, admin=True)
        # Serialize membership changes (also effective on PostgreSQL).
        db.scalar(select(EcoFamily).where(EcoFamily.id == family.id).with_for_update())
        member = db.get(FamilyMember, user_id)
        if member is None or member.family_id != family.id:
            raise ApiError(404, "NOT_FOUND", "Участник не найден в этой семье")
        if user_id == family.user_admin_id:
            raise ApiError(409, "ADMIN_CANNOT_LEAVE", "Администратор не может удалить себя")
        dependent = db.scalar(select(ChaildProfile.user_id).join(FamilyMember, FamilyMember.user_id == ChaildProfile.user_id)
                               .where(ChaildProfile.parent_id == user_id, FamilyMember.family_id == family.id))
        if dependent is not None:
            raise ApiError(409, "CHILDREN_IN_FAMILY", "Сначала отключите детей этого представителя от семьи")
        for request in db.scalars(select(PigBreakRequest).where(PigBreakRequest.child_user_id == user_id, PigBreakRequest.status == 'pending')):
            request.status, request.resolved_at = 'rejected', datetime.now(UTC)
        db.delete(member)
        if db.get(FamilyRemoval, user_id) is None:
            db.add(FamilyRemoval(user_id=user_id, family_id=family.id))
        return {"removed_user_id": user_id}
