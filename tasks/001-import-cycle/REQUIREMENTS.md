# Полное устранение циклического импорта auth_users/db_core

Устранить циклический импорт между `auth_users`, `db_core` и `md_articles` архитектурно, а не предзагрузкой `db_core` в `main.py`. Импорты авторизации, приложения и Alembic должны работать независимо, при этом SQLAlchemy metadata должна по-прежнему включать все фактически используемые ORM-модели.

## Подтверждённые решения

- «Пользователь просит устранить циклический импорт полностью, а не только обходить его предзагрузкой `db_core` в `main.py`.»
- «Текущее подтверждённое поведение: `cd fastapi-application && ../.venv/bin/python -c "from main import main_app; print(len(main_app.routes))"` проходит; прямой `../.venv/bin/python -c "from auth_users import active_user"` падает на цикле `auth_users.models -> db_core.__init__ -> md_articles.__init__ -> setup_frontend -> api_blog -> auth_users`.»
- «Нужно сделать архитектурно безопасные импорты, сохранить все ORM-модели в `Base.metadata` и Alembic autogenerate, сохранить auth/blog/order маршруты и не восстанавливать отсутствующий `ex_user_post`, если его нет в tree.»
- «Донор/стек: текущий `fastapi-users` в auth_users, SQLAlchemy/Alembic; не предлагай замену fastapi-users.»
- Меняется только импортная композиция. `fastapi-users`, SQLAlchemy, Alembic, схема JWT/cookie, модели, маршруты и HTTP-контракты не заменяются и не перепроектируются.
- Доменные модели не должны импортироваться из `db_core/__init__.py`. Этот initializer оставляется инфраструктурным и не должен знать о `auth_users`, `md_articles` или `ex_order_product`.
- Для сохранения регистрации моделей вводится минимальный явный загрузчик `db_core.model_registry.load_model_registry()`. Он вызывается только на границах, которым действительно нужна полная metadata: при сборке приложения и в `alembic/env.py`.
- `md_articles/__init__.py` не должен при импорте пакета тянуть `setup_frontend` и `api_blog`. Это устраняет побочный импорт frontend/API при загрузке `md_articles.models`; внутренний код продолжает импортировать `md_articles.setup_frontend` явно.
- Текущий подтверждённый счётчик приложения — `11`: каталог `ex_user_post` отсутствует в текущем tree, поэтому его маршруты не являются частью этой задачи и не восстанавливаются.
- Текущая единственная ревизия Alembic `5fed75984f99` остаётся head. Новая миграция не нужна: состав и структура таблиц не меняются.
- Ошибки `I001` в старом `db_core/__init__.py` должны исчезнуть за счёт удаления order-sensitive доменных импортов. Порядок импортов не должен быть смысловым условием загрузки; `ruff check --select I --fix` и IDE Optimize Imports должны оставлять рабочую архитектуру.

## Результат

После задания:

1. `from auth_users import active_user` проходит в отдельном чистом процессе без предварительного импорта `main` или `db_core`.
2. `from db_core import Base` проходит в отдельном чистом процессе и не запускает импорт доменных моделей и блогового frontend/API.
3. Полная загрузка приложения через `from main import main_app` проходит и сохраняет текущий фактический `len(main_app.routes) == 11`, включая auth, blog и order маршруты; отсутствующий `ex_user_post` не добавляется.
4. Явный вызов `load_model_registry()` наполняет `Base.metadata` всеми текущими моделями: `blog_post`, `blog_user`, `order_product_association`, `orders`, `products`, `user`.
5. `alembic/env.py` использует тот же явный загрузчик до присвоения `target_metadata = Base.metadata`; `alembic heads` видит `5fed75984f99 (head)`, а autogenerate не считает существующие модели отсутствующими.
6. В `main.py` отсутствует workaround `import db_core` как предзагрузка. Сборка приложения сама явно вызывает загрузчик metadata в композиционной границе.
7. Автоматическая сортировка импортов на изменённых файлах не возвращает цикл; после неё независимые импортные smoke-проверки снова проходят.
8. На изменённых файлах `uv run ruff check --select I` проходит после архитектурной правки и автофикса. Полный `uv run ruff check .` запускается для фиксации baseline; существующие нерелевантные lint-ошибки не маскируются как успех и не расширяют это задание.

