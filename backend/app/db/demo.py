from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.family import FamilyRemoval
from app.models import (
    Account, ChaildProfile, ChildAccountAccess, EcoFamily, FamilyAccount,
    FamilyMember, Pig, PigState, User,
)


def initialize_demo_database(engine: Engine) -> None:
    """Create missing tables and seed the demo without resetting existing data."""
    Base.metadata.create_all(engine)

    with Session(engine, autoflush=False) as session, session.begin():
        # Serialize SQLite startup seeds before checking which rows already exist.
        if engine.dialect.name == "sqlite":
            session.execute(text("BEGIN IMMEDIATE"))

        for user_id, login, role in ((10, "demo_parent", "parent"),
                                     (11, "demo_family_parent", "parent"),
                                     (20, "demo_child", "child")):
            user = session.get(User, user_id)
            login_owner = session.scalar(select(User).where(User.login == login))
            if login_owner is not None and login_owner.id != user_id:
                raise ValueError(f"The {login} login already belongs to another user.")
            if user is not None and (user.login != login or user.role != role):
                raise ValueError(f"Demo user ID {user_id} is occupied by another user or role.")
            if user is None:
                session.add(User(id=user_id, login=login, role=role))
        session.flush()

        for account_id, owner_id, balance, limit in ((100, 10, 20_000, 15_000),
                                                    (101, 10, 10_000, 5_000),
                                                    (110, 11, 15_000, None)):
            account = session.get(Account, account_id)
            if account is not None and account.user_id != owner_id:
                raise ValueError(f"Demo account ID {account_id} has another owner.")
            if account is None:
                session.add(
                    Account(
                        id=account_id,
                        user_id=owner_id,
                        balance=balance,
                        active=True,
                        limit=limit,
                        limit_period="daily" if limit is not None else None,
                    )
                )
        session.flush()

        pig = session.get(Pig, 500)
        if pig is not None and pig.account_id != 101:
            raise ValueError("Demo pig ID 500 belongs to another account.")
        if pig is None:
            account = session.get(Account, 101)
            reserved = session.scalar(
                select(func.coalesce(func.sum(Pig.current_balance), 0)).where(
                    Pig.account_id == 101
                )
            )
            if account.balance < reserved + 3_000:
                raise ValueError("Account 101 cannot cover the missing demo pig reserve.")
            session.add(
                Pig(
                    id=500,
                    account_id=101,
                    name="Велосипед",
                    current_balance=3_000,
                    goal_balance=30_000,
                )
            )
        session.flush()

        family = session.get(EcoFamily, 1)
        if family is None:
            session.add(EcoFamily(id=1, name="Демо-семья", user_admin_id=10))
        elif family.user_admin_id != 10:
            raise ValueError("Demo family ID 1 has another administrator.")
        session.flush()
        for user_id in (10, 11, 20):
            if session.get(FamilyRemoval, user_id) is not None:
                continue
            member = session.get(FamilyMember, user_id)
            if member is None:
                session.add(FamilyMember(user_id=user_id, family_id=1))
            elif member.family_id != 1:
                raise ValueError(f"Demo user {user_id} belongs to another family.")
        for account_id in (100, 101, 110):
            link = session.get(FamilyAccount, account_id)
            if link is None:
                session.add(FamilyAccount(account_id=account_id, family_id=1))
            elif link.family_id != 1:
                raise ValueError(f"Demo account {account_id} belongs to another family.")
        profile = session.get(ChaildProfile, 20)
        if profile is None:
            session.add(ChaildProfile(user_id=20, parent_id=10, age_group="children",
                                     agree_pig=True, agree_history=True, agree_transaction=True))
        elif profile.parent_id != 10:
            raise ValueError("The demo child has another parent_id.")
        session.flush()
        if session.get(ChildAccountAccess, (20, 101)) is None:
            session.add(ChildAccountAccess(child_user_id=20, account_id=101))
        state = session.get(PigState, 500)
        if state is None:
            session.add(PigState(pig_id=500, child_user_id=20, closed=False))
        elif state.child_user_id != 20:
            raise ValueError("Demo pig 500 is assigned to another child.")
        # Never reset balances, names, permissions, requests, or a closed pig.
