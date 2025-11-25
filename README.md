# AI Code Review Assistant

[![CI](https://github.com/Gu1t4rist/ai-code-review-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/Gu1t4rist/ai-code-review-assistant/actions/workflows/ci.yml)
[![Docker Build](https://github.com/Gu1t4rist/ai-code-review-assistant/actions/workflows/docker.yml/badge.svg)](https://github.com/Gu1t4rist/ai-code-review-assistant/actions/workflows/docker.yml)
[![Security Scan](https://github.com/Gu1t4rist/ai-code-review-assistant/actions/workflows/security.yml/badge.svg)](https://github.com/Gu1t4rist/ai-code-review-assistant/actions/workflows/security.yml)
[![Code Quality](https://github.com/Gu1t4rist/ai-code-review-assistant/actions/workflows/code-quality.yml/badge.svg)](https://github.com/Gu1t4rist/ai-code-review-assistant/actions/workflows/code-quality.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

AI-агент для автоматизации code review процессов в GitLab. Помогает сеньор-разработчикам проводить ревью кода, анализируя изменения в Merge Requests, проверяя их на соответствие стандартам и формируя рекомендации.

## Описание задачи

Разработать AI-агента, который помогает сеньор-разработчикам проводить ревью кода в GitLab. Агент анализирует изменения в Merge Request (MR), проверяет их на соответствие стандартам разработки и требованиям по функционалу, выявляет потенциальные ошибки и формирует рекомендации.

## Основные функции

- ✅ Анализировать изменения в коде (diff) при создании или обновлении Merge Request
- ✅ Оценивать корректность реализации относительно описанного функционала
- ✅ Оставлять комментарии с предложениями по улучшению и исправлению
- ✅ Формировать краткое резюме по MR с рекомендацией: merge / needs fixes / reject
- ✅ Поддерживать метки и статусы MR (например: ready-for-merge, needs-review, changes-requested)

## Ценность для банка

- Снижение нагрузки на опытных разработчиков за счёт автоматизации типовых проверок
- Повышение качества и единообразия кода в проектах
- Ускорение процесса ревью и принятия решений по Merge Request
- Поддержка культуры инженерных стандартов и соблюдения best practices
- Возможность использования решения как инструмента обучения младших разработчиков

## Ключевые метрики успеха

### Performance
- Доля релевантных рекомендаций
- Среднее время анализа Merge Request: ≤ 5 минут на MR

### Бизнес
- Уменьшение среднего времени, затрачиваемого сеньорами на ревью

## Архитектура

```
ai-code-review-assistant/
├── src/
│   └── ai_code_review/
│       ├── __init__.py
│       ├── main.py                 # Точка входа (CLI + FastAPI)
│       ├── config.py               # Конфигурация приложения
│       ├── gitlab/
│       │   ├── __init__.py
│       │   ├── client.py           # Async GitLab API клиент (httpx)
│       │   ├── models.py           # Модели данных GitLab
│       │   └── webhooks.py         # Обработка вебхуков
│       ├── ai/
│       │   ├── __init__.py
│       │   ├── review_engine.py    # AI движок для ревью
│       │   ├── prompts.py          # Промпты для LLM
│       │   └── llm_client.py       # Клиент для LLM (OpenAI, Anthropic)
│       └── utils/
│           ├── __init__.py
│           ├── logger.py           # Структурированное логирование
│           └── metrics.py          # Prometheus метрики
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_gitlab_client.py
│   ├── test_llm_client.py
│   ├── test_review_engine.py
│   └── test_metrics.py
├── .github/
│   └── workflows/
│       ├── ci.yml                  # Lint + Test
│       ├── docker.yml              # Docker build & push
│       ├── security.yml            # Security scan
│       └── code-quality.yml        # Code quality checks
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Технологический стек

- **Python 3.11+**
- **GitLab API**: httpx (async)
- **AI/LLM**: OpenAI API, Anthropic Claude API
- **Web Framework**: FastAPI (для вебхуков)
- **Async**: asyncio, aiohttp
- **Monitoring**: Prometheus metrics
- **Testing**: pytest, pytest-asyncio
- **Code Analysis**: ast, pylint, flake8
- **Docker**: для контейнеризации
- **Logging**: structlog

## Быстрый старт

### Установка

```bash
# Клонируйте репозиторий
git clone <repository-url>
cd ai-code-review-assistant

# Создайте виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установите зависимости
pip install -r requirements.txt

# Или установите в режиме разработки
pip install -e ".[dev]"
```

### Конфигурация

```bash
# Скопируйте пример конфигурации
cp .env.example .env

# Отредактируйте .env файл
nano .env
```

Необходимые переменные окружения:

```env
# GitLab Configuration
GITLAB_URL=https://gitlab.company.com
GITLAB_TOKEN=your-gitlab-token
GITLAB_WEBHOOK_SECRET=your-webhook-secret

# AI Provider Configuration
AI_PROVIDER=openai  # or anthropic
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key

# Application Settings
LOG_LEVEL=INFO
MAX_DIFF_SIZE=10000
REVIEW_TIMEOUT=300  # seconds
PORT=8000

# Database (optional, for metrics)
DATABASE_URL=postgresql://user:pass@localhost/ai_review
```

### Запуск

```bash
# Режим вебхука (рекомендуется)
python -m src.ai_code_review.main webhook

# Режим однократного анализа
python -m src.ai_code_review.main review --project-id 123 --mr-iid 45

# С помощью Docker
docker-compose up -d
```

## Использование

### 1. Настройка GitLab Webhook

В настройках проекта GitLab:

1. Перейдите в Settings → Webhooks
2. Добавьте URL: `http://your-server:8000/webhook`
3. Выберите события: `Merge request events`
4. Укажите Secret Token из `.env`
5. Сохраните

### 2. Автоматический режим

После настройки вебхука, агент будет автоматически анализировать MR при:
- Создании нового MR
- Обновлении кода в MR
- Запросе повторного ревью

### 3. Ручной режим

```bash
# Анализ конкретного MR
ai-code-review review --project-id 123 --mr-iid 45

# Или через python
python -m ai_code_review.main review --project-id 123 --mr-iid 45
```

## Примеры использования

### Webhook Response Example

Когда GitLab отправляет webhook на создание MR:

```json
{
  "object_kind": "merge_request",
  "project": {"id": 123},
  "object_attributes": {
    "iid": 45,
    "title": "Add user authentication",
    "state": "opened",
    "action": "open"
  }
}
```

Агент автоматически:
1. ✅ Получает diff всех измененных файлов
2. ✅ Анализирует код с помощью AI (Claude/GPT)
3. ✅ Находит проблемы безопасности, производительности, стиля
4. ✅ Оставляет inline комментарии в коде
5. ✅ Добавляет общее резюме с рекомендацией
6. ✅ Устанавливает метки (`ai-review:approved`, `ai-review:needs-fixes`, etc.)

### Manual Review Example

```bash
# Запустить review для MR #45 в проекте 123
ai-code-review review --project-id 123 --mr-iid 45

# Output:
# ✅ Review completed successfully!
# Recommendation: needs_fixes
# Total issues: 8
#   Critical: 1
#   High: 2
#   Medium: 3
#   Low: 2
```

### Metrics Monitoring

```bash
# Проверить метрики Prometheus
curl http://localhost:8000/metrics

# Примеры метрик:
# code_review_total{ai_provider="anthropic",status="success"} 42
# code_review_duration_seconds_sum 847.3
# ai_tokens_used_total{provider="anthropic",token_type="input"} 1847293
```

### 4. API Endpoints

```bash
# Healthcheck
GET /health

# Webhook endpoint
POST /webhook

# Manual review trigger
POST /api/v1/review
{
  "project_id": 123,
  "merge_request_iid": 45
}

# Get review status
GET /api/v1/review/{review_id}/status

# Get metrics
GET /api/v1/metrics
```

## Типы проверок

### 1. Стандарты кодирования
- Форматирование (PEP 8 для Python, etc.)
- Именование переменных и функций
- Структура кода и модульность
- Документация и комментарии

### 2. Безопасность
- SQL injection
- XSS уязвимости
- Жёстко заданные секреты
- Небезопасные зависимости

### 3. Производительность
- N+1 запросы
- Неэффективные алгоритмы
- Утечки памяти
- Блокирующие операции

### 4. Функциональность
- Соответствие описанию в MR
- Покрытие тестами
- Обработка ошибок
- Edge cases

### 5. Архитектура
- SOLID принципы
- Design patterns
- Разделение ответственности
- Coupling и cohesion

## Примеры комментариев

Агент оставляет комментарии в формате:

```markdown
🤖 **AI Code Review**

**Severity**: Medium
**Category**: Security

На строке 42 обнаружено использование параметров SQL запроса без экранирования.
Это может привести к SQL injection уязвимости.

**Рекомендация**:
Используйте параметризованные запросы:
\```python
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
\```

**Ссылки**:
- [OWASP SQL Injection](https://owasp.org/www-community/attacks/SQL_Injection)
```

## Резюме MR

После анализа агент формирует резюме:

```markdown
## 📊 AI Code Review Summary

**Overall Recommendation**: ⚠️ Needs Fixes

**Statistics**:
- Files changed: 12
- Lines added: 245
- Lines removed: 89
- Comments posted: 8

**Issues Found**:
- 🔴 Critical: 1 (Security)
- 🟡 Medium: 4 (Performance, Code Quality)
- 🟢 Low: 3 (Style)

**Key Concerns**:
1. SQL injection vulnerability in `user_service.py`
2. Missing error handling in API endpoints
3. Performance concern: N+1 queries in `get_orders()`

**Positive Points**:
✅ Good test coverage (85%)
✅ Clear commit messages
✅ Proper documentation

**Action Required**:
Please address critical and medium severity issues before merging.
```

## Метки и статусы

Агент автоматически управляет метками:

- `ai-review:approved` - Одобрено AI
- `ai-review:needs-fixes` - Требуются исправления
- `ai-review:rejected` - Отклонено
- `ai-review:in-progress` - Анализ выполняется
- `ai-review:security-risk` - Обнаружены проблемы безопасности
- `ai-review:performance-issues` - Проблемы производительности

## Мониторинг

Prometheus metrics доступны на `/metrics`:
  sql_injection_detection: true
  xss_detection: true

performance:
  detect_n_plus_one: true
  check_algorithm_complexity: true
  memory_leak_detection: true

review_rules:
  min_test_coverage: 80
  require_documentation: true
  max_files_per_mr: 30
  max_lines_per_mr: 1000
```

## Разработка

### Установка для разработки

```bash
pip install -e ".[dev]"
pre-commit install
```

### Запуск тестов

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=src/ai_code_review --cov-report=html

# Конкретный тест
pytest tests/test_review_engine.py -v

# Интеграционные тесты
pytest tests/integration/ -v
```

### Линтинг и форматирование

```bash
# Форматирование
black src/ tests/
isort src/ tests/

# Линтинг
flake8 src/ tests/
pylint src/
mypy src/
```

## Мониторинг и метрики

Агент собирает следующие метрики:

- Время анализа MR
- Количество комментариев
- Распределение по severity
- Процент принятых рекомендаций
- Количество обработанных MR

Метрики доступны через:
- Prometheus endpoint: `/metrics`
- Dashboard: Grafana
- Логи: structured JSON logs

## Troubleshooting

### Проблема: Агент не получает вебхуки

**Решение**:
1. Проверьте URL вебхука в настройках GitLab
2. Убедитесь, что порт доступен извне
3. Проверьте Secret Token
4. Посмотрите логи вебхуков в GitLab (Settings → Webhooks → Recent Events)

### Проблема: Слишком медленный анализ

**Решение**:
1. Увеличьте `MAX_DIFF_SIZE` в `.env`
2. Используйте более быстрый LLM provider
3. Настройте `MAX_CONCURRENT_REVIEWS` для параллелизма
4. Оптимизируйте промпты в `src/ai_code_review/ai/prompts.py`

### Проблема: Много false positives

**Решение**:
1. Настройте параметры AI модели в `.env` (temperature, max_tokens)
2. Обновите промпты в `src/ai_code_review/ai/prompts.py`
3. Используйте более точную модель (например, Claude 3.5 Sonnet)
4. Добавьте игнорирование для специфичных файлов

## Roadmap

- [x] v1.0: Базовый функционал ревью
- [x] v1.1: Async архитектура с httpx
- [x] v1.2: Prometheus metrics для мониторинга
- [ ] v1.3: Обучение на feedback от разработчиков
- [ ] v2.0: Поддержка GitHub и Bitbucket
- [ ] v2.1: Автоматическое исправление простых ошибок
- [ ] v2.2: Интеграция с CI/CD pipeline

## Контакты

Для вопросов и предложений:
- Email: dev-team@company.com
- Slack: #ai-code-review
- Issue Tracker: GitLab Issues

## Благодарности

Проект разработан для автоматизации code review процессов и повышения качества кода в организации.
