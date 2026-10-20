"""Обновление общих JSON-примеров: python -m examples.build_json_examples."""

import json
from pathlib import Path

from app.schemas.wire_models import (
    ExchangeFixtures, TestRead, TestSubmit, TransactionRead,
    TransferCreate, public_projection,
)

ROOT = Path(__file__).resolve().parents[2] / "docs" / "json-exchange"


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    test_stored = {
        "id": 8, "name": "Зачем нужна копилка", "modul": "Накопления",
        "level": "children", "questions": {"1": "Что происходит при пополнении своей копилки?"},
        "answers": {"1": ["Деньги резервируются", "Появляются новые деньги", "BYN превращаются в MT"]},
        "right_answer": {"1": 0}, "reward_MT": 10,
    }
    public_test = public_projection(TestRead, test_stored).model_dump(mode="json")
    transfer = {"id": 900, "cender": 100, "recipient": 101,
                "amount": 2500, "data": "2026-10-20T10:30:00Z"}
    fixtures = {
        "User": [
            {"id": 10, "login": "demo_parent", "role": "parent", "accounts": [100, 101],
             "ECOfamily_id": 1, "newses_id": [], "test_id": [], "auto_transaction": [20]},
            {"id": 11, "login": "demo_child", "role": "child", "accounts": [],
             "ECOfamily_id": 1, "newses_id": [5], "test_id": [], "auto_transaction": []},
        ],
        "ChaildProfile": [
            {"user_id": 11, "parent_id": 10, "age_group": "children",
             "agree_parent": {"pig": True, "history": True, "transaction": False},
             "tamagochi": {"name": "Банан", "eat": 80, "room": 1, "cloth": 2}, "MTcount": 50}
        ],
        "Test": [public_test],
        "Pig": [{"id": 500, "account_id": 101, "name": "Велосипед",
                 "current_balance": 3000, "goal_balance": 30000}],
        "Account": [
            {"id": 100, "user_id": 10, "balance": 20000, "pigs": [],
             "active_balance": 20000, "active": True, "transactions_history": [900],
             "limit": 15000, "limit_period": "daily"},
            {"id": 101, "user_id": 10, "balance": 10000, "pigs": [500],
             "active_balance": 7000, "active": True, "transactions_history": [900],
             "limit": 5000, "limit_period": "daily"},
        ],
        "Transaction": [transfer],
        "EcoFamily": [{"id": 1, "users_id": [10, 11], "user_admin_id": 10,
                       "name": "Демо-семья", "accounts": [100, 101]}],
        "News": [{"id": 5, "name": "Планируем накопления", "lavel": "children",
                  "test_id": 8, "test": public_test,
                  "text": "Копилка помогает отложить часть денег на выбранную цель."}],
        "Parent_Task": [{"id": 30, "parent_id": 10, "chaild_id": 11,
                         "data": "2026-10-25T17:00:00Z", "sum": 500,
                         "name": "Полить растения", "text": "Полить растения в своей комнате."}],
        "AutoTransaction": [{"id": 20, "recipient_accoun_id": 101,
                             "source_account_id": 100, "summ": 1000, "period": "weekly",
                             "data": "2026-10-20T06:00:00Z"}],
    }
    snapshot = ExchangeFixtures.model_validate_json(json.dumps(fixtures, ensure_ascii=False))
    request = TransferCreate.model_validate({"cender": 100, "recipient": 101, "amount": 2500})
    result = TransactionRead.model_validate_json(json.dumps(transfer))
    write_json(ROOT / "examples" / "entities.json", snapshot.model_dump(mode="json"))
    write_json(ROOT / "examples" / "transfer-request.json", request.model_dump(mode="json"))
    write_json(ROOT / "examples" / "transfer-response.json", result.model_dump(mode="json"))
    write_json(ROOT / "examples" / "account-response.json", snapshot.Account[1].model_dump(mode="json"))
    write_json(ROOT / "examples" / "test-submit.json", {"answers": {"1": 0}})
    write_json(ROOT / "examples" / "health-response.json", {"status": "ok"})
    write_json(ROOT / "examples" / "error-proposed.json", {
        "error": {"code": "INSUFFICIENT_FUNDS", "message": "Недостаточно доступных средств", "details": []}
    })
    write_json(ROOT / "examples" / "error-fastapi.json", {"detail": "Not Found"})
    for name, model in (("entities", ExchangeFixtures), ("transfer-request", TransferCreate),
                        ("test-submit", TestSubmit)):
        write_json(ROOT / "schemas" / f"{name}.schema.json", model.model_json_schema())
    print("Generated 8 JSON examples and 3 JSON Schemas.")


if __name__ == "__main__":
    main()
