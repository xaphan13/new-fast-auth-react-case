from typing import Annotated

from pydantic import BaseModel, Field


# ======================================================= #
# 1. МОДЕЛЬ ОТВЕТА (RESPONSE MODEL) pydantic Class Style  #
# ======================================================= #
class RespFieldStyle(BaseModel):
    # Обязательное поле (нет дефолтного значения)
    path: int = Field(
        ...,
        description="ID из пути URL",
    )
    # Необязательное поле (дефолт None)
    query: int | None = Field(
        None,
        description="ID из параметров запроса",
    )
    header: str | None = Field(
        None,
        description="ID пользователя из заголовка",
    )
    cookie: int = Field(
        ...,
        description="Счетчик из куки",
    )
    request: int = Field(
        ...,
        description="Порт клиента",
    )


# ================================================= #
# 2. МОДЕЛЬ ОТВЕТА (RESPONSE MODEL) Annotated Style #
# ================================================= #
class RespAnnotated(BaseModel):
    # Обязательное поле (нет дефолтного значения = None)
    path: Annotated[
        int,
        Field(description="ID из пути URL"),
    ]
    # Значение по умолчанию (= None) выносится за Annotated
    query: Annotated[
        int | None,
        Field(description="ID из параметров запроса"),
    ] = None
    header: Annotated[
        str | None,
        Field(description="ID пользователя из заголовка"),
    ] = None
    cookie: Annotated[
        int,
        Field(description="Счетчик из куки"),
    ]
    request: Annotated[
        int,
        Field(description="Порт клиента"),
    ]
