from typing import Annotated

from fastapi import APIRouter, Depends

from .cls_deps import (
    HeaderAccessDependency,
    PathReaderDependency,
    TokenIntrospectResult,
)
from .func_deps import (
    get_great_helper,
    get_header_dependency,
)
from .helper import GreatHelper, GreatService

router_dep_cls = APIRouter()


@router_dep_cls.get("/top-level-helper-creation")
def top_level_helper_creation(
    helper_name: Annotated[
        str,
        Depends(
            get_header_dependency(
                "x-helper-name",
                default_value="HelperOne",
            ),
        ),
    ],
    helper_default: Annotated[
        str,
        Depends(
            get_header_dependency(
                "x-helper-default-value",
            ),
        ),
    ],
):
    helper = GreatHelper(
        name=helper_name,
        default=helper_default,
    )
    return {
        "helper": helper.as_dict(),
        "message": "Top level helper creation",
    }


@router_dep_cls.get("/helper-as-dependency")
def helper_as_dependency(
    helper: Annotated[
        GreatHelper,
        Depends(get_great_helper),
    ],
):
    return {
        "helper": helper.as_dict(),
        "message": "helper-as-dependency",
    }


@router_dep_cls.get("/great-service-as-dependency")
def get_great_service_dependency(
    service: Annotated[
        GreatService,
        Depends(GreatService),
    ],
):
    return {
        "service": service.as_dict(),
        "message": "great-service-as-dependency",
    }


@router_dep_cls.get("/path-reader-dependency-from-method")
def path_reader_dependency(
    reader: Annotated[
        PathReaderDependency,
        Depends(PathReaderDependency(source="direct/bar").as_dependency),
        # Depends(path_reader.as_dependency),
    ],
):
    return {
        "reader": reader.read(foo="bar"),
        "message": "path-reader-dependency-from-method",
    }


@router_dep_cls.get("/direct-cls-dependency")
def direct_cls_dependency(
    token_data: Annotated[
        TokenIntrospectResult,
        Depends(HeaderAccessDependency(secret_token="qwerty-abc")),
        # Depends(access_required),
    ],
):
    return {
        "token_data": token_data.model_dump(),
        "message": "direct-cls-dependency",
    }
