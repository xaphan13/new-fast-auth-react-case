from fastapi import APIRouter

from .dep_examp_cls import router_dep_cls
from .dep_examp_simple import router_dep_simple

router_dep_examples = APIRouter(tags=["Dependencies Examples"])


router_dep_examples.include_router(
    router_dep_simple,
)


router_dep_examples.include_router(
    router_dep_cls,
)
