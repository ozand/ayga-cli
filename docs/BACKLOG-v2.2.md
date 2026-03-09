# A-Parser CLI v2.2 — Список доработок

**Дата:** 2026-03-08  
**На основе:** Уроков из интеграции с реальным A-Parser API

---

## 🔴 Критичные (P0) — Блокируют production использование

### 1. Убрать несуществующий метод `sync`
**Проблема:** Команда `aparser parsers sync` пытается вызвать `getParsersList`, которого нет в API  
**Решение:** 
- Удалить команду `sync` из CLI
- Создать статический manifest с топ-50 парсерами
- Добавить команду `aparser parsers list-static` для просмотра известных парсеров

**Файлы:** `src/aparser_cli/commands/parsers.py`, `src/aparser_cli/manifest.py`

---

### 2. Добавить статический manifest с популярными парсерами
**Проблема:** Нет способа узнать доступные парсеры без обращения к API  
**Решение:**
- Создать `src/aparser_cli/static_manifest.json` с 50+ популярными парсерами
- Включить: FreeAI::Perplexity, FreeAI::ChatGPT, SE::Google, Net::Whois и др.
- Для каждого парсера: название, категория, описание, required overrides

**Файлы:** Новый файл + обновление `manifest.py` для загрузки статики

---

### 3. Документировать proxyChecker для каждого парсера
**Проблема:** Perplexity требует `proxyChecker: reproxy_v4`, но это неочевидно  
**Решение:**
- Добавить поле `requiredOverrides` в static manifest
- При вызове `aparser parsers info FreeAI::Perplexity` показывать required overrides
- Добавить валидацию: если proxyChecker не указан — предупреждение

**Файлы:** `src/aparser_cli/commands/parsers.py`, static manifest

---

## 🟡 Важные (P1) — Улучшают UX

### 4. Улучшить команду `run` — добавить примеры использования
**Проблема:** Неочевидно, какие overrides нужны для каждого парсера  
**Решение:**
- `aparser run FreeAI::Perplexity --examples` — показать примеры запросов
- Автоматически подставлять `proxyChecker: reproxy_v4` для Perplexity
- Валидация перед отправкой: проверить все required overrides

**Файлы:** `src/aparser_cli/commands/run.py`

---

### 5. Добавить команду `test` для проверки конфигурации
**Проблема:** Сложно понять, работает ли парсер без реального запроса  
**Решение:**
- `aparser test FreeAI::Perplexity` — выполнить тестовый запрос с `query: "test"`
- Показать результат и логи
- Полезно для проверки proxyChecker и других настроек

**Файлы:** Новый файл `src/aparser_cli/commands/test.py`

---

### 6. Улучшить обработку ошибок A-Parser API
**Проблема:** Ошибки прокси неинформативны ("500 Internal Server Error")  
**Решение:**
- Парсить логи из ответа API
- Показывать человекочитаемые ошибки:
  - "Proxy error: попробуйте указать proxyChecker"
  - "Timeout: увеличьте значение timeout override"
- Добавить ссылку на документацию по troubleshooting

**Файлы:** `src/aparser_cli/client/http.py`, `src/aparser_cli/exceptions.py`

---

## 🟢 Желательные (P2) — Nice to have

### 7. Добавить шаблоны запросов (presets)
**Проблема:** Каждый раз писать overrides утомительно  
**Решение:**
- `aparser presets list` — список шаблонов
- `aparser presets save perplexity-business "FreeAI::Perplexity" --overrides "proxyChecker=reproxy_v4,timeout=120"`
- `aparser run --preset perplexity-business "запрос"`

**Файлы:** Новый модуль `src/aparser_cli/presets.py`

---

### 8. Интеграция с Redis очередью
**Проблема:** Не используем Redis API A-Parser  
**Решение:**
- Добавить команду `aparser redis status` — проверить очередь
- `aparser redis push` — добавить задачу в Redis вместо HTTP
- Полезно для batch processing

**Файлы:** `src/aparser_cli/client/redis.py`, команды

---

## 📋 План реализации

| # | Задача | Приоритет | Оценка | Субагент |
|---|--------|-----------|--------|----------|
| 1 | Убрать sync, добавить static manifest | P0 | 2ч | Subagent-1 |
| 2 | Документировать proxyChecker | P0 | 1ч | Subagent-1 |
| 3 | Улучшить run с examples и валидацией | P1 | 2ч | Subagent-2 |
| 4 | Добавить команду test | P1 | 2ч | Subagent-2 |
| 5 | Улучшить обработку ошибок | P1 | 2ч | Subagent-3 |
| 6 | Добавить presets | P2 | 3ч | Subagent-3 |
| 7 | Интеграция с Redis | P2 | 3ч | Subagent-4 |

**Всего:** 15 часов работы, 4 субагента

---

## ✅ Acceptance Criteria

- [ ] `aparser parsers list-static` показывает 50+ парсеров
- [ ] `aparser parsers info FreeAI::Perplexity` показывает required overrides
- [ ] `aparser test FreeAI::Perplexity` выполняет тестовый запрос
- [ ] `aparser run FreeAI::Perplexity "query"` автоматически подставляет proxyChecker
- [ ] Ошибки прокси показывают понятное сообщение с рекомендацией
- [ ] Все 141 тест проходят + новые тесты для новых команд
