"""Family piggy banks: children request closing; only their parent_id approves."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.api.dependencies import get_demo_actor_id
from app.db.session import get_request_db
from app.schemas.banking import ErrorResponse
from app.schemas.pigs import (
    EmptyCommand, FamilyMemberList, PigContribution, PigContributionReceipt, PigCreate, PigList,
    PigRename, PigView, RequestList, RequestView,
)
from app.schemas.wire_models import MAX_JS_INTEGER
from app.services import pigs

router = APIRouter(tags=["family-pigs-demo"], responses={
    code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 422, 503)
})
Database = Annotated[Session, Depends(get_request_db)]
Actor = Annotated[int, Depends(get_demo_actor_id)]
EntityId = Annotated[int, Path(gt=0, le=MAX_JS_INTEGER)]


@router.get("/pigs", response_model=PigList)
def list_pigs(db: Database, actor_id: Actor):
    return PigList(items=pigs.list_pigs(db, actor_id))


@router.post("/pigs", response_model=PigView, status_code=201)
def create_pig(command: PigCreate, db: Database, actor_id: Actor):
    return pigs.create_pig(db, actor_id, command)


@router.patch("/pigs/{pig_id}", response_model=PigView)
def rename_pig(pig_id: EntityId, command: PigRename, db: Database, actor_id: Actor):
    return pigs.rename_pig(db, actor_id, pig_id, command)


@router.post("/pigs/{pig_id}/contributions", response_model=PigView | PigContributionReceipt)
def contribute(pig_id: EntityId, command: PigContribution, db: Database, actor_id: Actor):
    return pigs.contribute(db, actor_id, pig_id, command)


@router.post("/pigs/{pig_id}/break-requests", response_model=RequestView, status_code=201)
def request_break(pig_id: EntityId, command: EmptyCommand, db: Database, actor_id: Actor):
    return pigs.request_break(db, actor_id, pig_id)


@router.post("/pigs/{pig_id}/break", response_model=PigView)
def break_pig(pig_id: EntityId, command: EmptyCommand, db: Database, actor_id: Actor):
    return pigs.break_pig(db, actor_id, pig_id)


@router.get("/pig-break-requests", response_model=RequestList)
def requests(db: Database, actor_id: Actor):
    return RequestList(items=pigs.list_requests(db, actor_id))


@router.post("/pig-break-requests/{request_id}/approve", response_model=RequestView)
def approve_request(request_id: EntityId, command: EmptyCommand, db: Database, actor_id: Actor):
    return pigs.resolve_request(db, actor_id, request_id, approve=True)


@router.post("/pig-break-requests/{request_id}/reject", response_model=RequestView)
def reject_request(request_id: EntityId, command: EmptyCommand, db: Database, actor_id: Actor):
    return pigs.resolve_request(db, actor_id, request_id, approve=False)


@router.get("/family/members", response_model=FamilyMemberList)
def family_members(db: Database, actor_id: Actor):
    return FamilyMemberList(items=pigs.family_members(db, actor_id))
