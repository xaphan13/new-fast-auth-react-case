from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


# ========================================================= #
# 1. RESPONSE MODEL - типы и валидация вынесены из pydantic #
# ========================================================= #
def check_port_range(v: int) -> int:
    if not (1024 <= v <= 65535):
        raise ValueError("Порт должен быть в диапазоне 1024-65535")
    return v


# ID из пути: положительное число
PathID = Annotated[
    int,
    Field(ge=1, description="ID из URL"),
]

# Query: либо None, либо число от 1 до 1000
QueryID = Annotated[
    int | None,
    Field(ge=1, le=1000, description="Параметр Query"),
]

# Custom Validator для порта
PortNumber = Annotated[
    int,
    AfterValidator(check_port_range),
]


# --- МОДЕЛЬ ---
class RespAfterValid(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    # Используем созданные типы
    path: PathID
    # Значение по умолчанию выносим за Annotated
    query: QueryID = None
    header: Annotated[
        str | None,
        Field(description="ID пользователя из заголовка"),
    ] = None
    cookie: int = Field(
        ...,
        description="Счетчик из куки",
    )
    request: PortNumber


# =================================================== #
# 2. RESPONSE MODEL - валидация полей через декоратор #
# =================================================== #
class RespDecorValid(BaseModel):
    # Поля объявляем просто (типы), вся логика будет ниже
    path: int
    query: int | None = None
    header: Annotated[
        str | None,
        Field(description="ID пользователя из заголовка"),
    ] = None
    cookie: Annotated[
        int,
        Field(description="Счетчик из куки"),
    ]
    request: int

    # 1. ПРОВЕРКА (Validation): если path < 1, то ошибка
    @field_validator("path")
    @classmethod
    def validate_path_is_even(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Path ID должен быть больше 0")
        return v

    # 2. СЛОЖНАЯ ЛОГИКА: Query должен быть (1 <= v <= 1000)
    @field_validator("query")
    @classmethod
    def validate_query_safe(cls, v: int | None) -> int | None:
        if 1 <= v <= 1000:
            return v
        raise ValueError("либо None, либо число от 1 до 1000")

    # 3. ОБЪЕДИНЕНИЕ (Несколько полей): Проверка порта
    @field_validator("request")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not (1024 <= v <= 65535):
            raise ValueError(f"Порт {v} не разрешен")
        return v
