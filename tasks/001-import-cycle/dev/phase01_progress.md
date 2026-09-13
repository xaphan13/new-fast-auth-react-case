# Прогресс фазы 01

Дата: 2026-09-13

## Исходный контракт

- Публичный импорт `db_core`: `from db_core import Base` из `db_core.model_base`.
- Текущие модельные модули: `auth_users.models` (`User` → `user`), `ex_order_product.model_order_product` (`Order` → `orders`, `Product` → `products`, `OrderProductAssociation` → `order_product_association`), `md_articles.models` (`BlogUser` → `blog_user`, `BlogPost` → `blog_post`).
- Старый `db_core/__init__.py` реэкспортировал все доменные модели; `md_articles/__init__.py` eager-import'ировал `setup_frontend`.
- Разрешённые продуктовые файлы фазы: `fastapi-application/db_core/__init__.py`, `fastapi-application/db_core/model_registry.py`, `fastapi-application/md_articles/__init__.py`.

## Порядок проверок

После каждого изменённого продуктового файла: импорт изменённого модуля, `ruff` по изменённому файлу, затем контрольный checkpoint. Сырые выводы команд сохраняются в `tasks/current/dev/phase01_*.txt`; в этот файл добавляются только краткие вердикты.

Статус: исходное состояние зафиксировано; правки ещё не начаты.

## 2026-09-13 — db_core/__init__.py

Удалены доменные реэкспорты и workaround-комментарии; оставлен только публичный инфраструктурный `Base`. Import probe и ruff: PASS (выводы: `phase01_after_db_core_import.txt`, `phase01_after_db_core_ruff.txt`).

## 2026-09-13 — db_core/model_registry.py

Создан минимальный `load_model_registry() -> None` с импортами `auth_users.models`, `ex_order_product.model_order_product` и `md_articles.models`; классы не дублируются и регистрируются через импорт в общей metadata. Registry import probe и ruff: PASS (выводы: `phase01_after_registry_import.txt`, `phase01_after_registry_ruff.txt`).

## 2026-09-13 — md_articles/__init__.py

Удалён eager-import `md_articles.setup_frontend` и его `__all__`; пакет теперь не запускает frontend/API при импорте моделей. Прямые внутренние импорты через `md_articles.setup_frontend` не менялись. Auth import probe и ruff: PASS (выводы: `phase01_after_md_articles_auth_import.txt`, `phase01_after_md_articles_ruff.txt`).

## Финальный checkpoint — 2026-09-13

- `auth_users` import probe: PASS, `auth-ok`.
- `db_core` Base import probe: PASS, `base-ok`.
- Registry metadata probe: PASS, точный набор `['blog_post', 'blog_user', 'order_product_association', 'orders', 'products', 'user']`.
- Import-only ruff по трём Python-файлам: PASS.
- `git diff --stat`/`git status`: изменены только три разрешённых продуктовых файла и `tasks/current/dev/phase01_progress.md`; сырые выводы находятся в `tasks/current/dev/phase01_*.txt`.
