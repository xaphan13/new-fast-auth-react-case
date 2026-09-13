from typing import Annotated

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

from .pydantic_schema import RespAnnotated

router_param_fast_cls = APIRouter(tags=["My Parameters - FastAPI Class Annotated"])


@router_param_fast_cls.get(
    "/my_items/{item_id}",
    response_model=RespAnnotated,
)
def fastapi_class_annotated(
    # 1. PATH
    # Тип int теперь явно виден IDE.
    # Alias "item_id" связывает аргумент path_item_id с {item_id} в URL.
    path_item_id: Annotated[
        int,
        Path(
            alias="item_id",
            ge=1,
            description="Path - item_id должен быть больше 0",
        ),
    ],
    # 2. QUERY
    # Значение по умолчанию (= None) выносим наружу.
    # Внутри Query() оставляем только метаданные.
    query_param_id: Annotated[
        int | None,
        Query(
            alias="param_id",
            description="Query - первый параметр",
        ),
    ] = None,
    # 3. HEADERS
    header_user_id: Annotated[
        str | None,
        Header(
            alias="user-id",
            description="Header - ай-ди клиента",
        ),
    ] = None,
    # 4. COOKIES
    # Значение по умолчанию (= 1) выносим наружу.
    cookie_number_req: Annotated[
        int,
        Cookie(
            alias="number-req",
            description="Cookie - количество запросов от клиента",
        ),
    ] = 1,
    # 5. REQUEST: Объект запроса
    request: Request = ...,
    # 6. RESPONSE: Объект ответа
    response: Response = ...,
):
    logF.info(f"fastapi_class_annotated :\n{path_item_id=} \n{query_param_id=}")
    logF.info(f"fastapi_class_annotated :\n{header_user_id=} \n{cookie_number_req=}")
    # logF.info(f"fastapi_class_annotated :\n{request.cookies=} \n{request.headers=}")
    logF.info(f"fastapi_class_annotated :\n{request.client=} \n{request.app.title=}")

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
