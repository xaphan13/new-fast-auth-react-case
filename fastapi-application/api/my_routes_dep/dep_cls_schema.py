from typing import Annotated

from fastapi import (
    Cookie,
    Header,
    Path,
    Query,
)


# ==========================================
# 1. CLASS для PATH (Dependency Class)
# ==========================================
class PathData:
    def __init__(
        self,
        item_id: Annotated[
            int,
            Path(
                alias="item_id",
                ge=1,
                description="Path - item_id должен быть больше 0",
            ),
        ],
    ):
        self.path_item_id = item_id


# ==========================================
# 2. CLASS для QUERY (Pydantic Model)
# ==========================================
class QueryData:
    def __init__(
        self,
        param_id: Annotated[
            int | None,
            Query(
                alias="param_id",
                description="Query - первый параметр",
            ),
        ] = None,
    ):
        self.query_param_id = param_id


# ==========================================
# 3. CLASS для HEADERS (Dependency Class)
# ==========================================
class HeaderData:
    def __init__(
        self,
        user_id: Annotated[
            str | None,
            Header(
                alias="user-id",
                description="Header - ай-ди клиента",
            ),
        ] = None,
    ):
        self.header_user_id = user_id


# ==========================================
# 4. CLASS для COOKIES (Dependency Class)
# ==========================================
class CookieData:
    def __init__(
        self,
        number_req: Annotated[
            int,
            Cookie(
                alias="number-req",
                description="Cookie - количество запросов от клиента",
            ),
        ] = 1,
    ):
        self.cookie_number_req = number_req
