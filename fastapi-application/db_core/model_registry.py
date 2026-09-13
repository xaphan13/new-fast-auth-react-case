"""Явная регистрация ORM-моделей на границах приложения и миграций."""

__all__ = ("load_model_registry",)


def load_model_registry() -> None:
    """Загрузить все текущие модельные модули в общую SQLAlchemy metadata."""

    from auth_users.models import User
    from ex_order_product.model_order_product import (
        Order,
        OrderProductAssociation,
        Product,
    )
    from md_articles.models import BlogPost, BlogUser

    # Имена импортов намеренно используются только для регистрации классов в metadata.
    _ = (BlogPost, BlogUser, Order, OrderProductAssociation, Product, User)