## Архитектурный разбор

### Bounded context

В задание входит только импортная композиция Python-приложения вокруг четырёх границ: инфраструктурный `db_core`, доменный пакет `auth_users`, доменный пакет `md_articles` и композиционные входы `main.py`/Alembic. Затрагиваются `Base`, загрузка ORM-моделей и импорты роутеров. Вне bounded context остаются бизнес-логика fastapi-users, JWT/cookie-поведение, схемы и хендлеры auth, блоговый YAML/Markdown, order-логика, frontend, HTTP-ответы и миграционная схема.

Подтверждённый дефект вызван тем, что `db_core/__init__.py` реэкспортирует доменные `Order/Product`, `BlogUser/BlogPost` и `auth_users.User`. При прямом импорте `auth_users.models` пакет `db_core` выполняет этот initializer, тот начинает импорт `md_articles`, а `md_articles.__init__` тянет frontend и `api_blog`, который снова импортирует `auth_users.active_user` из частично загруженного пакета. Комментарии о «безопасном импорте в конце» и предзагрузка в `main.py` только фиксируют порядок одного сценария, но не устраняют цикл.

### Интеграционные границы и контракты

- `db_core/__init__.py`: инфраструктурный публичный контракт `from db_core import Base`; доменные модели из него больше не экспортируются.
- `db_core/model_registry.py`: публичная функция `load_model_registry() -> None`. Она импортирует текущие модельные модули для регистрации классов в общей `Base.metadata`, не содержит HTTP-роутеров и не меняет модели. Повторный вызов безопасен благодаря кэшу модулей Python.
- `main.py`: до `create_app()` вызывается `load_model_registry()`. Существующие `main_app.include_router(...)`, `include_router_api_frontend(...)` и `mount_vite_react_assets(...)` сохраняются в том же порядке; catch-all остаётся последним.
- `alembic/env.py`: импортирует `Base`, вызывает `load_model_registry()`, затем задаёт `target_metadata = Base.metadata`. URL и текущая head-ревизия не меняются.
- `md_articles/__init__.py`: не выполняет eager-import `setup_frontend`; `main.py` продолжает использовать прямой импорт `from md_articles.setup_frontend import ...`. Если сохраняется пакетный API, он должен быть реализован только ленивым безопасным способом без импорта при загрузке `md_articles.models`; добавлять новый слой совместимости без необходимости нельзя.
- Набор таблиц metadata фиксирован: `{"blog_post", "blog_user", "order_product_association", "orders", "products", "user"}`. Модель отсутствующего `ex_user_post` в него не добавляется.

### Зависимости и порядок работ

1. Сначала удалить доменные импорты из `db_core/__init__.py` и сделать `md_articles/__init__.py` безопасным при импорте моделей; одновременно добавить явный model registry.
2. Затем подключить registry в `main.py` и Alembic. Эти изменения зависят от точной сигнатуры loader и набора модельных модулей.
3. После этого выполнить независимые import/metadata/route/Alembic/ruff проверки. Изменения фаз 1 и 2 последовательны; отдельные HTTP-проверки auth/blog/order можно выполнять после фазы 2 независимо от проверки import-порядка.

### Новая абстракция и почему она нужна

`db_core.model_registry` — единственный новый слой и минимальный загрузчик. Он нужен потому, что SQLAlchemy регистрирует ORM-класс в metadata только после импорта его модуля, но размещение этих импортов в `db_core/__init__.py` создаёт цикл. Без отдельной явной границы пришлось бы либо вернуть order-sensitive импортный порядок/предзагрузку, либо дублировать список моделей в `main.py` и Alembic, что приведёт к расхождению metadata. Registry устраняет дублирование и оставляет `db_core` независимым от доменов; новых зависимостей и сервисов не добавляет.

### Релевантные риски

