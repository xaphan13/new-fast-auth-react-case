from core.config import settings
from fastapi import APIRouter

from .my_param_dep_cls import router_param_dep_cls
from .my_param_dep_func import router_param_dep_func
from .my_param_fast_ann import router_param_fast_cls
from .my_param_fast_cls import router_param_fast_cls_old

router_param_extract = APIRouter()


router_param_extract.include_router(
    router_param_fast_cls_old,
    prefix=settings.api.v1.fastapi_class_old,
)

router_param_extract.include_router(
    router_param_fast_cls,
    prefix=settings.api.v1.fastapi_class_annotated,
)

router_param_extract.include_router(
    router_param_dep_cls,
    prefix=settings.api.v1.depends_class_annotated,
)

router_param_extract.include_router(
    router_param_dep_func,
    prefix=settings.api.v1.depends_function_annotated,
)
