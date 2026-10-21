# Family Banking Backend

Демонстрационный backend для MVP детско-семейного банковского приложения.
Python 3.12+, FastAPI, Uvicorn, Pydantic 2, Pydantic Settings, SQLAlchemy 2 и SQLite.
Реализованы демонстрационные пользователи, разрешённые счета, переводы родителя,
история и детские копилки с семейным пополнением и подтверждением родителя.
Детская привязка задаётся явно, владельцем счёта остаётся родитель. Настоящая
аутентификация, реальные банковские операции и карты в этот этап не входят.

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

## Демонстрационный API

В локальном `.env` для включения банковских маршрутов задайте:

```dotenv
DEMO_MODE=true
DEMO_USER_ID=10
```

По умолчанию `DEMO_MODE=false`: health остаётся доступным, а демонстрационные
маршруты возвращают `403 DEMO_MODE_DISABLED`. После изменения `.env` перезапустите
сервер. В режиме демонстрации нет настоящего входа: пользователь выбирается
настройкой `DEMO_USER_ID` либо необязательным заголовком `X-Demo-User-Id`.
Реальные персональные данные, реквизиты и деньги использовать нельзя.

При запуске создаются отсутствующие таблицы и демо-семья `1`: родитель `10`,
ребёнок `20` с `parent_id=10`, другой родитель `11`. Счета `100` и `101`
принадлежат `10`; ребёнку явно доступен `101` с копилкой `500`. Счёт `110`
принадлежит `11` и начинается с `15000` копеек. Все три счёта подключены к семье.
Начальные остатки: `20000` и `10000` копеек BYN; у `101` зарезервировано `3000`,
поэтому доступно `7000`. Дневные лимиты — `15000` и `5000` копеек соответственно.
Это настройки демонстрации, не законодательные пределы. Перезапуск не возвращает
начальные остатки и не удаляет историю.

| Метод и путь | Назначение |
| --- | --- |
| `GET /api/v1/health` | Доступность приложения |
| `GET /api/v1/me` | Действующий демонстрационный пользователь |
| `GET /api/v1/accounts` | Разрешённые счета: свои у родителя, явно подключённые у ребёнка |
| `GET /api/v1/accounts/{id}` | Один разрешённый счёт |
| `GET /api/v1/accounts/{id}/transactions?limit=50&offset=0` | История, сначала новые |
| `POST /api/v1/transactions` | Перевод между своими счетами родителя |
| `GET/POST /api/v1/pigs`, `PATCH /api/v1/pigs/{id}` | Список, создание и имя копилки |
| `/api/v1/pigs/{id}/contributions`, `/break-requests`, `/break` | Пополнение, запрос ребёнка, разбитие родителем |
| `/api/v1/pig-break-requests` и команды `/approve`, `/reject` | Запросы и решения назначенного родителя |
| `GET /api/v1/family/members` | Публичный список членов своей семьи |

Денежное тело: `{ "cender": 100, "recipient": 101, "amount": 2500 }`.
Стороны — ID счетов, сумма — целые копейки. Балансы, время и ID операции назначает
backend. Проверки прав, активности, резервов и лимита выполняются на сервере;
списание, зачисление и история сохраняются вместе. Ребёнку обычный
`POST /transactions` запрещён; для копилок есть отдельный маршрут пополнения.
Создание, имя, два варианта ответа пополнения, pending/approve/reject и
сохранение резерва: [контракт копилок](../docs/piggy-banks.md).

Полный контракт, ответы, коды ошибок и готовые PowerShell/uni-app примеры:
[docs/api-contract.md](../docs/api-contract.md). После успешного POST обновите
счета и историю через GET. При сетевой ошибке не повторяйте денежный POST
автоматически: серверная идемпотентность пока не реализована.

## uni-app Vue 3: подключение H5 по локальной сети

В общем репозитории уже есть H5: из корня запустите `dev.ps1`, затем откройте
`http://localhost:5173` или `http://<IPv4-frontend>:5173` на телефоне в той же сети.
Все запросы интерфейса идут на тот же origin через Vite-прокси `/api`.
Если backend на другом компьютере, задайте его адрес в `frontend/.env` как
`API_PROXY_TARGET=http://<IPv4-backend>:8000`. Подробности —
[frontend/README.md](../frontend/README.md).