- Риск корректности: если модельный модуль не попадёт в loader, таблица исчезнет из `Base.metadata` и Alembic autogenerate не увидит её. Поэтому список таблиц проверяется точным assert.
- Риск совместимости: удаление доменных реэкспортов из `db_core` может сломать внешний код, импортирующий модели оттуда. В bounded context репозитория такие потребители не подтверждены; зафиксированный контракт задания — `from db_core import Base`, а модели импортируются из своих доменных модулей/registry.
- Риск производительности несущественен: loader выполняется один раз при импорте приложения и один раз при загрузке Alembic; на обработку HTTP-запросов он не влияет.
- Риск безопасности не меняется: auth остаётся на текущем `fastapi-users` с JWT/cookie; секреты, статусы и права доступа не трогаются.
- Вне рамок остаются исправление дефектов auth/API, изменение миграционной схемы, удаление старых blog-таблиц и восстановление `ex_user_post`.

## Вне рамок

- Не менять `fastapi-users` на другую библиотеку, транспорт или стратегию.
- Не менять модели, поля, таблицы, связи, типы ID, миграции и содержимое `Base.metadata`, кроме способа их импорта.
- Не менять auth/blog/order URL, имена маршрутов, зависимости `active_user`, схемы ответов и поведение JWT/cookie.
- Не восстанавливать `ex_user_post`, его роуты или модели, если каталога нет в текущем tree.
- Не добавлять frontend-изменения, тестовый фреймворк, новые runtime-зависимости, CSRF/rate-limit и рефакторинг бизнес-логики.
- Не исправлять известные дефекты, не относящиеся к циклу импорта.
- Не редактировать `AGENTS.md`, `QWEN.md`, `README.md`, `docs/`, архивные задания и файлы фронтенда.
- Adversarial-прогон не включён: пользователь его явно не запрашивал.

## План фаз

Единица исполнения — фаза: одно делегирование, 1–3 файла, бюджет ~10–15 ходов.
Следующая фаза стартует только после зелёного checkpoint и ревью диффа оркестратором.
Прогресс фазы разработчик фиксирует в `tasks/current/dev/phaseNN_progress.md`.

| # | Фаза | Исполнитель | Файлы | Контракт | Checkpoint | Бюджет ходов |
|---|---|---|---|---|---|---|
| 1 | Разрыв доменного цикла и registry | backend-dev | `fastapi-application/db_core/__init__.py`; `fastapi-application/db_core/model_registry.py`; `fastapi-application/md_articles/__init__.py` | `db_core` экспортирует инфраструктурный `Base`; `load_model_registry() -> None` явно импортирует все шесть текущих таблиц; `md_articles` не тянет setup/API при импорте моделей | два независимых import-проба + точный assert набора metadata-таблиц | ~14 |
| 2 | Подключение границ приложения и Alembic | backend-dev | `fastapi-application/main.py`; `fastapi-application/alembic/env.py` | приложение явно вызывает loader вместо `import db_core`; Alembic вызывает тот же loader перед `target_metadata`; маршруты и head не меняются | import `main_app` → текущие `11`, `alembic heads` → `5fed75984f99 (head)`, import-only ruff по изменённым файлам | ~12 |
| 3 | Финальная независимая проверка | qa | `tasks/current/e2e/import-cycle.md` | зафиксировать сырые результаты независимых импортов, metadata/Alembic, route smoke и проверки сортировки импортов; код продукта не менять | полный список критериев ниже, выводы сохранены в e2e-файле | ~10 |

### Фаза 1: Разрыв доменного цикла и registry

- Файлы: `fastapi-application/db_core/__init__.py`, `fastapi-application/db_core/model_registry.py`, `fastapi-application/md_articles/__init__.py`.
- Контракт:
  - `db_core/__init__.py` содержит только безопасный инфраструктурный импорт `Base` и не импортирует `auth_users`, `md_articles` или `ex_order_product`.
  - `db_core.model_registry.load_model_registry() -> None` импортирует `auth_users.models`, `ex_order_product.model_order_product` и `md_articles.models` (плюс только необходимые текущие модельные модули) для регистрации `User`, `Order`, `Product`, `OrderProductAssociation`, `BlogUser`, `BlogPost` в общей metadata.
  - `md_articles/__init__.py` больше не импортирует `setup_frontend` на уровне package import. Если сохранение ранее доступных пакетных имён необходимо для подтверждённых внутренних потребителей, использовать отложенный доступ без eager-import; не возвращать циклическую загрузку.
  - Не переносить модели в новый пакет, не менять классы и не добавлять `ex_user_post`.
