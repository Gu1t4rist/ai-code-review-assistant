# Архитектура AI Code Review Assistant

## Обзор системы

AI Code Review Assistant - это микросервис, предназначенный для автоматизации процесса code review в GitLab с использованием больших языковых моделей (LLM).

## Компоненты системы

### 1. GitLab Integration Layer (`gitlab/`)

**Назначение**: Взаимодействие с GitLab API

**Компоненты**:
- `client.py` - GitLab API клиент
  - Получение информации о MR
  - Парсинг diff'ов
  - Публикация комментариев
  - Управление метками
  
- `models.py` - Модели данных
  - `MergeRequestInfo` - информация о MR
  - `DiffChange` - изменения в файлах
  - `ReviewIssue` - найденные проблемы
  - `ReviewSummary` - итоговое резюме
  
- `webhooks.py` - Обработка вебхуков
  - Валидация подписей
  - Обработка событий MR
  - Асинхронная обработка ревью

**Ключевые операции**:
```python
# Получить MR с изменениями
mr_info = gitlab_client.get_merge_request_info(project_id, mr_iid)

# Опубликовать комментарий
gitlab_client.post_comment(project_id, mr_iid, comment, file_path, line_number)

# Обновить метки
gitlab_client.update_labels_for_review(project_id, mr_iid, summary)
```

### 2. AI Analysis Layer (`ai/`)

**Назначение**: AI-анализ кода с использованием LLM

**Компоненты**:
- `llm_client.py` - Клиенты для LLM провайдеров
  - OpenAI (GPT-4, GPT-3.5)
  - Anthropic (Claude)
  - Azure OpenAI
  
- `prompts.py` - Промпты для анализа
  - Системные промпты
  - Шаблоны для разных типов анализа
  - Форматирование запросов
  
- `review_engine.py` - Движок для ревью кода
  - Анализ файлов
  - Проверка безопасности
  - Оценка производительности
  - Генерация резюме

**Процесс анализа**:
```
1. Фильтрация изменений (размер, тип файла)
2. Параллельный анализ файлов (с ограничением)
3. Специализированные проверки:
   - Безопасность (SQL injection, XSS, secrets)
   - Производительность (N+1, алгоритмы)
   - Покрытие тестами
4. Генерация общего резюме
5. Формирование рекомендации (approve/needs_fixes/reject)
```

### 3. Configuration Layer (`config.py`)

**Назначение**: Управление конфигурацией

**Функции**:
- Загрузка из переменных окружения
- Валидация настроек
- Настройки по умолчанию
- Feature flags

**Основные настройки**:
```python
settings = get_settings()
settings.gitlab_url          # GitLab URL
settings.gitlab_token        # API токен
settings.ai_provider         # openai/anthropic
settings.max_diff_size       # Макс размер diff
settings.enable_security_scan # Включить проверку безопасности
```

### 4. Web Application Layer (`main.py`)

**Назначение**: HTTP API и вебхуки

**Endpoints**:
- `GET /` - Информация о сервисе
- `GET /health` - Health check
- `POST /webhook` - GitLab webhook endpoint
- `POST /api/v1/review` - Ручной запуск ревью
- `GET /api/v1/metrics` - Метрики

**Режимы работы**:
1. **Webhook mode**: Автоматическая обработка событий MR
2. **Manual mode**: Разовый анализ конкретного MR

### 5. Utilities (`utils/`)

**Компоненты**:
- `logger.py` - Структурированное логирование
- `metrics.py` - Сбор метрик (опционально)

## Поток данных

```
┌─────────────┐
│   GitLab    │
│   Webhook   │
└──────┬──────┘
       │ MR Event
       ↓
┌─────────────────┐
│  FastAPI Server │
│   (main.py)     │
└──────┬──────────┘
       │
       ↓
┌─────────────────┐
│ WebhookHandler  │
│  (webhooks.py)  │
└──────┬──────────┘
       │
       ↓
┌─────────────────┐     ┌──────────────┐
│  GitLabClient   │────→│  GitLab API  │
│   (client.py)   │←────│              │
└──────┬──────────┘     └──────────────┘
       │ MR Info + Diffs
       ↓
┌─────────────────┐
│ ReviewEngine    │
│(review_engine.py│
└──────┬──────────┘
       │
       ↓
┌─────────────────┐     ┌──────────────┐
│   LLM Client    │────→│  OpenAI/     │
│ (llm_client.py) │←────│  Anthropic   │
└──────┬──────────┘     └──────────────┘
       │ Analysis Results
       ↓
┌─────────────────┐
│ ReviewSummary   │
│   + Issues      │
└──────┬──────────┘
       │
       ↓
┌─────────────────┐     ┌──────────────┐
│  GitLabClient   │────→│  GitLab API  │
│  Post Results   │     │  (Comments)  │
└─────────────────┘     └──────────────┘
```

## Алгоритм анализа

### 1. Получение данных