Ниже — дополнительная настройка для прямых запросов из браузера на backend
при явно заданном `VITE_API_BASE_URL`. Узнайте фактический IPv4 через `ipconfig`.
Origin — протокол, адрес и порт H5-страницы, без пути и завершающего `/`.

В `backend/.env` задайте явный JSON-массив разрешённых origins:

```dotenv
CORS_ORIGINS=["<FRONTEND_ORIGIN>"]
```

Замените `<FRONTEND_ORIGIN>` фактическим origin и перезапустите backend.
Если H5 открывается на компьютере и телефоне по разным origins, добавьте каждый
явно. Значения `http://localhost:5173` и `http://127.0.0.1:5173` в примере
конфигурации и настройках по умолчанию — унаследованные примеры локального
запуска. Текущий Vite использует фиксированный порт `5173`; LAN-origin
содержит фактический IPv4 frontend-компьютера.

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
(`Content-Type`, `Authorization`, `X-Demo-User-Id`). Wildcard origins отклоняются
конфигурацией. Настоящая аутентификация и cookies пока не реализованы.
Подробнее: [официальная документация FastAPI по CORS](https://fastapi.tiangolo.com/tutorial/cors/).
Пример frontend-запроса: [uni.request](https://uniapp.dcloud.net.cn/api/request/request.html).

## Конфигурация и база данных

Настройки находятся в `app/core/config.py`. `.env` читается из каталога `backend`,
независимо от рабочего каталога;
системные переменные окружения имеют приоритет. Пример хранится в `.env.example`;
локальный `.env` не попадает в Git. Списки в `.env` задаются JSON-массивом.
Подробнее: [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/).

SQLAlchemy-модели пользователей, счетов, семьи, детских связей, копилок, запросов
на разбитие и переводов находятся в `app/models/`.
Для экземпляра приложения создаются engine и фабрика сессий из его настроек;
запрос получает отдельную сессию, которая закрывается после завершения.
При `DEMO_MODE=true` lifespan создаёт отсутствующие таблицы и демонстрационные
записи, не сбрасывая существующие данные. Механизма миграций пока нет: повторный
запуск не обновляет структуру уже существующих таблиц.

SQLite входит в Python и не требует отдельной установки. Путь
`sqlite:///./family_banking.db` считается от рабочего каталога. Запускайте
приложение из `backend`, чтобы база создавалась там же. Для денежных записей
SQLite использует `BEGIN IMMEDIATE`; деньги и история меняются одной транзакцией.
Время операций хранится как UTC, календарные лимиты рассчитываются по UTC+03.

Для будущего перехода на PostgreSQL потребуется установить соответствующий
драйвер (например, `psycopg`), изменить `DATABASE_URL` на
`postgresql+psycopg://user:password@localhost:5432/family_banking` и подготовить
схему/миграции. Текущий демонстрационный запуск рассчитан на SQLite; PostgreSQL
не требуется и его драйвер сейчас не устанавливается.
SQLite-параметр `check_same_thread=False` применяется только к SQLite.
Подробнее: [SQLAlchemy SQLite](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html).

## Тесты

Из каталога `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
```

HTTP-тесты используют HTTPX AsyncClient с ASGITransport без внешнего сервера.
Контрактные тесты проверяют сериализацию JSON и исключение секретных полей.
Проверки финансового сценария должны использовать временную SQLite, чтобы
не менять локальную демонстрационную БД. Фактический результат тестов получают
командой выше; сохранённые JSON-примеры сами по себе его не подтверждают.

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
    │   │   └── endpoints/      # health, пользователи, счета, переводы и копилки
    │   ├── core/              # настройки и общая обработка API
    │   ├── db/                # engine, сессии, старт демонстрационной БД
    │   ├── models/            # счета, семья, детский доступ, копилки и запросы
    │   ├── services/          # проверки прав, балансы и переводы
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
Это проверка данных и сборка ответов. Денежный сервис используется HTTP API;
самостоятельный пример ниже только читает фикстуры, не выполняет перевод.

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
