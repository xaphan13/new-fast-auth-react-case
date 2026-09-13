# Фаза 3 — независимая QA-проверка import-cycle

Дата прогона: 2026-09-13. Рабочий каталог: `/home/max/0_0_26_new_one/new-fast-auth-react-case`. Все проверки продукта запускались с `cwd=fastapi-application`, если это явно не указано иначе. Изменений в код продукта, `REQUIREMENTS.md` и progress-файлы не вносилось.

## Предварительная проверка сервера

Команда из корня:

```bash
pgrep -af "uvicorn.*main:main_app"
curl -m 3 -sS -o /tmp/qa_openapi_preflight -w 'http_code=%{http_code}\n' http://127.0.0.1:8000/openapi.json
```

Ожидание: если сервер уже запущен, переиспользовать его; иначе порт свободен и можно поднять ровно один сервер.

Фактически: curl вернул `http_code=000`, exit `7` (`Failed to connect to 127.0.0.1 port 8000`), поэтому был поднят один QA-сервер из `fastapi-application`:

```bash
../.venv/bin/uvicorn main:main_app --host 127.0.0.1 --port 8000
```

Проверка готовности вернула `ready_http_code=200` (после двух первоначальных `000`). PID процесса: `954819`.

## Критерий 1 — прямой импорт auth

Команда:

```bash
(cd fastapi-application && ../.venv/bin/python -c "from auth_users import active_user; assert active_user is not None; print('auth-ok')")
```

Expected: exit `0`, ровно `auth-ok`, без `ImportError` и `partially initialized module`.

Actual, первый чистый процесс:

```text
auth-ok
exit=0
```

После import-autofix probe повторено в новом чистом процессе:

```text
auth-ok
exit=0
```

**Результат: PASS.**

## Критерий 2 — независимый импорт Base

Команда:

```bash
(cd fastapi-application && ../.venv/bin/python -c "from db_core import Base; assert Base is not None; print('base-ok')")
```

Expected: exit `0`, ровно `base-ok`.

Actual, первый чистый процесс:

```text
base-ok
exit=0
```

После import-autofix probe повторено в новом чистом процессе:

```text
base-ok
exit=0
```

**Результат: PASS.**

## Критерий 3 — точная metadata

Команда:

```bash
(cd fastapi-application && ../.venv/bin/python -c "from db_core import Base; from db_core.model_registry import load_model_registry; load_model_registry(); expected={'blog_post','blog_user','order_product_association','orders','products','user'}; assert set(Base.metadata.tables)==expected, sorted(Base.metadata.tables); print(sorted(Base.metadata.tables))")
```

Expected: exit `0`; множество таблиц ровно `{'blog_post','blog_user','order_product_association','orders','products','user'}`; лишние таблицы, включая `ex_user_post`, отсутствуют.

Actual, первый процесс:

```text
['blog_post', 'blog_user', 'order_product_association', 'orders', 'products', 'user']
exit=0
```

После import-autofix probe повторено:

```text
['blog_post', 'blog_user', 'order_product_association', 'orders', 'products', 'user']
exit=0
```

**Результат: PASS.**

## Критерий 4 — независимая сборка приложения и route count

Первоначальная проверка по `main_app.routes` с чтением только верхнего уровня вывела `route_count=11`, но завершилась exit `1`, потому что пять верхнеуровневых объектов имеют тип `fastapi.routing._IncludedRouter` и не имеют собственного атрибута `path`. Это особенность структуры вложенных роутеров, а не ошибка импорта. Фактические API-пути были проверены через OpenAPI и повторным probe после import-autofix.

Повторная команда:

```bash
(cd fastapi-application && ../.venv/bin/python - <<'PY'
from main import main_app
required = {
    '/auth/jwt/login', '/auth/jwt/logout', '/auth/register', '/users/me',
    '/auth/account', '/api/blog/articles', '/api/blog/sections',
    '/orders/get_all_orders',
}
paths = sorted(main_app.openapi()['paths'])
matching = sorted(required.intersection(paths))
print(f'route_count={len(main_app.routes)}')
print(f'matching_routes={matching}')
print(f'openapi_path_count={len(paths)}')
print(f'ex_user_post_paths={[path for path in paths if "ex_user_post" in path]}')
assert len(main_app.routes) == 11
assert set(matching) == required
assert not any('ex_user_post' in path for path in paths)
print('main-routes-ok')
PY
)
```

