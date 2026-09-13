from typing import Annotated

from config_log import logF
from fastapi import (
    APIRouter,
    Depends,
    Request,
    Response,
)

from .dep_cls_schema import (
    CookieData,
    HeaderData,
    PathData,
    QueryData,
)
from .pydantic_validator import RespAfterValid

router_param_dep_cls = APIRouter(tags=["My Parameters - Depends Class Annotated"])


@router_param_dep_cls.get(
    "/my_items/{item_id}",
    response_model=RespAfterValid,
)
def depends_class_annotated(
    # Внедряем каждый класс через Depends()
    path_cls: Annotated[
        PathData,
        Depends(),
    ],  # 1. Path Class
    query_cls: Annotated[
        QueryData,
        Depends(),
    ],  # 2. Query Class
    header_cls: Annotated[
        HeaderData,
        Depends(),
    ],  # 3. Header Class
    cookie_cls: Annotated[
        CookieData,
        Depends(),
    ],  # 4. Cookie Class
    # 5. REQUEST: Объект запроса
    request: Request = ...,
    # 6. RESPONSE: Объект ответа
    response: Response = ...,
):
    logF.info(f"depends_class_annotated :\n{path_cls.path_item_id=} \n{query_cls.query_param_id=}")
    logF.info(
        f"depends_class_annotated :"
        + f"\n{header_cls.header_user_id=} "
        + f"\n{cookie_cls.cookie_number_req=}"
    )
    # logF.info(f"depends_class_annotated :\n{request.cookies=} \n{request.headers=}")
    logF.info(f"depends_class_annotated :\n{request.client=} \n{request.app.title=}")

    # Модифицируем Response (то, что уйдет клиенту)
    response.headers["X-Custom-Header"] = "Processed-By-FastAPI"
    response.set_cookie(key="visited", value="true")
    response.set_cookie(key="number-req", value=str(cookie_cls.cookie_number_req + 1))

    return {
        "path": path_cls.path_item_id,
        "query": query_cls.query_param_id,
        "header": header_cls.header_user_id,
        "cookie": cookie_cls.cookie_number_req,
        "request": request.client.port,
    }
