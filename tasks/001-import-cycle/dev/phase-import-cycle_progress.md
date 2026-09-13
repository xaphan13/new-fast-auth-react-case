# Прогресс исправления circular import

- 2026-09-13 — начато: проверены AGENTS.md, текущий git diff и файлы цепочки импорта; план — точечная правка `fastapi-application/main.py`.
- 2026-09-13 — `fastapi-application/main.py`: порядок импорта изменён так, чтобы `create_fastapi`/`db_core` загружались до `auth_users`; возвращено подключение `r_users_sql`; роутер auth передаётся в `include_router_api_frontend`. Проверки: выполняются.
- 2026-09-13 — `fastapi-application/main.py`: добавлена явная предзагрузка `db_core` перед `auth_users`; ссылка на отсутствующий в репозитории `ex_user_post` не используется; сохранены существующие `router_api`, `r_order_one` и auth/blog композиция. Проверки: импорт PASS (`11` маршрутов), Ruff PASS.
