"""Demo actor selection. This is deliberately not real authentication."""

from typing import Annotated

from fastapi import Header, Request

from app.core.errors import ApiError
from app.schemas.wire_models import MAX_JS_INTEGER


def get_demo_actor_id(
    request: Request,
    x_demo_user_id: Annotated[int | None, Header(
        gt=0, le=MAX_JS_INTEGER,
        description="Только DEMO_MODE: небезопасный выбор демо-пользователя, не авторизация",
    )] = None,
) -> int:
    settings = request.app.state.settings
    if not settings.demo_mode:
        raise ApiError(403, "DEMO_MODE_DISABLED", "Демонстрационный режим выключен")
    # No database query here: write services must lock before their first query.
    return settings.demo_user_id if x_demo_user_id is None else x_demo_user_id
