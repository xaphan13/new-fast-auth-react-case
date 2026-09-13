from datetime import datetime
from enum import Enum

from pydantic import BaseModel


# ==================================================================== #
#                   BaseModel - Order - pydantic                       #
# ==================================================================== #
class OrderGetQuery(BaseModel):
    id: int | None = None
    created_at: datetime | None = None
    promocode: str | None = None


class OrderCreateBody(BaseModel):
    promocode: str | None = None


class OrderUpdateBody(BaseModel):
    promocode: str | None = None


class OrderGetAllOrderbyQuery(str, Enum):
    id = "id"
    time = "time"
    promocode = "promocode"


class OrderGetOrderbyList(BaseModel):
    order_by_list: list[OrderGetAllOrderbyQuery] = ["id"]


# ======================================================================= #
#                     BaseModel - Product - pydantic                      #
# ======================================================================= #
class ProductGetQuery(BaseModel):
    id: int | None = 0
    name: str | None = None
    description: str | None = None
    price: int | None = None


class ProductCreateBody(BaseModel):
    name: str
    description: str
    price: int


class ProductUpdateBody(BaseModel):
    name: str | None = ""
    description: str | None = ""
    price: int | str = ""


# schemas are used when : get(GET) a OrderProductAssociation(Base)
class AssociationGetQuery(BaseModel):
    id: int | None = 0
    count: int | None = 0
    unit_price: int | None = 0
    order_id: int | None = 0
    product_id: int | None = 0


# =========================================================== #
#             RESPONSE : response_model pydantic              #
# =========================================================== #
class OrderProductBase(BaseModel):
    class Config:
        from_attributes = True


# schema is used as a response_model for Order(Base)
class OrderResp(OrderProductBase):
    id: int
    created_at: datetime
    promocode: str


# schema is used as a response_model for Product(Base)
class ProductResp(OrderProductBase):
    id: int
    name: str
    description: str
    price: int


# schema is used as a response_model for OrderProductAssociation(Base)
class AssociationResp(BaseModel):
    id: int
    count: int
    unit_price: int
    order_id: int
    product_id: int


# ==================================================================== #
#     relationship('Order', secondary='order_product_association')     #
# ==================================================================== #
class ProductRespWithOrders(ProductResp):
    orders: list[OrderResp]


class ProductRespWithsAssoc(ProductResp):
    orders_details: list[AssociationResp]


class ProductRespWithOrdersAssoc(ProductResp):
    orders: list[OrderResp]
    orders_details: list[AssociationResp]


# ====================================================================== #
#     relationship('Product', secondary='order_product_association')     #
# ====================================================================== #
class OrderRespWithProducts(OrderResp):
    products: list[ProductResp]


class OrderRespWithAssoc(OrderResp):
    products_details: list[AssociationResp]


class OrderRespWithProductsAssoc(OrderResp):
    products: list[ProductResp]
    products_details: list[AssociationResp]


class OrderRespWithProductsDetails(OrderResp):
    products: list[ProductRespWithsAssoc]
