# 05. Авторизация: дальнейшее развитие

Этот документ больше не описывает миграцию на `fastapi-users`: миграция уже выполнена. Текущее состояние и фактический контракт находятся в [04_authorization.md](04_authorization.md).

## Что уже сделано

- auth-слой вынесен в `fastapi-application/auth_users/`;
- `User` использует UUID и стандартные поля fastapi-users;
- пароль проверяется через `UserManager`, минимум — 8 символов;
- вход/выход работают через JWT в cookie `auth`;
- `/auth/account` поддерживает username, email и аватар;
- блог защищает операции управления dependency `active_user`;
- фронтенд использует `/auth/*` и `/users/*`, без самописной CSRF-сессии.

## Следующие варианты

### 1. Безопасность production

Перед публикацией приложения нужно:

- задавать уникальный `APP__WEB__SECRET_KEY` вне репозитория;
- включать `APP__AUTH_USERS__COOKIE_SECURE=true` только при HTTPS;
- проверить proxy headers и фактическую схему запроса;
- ограничить CORS, если API и фронтенд будут на разных origin;
- добавить rate limit на login и register;
- не использовать учебные пароли и dev-профиль PostgreSQL в production.

### 2. Email verification и reset password

`UserManager` уже содержит секреты `verification_token_secret` и `reset_password_token_secret`, но роутеры этих потоков не подключены. Для реализации нужны email-доставка, UI-состояния и явный контракт сроков жизни токенов. Это отдельная фича, а не продолжение миграции.

### 3. Роли редакторов

Сейчас `active_user` защищает `/api/blog/art_manage*`, поэтому любой активный пользователь может менять `articles.yaml`. Если нужен редакторский доступ, следует использовать `superuser_user` или добавить отдельное поле/permission-модель и зафиксировать её в API-контракте.

### 4. Сессии и отзыв токенов

JWT — stateless-токен: logout очищает cookie браузера, но уже скопированный токен остаётся действительным до истечения lifetime или смены секрета. Если нужен мгновенный отзыв на сервере, следует рассмотреть database/Redis strategy либо таблицу отозванных токенов.

### 5. Проверки

После изменений авторизации проверить:

```bash
cd fastapi-application
../.venv/bin/python -c "from main import main_app; print(len(main_app.openapi()['paths']))"
curl -i -c /tmp/auth.cookies -X POST http://127.0.0.1:8000/auth/register -H 'Content-Type: application/json' -d '{"email":"user@example.com","password":"password123"}'
curl -i -c /tmp/auth.cookies -b /tmp/auth.cookies -X POST http://127.0.0.1:8000/auth/jwt/login -H 'Content-Type: application/x-www-form-urlencoded' --data 'username=user@example.com&password=password123'
curl -i -b /tmp/auth.cookies http://127.0.0.1:8000/users/me
```

Не фиксируйте в документации старые значения счётчика маршрутов: актуальный источник — `/openapi.json` и код `main.py`.
