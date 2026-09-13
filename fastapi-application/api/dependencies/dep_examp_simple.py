from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Header,
)

from .func_deps import (
    get_header_dependency,
    get_x_foo_bar,
)

router_dep_simple = APIRouter()


@router_dep_simple.get("/single-direct-dependency")
def single_direct_dependency(
    foobar: Annotated[
        str,
        Header(),
    ],
):
    return {
        "foobar": foobar,
        "message": "single direct dependency foobar",
    }


@router_dep_simple.get("/single-via-func")
def single_via_func(
    foobar: Annotated[
        str,
        Depends(get_x_foo_bar),
    ],
):
    return {
        "x-foobar": foobar,
        "message": "single via-func dependency foobar",
    }


@router_dep_simple.get("/multi-direct-and-via-func")
def multi_direct_and_via_func(
    fizzbuzz: Annotated[
        str,
        Header(alias="x-fizz-buzz"),
    ],
    foobar: Annotated[
        str,
        Depends(get_x_foo_bar),
    ],
):
    return {
        "x-fizz-buzz": fizzbuzz,
        "x-foobar": foobar,
        "message": "multi-direct and-via-func dependency foobar",
    }


@router_dep_simple.get("/multi-indirect")
def multi_indirect_dependencies(
    foobar: Annotated[
        str,
        Depends(get_header_dependency("x-foobar")),
    ],
    fizzbuzz: Annotated[
        str,
        Depends(
            get_header_dependency(
                "x-fizz-buzz",
                default_value="FizzBuzz",
            ),
        ),
    ],
):
    return {
        "x-fizz-buzz": fizzbuzz,
        "x-foobar": foobar,
        "message": "multi-indirect dependency",
    }
