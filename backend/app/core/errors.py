"""Safe JSON errors; request bodies and database exceptions are never echoed."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def business_error(_request: Request, exc: ApiError):
        return JSONResponse(status_code=exc.status_code, content={
            "error": {"code": exc.code, "message": exc.message, "details": []},
        })

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError):
        details = [{"field": ".".join(str(part) for part in item["loc"]),
                    "code": item["type"]} for item in exc.errors()]
        return JSONResponse(status_code=422, content={"error": {
            "code": "VALIDATION_ERROR", "message": "Проверьте поля запроса", "details": details,
        }})

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, exc: HTTPException):
        codes = {400: "BAD_REQUEST", 401: "UNAUTHORIZED", 403: "ACCESS_DENIED",
                 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}
        messages = {400: "Некорректный запрос", 401: "Требуется вход",
                    403: "Нет доступа", 404: "Объект не найден", 405: "Метод не поддерживается"}
        return JSONResponse(status_code=exc.status_code, headers=exc.headers, content={"error": {
            "code": codes.get(exc.status_code, f"HTTP_{exc.status_code}"),
            "message": messages.get(exc.status_code, "Не удалось выполнить запрос"), "details": [],
        }})
