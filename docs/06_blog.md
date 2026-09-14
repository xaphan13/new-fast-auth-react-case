# 06. Блог

Блог состоит из файлового контента `content_art/`, YAML-реестра `md_articles/articles.yaml`, JSON API FastAPI и React-интерфейса. SQLAlchemy используется для пользователей авторизации, но статьи в БД не хранятся.

## Состав

| Компонент | Файл | Назначение |
|---|---|---|
| API статей | `md_articles/api_blog.py` | sections, articles, detail |
| Управление реестром | `md_articles/api_blog.py` | add_all, meta, sync |
| Реестр и рендер | `md_articles/schema_art.py` | YAML, mtime-кэш, Markdown |
| Схемы API | `md_articles/schema_blog.py` | `MetaIn`, `SectionOut` |
| Подключение | `md_articles/setup_frontend.py` | `/static`, `/assets`, catch-all |
| Контент | `content_art/` | `.md` и `.markdown` |
| Клиент статей | `frontend/src/api/blog.ts` | GET-обёртки |
| Управление | `frontend/src/api/artManage.ts` | защищённые POST/GET |

## Хранение статей

`content_art/` содержит Markdown-файлы. Первая папка в относительном пути — `section`:

```text
content_art/
├── Python/article.md       → section = Python
├── Fast API/intro.md       → section = Fast API
└── article-root.md         → section = ""
```

`articles.yaml` содержит список записей:

```yaml
articles:
  - author: Автор
    lang: Python
    art_id: 123
    title: Заголовок
    file_name: Python/article.md
    section: Python
```

`section` автоматически вычисляется из `file_name`, если не задан. Поля `content` в YAML нет: HTML строится только при запросе конкретной статьи.

## Кэш и запись реестра

`get_articles()` сравнивает `st_mtime_ns` и размер файла. Если YAML не менялся, используется кэш процесса. При ошибке разбора предыдущий рабочий список сохраняется, а причина доступна через `get_registry_error()`.

`save_articles()` пишет YAML во временный файл в той же папке и заменяет исходный через `os.replace`. После записи mtime-кэш инвалидируется.

## API

### Публичные маршруты

| Метод | URL | Ответ |
|---|---|---|
| GET | `/api/blog/sections` | `{sections: [{name,label,count}]}` |
| GET | `/api/blog/articles` | `{articles: [...]}`; optional `?section=` |
| GET | `/api/blog/articles/{art_id}` | `{article: {..., content: "<html>"}}` |

Список отдаёт только записи с непустыми `author`, `lang` и `title`. Detail дополнительно требует существующий файл на диске; иначе 404.

### Управление реестром

Все маршруты требуют `Depends(active_user)` из `auth_users`:

| Метод | URL | Назначение |
|---|---|---|
| GET | `/api/blog/art_manage` | реестр, новые файлы, missing entries, yaml_error |
| POST | `/api/blog/art_manage/add_all` | добавить все незарегистрированные Markdown-файлы |
| POST | `/api/blog/art_manage/meta` | добавить/обновить метаданные одного файла |
| POST | `/api/blog/art_manage/sync` | удалить записи без файла |

`add_all` создаёт дефолты `author=NoName`, `title=stem`, `lang=section` и уникальный timestamp-based `art_id`. `meta` сохраняет существующий `section` при обновлении. `sync` удаляет только сиротские записи.

Анонимный запрос к управлению получает 401. Отдельного блогового login API, Starlette-сессии и CSRF-протокола нет — авторизация документирована в [04_authorization.md](04_authorization.md).

## Рендер Markdown

`render_article()` читает файл из `content_art/`. Для `.md` и `.markdown` используется `markdown()` с extensions `fenced_code` и `tables`; другие расширения возвращаются как текст.

Бэкенд отдаёт готовый HTML. `frontend/src/components/MarkdownContent.tsx` вставляет его в единственном разрешённом в проекте месте через `dangerouslySetInnerHTML`, затем запускает глобальный highlight.js. Клиент регистрирует алиасы `env`, `jinja2`, `vue`, `txt`, `js`, `jsx`, `make`, `Dockerfile`, `toml`.

Контент считается доверенным локальным контентом проекта. Если статьи начнут редактировать внешние пользователи, перед вставкой нужен отдельный HTML-sanitizer.

## React-маршруты

`frontend/src/App.tsx` объявляет:

- `/` — статьи и пагинация;
- `/section/:name` — фильтр раздела;
- `/art/:author/:artId` — статья;
- `/about` — информация о сайте;
- `/login`, `/register` — auth-формы;
- `/account` — аккаунт, защищённый `RequireAuth`;
- `/art_manage` — управление реестром, защищённое `RequireAuth`.

`AuthContext` получает пользователя из `/users/me`; блоговые GET-маршруты не требуют входа. `Header` показывает ссылку управления даже анониму, но API и `RequireAuth` не дают выполнить защищённое действие.

## Управление реестром во фронтенде

`ArtManagePage` загружает полный контекст, фильтрует записи по title/file_name и признакам «без автора»/«без языка», редактирует выбранную запись через `ArtManageForms`, добавляет новые файлы и очищает отсутствующие. После каждой мутации выполняется повторная загрузка.

## Подключение React

`include_router_api_frontend()` монтирует `/static`, auth-роутер и `router_blog_api`. `mount_vite_react_assets()` монтирует `/assets`, затем вручную добавляет catch-all. Для `/api` catch-all возвращает JSON 404; для обычных путей — `frontend/dist/index.html`.

## Добавление статьи

1. Создать `.md` в `fastapi-application/content_art/<section>/`.
2. Открыть `/art_manage` под активным пользователем.
3. Нажать добавление новых файлов или заполнить метаданные.
4. Проверить `/api/blog/articles` и открыть страницу статьи.

Если файл удалён вручную, `art_manage` покажет `missing_entries`; `sync` удалит запись из YAML.