- Шаги:
  1. Сначала зафиксировать список текущих модельных модулей и публичный `Base`-контракт; не копировать модели в registry.
  2. Удалить из `db_core/__init__.py` доменные реэкспорты и комментарии, описывающие workaround-предзагрузку.
  3. Создать `model_registry.py` одним цельным файлом с одной явной функцией loader и русским docstring о границе metadata.
  4. Убрать eager-import frontend/API из `md_articles/__init__.py`, сохранив прямые внутренние импорты через `md_articles.setup_frontend`.
  5. Записать прогресс после каждого файла; проверить diff, чтобы не появились изменения моделей или маршрутов.
- Checkpoint:
  ```bash
  cd fastapi-application && ../.venv/bin/python -c "from auth_users import active_user; assert active_user is not None; print('auth-ok')"
  cd fastapi-application && ../.venv/bin/python -c "from db_core import Base; assert Base is not None; print('base-ok')"
  cd fastapi-application && ../.venv/bin/python -c "from db_core import Base; from db_core.model_registry import load_model_registry; load_model_registry(); expected={'blog_post','blog_user','order_product_association','orders','products','user'}; assert set(Base.metadata.tables)==expected, sorted(Base.metadata.tables); print(sorted(Base.metadata.tables))"
  ```
  Ожидание: первые команды печатают ровно `auth-ok` и `base-ok`; третья печатает ровно отсортированный список из шести таблиц и завершается с кодом `0`.
- Готовность фазы: прямой `auth_users`-импорт не зависит от `main`/предзагрузки, `from db_core import Base` не запускает доменные импорты, loader даёт точный набор из шести таблиц, а diff ограничен тремя файлами фазы.

### Фаза 2: Подключение границ приложения и Alembic

- Файлы: `fastapi-application/main.py`, `fastapi-application/alembic/env.py`.
- Контракт:
  - `main.py` импортирует `load_model_registry` и вызывает его до создания/регистрации приложения; строки `import db_core` как workaround нет.
  - Порядок подключения `router_api`, order router, `include_router_api_frontend` и SPA catch-all не меняется. Отсутствующий `ex_user_post` не добавляется.
  - `alembic/env.py` импортирует `Base` и loader из `db_core`, вызывает loader до `target_metadata = Base.metadata`; настройки URL и функции online/offline migrations сохраняются.
  - Никаких новых revision-файлов и изменений `alembic/versions/`.
- Шаги:
  1. Подключить loader в composition boundary `main.py`; не добавлять импорт доменных моделей в main.
  2. Подключить loader в Alembic boundary рядом с `target_metadata`.
  3. Проверить, что один и тот же registry используется в обоих местах и список таблиц не дублируется.
  4. Проверить независимые процессы после автоматической сортировки импортов на изменённых файлах.
- Checkpoint:
  ```bash
  uv run ruff check --select I fastapi-application/db_core/__init__.py fastapi-application/db_core/model_registry.py fastapi-application/md_articles/__init__.py fastapi-application/main.py fastapi-application/alembic/env.py
  cd fastapi-application && ../.venv/bin/python -c "from main import main_app; assert len(main_app.routes)==11; print(len(main_app.routes))"
  cd fastapi-application && ../.venv/bin/python -c "from auth_users import active_user; from db_core import Base; assert active_user is not None and Base is not None; print('independent-imports-ok')"
  cd fastapi-application && ../.venv/bin/alembic heads
  ```
  Ожидание: ruff завершается с кодом `0` без `I001`; route probe печатает `11`; независимый probe печатает `independent-imports-ok`; `alembic heads` содержит `5fed75984f99 (head)`.
- Готовность фазы: приложение собирается без предзагрузки `db_core`, Alembic получает полную metadata через loader, текущий head и route count сохранены, изменены только два файла фазы.

### Фаза 3: Финальная независимая проверка

