# Контракт обмена JSON

Полное описание и примеры находятся в [json-exchange/api-contract.md](json-exchange/api-contract.md).
Общие примеры JSON: [json-exchange/README.md](json-exchange/README.md).

Схемы установлены в `backend/app/schemas/wire_models.py` относительно корня
репозитория. Запускаемый пример проекта — `backend/examples/json_exchange.py`:
из `backend` выполните `.\.venv\Scripts\python.exe -m examples.json_exchange`.

- Форматы всех 10 объектов: `json-exchange/examples/entities.json`.
- Входной перевод: `json-exchange/examples/transfer-request.json`.
- Публичный счёт: `json-exchange/examples/account-response.json`.
- Python/Pydantic: `backend/app/schemas/wire_models.py` от корня репозитория.
- Генератор JSON: `backend/examples/build_json_examples.py`.
- Клиент uni-app: `frontend/src/api/api.js`.
- Пример использования: `frontend/src/api/example-usage.js`.
- Проверки frontend: `frontend/tests/`.
- JSON Schema: `json-exchange/schemas/`.

Работает только `GET /api/v1/health`. Остальные маршруты — проект контракта;
операции БД, авторизация и банковские сервисы этими примерами не реализованы.
Связь ребёнка с выделенным родительским счётом ещё требует уточнения.
