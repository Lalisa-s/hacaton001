from datetime import UTC, datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

MAX_SAFE_INTEGER = 9_007_199_254_740_991


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('parent', 'child')", name="ck_users_role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(100), unique=True)
    role: Mapped[str] = mapped_column(String(10))

    accounts: Mapped[list["Account"]] = relationship(back_populates="user")


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint(
            f"balance >= 0 AND balance <= {MAX_SAFE_INTEGER}",
            name="ck_accounts_balance",
        ),
        CheckConstraint(
            f'"limit" IS NULL OR ("limit" >= 0 AND "limit" <= {MAX_SAFE_INTEGER})',
            name="ck_accounts_limit",
        ),
        CheckConstraint(
            '("limit" IS NULL AND limit_period IS NULL) OR '
            '("limit" IS NOT NULL AND limit_period IS NOT NULL)',
            name="ck_accounts_limit_pair",
        ),
        CheckConstraint(
            "limit_period IS NULL OR limit_period IN ('daily', 'weekly', 'monthly')",
            name="ck_accounts_limit_period",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    balance: Mapped[int] = mapped_column(BigInteger, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    limit: Mapped[int | None] = mapped_column("limit", BigInteger, nullable=True, quote=True)
    limit_period: Mapped[str | None] = mapped_column(String(10), nullable=True)

    user: Mapped["User"] = relationship(back_populates="accounts")
    pigs: Mapped[list["Pig"]] = relationship(back_populates="account")


class Pig(Base):
    __tablename__ = "pigs"
    __table_args__ = (
        CheckConstraint(
            f"current_balance >= 0 AND current_balance <= {MAX_SAFE_INTEGER}",
            name="ck_pigs_current_balance",
        ),
        CheckConstraint(
            f"goal_balance > 0 AND goal_balance <= {MAX_SAFE_INTEGER}",
            name="ck_pigs_goal_balance",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    current_balance: Mapped[int] = mapped_column(BigInteger, default=0)
    goal_balance: Mapped[int] = mapped_column(BigInteger)

    account: Mapped["Account"] = relationship(back_populates="pigs")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint(
            f"amount > 0 AND amount <= {MAX_SAFE_INTEGER}",
            name="ck_transactions_amount",
        ),
        CheckConstraint("cender <> recipient", name="ck_transactions_accounts"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cender: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    recipient: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    amount: Mapped[int] = mapped_column(BigInteger)
    data: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )

