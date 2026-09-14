# 04. Авторизация

Текущая авторизация находится в `fastapi-application/auth_users/` и построена на `fastapi-users` с SQLAlchemy-адаптером, `CookieTransport` и `JWTStrategy`. Это отдельный слой приложения; блог не содержит собственного login/session/CSRF-кода.

## Контракт маршрутов

| Метод | Путь | Доступ | Назначение |
|---|---|---|---|
| POST | `/auth/jwt/login` | публичный | form-urlencoded `username=<email>&password=...`; 204 + cookie |
| POST | `/auth/jwt/logout` | публичный | очистить cookie; 204 |
| POST | `/auth/register` | публичный | JSON `{email,password}`; 201 |
| GET | `/users/me` | `active_user` | текущий пользователь |
| PATCH | `/users/me` | `active_user` | email/password через fastapi-users |
| GET | `/users/{id}` | `superuser_user` | прочитать пользователя |
| PATCH | `/users/{id}` | `superuser_user` | изменить пользователя |
| DELETE | `/users/{id}` | `superuser_user` | удалить пользователя |
| POST | `/auth/account` | `active_user` | username/email/аватар, multipart |

Последние три маршрута зарегистрированы библиотекой, но текущий React-клиент их не вызывает. Защищённые маршруты возвращают 401 для анонимного запроса.

## Модель User

`auth_users/models.py` содержит:

- UUID `id` из `SQLAlchemyBaseUserTableUUID`;
- уникальный `email`;
- `hashed_password`;
- `is_active`, `is_superuser`, `is_verified`;
- `username` длиной до 20 символов;
- `image_file` с default `default.jpg`;
- `created_at`.

`username` nullable на уровне SQLAlchemy, потому что стандартная регистрация сначала создаёт пользователя только с email и password. `UserManager.on_after_register()` затем записывает username из email и default-аватар.

`UserRead` отдаёт `id`, `email`, флаги пользователя, `username` и `image_file`; пароль и `hashed_password` в ответ не попадают.

## Сборка fastapi-users

```text
auth_users/router.py
  ├── get_auth_router(auth_backend)      → /auth/jwt/login, /auth/jwt/logout
  ├── get_register_router(...)           → /auth/register
  ├── get_users_router(...)              → /users/me, /users/{id}
  └── account.router                     → /auth/account
```

`fastapi_users_obj.py` создаёт:

- `fastapi_users = FastAPIUsers[User, UUID](...)`;
- `active_user = fastapi_users.current_user(active=True)`;
- `optional_user`;
- `superuser_user`.

`user_manager.py` связывает `CurrentSession` с `SQLAlchemyUserDatabase`, проверяет минимальную длину пароля 8 и переводит `IntegrityError` дубликата в штатный `UserAlreadyExists`.

## Cookie и JWT

Настройки находятся в `core/config.py` в `AuthUsersConfig`:

| Параметр | Текущее значение |
|---|---|
| cookie name | `auth` |
| max age | `86400` секунд |
| HttpOnly | `true` |
| SameSite | `lax` |
| Secure | `false` для dev HTTP |
| JWT lifetime | `86400` секунд |
| algorithm | `HS256` |
| minimum password length | `8` |

JWT подписывается `settings.web.secret_key`. Тот же секрет передан менеджеру для токенов verification/reset, хотя соответствующие маршруты сейчас не подключены.

`frontend/src/api/client.ts` всегда использует `credentials: 'include'`. В `localStorage` токен не сохраняется. Отдельного CSRF-токена нет: текущий контракт рассчитан на same-origin cookie, `HttpOnly` и `SameSite=Lax`. При выносе API на другой origin нужно отдельно пересмотреть CORS, cookie-политику и CSRF-модель.

## Account и аватар

`POST /auth/account` — проектный multipart-маршрут поверх `active_user`.

```text
username: str
email: str
picture: UploadFile | отсутствует
```

`auth_users/helpers.py` проверяет email и уникальность, а `save_picture()` сохраняет изображение после resize 125×125. Имя файла генерируется случайно и сохраняется в `User.image_file`. React строит URL как `/static/profile_pics/${image_file}`.

## React-контракт

- `api/auth.ts`: login → form-urlencoded и последующий `/users/me`; logout → `/auth/jwt/logout`; register → `/auth/register`; account → `/auth/account`.
- `AuthContext.tsx`: при старте вызывает `/users/me`; 401 означает `user = null`.
- `App.tsx`: `RequireAuth` защищает `/account` и `/art_manage` на уровне UI.
- API всё равно проверяет dependency `active_user`; UI-защита не является механизмом безопасности.

## Схема базы и миграции

Таблица текущей авторизации — `user`, с UUID и полями fastapi-users. Исторические `blog_user` и `blog_post` остаются отдельными таблицами миграции и не участвуют в текущем auth-контракте.

Миграция находится в `fastapi-application/alembic/versions/2026-09-13_22-34--caf2fea11a9d--initial.py`. Alembic берёт `Base.metadata` из приложения; перед генерацией миграции должны импортироваться модели `auth_users`.

## Важные ограничения

- Email verification, reset password, OAuth и rate limit не подключены.
- Авторизация не даёт отдельной роли редактора: управление реестром доступно любому `active_user`.
- Смена `secret_key` инвалидирует ранее выданные JWT и токены.
- `cookie_secure` нужно включать за HTTPS; текущий `false` предназначен для локального HTTP.
