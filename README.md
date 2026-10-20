# hacaton001

Общий репозиторий MVP детско-семейного банковского приложения.

```text
hacaton001/
├── backend/       # FastAPI, SQLAlchemy, SQLite, тесты
├── frontend/      # место для классического uni-app / Vue 3
├── .gitignore
└── README.md
```

В `backend/` размещён подготовленный Python-проект. В `frontend/` пока только
`.gitkeep`, чтобы папка сохранялась в Git. Frontend-разработчик добавляет свой
проект в эту папку на своём компьютере.

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
