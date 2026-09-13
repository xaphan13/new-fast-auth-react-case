# Анализ файла backend/router.py

## Общее описание

Файл содержит роутер FastAPI для реализации OAuth 2.0 аутентификации через Google. Основная цель - позволить пользователям войти в приложение через их Google аккаунт и получить доступ к их Google Drive файлам.

## Импорты и настройка

```python
from typing import Annotated
from fastapi import APIRouter, Body
from fastapi.responses import RedirectResponse
import aiohttp
import jwt
from state_storage import state_storage
from oauth_google import generate_google_oauth_redirect_uri
from config import settings

router = APIRouter(prefix="/auth")
```

-   `APIRouter` создает группу маршрутов с общим префиксом `/auth`
-   `aiohttp` используется для асинхронных HTTP-запросов к Google API
-   `jwt` для декодирования токенов от Google
-   Импорты локальных модулей для хранения состояния и конфигурации

## Эндпоинт 1: `/auth/google/url` (GET)

```python
@router.get("/google/url")
def get_google_oauth_redirect_uri():
    uri = generate_google_oauth_redirect_uri()
    return RedirectResponse(url=uri, status_code=302)
```

**Назначение:** Инициация процесса OAuth аутентификации

**Как работает:**

1.  Вызывается когда пользователь нажимает "Войти через Google"
2.  Генерирует URL с параметрами для Google OAuth
3.  Возвращает HTTP 302 редирект, который перенаправляет браузер на страницу входа Google

**Что происходит в `generate_google_oauth_redirect_uri()`:**

-   Создается случайный `state` для защиты от CSRF
-   Формируется URL вида: `https://accounts.google.com/o/oauth2/v2/auth?client_id=...&scope=...`

## Эндпоинт 2: `/auth/google/callback` (POST)

```python
@router.post("/google/callback")
async def handle_code(
    code: Annotated[str, Body()],
    state: Annotated[str, Body()],
):

```

**Назначение:** Обработка ответа от Google после успешной аутентификации

### Шаг 2.1: Проверка безопасности

```python
if state not in state_storage:
    raise Exception("Invalid state")
```

-   Проверяет, что параметр `state` соответствует ранее сгенерированному
-   Защищает от CSRF-атак

### Шаг 2.2: Обмен кода на токены

```python
async with aiohttp.ClientSession() as session:
    async with session.post(
        url="https://oauth2.googleapis.com/token",
        data={
            "client_id": settings.OAUTH_GOOGLE_CLIENT_ID,
            "client_secret": settings.OAUTH_GOOGLE_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "redirect_uri": "http://localhost:3000/auth/google",
            "code": code,
        },
        ssl=False,
    ) as response:
        res = await response.json()
        id_token = res["id_token"]
        access_token = res["access_token"]
```

**Что происходит:**

1.  Отправляет POST-запрос к Google с авторизационным кодом
2.  Получает два токена:
    -   `id_token` - содержит информацию о пользователе (имя, email)
    -   `access_token` - для доступа к Google API

### Шаг 2.3: Декодирование информации о пользователе

```python
user_data = jwt.decode(
    id_token,
    algorithms=["RS256"],
    options={"verify_signature": False},
)
```

-   Извлекает данные пользователя из ID токена
-   ⚠️ **Внимание:** `verify_signature=False` используется только для примера, в продакшене нужна проверка подписи

### Шаг 2.4: Запрос к Google Drive API

```python
async with aiohttp.ClientSession() as session:
    async with session.get(
        url="https://www.googleapis.com/drive/v3/files",
        headers={"Authorization": f"Bearer {access_token}"},
        ssl=False,
    ) as response:
        res = await response.json()
        files = [item["name"] for item in res["files"]]
```

-   Использует `access_token` для запроса списка файлов из Google Drive
-   Извлекает только имена файлов

### Шаг 2.5: Возврат результата

```python
return {
    "user": user_data,
    "files": files,
}
```

## Поток выполнения (OAuth 2.0 Flow)

1.  **Пользователь** → Нажимает "Войти через Google"
2.  **Фронтенд** → GET `/auth/google/url`
3.  **Бэкенд** → Генерирует URL и делает редирект на Google
4.  **Пользователь** → Вводит логин/пароль на странице Google
5.  **Google** → Перенаправляет на фронтенд с `code` и `state`
6.  **Фронтенд** → POST `/auth/google/callback` с полученными параметрами
7.  **Бэкенд** → Обменивает код на токены, получает данные пользователя и файлы
8.  **Фронтенд** → Получает информацию о пользователе и его файлах

## Проблемы безопасности в текущей реализации

⚠️ **Для учебных целей код содержит упрощения:**

1.  `ssl=False` - отключена проверка SSL сертификатов
2.  `verify_signature=False` - не проверяется подпись JWT токена
3.  Простое хранение state в памяти (не подходит для продакшена)
4.  Отсутствует обработка ошибок
5.  Токены не сохраняются для последующего использования

## Заключение

Код демонстрирует базовую реализацию OAuth 2.0 flow с Google, позволяя пользователям авторизоваться и получать доступ к их Google Drive файлам. Для продакшен-использования требуются дополнительные меры безопасности и обработка ошибок.
