# 06. Связка, авторизация и деплой: как две половины становятся одним сайтом

> Цикл «FastAPI + React». Предыдущая: [05. Фронтенд](05-react-frontend.md) · Следующая: [07. Альтернативы](07-alternatives.md)

## 1. Dev: два сервера и невидимый прокси

В разработке живут два процесса:

```
Браузер ──▶ Vite :5173 (исходники TS/TSX + HMR)
                 │  proxy /api и /static
                 ▼
            FastAPI :8000 (JSON API, аватары, БД)
```

Прокси в `vite.config.ts` — то, что делает связку бесшовной:

```typescript
server: {
  port: 5173,
  proxy: {
    "/api":    { target: "http://localhost:8000", changeOrigin: true },
    "/static": { target: "http://localhost:8000", changeOrigin: true },
  },
},
```

**Почему прокси, а не прямые запросы на `:8000`:** браузер видит всё на одном
origin `:5173` — нет CORS, нет абсолютных URL в коде (`fetch('/api/...')`), cookie
ставятся без оговорок. Код фронтенда при этом один и тот же в dev и в prod.

## 2. Prod: один сервер раздаёт всё

```bash
cd frontend && npm run build     # → dist/index.html + dist/assets/*.js|css
cd fastapi-application && uvicorn main:main_app --port 8000
```

Три элемента SPA-хостинга в `main.py` (реальный код):

```python
# 1) бандлы фронтенда
main_app.mount(
    "/assets",
    StaticFiles(directory=BASE_DIR.parent / "frontend" / "dist" / "assets", check_dir=False),
    name="spa_assets",
)


# 2) catch-all: любой неизвестный GET-путь → index.html
async def spa_fallback(request):
    path = request.url.path
    if path.startswith("/api"):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    index_html = BASE_DIR.parent / "frontend" / "dist" / "index.html"
    if not index_html.is_file():
        return JSONResponse(
            status_code=404,
            content={"detail": "Frontend не собран: выполните npm run build в frontend/"},
        )
    return FileResponse(index_html)


main_app.router.routes.append(Route("/{full_path:path}", spa_fallback, methods=["GET"]))
```

Разбор «почему именно так»:

- **`check_dir=False`** — сервер стартует даже без собранного фронтенда
  (бэкенд-разработка не зависит от `npm run build`).
- **`/api*` перехватывается раньше** — неизвестный API-путь должен вернуть честный
  404 JSON, а не HTML-страницу React (иначе клиент получит 200 с HTML и упадёт на
  `JSON.parse`).
- **catch-all добавляется последним** — маршрутизация Starlette идёт по порядку
  регистрации; поставите catch-all раньше роутеров — он «съест» их всех.
- **Отсутствие `dist` — понятная ошибка с подсказкой**, а не молчаливая пустая
  страница.

## 3. Почему нет CORS — и когда он появится

CORS — это проверка *браузером*: разрешает ли сервер A странице с origin B
делать запросы. Пока API и SPA на одном origin (через прокси в dev, через
один сервер в prod) — междоменных запросов нет, CORS не нужен.

Он появится, когда разнесёте домены (статья 07, способ B). Тогда на FastAPI:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com"],  # не "*" при cookie-сессиях!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Плюс cookie с `SameSite=None; Secure` и общий домен. Это не «бесплатно» — ещё
одна причина, почему SPA-хостинг на самом FastAPI — удачный дефолт.

## 4. Авторизация: cookie-сессии + CSRF

Выбор проекта — **серверные cookie-сессии** (SessionMiddleware starlette), а не
JWT. Почему:

| | Cookie-сессии | JWT в localStorage |
|---|---|---|
| XSS-риск | cookie httpOnly — JS токен не читает | токен украден скриптом при XSS |
| Отзыв сессии | удалить сессию на сервере | невозможно до истечения срока |
| CSRF-риск | есть → нужен CSRF-токен | нет (но есть XSS) |
| Сложность | middleware + подписанная cookie | выпуск/обновление/хранение токенов |

Для классического сайта с формами cookie-сессии проще и безопаснее. JWT берут
под мобильные клиенты и микросервисы.

**Как это устроено на бэкенде** (`md_articles/`):

1. `SessionMiddleware` — подписанная cookie (ключ из `settings.web.secret_key`,
   14 дней); в сессии `user_id` и `csrf_token`.
2. Middleware `inject_current_user_middleware` на каждом запросе грузит
   пользователя в `request.state.current_user`.
3. Зависимость `require_login_api` возвращает **403 JSON** (не редирект — SPA
   сама решит, куда перевести пользователя).
4. Изменяющие запросы требуют CSRF: JSON — заголовок `X-CSRF-Token`, формы —
   поле `csrf_token`.

**Как на фронтенде** — всё спрятано в базовом клиенте (`src/api/client.ts`):

```typescript
// POST с JSON-телом; CSRF-токен кладём в заголовок X-CSRF-Token.
export async function postJson<T = unknown>(path: string, body: unknown): Promise<T> {
  const token = await getCsrfToken();                    // GET /api/blog/csrf
  const res = await request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': token },
    body: JSON.stringify(body),
  });
  return (await ensureOk(res)) as T;
}
```

Компоненты вызывают `postJson('/api/blog/login', {...})` и не знают о CSRF
вообще — токен добывается и подставляется автоматически.

## 5. Деплой: варианты по нарастающей

1. **Один uvicorn на 8000** (как в этом проекте) — личные проекты, демо.
2. **gunicorn + UvicornWorker** — многопроцессность на одном хосте:
   ```bash
   gunicorn main:main_app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```
   Помните: пул БД умножается на число воркеров (см. [статью 03](03-database-layer.md)).
3. **+ nginx спереди** — TLS, gzip, раздача статики, rate limit; приложение за
   прокси. Схема `nginx_pg_admin.yml` в этом репозитории — пример такой сборки.
4. **Контейнеры** — образ для FastAPI, отдельный образ сборки фронтенда с
   копированием `dist/` в образ бэкенда (multi-stage), PostgreSQL рядом.

Инвариант всех вариантов: **артефакт фронтенда — это каталог `dist/`**, и его
нужно лишь доставить туда, откуда его отдаст сервер.

## 6. Чекпоинт самопроверки

- [ ] Dev: браузер только на `:5173`, прокси настроен, абсолютных URL в коде нет.
- [ ] Prod: `npm run build` в пайплайне деплоя — без него сайт «старый».
- [ ] catch-all — последним; `/api*` отвечает 404 JSON, а не HTML.
- [ ] Сессии — httpOnly cookie; изменяющие запросы — с CSRF-токеном.
- [ ] Неавторизованный API-доступ — 403 JSON, редирект решает SPA.
- [ ] `secret_key` — из конфига, стабильный между рестартами воркеров.