- Файлы: `tasks/current/e2e/import-cycle.md`.
- Контракт: qa не меняет код продукта; все сырые выводы команд сохраняет в одном markdown-артефакте с командами, exit code и ожидаемым/фактическим результатом.
- Шаги и проверки:
  1. Запустить в отдельных процессах прямые `from auth_users import active_user` и `from db_core import Base`; предварительно не импортировать `main`, `db_core` или registry.
  2. Проверить `load_model_registry()` и точный set из шести таблиц.
  3. Проверить `from main import main_app`, `len(main_app.routes) == 11` и наличие auth/blog/order путей; не требовать `/users/get_all_users` и не добавлять `ex_user_post`.
  4. Проверить `alembic heads`; при доступной локальной SQLite-базе выполнить `alembic upgrade heads`, затем `alembic check` и зафиксировать отсутствие новых upgrade operations. Если проверка зависит от отсутствующего/грязного локального DB-файла, отдельно записать это как environment limitation, но metadata probe обязателен.
  5. Выполнить `uv run ruff check .`; проблемы, не связанные с импортным циклом, перечислить отдельно с файлами и кодами, не объявляя их исправленными.
  6. Выполнить на изменённых Python-файлах `uv run ruff check --select I --fix ...`, затем повторить независимые import-пробы, route count и metadata assert. Ожидание: сортировка завершается успешно и не возвращает цикл.
  7. Выполнить дешёвый runtime smoke уже существующих поверхностей: `/docs`, `/api/blog/articles`, один order endpoint и проверку auth route paths через `main_app`; сервер запускать из `fastapi-application`, не оставлять процесс после прогона.
- Checkpoint: `tasks/current/e2e/import-cycle.md` существует, содержит PASS/FAIL по каждому критерию, команды запуска из правильного cwd и дословные существенные выводы; открытый дефект заводится только при объективном несоответствии контракту.
- Готовность фазы: все критерии успеха подтверждены артефактом, либо несоответствие явно заведено в `DEFECTS.md`; код продукта после проверки сортировки импортов остаётся согласованным с фазами 1–2.

## Критерии успеха

Проверяются qa по завершении всех фаз; сырые выводы — в `tasks/current/e2e/import-cycle.md`.

| # | Критерий | Проверка | Ожидание |
|---|---|---|---|
| 1 | Прямой импорт auth не требует предзагрузки | `cd fastapi-application && ../.venv/bin/python -c "from auth_users import active_user; assert active_user is not None; print('auth-ok')"` в чистом процессе | Код `0`, ровно `auth-ok`, без `ImportError`/partially initialized module |
| 2 | Базовый db_core-импорт независим | `cd fastapi-application && ../.venv/bin/python -c "from db_core import Base; assert Base is not None; print('base-ok')"` | Код `0`, ровно `base-ok` |
| 3 | Все текущие ORM-модели зарегистрированы | Импорт `Base`, вызов `load_model_registry()`, assert точного set таблиц `blog_post`, `blog_user`, `order_product_association`, `orders`, `products`, `user` | Assert проходит; отсутствующие и лишние таблицы отсутствуют; `ex_user_post` не появляется |
| 4 | Приложение собирается независимо | `cd fastapi-application && ../.venv/bin/python -c "from main import main_app; assert len(main_app.routes)==11; print(len(main_app.routes))"` | Код `0`, печать `11` |
| 5 | Auth/blog/order маршруты сохранены | Python probe по `main_app.routes` с assert путей `/auth/jwt/login`, `/auth/jwt/logout`, `/auth/register`, `/users/me`, `/auth/account`, `/api/blog/articles`, `/api/blog/sections`, `/orders/get_all_orders` (или фактического существующего order endpoint из router) | Все перечисленные фактические маршруты найдены; route count `11`; `ex_user_post` не восстанавливается |
| 6 | Alembic видит текущий head | `cd fastapi-application && ../.venv/bin/alembic heads` | Вывод содержит `5fed75984f99 (head)` |
| 7 | Alembic получает полную metadata | `cd fastapi-application && ../.venv/bin/alembic upgrade heads && ../.venv/bin/alembic check` при доступной SQLite-БД, плюс metadata assert из критерия 3 | Upgrade завершается успешно; `alembic check` сообщает отсутствие новых upgrade operations; при невозможности DB-проверки metadata assert и причина ограничения записаны отдельно |
| 8 | Import-related Ruff rules clean | `uv run ruff check --select I` on the phase 1–2 Python files; separately run `uv run ruff check .` and record the existing baseline | Изменённые файлы проходят import checks; полный baseline перечислен отдельно и не объявляется исправленным без отдельного scope |
| 9 | Автосортировка не возвращает цикл | `uv run ruff check --select I --fix` на пяти изменённых Python-файлах, затем повтор критериев 1–4 | Автофикс завершается без ошибок, повторные независимые импорты и route/metadata probes проходят; порядок импортов не является runtime workaround |
| 10 | Рантайм-соседние поверхности не сломаны | При запущенном приложении: `curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/docs`, `curl -s http://127.0.0.1:8000/api/blog/articles`, один `curl` order endpoint | `/docs` отвечает `200`, blog endpoint отвечает валидным JSON, order endpoint отвечает без import/runtime traceback; доказательство в e2e |

