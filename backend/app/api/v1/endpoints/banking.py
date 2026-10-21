"""Implemented demo API. No real authentication or banking integration."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_demo_actor_id
from app.db.session import get_request_db
from app.schemas.banking import AccountList, ErrorResponse, TransactionList
from app.schemas.wire_models import MAX_JS_INTEGER, AccountRead, TransactionRead, TransferCreate, UserRead
from app.services import banking

router = APIRouter(tags=["banking-demo"], responses={
    code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 422, 503)
})
Database = Annotated[Session, Depends(get_request_db)]
Actor = Annotated[int, Depends(get_demo_actor_id)]
AccountId = Annotated[int, Path(gt=0, le=MAX_JS_INTEGER)]


@router.get("/me", response_model=UserRead)
def me(db: Database, actor_id: Actor):
    return banking.get_me(db, actor_id)


@router.get("/accounts", response_model=AccountList)
def accounts(db: Database, actor_id: Actor):
    return AccountList(items=banking.list_accounts(db, actor_id))


@router.get("/accounts/{account_id}", response_model=AccountRead)
def account(account_id: AccountId, db: Database, actor_id: Actor):
    return banking.get_account(db, actor_id, account_id)


@router.get("/accounts/{account_id}/transactions", response_model=TransactionList)
def history(account_id: AccountId, db: Database, actor_id: Actor,
            limit: Annotated[int, Query(ge=1, le=100)] = 50,
            offset: Annotated[int, Query(ge=0)] = 0):
    return TransactionList(items=banking.get_history(db, actor_id, account_id, limit, offset))


@router.post("/transactions", response_model=TransactionRead, status_code=201)
def transfer(command: TransferCreate, db: Database, actor_id: Actor):
    return banking.create_transfer(db, actor_id, command)