```python
# Webhook получает событие
event = WebhookEvent(**request_body)

# Извлечение информации о MR
mr_info = gitlab_client.get_merge_request_info(project_id, mr_iid)

# mr_info содержит:
# - Метаданные MR (title, description, author)
# - Список изменений (DiffChange)
# - Diff для каждого файла
```

### 2. Фильтрация изменений

```python
def _filter_changes(changes: list[DiffChange]):
    filtered = []
    for change in changes:
        # Пропустить удаленные файлы
        if change.deleted_file:
            continue
            
        # Пропустить слишком большие файлы
        if change.additions + change.deletions > max_diff_size:
            continue
            
        # Пропустить бинарные/сгенерированные файлы
        if is_ignored_file(change.file_path):
            continue
            
        filtered.append(change)
    return filtered
```

### 3. Параллельный анализ файлов

```python
# Ограничение параллелизма (3 файла одновременно)
semaphore = asyncio.Semaphore(3)

async def review_with_semaphore(change: DiffChange):
    async with semaphore:
        return await review_file_change(change, mr_info)

# Запуск параллельных задач
tasks = [review_with_semaphore(change) for change in changes]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

### 4. Анализ отдельного файла

```python
async def _review_file_change(change: DiffChange, mr_info: MergeRequestInfo):
    # Формирование промпта
    prompt = get_file_analysis_prompt(
        file_path=change.file_path,
        change_type="new file" if change.new_file else "modified",
        diff=change.diff,
        mr_description=mr_info.description
    )
    
    # Запрос к LLM
    result = await llm_client.generate_structured_output(
        prompt, 
        CODE_REVIEW_SYSTEM_PROMPT
    )
    
    # Парсинг результатов
    issues = [ReviewIssue(**issue_data) for issue_data in result["issues"]]
    
    return {
        "file_path": change.file_path,
        "issues": issues,
        "positive_points": result["positive_points"],
        "assessment": result["assessment"]
    }
```

### 5. Специализированные проверки

```python
# Проверка безопасности
if settings.enable_security_scan:
    security_issues = await perform_security_scan(changes)
    all_issues.extend(security_issues)

# Проверка производительности
if settings.enable_performance_check:
    performance_issues = await perform_performance_check(changes)
    all_issues.extend(performance_issues)

# Анализ покрытия тестами
test_coverage = await analyze_test_coverage(mr_info)
```

### 6. Генерация итогового резюме

```python
async def _generate_summary(mr_info, file_reviews, all_issues, test_coverage):
    # Формирование промпта с результатами
    prompt = get_mr_summary_prompt(
        mr_title=mr_info.title,
        mr_description=mr_info.description,
        files_changed=len(mr_info.changes),
        total_additions=sum(c.additions for c in mr_info.changes),
        total_deletions=sum(c.deletions for c in mr_info.changes),
        file_reviews=formatted_reviews
    )
    
    # Запрос финального резюме
    result = await llm_client.generate_structured_output(prompt, system_prompt)
    
    # Fallback на rule-based рекомендацию
    if critical_issues > 0:
        recommendation = "reject"
    elif high_issues > 3:
        recommendation = "needs_fixes"
    else:
        recommendation = result["recommendation"]
    
    return ReviewSummary(
        recommendation=recommendation,
        issues=all_issues,
        positive_points=result["positive_points"],
        key_concerns=result["key_concerns"],
        test_coverage=test_coverage,
        overall_comment=result["overall_comment"]
    )
```

### 7. Публикация результатов

```python
# Публикация критических и важных проблем как inline-комментарии
for issue in summary.issues:
    if issue.severity in ["critical", "high"]:
        gitlab_client.post_issue_comment(project_id, mr_iid, issue)

# Публикация общего резюме
gitlab_client.post_review_summary(project_id, mr_iid, summary)

# Обновление меток MR
gitlab_client.update_labels_for_review(project_id, mr_iid, summary)
```

## Типы проверок

### 1. Безопасность (Security)

**Проверяемые уязвимости**:
- SQL Injection
- XSS (Cross-Site Scripting)
- Жёстко заданные секреты (hardcoded secrets)
- Аутентификация/Авторизация
- Command Injection
- Path Traversal
- Небезопасная десериализация
- Отсутствие валидации ввода

**Severity**: Critical, High

### 2. Производительность (Performance)

**Проверяемые проблемы**:
- N+1 запросы
- Неэффективные алгоритмы (O(n²) и хуже)
- Утечки памяти
- Блокирующие операции I/O
- Отсутствие кэширования
- Отсутствие индексов БД

**Severity**: High, Medium

### 3. Качество кода (Code Quality)

**Проверяемые аспекты**:
- SOLID принципы
- Design patterns
- DRY (Don't Repeat Yourself)
- Именование переменных/функций
- Модульность
- Coupling/Cohesion

**Severity**: Medium, Low

### 4. Стиль (Style)

**Проверяемые аспекты**:
- Длина строк
- Отступы
- Форматирование
- Соглашения об именовании

**Severity**: Low

### 5. Тестирование (Testing)

**Проверяемые аспекты**:
- Покрытие тестами
- Unit tests
- Integration tests
- Edge cases
- Обработка ошибок

**Severity**: Medium

## Рекомендации

### Approve (✅)

**Критерии**:
- Нет критических проблем
- Нет важных проблем ИЛИ не более 1-2 важных проблем
- Хорошее покрытие тестами (>80%)
- Соответствие стандартам кодирования

### Needs Fixes (⚠️)

**Критерии**:
- Есть важные проблемы (3+)
- Средние проблемы требуют внимания
- Недостаточное покрытие тестами (<80%)
- Отсутствие обработки ошибок

### Reject (❌)

**Критерии**:
- Есть критические проблемы безопасности
- Серьёзные архитектурные проблемы
- Множественные важные проблемы (>5)
- Не соответствует требованиям функционала

## Масштабирование

### Горизонтальное масштабирование

```yaml
# Несколько инстансов за load balancer
services:
  ai-code-review-1:
    ...
  ai-code-review-2:
    ...
  ai-code-review-3:
    ...
  
  nginx:
    image: nginx
    depends_on:
      - ai-code-review-1
      - ai-code-review-2
      - ai-code-review-3