## Финальные критерии

1. Каждый критерий успеха подтверждён доказательством в `tasks/current/e2e/import-cycle.md`; впечатления и пересказ без команды не считаются доказательством.
2. `tasks/current/DEFECTS.md` создаётся только при найденном дефекте; к закрытию задания в нём нет статусов `OPEN`.
3. Adversarial-прогон не выполняется и `ADVERSARIAL_REVIEW.md` не создаётся, поскольку adversary явно не был запрошен при создании задания.
4. После QA не остаются тестовые серверы и фоновые процессы uvicorn.

## Открытые вопросы

Нет. В режиме yolo неоднозначности закрыты в подтверждённых решениях: вводится один минимальный `db_core.model_registry`, `db_core` больше не реэкспортирует доменные модели, `md_articles` не делает eager-import frontend/API, текущая миграция остаётся head, а `ex_user_post` не восстанавливается.

---

# Отчёт о выполнении

- Дата закрытия: 2026-09-13
- Коммит: не создавался

## Итог
Циклический импорт устранён через инфраструктурный `db_core.model_registry`; прямые auth/db_core-импорты, сборка приложения, metadata и Alembic работают независимо. Все критерии подтверждены в [e2e/import-cycle.md](e2e/import-cycle.md).

## Изменения
- `fastapi-application/db_core/__init__.py` → оставлен только экспорт `Base`.
- `fastapi-application/db_core/model_registry.py` → добавлен единый загрузчик ORM-моделей.
- `fastapi-application/md_articles/__init__.py` → убран eager-import frontend/API.
- `fastapi-application/main.py` → явный вызов registry на composition boundary; сохранён `uvicorn`.
- `fastapi-application/alembic/env.py` → тот же registry вызывается до `target_metadata`.

## Критерии успеха

| # | Критерий | Результат | Доказательство |
|---|---|---|---|
| 1–5 | Независимые импорты, metadata и auth/blog/order маршруты | PASS | [e2e/import-cycle.md](e2e/import-cycle.md) |
| 6–7 | Alembic head и отсутствие новых upgrade operations | PASS | [e2e/import-cycle.md](e2e/import-cycle.md) |
| 8–9 | Import Ruff и автосортировка | PASS в scope; полный baseline отдельно | [e2e/import-cycle.md](e2e/import-cycle.md) |
| 10 | Runtime smoke `/docs`, blog и order | PASS | [e2e/import-cycle.md](e2e/import-cycle.md) |

## Дефекты
Не найдены — `DEFECTS.md` не создавался.

## Adversarial-прогон
В рамках текущего задания не выполнялся по условиям спеки. В архиве сохранён ранее существовавший артефакт `ADVERSARIAL_REVIEW.md`; новых ADV-записей текущий прогон не добавлял.

## Участники
- backend-dev: фазы 1–2 и post-QA import checkpoint.
- qa: независимая проверка и runtime smoke.
- adversary: не привлекался по условиям спеки.
- оркестратор: ревью диффа, исправление F821-регрессии через делегированный узкий checkpoint и архивирование.
