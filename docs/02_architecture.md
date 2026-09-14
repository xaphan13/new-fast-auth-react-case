# 02. Архитектура

## Общая схема

Проект — модульный монолит: один FastAPI-процесс обслуживает JSON API, аватары и собранный React-фронтенд.

```text
Браузер
  ├── React Router: /, /section/*, /art/*, /account, /art_manage
  ├── fetch /auth/* и /users/*
  └── fetch /api/blog/*
          │
          ▼
FastAPI main_app
  ├── demo API /api/v1/*
  ├── order API /orders/*
  ├── auth_users /auth/* и /users/*
  ├── blog API /api/blog/*
  ├── /static/profile_pics/*
  ├── /assets/*
  └── catch-all → frontend/dist/index.html
          │
          ├── SQLite/PostgreSQL через db_core
          ├── User через auth_users
          └── articles.yaml + content_art/*.md через md_articles
```

## Границы пакетов

| Слой | Ответственность |
|---|---|
| `core`, `base_dir_path`, `config_log` | настройки, пути, логирование |
| `db_core` | engine, async-сессии, `Base`, типы SQLAlchemy |
| `api` | учебные примеры FastAPI |
| `ex_order_product` | учебный SQLAlchemy-домен заказов |
| `auth_users` | User, пароль, cookie-JWT, зависимости доступа, аккаунт |
| `md_articles` | реестр и контент статей, блоговый API, подключение статики |
| `frontend` | UI, React Router, fetch-клиенты и локальное состояние |
| `main.py` | единственная точка композиции приложения |

Домены не должны импортировать друг друга без необходимости. `main.py` передаёт auth-роутер в `include_router_api_frontend()` явно, чтобы не создавать цикл импортов.

## Авторизация и блог разделены

Авторизация больше не реализуется в `md_articles`: там нет `api_auth.py`, `middleware_auth.py`, `SessionMiddleware`, `request.state.current_user` или самописного CSRF. Пакет `auth_users` выдаёт JWT в HttpOnly-cookie, а блог использует dependency `active_user` только для операций управления реестром.

Подробности:

- [04_authorization.md](04_authorization.md) — модель User, fastapi-users, cookie/JWT и фронтенд-контракт.
- [06_blog.md](06_blog.md) — статьи, YAML-реестр, Markdown, API и React-страницы.

## Хранилища данных

- **SQLAlchemy/БД:** пользователи `user`, демо-таблицы заказов и товаров, исторические `blog_user`/`blog_post`.
- **YAML:** `fastapi-application/md_articles/articles.yaml` — метаданные статей.
- **Файлы:** `fastapi-application/content_art/` — исходный Markdown; `static/profile_pics/` — аватары.
- **Браузер:** HttpOnly cookie `auth` для JWT и `localStorage` для тем сайта/подсветки.

Статьи не хранятся в SQLAlchemy. Реестр читается с mtime-кэшем, а запись выполняется через временный файл и `os.replace`.

## Поток запроса

1. Uvicorn передаёт запрос FastAPI.
2. Роутинг выбирает вложенный роутер; catch-all находится последним.
3. FastAPI разрешает dependency и открывает `CurrentSession`, если она нужна.
4. Для защищённого маршрута `active_user` читает JWT из cookie и загружает `User` через `SQLAlchemyUserDatabase`.
5. Обработчик читает БД или файловый реестр.
6. Ответ сериализуется FastAPI; JSON API возвращает данные для React.

В отличие от прежней документации, отдельной middleware-сессии с `user_id` нет. JWT самодостаточен для аутентификации, но dependency всё равно обращается к БД за актуальным пользователем и проверяет `is_active`.

## Frontend dev и production

В dev Vite работает на `:5173` и проксирует `/api` и `/static` на `http://localhost:8000`. Пути `/auth` и `/users` в `vite.config.ts` явно не проксируются; для auth-флоу удобнее same-origin production-сборка или настройка прокси перед использованием отдельного Vite-origin.

В production FastAPI раздаёт `frontend/dist/assets` и возвращает `index.html` для history-mode маршрутов React. Для неизвестных `/api/*` catch-all отдаёт JSON 404, а не HTML.

## Архитектурные инварианты

1. `mount_vite_react_assets(main_app)` вызывается после всех `include_router`.
2. `frontend/dist` не коммитится.
3. Путь аватара в БД хранится как имя файла; URL `/static/profile_pics/<имя>` собирает фронтенд.
4. Секрет `settings.web.secret_key` используется JWT-стратегией и токенами fastapi-users.
5. Реестр статей изменяется только через функции `schema_art.py`, а не прямой записью из роутера.
