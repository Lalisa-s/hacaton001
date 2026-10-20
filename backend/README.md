# Family Banking Backend

Минимальный backend для MVP детско-семейного банковского приложения.
Python 3.12+, FastAPI, Uvicorn, Pydantic 2, Pydantic Settings, SQLAlchemy 2 и SQLite.
Пользователи, карты, транзакции и другая банковская логика пока не реализованы.

## Открытие в PyCharm и установка

Backend находится в `backend/` общего репозитория `hacaton001`.
В PyCharm выберите **File → Open** и откройте общий каталог `hacaton001`.
Не создавайте внутри него ещё один проект или Git-репозиторий.
Все команды ниже выполняются в терминале **PowerShell**. Из корня репозитория
сначала перейдите в backend:

```powershell
cd backend
```

Для новой установки с установленным Python 3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item .env.example .env
}
```

Поддерживается также Python новее 3.12: укажите установленную версию
в команде создания окружения, например `py -3.13 -m venv .venv`.

Если `py` недоступен, создайте окружение через полный путь к Python 3.12+:

```powershell
& 'C:\path\to\Python312\python.exe' -m venv .venv
```

Если `backend/.venv` уже существует, не пересоздавайте его.
Окружение из прежней папки не переносится: для нового расположения используется
собственное окружение в `backend/.venv`. Локальный `.env` перенесён из прежнего
backend; команда выше создаёт его из примера только при отсутствии файла.
Для PyCharm: **Settings → Project → Python Interpreter → Add Interpreter →
Add Local Interpreter → Existing** и выберите
`hacaton001\backend\.venv\Scripts\python.exe`.
При настройке запуска задайте рабочим каталогом `hacaton001\backend`.
Активация окружения не требуется: команды используют его интерпретатор напрямую
и не зависят от ExecutionPolicy PowerShell.

## Запуск

Из каталога `backend`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- Health: <http://127.0.0.1:8000/api/v1/health>
- Swagger UI: <http://127.0.0.1:8000/docs>
- OpenAPI: <http://127.0.0.1:8000/openapi.json>

Остановка сервера: **Ctrl+C**. `--reload` предназначен для разработки.
`0.0.0.0` — адрес прослушивания всех сетевых интерфейсов;
в браузере используйте `127.0.0.1` или фактический IPv4 backend-компьютера.

Проверка из второго терминала:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
(Invoke-WebRequest http://127.0.0.1:8000/docs).StatusCode
```

Health возвращает HTTP 200 и `{"status":"ok"}`. Это проверка доступности
приложения; соединение с БД она не проверяет.

## uni-app Vue 3: подключение H5 по локальной сети

Frontend-разработчик запускает H5 средствами своего проекта uni-app.
Узнайте фактический IPv4 backend-компьютера командой `ipconfig`, а точный origin
H5-страницы — у frontend-разработчика. Origin — протокол, адрес и порт страницы
в браузере, без пути и завершающего `/`.

В `backend/.env` задайте явный JSON-массив разрешённых origins:

```dotenv
CORS_ORIGINS=["<FRONTEND_ORIGIN>"]
```

Замените `<FRONTEND_ORIGIN>` фактическим origin и перезапустите backend.
Если H5 открывается на компьютере и телефоне по разным origins, добавьте каждый
явно. Значения `http://localhost:5173` и `http://127.0.0.1:5173` в примере
конфигурации и настройках по умолчанию — унаследованные примеры локального
запуска. Реальные адрес и порт frontend пока не согласованы.

На frontend настройте `apiBaseUrl` как `http://<BACKEND_IP>:8000/api/v1`,
заменив `<BACKEND_IP>` фактическим IPv4 backend. Передайте это значение
из конфигурации frontend в функцию проверки:

```javascript
function checkBackend(apiBaseUrl) {
  uni.request({
    url: `${apiBaseUrl}/health`,
    method: 'GET',
    timeout: 10000,
    success(res) {
      if (res.statusCode === 200 && res.data.status === 'ok') {
        console.log('Backend подключён')
      } else {
        console.error('Неожиданный ответ API', res.statusCode, res.data)
      }
    },
    fail(error) {
      console.error('Ошибка подключения', error)
    }
  })
}
```

HTTP-статус нужно проверять внутри `success`: этот callback сам по себе
не означает успешный ответ API.

С другого компьютера или телефона откройте `http://<BACKEND_IP>:8000/docs`,
подставив IPv4 backend. Устройства должны быть доступны друг другу в локальной
сети. Если Windows Firewall блокирует соединение, разрешите Python/входящий
TCP 8000 для частной сети. `localhost` на телефоне или втором компьютере
указывает на это устройство, поэтому для API используйте адрес backend.

