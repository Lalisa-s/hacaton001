"""Pydantic-схемы запросов и публичных ответов JSON.

Проверка формата и сборка ответов не выполняют переводы, не проверяют права
и не заменяют модели SQLAlchemy или банковские сервисы.
"""

from datetime import datetime, timezone
from typing import Annotated, Literal, TypeVar

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_serializer,
    model_validator,
)

MAX_JS_INTEGER = 9_007_199_254_740_991
Id = Annotated[int, Field(strict=True, gt=0, le=MAX_JS_INTEGER)]
Money = Annotated[int, Field(strict=True, ge=0, le=MAX_JS_INTEGER)]
PositiveMoney = Annotated[int, Field(strict=True, gt=0, le=MAX_JS_INTEGER)]
Text = Annotated[str, StringConstraints(strict=True, min_length=1)]
QuestionId = Annotated[str, StringConstraints(pattern=r"^[1-9][0-9]*$")]
AnswerIndex = Annotated[int, Field(strict=True, ge=0)]
Period = Literal["daily", "weekly", "monthly"]
Level = Literal["children", "teanagers", "adult"]


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class TimestampDTO(DTO):
    data: AwareDatetime

    @field_serializer("data", when_used="json")
    def utc_data(self, value: datetime) -> str:
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class UserRead(DTO):
    id: Id
    login: Text
    role: Literal["parent", "child"]
    accounts: list[Id]
    ECOfamily_id: Id | None
    newses_id: list[Id]
    test_id: list[Id]
    auto_transaction: list[Id]


class AgreeParent(DTO):
    pig: bool
    history: bool
    transaction: bool


class Tamagochi(DTO):
    name: Text
    # Proposed wire convention: satiety 0..100, numeric catalog identifiers.
    eat: Annotated[int, Field(strict=True, ge=0, le=100)]
    room: Id
    cloth: Id


class ChaildProfileRead(DTO):
    user_id: Id
    parent_id: Id
    age_group: Literal["children", "teanagers"]
    agree_parent: AgreeParent
    tamagochi: Tamagochi
    MTcount: Money


class TestRead(DTO):
    id: Id
    name: Text
    modul: Text
    level: Level
    questions: dict[QuestionId, Text]
    answers: dict[QuestionId, list[Text]]
    reward_MT: Money

    @model_validator(mode="after")
    def matching_questions(self):
        if not self.questions or self.questions.keys() != self.answers.keys():
            raise ValueError("questions and answers must have the same nonempty keys")
        if any(not options for options in self.answers.values()):
            raise ValueError("each question must have answer options")
        return self


class TestSubmit(DTO):
    # Each value is one zero-based choice index, not an amount of MT.
    answers: dict[QuestionId, AnswerIndex]


class PigRead(DTO):
    id: Id
    account_id: Id
    name: Text
    current_balance: Money
    goal_balance: PositiveMoney


class AccountRead(DTO):
    id: Id
    user_id: Id
    balance: Money
    pigs: list[Id]
    active_balance: Money
    active: bool
    transactions_history: list[Id]
    limit: Money | None
    limit_period: Period | None

    @model_validator(mode="after")
    def consistent_balance_and_limit(self):
        if self.active_balance > self.balance:
            raise ValueError("active_balance cannot exceed balance")
        if (self.limit is None) != (self.limit_period is None):
            raise ValueError("limit and limit_period must both be null or both set")
        return self


class TransferCreate(DTO):
    cender: Id
    recipient: Id
    amount: PositiveMoney

    @model_validator(mode="after")
    def distinct_accounts(self):
        if self.cender == self.recipient:
            raise ValueError("cender and recipient must be different accounts")
        return self


class TransactionRead(TimestampDTO):
    id: Id
    cender: Id
    recipient: Id
    amount: PositiveMoney


class EcoFamilyRead(DTO):
    id: Id
    users_id: list[Id]
    user_admin_id: Id
    name: Text
    accounts: list[Id]


class NewsRead(DTO):
    id: Id
    name: Text
    lavel: Level
    test_id: Id | None
    test: TestRead | None
    text: Text

    @model_validator(mode="after")
    def matching_test(self):
        if (self.test_id is None) != (self.test is None):
            raise ValueError("test_id and test must both be null or both set")
        if self.test is not None and self.test.id != self.test_id:
            raise ValueError("test_id must match test.id")
        return self


class ParentTaskRead(TimestampDTO):
    id: Id
    parent_id: Id
    chaild_id: Id
    sum: PositiveMoney
    name: Text
    text: Text


class AutoTransactionRead(TimestampDTO):
    id: Id
    recipient_accoun_id: Id
    source_account_id: Id
    summ: PositiveMoney
    period: Period


class ExchangeFixtures(DTO):
    """A local example file; this is not an implemented bootstrap endpoint."""

    User: list[UserRead]
    ChaildProfile: list[ChaildProfileRead]
    Test: list[TestRead]
    Pig: list[PigRead]
    Account: list[AccountRead]
    Transaction: list[TransactionRead]
    EcoFamily: list[EcoFamilyRead]
    News: list[NewsRead]
    Parent_Task: list[ParentTaskRead]
    AutoTransaction: list[AutoTransactionRead]


PublicModel = TypeVar("PublicModel", bound=DTO)


def public_projection(model: type[PublicModel], stored: dict) -> PublicModel:
    """Explicit public-field whitelist; never serialize an ORM __dict__."""
    return model.model_validate({name: stored[name] for name in model.model_fields})


def parse_transfer_json(raw: str | bytes) -> TransferCreate:
    """Validate a JSON document. This does not perform a bank transfer."""
    return TransferCreate.model_validate_json(raw)


def account_response(stored: dict, pigs: list[PigRead]) -> AccountRead:
    """Build a public account response from already authorized server data.

    The service must select relevant current reserves and check authorization.
    This function only demonstrates assembling a public response.
    """
    if any(pig.account_id != stored["id"] for pig in pigs):
        raise ValueError("a pig belongs to a different account")
    data = {name: stored[name] for name in AccountRead.model_fields
            if name not in {"pigs", "active_balance"}}
    data["pigs"] = [pig.id for pig in pigs]
    data["active_balance"] = stored["balance"] - sum(p.current_balance for p in pigs)
    return AccountRead.model_validate(data)