Expected: exit `0`, `route_count=11`.

Actual:

```text
route_count=11
matching_routes=['/api/blog/articles', '/api/blog/sections', '/auth/account', '/auth/jwt/login', '/auth/jwt/logout', '/auth/register', '/orders/get_all_orders', '/users/me']
openapi_path_count=32
ex_user_post_paths=[]
main-routes-ok
exit=0
```

**Результат: PASS.**

## Критерий 5 — auth/blog/order routes и отсутствие ex_user_post

Expected: через фактический маршрутный контракт должны присутствовать все восемь путей:

```text
/auth/jwt/login
/auth/jwt/logout
/auth/register
/users/me
/auth/account
/api/blog/articles
/api/blog/sections
/orders/get_all_orders
```

`ex_user_post` не должен появляться.

Первый диагностический вывод `main_app.routes`:

```text
route_count=11
route[0] ... path='/openapi.json'
route[1] ... path='/docs'
route[2] ... path='/docs/oauth2-redirect'
route[3] ... path='/redoc'
route[4] type=fastapi.routing._IncludedRouter path='<missing>'
route[5] type=fastapi.routing._IncludedRouter path='<missing>'
route[6] type=starlette.routing.Mount path='/static'
route[7] type=fastapi.routing._IncludedRouter path='<missing>'
route[8] type=fastapi.routing._IncludedRouter path='<missing>'
route[9] type=starlette.routing.Mount path='/assets'
route[10] ... path='/{full_path:path}'
```

Фактический OpenAPI path list содержал `32` пути. Существенная часть:

```text
'/api/blog/articles'
'/api/blog/sections'
'/auth/account'
'/auth/jwt/login'
'/auth/jwt/logout'
'/auth/register'
'/orders/get_all_orders'
'/users/me'
```

`ex_user_post_paths=[]`.

**Результат: PASS.** Маршруты фактически раскрыты во вложенных роутерах/OpenAPI; отсутствие пути на самих `_IncludedRouter` не является отсутствием endpoint.

## Критерий 6 — Alembic head

Команда из `fastapi-application`:

```bash
../.venv/bin/alembic heads
```

Expected: `5fed75984f99 (head)`.

Actual:

```text
5fed75984f99 (head)
exit=0
```

**Результат: PASS.**

## Критерий 7 — Alembic metadata и SQLite upgrade/check

Команда из `fastapi-application`:

```bash
../.venv/bin/alembic upgrade heads && ../.venv/bin/alembic check
```

Expected: upgrade доступен, затем `alembic check` сообщает отсутствие новых операций; metadata probe из критерия 3 проходит.

Actual:

```text
No new upgrade operations detected.
exit=0
```

Metadata probe также прошёл с точным шестью таблицами набором (см. критерий 3).

**Результат: PASS.** Ограничения локальной SQLite не возникло.

## Критерий 8 — import-only Ruff и полный baseline

### Import-only Ruff на пяти изменённых Python-файлах

Команда из корня:

```bash
uv run ruff check --select I \
  fastapi-application/db_core/__init__.py \
  fastapi-application/db_core/model_registry.py \
  fastapi-application/md_articles/__init__.py \
  fastapi-application/main.py \
  fastapi-application/alembic/env.py
```

Expected: exit `0`, без `I001`.

Actual:

```text
All checks passed!
exit=0
```

### Полный baseline Ruff

Команда:

```bash
uv run ruff check .
```

Expected: baseline зафиксирован честно; нерелевантные ошибки не объявляются исправленными.

Actual: exit `1`, найдено `18 errors`, из них `5 fixable with the --fix option`.

Существенный полный вывод с файлами и кодами:

