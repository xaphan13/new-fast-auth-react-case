# 01. Карта проекта

Проект — учебный модульный монолит на FastAPI 0.111+ / Python 3.12 с React 18 + TypeScript + Vite + Tailwind CSS v4. Бэкенд и собранный фронтенд обслуживаются одним ASGI-приложением; в dev фронтенд запускается отдельным Vite-сервером.

## Основные части

- `fastapi-application/api/` — демонстрации `Depends` и извлечения параметров.
- `fastapi-application/ex_order_product/` — демонстрационный домен заказов и товаров.
- `fastapi-application/db_core/` — SQLAlchemy 2.0 async, общая `Base`, сессии и типы колонок.
- `fastapi-application/auth_users/` — текущая авторизация на `fastapi-users`.
- `fastapi-application/md_articles/` — JSON API блога, YAML-реестр статей и серверный Markdown-рендер.
- `fastapi-application/content_art/` — Markdown-файлы статей.
- `fastapi-application/static/profile_pics/` — аватары пользователей.
- `frontend/` — React-приложение и клиентские API-обёртки.
- `fastapi-application/alembic/` — асинхронные миграции.
- `docs/` — актуальная техническая документация.

## Точки сборки приложения

`fastapi-application/main.py` создаёт приложение через `create_app()`, подключает демонстрационный роутер, роутер заказов, затем авторизацию и блог через `include_router_api_frontend()`. Вызов `mount_vite_react_assets()` должен оставаться последним: он добавляет `/assets` и catch-all `/{full_path:path}`.

`create_fastapi.py` отвечает только за каркас FastAPI и lifespan. Доменная композиция находится в `main.py`.

## Дерево важных файлов

```text
fastapi-application/
├── main.py
├── create_fastapi.py
├── core/config.py
├── db_core/
│   ├── db_async.py
│   ├── model_base.py
│   └── type_for_models.py
├── api/
├── ex_order_product/
├── auth_users/
│   ├── models.py
│   ├── schemas.py
│   ├── user_manager.py
│   ├── auth_backend.py
│   ├── fastapi_users_obj.py
│   ├── router.py
│   ├── account.py
│   └── helpers.py
├── md_articles/
│   ├── articles.yaml
│   ├── api_blog.py
│   ├── schema_art.py
│   ├── schema_blog.py
│   ├── models.py
│   └── setup_frontend.py
├── content_art/
├── static/profile_pics/
└── alembic/versions/

frontend/
├── src/api/
├── src/context/AuthContext.tsx
├── src/pages/
├── src/components/
├── src/App.tsx
├── src/main.tsx
└── vite.config.ts
```

## API-инвентарь

Проверка OpenAPI на текущем коде:

```bash
cd fastapi-application
../.venv/bin/python -c "from main import main_app; print(len(main_app.openapi()['paths']))"
```

Ожидается **32 path-ключа OpenAPI** и **35 HTTP-операций**. `len(main_app.routes)` возвращает **11 верхнеуровневых объектов**: 4 включённых роутера, 5 служебных `Route` и 2 `Mount`. Эти значения нельзя смешивать: FastAPI хранит вложенные роутеры как отдельные объекты, а OpenAPI разворачивает их операции.

Группы маршрутов:

| Группа | Пути | Источник |
|---|---|---|
| Depends и параметры | `/api/v1/...` | `api/` |
| Заказы | `/orders/...` | `ex_order_product/router_order_one.py` |
| Авторизация | `/auth/...`, `/users/...` | `auth_users/router.py` |
| Блог | `/api/blog/...` | `md_articles/api_blog.py` |
| Swagger/OpenAPI | `/docs`, `/redoc`, `/openapi.json`, `/docs/oauth2-redirect` | FastAPI |
| React | `/assets/*`, `/{full_path:path}` | `md_articles/setup_frontend.py` |
| Аватары | `/static/*` | `StaticFiles` |

Полный контракт удобнее всего смотреть в `/openapi.json`, а подробности блога и авторизации вынесены в [06_blog.md](06_blog.md) и [04_authorization.md](04_authorization.md).

## Конфигурация и база

Конфигурация описана вложенными моделями в `core/config.py`. Переменные используют `APP__` и разделитель `__`; обязательное поле — `APP__DB__URL`. По умолчанию активен SQLite из `dev_sqlite.env`, PostgreSQL описан в `prod_db.env`.

SQLite-файл `./one_simple.db` разрешается относительно cwd процесса. Поэтому приложение предпочтительно запускать из `fastapi-application/`. Логи привязаны к `BASE_DIR` и не зависят от cwd.

Модели авторизации и демо-доменов должны быть импортированы до запуска Alembic, чтобы попасть в `Base.metadata`. Текущий `db_core/__init__.py` экспортирует только `Base`; миграция `alembic/versions/2026-09-13_22-34--caf2fea11a9d--initial.py` уже содержит таблицы `user`, `orders`, `products`, `order_product_association`, `blog_user` и `blog_post`.

## Проверка фронтенда

```bash
cd frontend
npm run build
```

Сборка создаёт `frontend/dist`, который не коммитится. Без `dist` API и Swagger работают, а catch-all возвращает JSON 404 с подсказкой собрать фронтенд.
