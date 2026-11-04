# TPUMON

Сервис проверяет доступность настроенных HTTP-ресурсов и отдаёт их текущие статусы через REST API.

## Требования

Для запуска через Docker нужны Docker Engine с Compose и свободный порт 8000. Для запуска без Docker нужны Python 3.13 и Poetry 2.x.

## Быстрый запуск

Создайте файл настроек:

```sh
cp .env.example .env
```

Добавьте в `.env` переменную `SERVICES` как JSON-массив объектов с полями `name` и `url`. При необходимости укажите `API_PORT`.

```sh
make prod
```

API будет доступен по адресу `http://localhost:8000`, документация OpenAPI — по адресу `http://localhost:8000/docs`, проверка процесса — `http://localhost:8000/health`. Если изменён `API_PORT`, используйте этот порт в адресах.

Для запуска в режиме разработки:

```sh
make dev
```

Для остановки контейнеров:

```sh
make down
```

Для запуска приложения без Docker:

```sh
make install
make run
```

Для проверки HTTP-сервисов без Docker достаточно настроить `SERVICES` в `.env`.
