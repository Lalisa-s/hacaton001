# hacaton001

Общий репозиторий MVP детско-семейного банковского приложения.

```text
hacaton001/
├── backend/       # FastAPI, SQLAlchemy, SQLite, тесты
├── frontend/      # модули uni-app для обмена JSON и проверки
├── docs/          # общий контракт, примеры JSON и JSON Schema
├── .gitignore
└── README.md
```

В `backend/` размещён Python-проект, схемы JSON, примеры и тесты.
В `frontend/src/api/` находятся готовые клиентские модули, в `frontend/tests/` —
проверки JSON. Frontend-разработчик подключает модули к своему приложению uni-app;
Vue/uni-app приложение в этой папке пока не инициализировано.

## Запуск backend

Команды PowerShell из корня `hacaton001`:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Локальные адреса:

- Health: <http://127.0.0.1:8000/api/v1/health>
- Swagger UI: <http://127.0.0.1:8000/docs>

После первого клонирования на другом компьютере нужно создать собственное
окружение Python 3.12+, установить `backend/requirements.txt` и создать локальный
`backend/.env` по примеру. Подробная инструкция: [backend/README.md](backend/README.md).

## Проверка backend

Из папки `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
```

## PyCharm

Открывайте корень `hacaton001`. Для backend выберите интерпретатор
`backend\.venv\Scripts\python.exe` и рабочий каталог `backend`.
Виртуальное окружение и локальные настройки остаются на каждом компьютере.

## Совместная работа

Репозиторий Git общий и находится в корне `hacaton001`; в `backend/` и `frontend/`
вложенные репозитории не нужны. Изменения frontend и backend размещаются
в соответствующих папках.

`.gitignore` исключает виртуальные окружения, `.env`, локальные базы данных,
IDE-настройки, `node_modules` и результаты сборки. Файлы `.env.example`
сохраняются в Git как примеры конфигурации.

Для соединения устройств по LAN требуется фактический адрес backend-компьютера
и origin H5 frontend. Конкретные IP и порт frontend согласуются отдельно.

## Обмен JSON с frontend

Предлагаемый контракт и самостоятельные примеры Python/uni-app:
[docs/api-contract.md](docs/api-contract.md).
JSON передаётся в HTTP; файлы примеров используются для согласования и проверок.
Сейчас реализован только health, остальные маршруты обозначены как проект.

Из корня репозитория клиентские проверки запускаются без npm-зависимостей:

```powershell
node .\frontend\tests\test-api.mjs
node .\frontend\tests\test-fixtures.mjs
```
