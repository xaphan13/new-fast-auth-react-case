from __future__ import annotations

from datetime import UTC, datetime, timezone
from typing import Annotated

from sqlalchemy import (
    DateTime,
    String,
    func,
)
from sqlalchemy.orm import mapped_column

int_primary_key = Annotated[
    int,
    mapped_column(
        primary_key=True,
        index=True,
    ),
]


time_stamp_utc = Annotated[
    datetime,
    mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    ),
]


str_len_20 = Annotated[
    str,
    mapped_column(String(20)),
]


str_len_50 = Annotated[
    str,
    mapped_column(String(50)),
]


str_len_60 = Annotated[
    str,
    mapped_column(String(60)),
]


str_len_100 = Annotated[
    str,
    mapped_column(String(100)),
]


str_len_120 = Annotated[
    str,
    mapped_column(String(120)),
]


text_content = Annotated[
    str,
    mapped_column(String(10000)),
]