CORS разрешает credentials и использует явные списки origins, методов
(`GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`) и заголовков
(`Content-Type`, `Authorization`). Wildcard origins отклоняются конфигурацией.
Настройка подготовлена для интеграции; авторизация и cookies пока не реализованы.
Подробнее: [официальная документация FastAPI по CORS](https://fastapi.tiangolo.com/tutorial/cors/).
Пример frontend-запроса: [uni.request](https://uniapp.dcloud.net.cn/api/request/request.html).

## Конфигурация и база данных

Настройки находятся в `app/core/config.py`. `.env` читается из каталога `backend`,
независимо от рабочего каталога;
системные переменные окружения имеют приоритет. Пример хранится в `.env.example`;
локальный `.env` не попадает в Git. Списки в `.env` задаются JSON-массивом.
Подробнее: [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/).

`app/db/session.py` содержит SQLAlchemy engine и зависимость `get_db()`:
одна сессия на запрос с закрытием после завершения. Бизнес-моделей, таблиц
и автоматического создания схемы нет. SQLite входит в Python и не требует
отдельной установки. `family_banking.db` создастся при первом соединении с БД;
путь `sqlite:///./family_banking.db` считается от рабочего каталога.
Запускайте приложение из `backend`, чтобы локальная база создавалась там же.

Для будущего перехода на PostgreSQL потребуется установить соответствующий
драйвер (например, `psycopg`), изменить `DATABASE_URL` на
`postgresql+psycopg://user:password@localhost:5432/family_banking` и подготовить
схему/миграции, когда появятся модели. Сейчас драйвер и миграции не нужны.
SQLite-параметр `check_same_thread=False` применяется только к SQLite.
Подробнее: [SQLAlchemy SQLite](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html).

## Тесты

Из каталога `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
```

HTTP-тесты используют HTTPX AsyncClient с ASGITransport и работают без внешнего
сервера. Проверяются health, Swagger/OpenAPI, разрешённые и запрещённые CORS
origins, конфигурация и SQLAlchemy с временной SQLite.

## Структура общего репозитория

```text
hacaton001/
├── .git/                       # один общий Git-репозиторий
├── .gitignore
├── frontend/                   # код frontend-разработчика
└── backend/
    ├── app/
    │   ├── main.py             # FastAPI и CORS
    │   ├── api/v1/
    │   │   ├── router.py
    │   │   └── endpoints/health.py
    │   ├── core/config.py      # настройки
    │   ├── db/session.py       # engine и сессия SQLAlchemy
    │   └── schemas/wire_models.py # проверка и сборка JSON
    ├── tests/
    │   ├── test_api.py
    │   ├── test_config.py
    │   ├── test_database.py
    │   └── test_json_schemas.py
    ├── examples/
    │   ├── json_exchange.py   # запускаемый пример JSON
    │   └── build_json_examples.py # генератор общих JSON и JSON Schema
    ├── .venv/                  # локальное окружение, игнорируется Git
    ├── .env                    # локальные настройки, игнорируются Git
    ├── .env.example
    ├── pytest.ini
    ├── requirements.txt
    └── README.md
```

Каталоги Python-пакетов также содержат `__init__.py`.
`requirements.txt` фиксирует версии прямых зависимостей проверенной установки;
остальные пакеты устанавливаются автоматически как их зависимости.

## Git

Работа frontend и backend ведётся в одном репозитории `hacaton001`.
Внутри `backend` и `frontend` не выполняйте `git init` и не копируйте `.git`
из прежнего проекта. Посмотреть состояние общего репозитория из `backend`:

```powershell
git -C .. status --short --branch
git -C .. remote -v
```

Окружение, `.env`, кэши и локальные базы исключены общим `.gitignore`.
Коммиты, отправка изменений и слияния выполняются для общего репозитория.

## Код обработки JSON

Pydantic-схемы и функции `parse_transfer_json`, `public_projection`,
`account_response` находятся в `app/schemas/wire_models.py`.
Это проверка данных и сборка ответов; операции с деньгами выполняются будущими сервисами.

Пример из терминала PyCharm с рабочей папкой `backend`:

```powershell
.\.venv\Scripts\python.exe -m examples.json_exchange
.\.venv\Scripts\python.exe -m pytest tests/test_json_schemas.py -q
```

Пример читает файлы из `../docs/json-exchange/examples/`, проверяет запрос и
собирает публичный JSON счёта. Он не записывает данные в БД.

Можно указать свой файл запроса:

```powershell
.\.venv\Scripts\python.exe -m examples.json_exchange --request-file ..\docs\json-exchange\examples\transfer-request.json
```

После изменения схем обновите общие JSON-примеры и JSON Schema:

```powershell
.\.venv\Scripts\python.exe -m examples.build_json_examples
```

Генератор использует `app/schemas/wire_models.py` и записывает общие материалы
в `../docs/json-exchange/examples/` и `../docs/json-exchange/schemas/`.

В коде backend импортируйте схемы так:

```python
from app.schemas.wire_models import AccountRead, TransferCreate, parse_transfer_json
```
