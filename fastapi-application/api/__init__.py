from core.config import settings
from fastapi import APIRouter

from .dependencies import router_dep_examples
from .my_routes_dep import router_param_extract

router_api = APIRouter(
    prefix=settings.api.prefix,
)


router_api_v1 = APIRouter(
    prefix=settings.api.v1.prefix,
)

router_api_v1.include_router(
    router_dep_examples,
    prefix=settings.api.v1.dep_examples,
)

router_api_v1.include_router(
    router_param_extract,
)


router_api.include_router(router_api_v1)
