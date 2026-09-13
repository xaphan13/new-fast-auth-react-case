from __future__ import annotations

from db_core.model_base import Base
from db_core.type_for_models import (
    int_primary_key,
    str_len_50,
    str_len_100,
    time_stamp_utc,
)
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    relationship,
)


class Order(Base):
    id: Mapped[int_primary_key]

    created_at: Mapped[time_stamp_utc]
    promocode: Mapped[str_len_50 | None]

    # association between Order -> Association
    products_details = relationship(
        "OrderProductAssociation",
        back_populates="order",
        cascade="all, delete",
        overlaps="orders",
    )

    # association many to many
    products = relationship(
        "Product",
        secondary="order_product_association",
        back_populates="orders",
        overlaps="products_details",
    )


class Product(Base):
    id: Mapped[int_primary_key]

    name: Mapped[str_len_50]
    description: Mapped[str_len_100]
    price: Mapped[int]

    # association between Product -> Association
    orders_details = relationship(
        "OrderProductAssociation",
        back_populates="product",
        cascade="all, delete",
        overlaps="products",
    )

    # association many to many
    orders = relationship(
        "Order",
        secondary="order_product_association",
        back_populates="products",
        overlaps="orders_details",
    )


class OrderProductAssociation(Base):
    __tablename__ = "order_product_association"

    id: Mapped[int_primary_key]

    count = Column(Integer(), default=1, server_default="1")
    unit_price = Column(Integer(), default=0, server_default="0")

    order_id = Column(
        Integer(),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )

    product_id = Column(
        Integer(),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )

    # association between Assocation -> Order
    order = relationship(
        "Order",
        back_populates="products_details",
        overlaps="orders, products",
    )

    # association between Assocation -> Product
    product = relationship(
        "Product",
        back_populates="orders_details",
        overlaps="orders, products",
    )
    # fmt: off
    __table_args__ = (
        UniqueConstraint(
            order_id, product_id,
            name="idx_unique_order_product",
        ),
    )
    # fmt: on
