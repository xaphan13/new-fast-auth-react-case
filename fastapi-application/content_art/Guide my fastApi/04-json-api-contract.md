# 04. JSON API: контракт, валидация, ошибки, документация

> Цикл «FastAPI + React». Предыдущая: [03. Слой данных](03-database-layer.md) · Следующая: [05. Фронтенд](05-react-frontend.md)

## 1. Схема = контракт = валидация = документация

Ключевая идея FastAPI: **pydantic-схема описывает контракт один раз**, а
фреймворк из неё извлекает сразу четыре вещи:

1. Валидацию входа (422 с описанием полей при ошибке).
2. Сериализацию выхода (лишние поля — например, `password` — наружу не уйдут,
   если схема ответа их не содержит).
3. Схему OpenAPI → интерактивную документацию `/docs` и `/redoc`.
4. Типизацию для IDE: автодополнение и проверка прямо в обработчике.

## 2. Схемы запросов и ответов — раздельные

```python
class UserCreate(BaseModel):
    nickname: str
    firstname: str
    surname: str
    password: str


class UserResp(BaseModel):
    id: int
    nickname: str
    firstname: str
    surname: str
    model_config = ConfigDict(from_attributes=True)  # читаем из ORM-объектов
```

**Почему раздельные:** `UserResp` не содержит `password` — пароль физически не
может утечь в ответ. (Распространённая ошибка — наследовать `UserResp` от
`UserCreate` ради DRY: тогда поле `password` попадает в схему ответа. В этом
проекте такой дефект осознанно оставлен как учебный.)

`from_attributes=True` — разрешение pydantic читать атрибуты ORM-объектов, а не
только dict. Благодаря ему обработчик возвращает объекты SQLAlchemy напрямую.

## 3. Обработчик: тонкий, типизированный, читаемый

`example_sql/router_users.py` — реальный код:

```python
r_users_sql = APIRouter(
    prefix=settings.api.user_post_prefix,
    tags=["Sql example users"],
)


@r_users_sql.get("/get_all_users", response_model=list[UserResp])
async def get_users(session: CurrentSession):
    return await users_crud.get_all_users(session=session)


@r_users_sql.post("/create_user", response_model=UserResp)
async def create_user(
    session: CurrentSession,
    user_create: Annotated[UserCreate, Body()],
):
    return await users_crud.create_user(session=session, user_create=user_create)
```

Обратите внимание:

- `response_model` в декораторе — FastAPI сам провалидирует и сериализует ответ
  по схеме. То, что CRUD вернул лишнее, наружу не пройдёт.
- Тело запроса — просто параметр с типом `UserCreate`. Ни `request.json()`, ни
  ручных проверок.
- Обработчик не содержит SQL и бизнес-логики — только склейку зависимостей.

## 4. Иерархия схем под стратегии загрузки

Приём из `ex_order_product/schema_order_product.py`: дерево схем ответов
соответствует дереву `joinedload`/`selectinload`:

```
OrderResp                                  базовая: только поля заказа
├── OrderRespWithProducts                  + products: List[ProductResp]
├── OrderRespWithAssoc                     + products_details: List[AssociationResp]
└── OrderRespWithProductsDetails           + products c вложенными ассоциациями
```

**Зачем:** глубина сериализации контролируется на уровне типов. Эндпоинт,
который не сделал `joinedload`, физически не сможет вернуть вложенные объекты —
и не отдаст клиенту N+1 ленивых загрузок в сериализаторе. Клиент по имени схемы
видит, что получит.

## 5. Ошибки: осмысленные статусы вместо 500

Три уровня обработки ошибок:

| Источник | Как обрабатывать | Результат |
|---|---|---|
| Невалидный вход | Ничего: pydantic сам | 422 + JSON с описанием полей |
| Ожидаемая бизнес-ситуация | `raise HTTPException` | 404 / 409 / 403 + `{"detail": ...}` |
| Неожиданное исключение | Сессия делает rollback и пробрасывает | 500 (и это правильно — честный сигнал бага) |

```python
if existing_order:
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order already exists")
```

**Типичный дефект, который стоит проверить в своём API:** дубликат уникального
поля без перехвата `IntegrityError` даёт 500 вместо 409. Перехватывайте
конфликты целостности явно и переводите их в осмысленные статусы.

**Свой формат 422 для SPA-клиента** (реальный приём из `md_articles/api_blog.py`):
кастомный обработчик `RequestValidationError` возвращает
`{"errors": {поле: [тексты]}}` для `/api/blog` — React показывает ошибки прямо у
полей формы, а дефолтный формат FastAPI для остальных частей сохраняется.

## 6. Версионирование

Префиксы версий — часть конфига, а не хардкод:

```python
router_api = APIRouter(prefix=settings.api.prefix)  # "/api"
router_api_v1 = APIRouter(prefix=settings.api.v1.prefix)  # "/v1"
router_api.include_router(router_api_v1)
```

Практические правила:

- Ломающие изменения контракта → новый префикс `/api/v2`, старый живёт до
  перехода клиентов.
- Добавление *необязательных* полей в ответ — не ломающее изменение, можно в v1.
- Доменные роутеры (`/users`, `/orders`) в этом проекте живут без версии — это
  осознанный упрощённый выбор учебного проекта; в продуктовом коде весь
  публичный API держите под версией.

## 7. OpenAPI — бесплатная документация контракта

```bash
curl -s http://127.0.0.1:8000/openapi.json | python -m json.tool | head -30
```

`/docs` (Swagger UI) — можно дёргать эндпоинты руками; `/openapi.json` —
машиночитаемый контракт, из которого генерируют TypeScript-типы для фронтенда
(инструменты типа `openapi-typescript`). Это закрывает главную боль связки:
**рассинхрон типов клиента и сервера**. Даже если не генерировать автоматически,
держите `frontend/src/types.ts` синхронным со схемами pydantic — см. [статью 05](05-react-frontend.md).

## 8. Чекпоинт самопроверки

- [ ] Схемы запроса и ответа раздельные; в ответе нет чувствительных полей.
- [ ] Каждый эндпоинт имеет `response_model`.
- [ ] Ожидаемые ситуации — осмысленные 4xx, а не 500.
- [ ] 422 для SPA-клиента — в удобном для форм формате.
- [ ] Публичный API под версионным префиксом.
- [ ] Контракт виден на `/docs` и совпадает с типами фронтенда.
