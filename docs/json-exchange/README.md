# Общие структуры и примеры JSON

Действующие маршруты, запуск DEMO_MODE, права доступа и ошибки описаны в
[основном API-контракте](../api-contract.md). Действующие семейные копилки,
детская привязка и запросы родителю — в [контракте копилок](../piggy-banks.md).

В этой папке остаются материалы, общие для backend и frontend:

- `api-contract.md` — описание обмена и полей всех объектов;
- `examples/` — 8 JSON-файлов с запросами, ответами и тестовыми данными;
- `schemas/` — 3 машиночитаемые JSON Schema.

Код расположен в папках проекта относительно корня `hacaton001`:

| Назначение | Путь |
| --- | --- |
| Pydantic-схемы | `backend/app/schemas/wire_models.py` |
| Разбор и сборка JSON | `backend/examples/json_exchange.py` |
| Генератор примеров | `backend/examples/build_json_examples.py` |
| Проверки backend | `backend/tests/test_json_schemas.py` |
| Клиент uni-app | `frontend/src/api/api.js` |
| Пример использования | `frontend/src/api/example-usage.js` |
| Проверки frontend | `frontend/tests/` |

Backend: из папки `backend` в PowerShell:

```powershell
.\.venv\Scripts\python.exe -m examples.json_exchange
.\.venv\Scripts\python.exe -m pytest tests/test_json_schemas.py -q
.\.venv\Scripts\python.exe -m examples.build_json_examples
```

Frontend: из корня репозитория, если Node.js уже установлен:

```powershell
node .\frontend\tests\test-api.mjs
node .\frontend\tests\test-fixtures.mjs
```

Оба набора проверок используют одни файлы из `docs/json-exchange/examples/`.
Генератор читает действующие Pydantic-схемы и обновляет примеры и JSON Schema.
Новых зависимостей для этих проверок не требуется.

Работают `GET /api/v1/health`, `/me`, `/accounts`, `/accounts/{id}`,
`/accounts/{id}/transactions` и `POST /api/v1/transactions`. Кроме health,
они доступны только при `DEMO_MODE=true`. Перевод выполняется между собственными
счетами действующего родителя; настоящая аутентификация не реализована.
Копилки, семейное участие и явная детская привязка также реализованы, но новые
команды и расширенные ответы описаны отдельно. Учебные объекты, питомец, задания
и расписание в `entities.json` остаются примерами будущих функций.
Фикстура не является снимком текущей SQLite: её операция `900` не создаётся
автоматически в новой демонстрационной БД.
JSON передаётся в HTTP. Файлы используются как примеры для согласования и тестов.
