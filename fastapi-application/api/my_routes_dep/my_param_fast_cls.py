from config_log import logF
from fastapi import (
    APIRouter,
    Cookie,
    Header,
    Path,
    Query,
    Request,
    Response,
)

from .pydantic_schema import RespFieldStyle

router_param_fast_cls_old = APIRouter(tags=["My Parameters - FastAPI Class Old"])


@router_param_fast_cls_old.get(
    "/my_items/{item_id}",
    response_model=RespFieldStyle,
)
def fastapi_class_old(
    # 1. PATH: Явное указание класса Path
    # Используется для валидации переменной из URL пути (/items/5)
    path_item_id: int = Path(
        alias="item_id",
        ge=1,
        description="Path - item_id должен быть больше 0",
    ),
    # 2. QUERY: Явное указание класса Query - имя через alias
    # Используется для параметров после ? (например, ?param_id=123)
    query_param_id: int | None = Query(
        default=None,
        alias="param_id",
        description="Query - первый параметр",
    ),
    # 3. HEADERS: Явное указание класса Header
    # FastAPI Извлекает значение из Header по alias (user_id)
    header_user_id: str | None = Header(
        default=None,
        alias="user-id",
        description="Header - ай-ди клиента",
    ),
    # 4. COOKIES: Явное указание класса Cookie
    # Извлекает значение из Cookie по alias (number_req)
    cookie_number_req: int = Cookie(
        default=1,
        alias="number-req",
        description="Cookie - количество запросов от клиента",
    ),
    # 5. REQUEST: Объект запроса
    request: Request = ...,
    # 6. RESPONSE: Объект ответа
    response: Response = ...,
):
    logF.info(f"fastapi_class_old :\n{path_item_id=} \n{query_param_id=}")
    logF.info(f"fastapi_class_old :\n{header_user_id=} \n{cookie_number_req=}")
    # logF.info(f"fastapi_class_old :\n{request.cookies=} \n{request.headers=}")

    logF.info(f"fastapi_class_old 1 :\nclient={request.client} \napp.title='{request.app.title}'")

    logF.info(
        f"fastapi_class_old 2 :\nclient={request.client} \napp.title='{request.app.title}'"
    )

    # Модифицируем Response (то, что уйдет клиенту)
    response.headers["X-Custom-Header"] = "Processed-By-FastAPI"
    response.set_cookie(key="visited", value="true")
    response.set_cookie(key="number-req", value=str(cookie_number_req + 1))

    return {
        "path": path_item_id,
        "query": query_param_id,
        "header": header_user_id,
        "cookie": cookie_number_req,
        "request": request.client.port,
    }
