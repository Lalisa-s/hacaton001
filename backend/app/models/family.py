"""Family permissions are separate from legal bank account ownership."""

from datetime import UTC, datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EcoFamily(Base):
    __tablename__ = "eco_families"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    user_admin_id: Mapped[int] = mapped_column(ForeignKey("users.id"))


class FamilyMember(Base):
    __tablename__ = "family_members"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("eco_families.id"), index=True)


class FamilyAccount(Base):
    __tablename__ = "family_accounts"

    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("eco_families.id"), index=True)


class ChaildProfile(Base):
    __tablename__ = "chaild_profiles"
    __table_args__ = (
        CheckConstraint("user_id <> parent_id", name="ck_child_parent_distinct"),
        CheckConstraint("age_group IN ('children', 'teanagers')", name="ck_child_age_group"),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    age_group: Mapped[str] = mapped_column(String(12), default="children")
    agree_pig: Mapped[bool] = mapped_column(Boolean, default=True)
    agree_history: Mapped[bool] = mapped_column(Boolean, default=True)
    agree_transaction: Mapped[bool] = mapped_column(Boolean, default=True)


class ChildAccountAccess(Base):
    __tablename__ = "child_account_access"

    child_user_id: Mapped[int] = mapped_column(ForeignKey("chaild_profiles.user_id"), primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), primary_key=True)


class PigState(Base):
    """Additional fields without altering the existing pigs table."""

    __tablename__ = "pig_states"

    pig_id: Mapped[int] = mapped_column(ForeignKey("pigs.id"), primary_key=True)
    child_user_id: Mapped[int] = mapped_column(ForeignKey("chaild_profiles.user_id"), index=True)
    closed: Mapped[bool] = mapped_column(Boolean, default=False)


class PigBreakRequest(Base):
    __tablename__ = "pig_break_requests"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="ck_pig_request_status"),
        CheckConstraint(
            "(status = 'pending' AND resolved_at IS NULL) OR "
            "(status <> 'pending' AND resolved_at IS NOT NULL)",
            name="ck_pig_request_resolution",
        ),
        Index("uq_pending_pig_break_request", "pig_id", unique=True,
              sqlite_where=text("status = 'pending'"), postgresql_where=text("status = 'pending'")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pig_id: Mapped[int] = mapped_column(ForeignKey("pigs.id"), index=True)
    child_user_id: Mapped[int] = mapped_column(ForeignKey("chaild_profiles.user_id"), index=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(10), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SharedFamilyAccount(Base):
    __tablename__ = "shared_family_accounts"
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("eco_families.id"), index=True)


class SharedFamilyPig(Base):
    __tablename__ = "shared_family_pigs"
    pig_id: Mapped[int] = mapped_column(ForeignKey("pigs.id"), primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("eco_families.id"), index=True)


class FamilyRemoval(Base):
    __tablename__ = "family_removals"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("eco_families.id"))


class FamilyInvitation(Base):
    __tablename__ = "family_invitations"
    id: Mapped[int] = mapped_column(primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("eco_families.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
