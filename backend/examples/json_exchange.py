r"""Запуск из backend: .\.venv\Scripts\python.exe -m examples.json_exchange."""

import argparse
import json
import sys
from pathlib import Path

from app.schemas.wire_models import (
    ExchangeFixtures,
    account_response,
    parse_transfer_json,
)

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "docs" / "json-exchange" / "examples"


def main() -> None:
    # Один формат вывода в PyCharm и терминале Windows.
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Разбор JSON без выполнения перевода")
    parser.add_argument("--request-file", type=Path,
                        default=EXAMPLES_DIR / "transfer-request.json")
    args = parser.parse_args()
    raw_request = args.request_file.read_text(encoding="utf-8")
    command = parse_transfer_json(raw_request)
    print("Разобранный запрос (перевод не выполняется):", command.model_dump())

    fixtures = ExchangeFixtures.model_validate_json(
        (EXAMPLES_DIR / "entities.json").read_text(encoding="utf-8")
    )
    stored_account = fixtures.Account[1].model_dump()
    pigs = [pig for pig in fixtures.Pig if pig.account_id == stored_account["id"]]
    response = account_response(stored_account, pigs)

    # Для записи в файл нужна строка; в FastAPI возвращаем сам response.
    raw_response = response.model_dump_json(indent=2)
    print("Собранный публичный JSON счёта:")
    print(raw_response)
    parsed_response = json.loads(raw_response)
    amount = parsed_response["active_balance"]
    print("Доступный остаток:", f"{amount // 100}.{amount % 100:02d} BYN")


if __name__ == "__main__":
    main()