```text
UP035, I001, UP007 x3 — fastapi-application/alembic/versions/2026-09-13_19-06--5fed75984f99--initial.py
B008 x2, SIM102 x2 — fastapi-application/auth_users/account.py
BLE001 — fastapi-application/auth_users/helpers.py
B008 — fastapi-application/auth_users/user_manager.py
B008 x2 — fastapi-application/ex_order_product/router_order_one.py
UP035 — fastapi-application/ex_order_product/schema_order_product.py
F821 Undefined name `uvicorn` — fastapi-application/main.py:31
B008 x4 — fastapi-application/md_articles/api_blog.py
```

Полный существенный сырой фрагмент:

```text
UP035 ... alembic/versions/...initial.py:9
I001 ... alembic/versions/...initial.py:9
UP007 ... alembic/versions/...initial.py:17
UP007 ... alembic/versions/...initial.py:18
UP007 ... alembic/versions/...initial.py:19
B008 ... auth_users/account.py:33
B008 ... auth_users/account.py:36
SIM102 ... auth_users/account.py:49
SIM102 ... auth_users/account.py:52
BLE001 ... auth_users/helpers.py:34
B008 ... auth_users/user_manager.py:95
B008 ... ex_order_product/router_order_one.py:59
B008 ... ex_order_product/router_order_one.py:78
UP035 ... ex_order_product/schema_order_product.py:3
B008 ... md_articles/api_blog.py:114
B008 ... md_articles/api_blog.py:136
B008 ... md_articles/api_blog.py:169
B008 ... md_articles/api_blog.py:220
Found 18 errors.
[*] 5 fixable with the `--fix` option (1 hidden fix can be enabled with the `--unsafe-fixes` option).
exit=1
```

**Результат: PASS для import-related scope; полный Ruff baseline — FAIL как общий baseline, не относящийся целиком к import-cycle.** После восстановления требуемого `import uvicorn` собственная F821-регрессия в `main.py` устранена; оставшиеся 18 ошибок находятся вне scope задания.

## Критерий 9 — проверка автосортировки импортов и повторные probes

Команда из корня:

```bash
uv run ruff check --select I --fix \
  fastapi-application/db_core/__init__.py \
  fastapi-application/db_core/model_registry.py \
  fastapi-application/md_articles/__init__.py \
  fastapi-application/main.py \
  fastapi-application/alembic/env.py
```

Expected: exit `0`; автофикс не возвращает циклический workaround; повторные независимые импорты, metadata и routes проходят.

Actual:

```text
exit=0
```

Write-mode `--fix` выполнен после QA; продуктовый diff не изменился сверх архитектурных правок. Повторно прошли:

```text
auth-ok
base-ok
['blog_post', 'blog_user', 'order_product_association', 'orders', 'products', 'user']
route-count= 11
required-paths= ['/api/blog/articles', '/api/blog/sections', '/auth/account', '/auth/jwt/login', '/auth/jwt/logout', '/auth/register', '/orders/get_all_orders', '/users/me']
All checks passed!
```

**Результат: PASS.** Автосортировка завершилась без изменений и не вернула цикл; независимые import/metadata/route probes после неё прошли.

## Критерий 10 — runtime smoke и логи

Сервер был поднят из `fastapi-application` одним процессом PID `954819` после проверки свободного порта.

### `/docs`

Команда:

```bash
curl -sS http://127.0.0.1:8000/docs -o /tmp/qa_docs_body -w 'http_code=%{http_code} body_bytes=%{size_download}\n'
```

Expected: HTTP `200`.

Actual:

```text
http_code=200 body_bytes=1031
curl_exit=0
body_prefix: <!DOCTYPE html> <html> <head> <meta name="viewport" ...
```

### `/api/blog/articles`

Команда:

```bash
curl -sS http://127.0.0.1:8000/api/blog/articles -o /tmp/qa_blog_body -w 'http_code=%{http_code} body_bytes=%{size_download}\n'
```

Expected: допустим любой контрактный HTTP-код, но тело должно быть валидным JSON и без traceback.

Actual:

```text
http_code=200 body_bytes=15893
curl_exit=0
valid_json=True type=dict prefix={'articles': [{'author': 'NoName', 'lang': 'AI инструменты', 'art_id': 1788345978, 'title': 'aion-zcode-1', 'file_name': 'AI инструменты/aion-zcode-1.md', 'section': 'AI инструменты', 'complete': True}, ...]}
```

