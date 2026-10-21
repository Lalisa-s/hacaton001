"""Collection and error responses for implemented banking demo endpoints."""

from pydantic import Field

from app.schemas.wire_models import AccountRead, DTO, TransactionRead


class AccountList(DTO):
    items: list[AccountRead]


class TransactionList(DTO):
    items: list[TransactionRead]


class ErrorDetail(DTO):
    field: str
    code: str


class ErrorBody(DTO):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(DTO):
    error: ErrorBody
