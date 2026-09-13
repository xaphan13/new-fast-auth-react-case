from typing import Annotated

from fastapi import (
    Cookie,
    Header,
    Path,
    Query,
)


def get_item_id(
    item_id: Annotated[
        int,
        Path(
            alias="item_id",
            ge=1,
            description="Path - item_id должен быть больше 0",
        ),
    ],
) -> int:
    """Извлекает и валидирует ID из пути."""
    return item_id


def get_param_id(
    param_id: Annotated[
        int | None,
        Query(
            alias="param_id",
            description="Query - первый параметр",
        ),
    ] = None,
) -> int | None:
    """Извлекает параметр из строки запроса."""
    return param_id


def get_user_id(
    user_id: Annotated[
        str | None,
        Header(
            alias="user-id",
            description="Header - ай-ди клиента",
        ),
    ] = None,
) -> str | None:
    """Извлекает ID пользователя из заголовков."""
    return user_id


def get_number_req(
    number_req: Annotated[
        int,
        Cookie(
            alias="number-req",
            description="Cookie - количество запросов от клиента",
        ),
    ] = 1,
) -> int:
    """Извлекает счетчик запросов из кук."""
    return number_req
