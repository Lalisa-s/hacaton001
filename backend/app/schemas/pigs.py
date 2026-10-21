"""Public piggy-bank requests; all monetary values are integer BYN kopecks."""

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, StringConstraints, field_serializer

from app.schemas.wire_models import DTO, Id, PigRead, PositiveMoney

PigName = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=100)]


class PigView(PigRead):
    child_user_id: Id
    parent_id: Id
    closed: bool
    pending_request_id: Id | None


class PigList(DTO):
    items: list[PigView]


class PigCreate(DTO):
    account_id: Id
    child_user_id: Id
    name: PigName
    goal_balance: PositiveMoney


class PigRename(DTO):
    name: PigName


class PigContribution(DTO):
    account_id: Id
    amount: PositiveMoney


class PigContributionReceipt(DTO):
    """No disclosure of another child's savings when contributing by shared ID."""

    pig_id: Id
    amount: PositiveMoney


class EmptyCommand(DTO):
    pass


class RequestView(DTO):
    id: Id
    pig_id: Id
    child_user_id: Id
    parent_id: Id
    status: Literal["pending", "approved", "rejected"]
    created_at: AwareDatetime
    resolved_at: AwareDatetime | None

    @field_serializer("created_at", "resolved_at", when_used="json")
    def utc_timestamp(self, value: datetime | None) -> str | None:
        return None if value is None else value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class RequestList(DTO):
    items: list[RequestView]


class FamilyMemberView(DTO):
    id: Id
    login: str
    role: Literal["parent", "child"]
    parent_id: Id | None
    accounts: list[Id]


class FamilyMemberList(DTO):
    items: list[FamilyMemberView]
