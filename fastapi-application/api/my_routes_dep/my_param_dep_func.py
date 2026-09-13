from typing import Annotated

from config_log import logF
from fastapi import (
    APIRouter,
    Depends,
    Request,
    Response,
)

from .dep_func_schema import (
    get_item_id,
    get_number_req,
    get_param_id,
    get_user_id,
)
from .pydantic_validator import RespDecorValid

router_param_dep_func = APIRouter(tags=["My Parameters - Depends Functions Annotated"])


@router_param_dep_func.get(
    "/my_items/{item_id}",
    response_model=RespDecorValid,
)
def depends_function_annotated(
    # 1. PATH: Получаем результат функции get_path_item_id
    path_item_id: Annotated[
        int,
        Depends(get_item_id),
    ],
    # 2. QUERY: Получаем результат функции get_query_param_id
    query_param_id: Annotated[
        int | None,
        Depends(get_param_id),
    ],
    # 3. HEADERS: Получаем результат функции get_header_user_id
    header_user_id: Annotated[
        str | None,
        Depends(get_user_id),
    ],
    # 4. COOKIES: Получаем результат функции get_cookie_number_req
    cookie_number_req: Annotated[
        int,
        Depends(get_number_req),
    ],
    # 5. REQUEST: Объект запроса
    request: Request = ...,
    # 6. RESPONSE: Объект ответа
    response: Response = ...,
):
    logF.info(f"depends_function_annotated :\n{path_item_id=} \n{query_param_id=}")
    logF.info(f"depends_function_annotated :\n{header_user_id=} \n{cookie_number_req=}")
    # logF.info(f"depends_function_annotated :\n{request.cookies=} \n{request.headers=}")
    logF.info(f"depends_function_annotated :\n{request.client=} \n{request.app.title=}")

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