```

### Кэширование

```python
# Redis для кэширования результатов
cache_key = f"review:{project_id}:{mr_iid}:{last_commit_sha}"

# Проверка кэша
if cached_result := redis.get(cache_key):
    return cached_result

# Сохранение результата
redis.setex(cache_key, ttl=3600, value=result)
```

### Очередь задач

```python
# Celery для асинхронной обработки
@celery.task
def process_mr_review(project_id: int, mr_iid: int):
    # Длительная обработка
    ...
    
# В webhook handler
process_mr_review.delay(project_id, mr_iid)
```

## Мониторинг и метрики

### Ключевые метрики

1. **Performance**:
   - Время обработки MR
   - Время ответа LLM
   - Количество токенов использовано

2. **Quality**:
   - Процент релевантных комментариев
   - Количество false positives
   - Feedback от разработчиков

3. **Usage**:
   - Количество обработанных MR
   - Распределение рекомендаций (approve/needs_fixes/reject)
   - Топ категорий проблем

### Логирование

```python
logger.info(
    "mr_review_completed",
    project_id=project_id,
    mr_iid=mr_iid,
    recommendation=summary.recommendation,
    total_issues=len(summary.issues),
    critical_issues=len(summary.critical_issues),
    duration_seconds=duration
)
```

## Безопасность

### 1. Аутентификация

- GitLab webhook signature verification
- API token rotation
- Принцип наименьших привилегий

### 2. Обработка секретов

- Хранение в environment variables
- Использование secret managers (Vault, AWS Secrets Manager)
- Никогда не логировать секреты

### 3. Rate Limiting

```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@app.post("/webhook", dependencies=[Depends(RateLimiter(times=60, seconds=60))])
async def webhook(...):
    ...
```

## Производительность

### Оптимизации

1. **Параллельная обработка файлов** (asyncio.gather)
2. **Семафоры для ограничения нагрузки** (asyncio.Semaphore)
3. **Кэширование LLM ответов** (Redis)
4. **Пропуск неизменённых файлов**
5. **Батчинг запросов к LLM**

### Ограничения

```python
# Лимиты для предотвращения перегрузки
MAX_FILES_FOR_REVIEW = 50
MAX_DIFF_SIZE = 10000  # строк
REVIEW_TIMEOUT = 300   # секунд
MAX_CONCURRENT_REVIEWS = 3
```

## Тестирование

### Типы тестов

1. **Unit Tests** - тестирование отдельных компонентов
2. **Integration Tests** - тестирование взаимодействия компонентов
3. **E2E Tests** - тестирование полного потока

### Запуск тестов

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=src/ai_code_review --cov-report=html

# Только unit tests
pytest tests/ -m unit

# Только integration tests
pytest tests/ -m integration
```

## Развертывание

### Production Checklist

- [ ] Настроить переменные окружения
- [ ] Включить SSL/TLS
- [ ] Настроить rate limiting
- [ ] Включить мониторинг (Prometheus/Grafana)
- [ ] Настроить логирование (централизованное)
- [ ] Включить error tracking (Sentry)
- [ ] Настроить backup БД
- [ ] Настроить health checks
- [ ] Документировать runbook
- [ ] Настроить alerts

### CI/CD Pipeline

```yaml
# .gitlab-ci.yml
stages:
  - test
  - build
  - deploy

test:
  stage: test
  script:
    - pytest --cov

build:
  stage: build
  script:
    - docker build -t ai-code-review .
    
deploy:
  stage: deploy
  script:
    - docker-compose up -d
  only:
    - main
```

## Заключение

AI Code Review Assistant представляет собой полнофункциональное решение для автоматизации code review процесса с использованием современных LLM технологий. Система спроектирована с учётом масштабируемости, надёжности и производительности.