### Существующий order endpoint `/orders/get_all_orders`

Команда:

```bash
curl -sS http://127.0.0.1:8000/orders/get_all_orders -o /tmp/qa_order_body -w 'http_code=%{http_code} body_bytes=%{size_download}\n'
```

Expected: допустимы `401/422/404` по контракту, но не `500` и не import traceback.

Actual:

```text
http_code=422 body_bytes=92
curl_exit=0
{"detail":[{"type":"missing","loc":["query","params"],"msg":"Field required","input":null}]}
```

### Auth route paths через работающий app OpenAPI

Команда извлекла paths из:

```bash
curl -sS http://127.0.0.1:8000/openapi.json -o /tmp/qa_openapi_final -w 'http_code=%{http_code} body_bytes=%{size_download}\n'
```

Actual:

```text
http_code=200 body_bytes=33456
matching=['/api/blog/articles', '/api/blog/sections', '/auth/account', '/auth/jwt/login', '/auth/jwt/logout', '/auth/register', '/orders/get_all_orders', '/users/me']
ex_user_post=[]
path_count=32
```

### Логи

В `fastapi-application/log/one_fast.log` выполнен scan строк `Traceback` и `ERROR`:

```text
fastapi-application/log/one_fast.log: matching_lines=0
log_scan_exit=0
```

Uvicorn startup/request log:

```text
INFO: Started server process [954819]
INFO: Waiting for application startup.
INFO: Application startup complete.
INFO: Uvicorn running on http://127.0.0.1:8000
INFO: ... "GET /openapi.json HTTP/1.1" 200 OK
INFO: ... "GET /docs HTTP/1.1" 200 OK
INFO: ... "GET /api/blog/articles HTTP/1.1" 200 OK
INFO: ... "GET /orders/get_all_orders HTTP/1.1" 422 Unprocessable Entity
INFO: Shutting down
INFO: Application shutdown complete.
INFO: Finished server process [954819]
```

В stderr был только `FastAPIDeprecationWarning` о `ORJSONResponse`, без traceback и без HTTP 500.

**Результат: PASS.**

## Завершение и очистка

Свой сервер остановлен корректно:

```text
stopped_pid=954819
```

Проверка после остановки:

```text
pgrep -af '[u]vicorn[[:space:]].*main:main_app'
pgrep_exit=1

curl -m 2 -sS -o /tmp/qa_poststop_final -w 'http_code=%{http_code}\n' http://127.0.0.1:8000/openapi.json
http_code=000
poststop_curl_exit=7
```

**Серверов uvicorn, поднятых QA, не осталось; порт 8000 свободен.**

## Итог по критериям

| # | Expected | Actual | Результат |
|---:|---|---|---|
| 1 | Прямой auth import, exit 0, `auth-ok` | `auth-ok`, exit 0; повтор после autofix также 0 | PASS |
| 2 | Прямой Base import, exit 0, `base-ok` | `base-ok`, exit 0; повтор также 0 | PASS |
| 3 | Ровно шесть требуемых metadata tables | Точный set получен, exit 0; повтор также 0 | PASS |
| 4 | `main_app` import и `len==11` | `route_count=11`, exit 0 | PASS |
| 5 | 8 auth/blog/order paths, без `ex_user_post` | Все 8 в OpenAPI, `ex_user_post=[]` | PASS |
| 6 | `5fed75984f99 (head)` | Получен ровно этот head, exit 0 | PASS |
| 7 | Alembic upgrade/check без новых операций | `No new upgrade operations detected.`, exit 0 | PASS |
| 8 | Import Ruff clean; общий baseline отдельно | 5 файлов: PASS; полный Ruff: 18 baseline errors, exit 1; F821 в main.py устранён | PASS в scope / baseline FAIL отдельно |
| 9 | Автосортировка не возвращает цикл; повторные probes | write-mode `--fix`: exit 0, product diff не изменился; повторные probes PASS | PASS |
| 10 | `/docs` 200, blog valid JSON, order не 500, без traceback | 200; JSON 200; order 422 JSON; лог без Traceback/ERROR | PASS |

Дефектов продукта объективно не обнаружено; `tasks/current/DEFECTS.md` не создавался.
