# Production Deployment Guide

Руководство по развертыванию AI Code Review Assistant в production окружении.

## Содержание

- [Требования](#требования)
- [Способ 1: Docker Compose (рекомендуется)](#способ-1-docker-compose-рекомендуется)
- [Способ 2: Systemd Service](#способ-2-systemd-service)
- [Способ 3: Cloud Platforms](#способ-3-cloud-platforms)
- [Настройка безопасности](#настройка-безопасности)
- [Мониторинг](#мониторинг)

---

## Требования

### Минимальные требования к серверу

- **CPU**: 2 cores
- **RAM**: 4 GB
- **Disk**: 20 GB SSD
- **OS**: Ubuntu 20.04+ / Debian 11+
- **Python**: 3.10+
- **Network**: Статический IP или domain name

---

## Способ 1: Docker Compose (рекомендуется)

### 1.1. Установка Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 1.2. Подготовка проекта

```bash
# Клонируйте репозиторий
cd /opt
sudo git clone https://gitlab.com/your-org/ai-code-review-assistant.git
cd ai-code-review-assistant

# Настройте .env файл
sudo cp .env.example .env
sudo nano .env
```

**Production переменные:**

```env
# GitLab
GITLAB_URL=https://gitlab.company.com
GITLAB_TOKEN=glpat-xxx
GITLAB_WEBHOOK_SECRET=your-strong-secret

# AI Provider
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxx
AI_MODEL=claude-3-haiku-20240307

# Application
APP_ENV=production
LOG_LEVEL=INFO
PORT=8000
```

### 1.3. Docker Compose для Production

`docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  ai-code-review:
    build: .
    container_name: ai-code-review
    restart: always
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config:ro
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G

  nginx:
    image: nginx:alpine
    container_name: nginx-proxy
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
    depends_on:
      - ai-code-review
```

### 1.4. Nginx конфигурация

`nginx/nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream ai_code_review {
        server ai-code-review:8000;
    }

    server {
        listen 80;
        server_name code-review.company.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name code-review.company.com;

        ssl_certificate /etc/letsencrypt/live/code-review.company.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/code-review.company.com/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;

        location /webhook {
            proxy_pass http://ai_code_review;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_read_timeout 300s;
        }

        location /health {
            proxy_pass http://ai_code_review;
        }
    }
}
```

### 1.5. SSL сертификат

```bash
# Let's Encrypt
sudo certbot certonly --standalone -d code-review.company.com
```

### 1.6. Запуск

```bash
sudo docker-compose -f docker-compose.prod.yml up -d

# Проверка логов
sudo docker-compose logs -f

# Проверка статуса
sudo docker-compose ps
```

---

## Способ 2: Systemd Service

Для тех, кто не использует Docker.

### 2.1. Установка

```bash
# Создайте пользователя
sudo useradd -r -s /bin/false ai-reviewer

# Создайте директорию
sudo mkdir -p /opt/ai-code-review-assistant
cd /opt/ai-code-review-assistant
sudo git clone https://gitlab.com/your-org/ai-code-review-assistant.git .

# Установите зависимости
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

### 2.2. Systemd unit

`/etc/systemd/system/ai-code-review.service`:

```ini
[Unit]
Description=AI Code Review Assistant
After=network.target

[Service]
Type=simple
User=ai-reviewer
WorkingDirectory=/opt/ai-code-review-assistant
EnvironmentFile=/opt/ai-code-review-assistant/.env

ExecStart=/opt/ai-code-review-assistant/venv/bin/python -m uvicorn \
    src.ai_code_review.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 2.3. Запуск

```bash
sudo systemctl daemon-reload
sudo systemctl start ai-code-review
sudo systemctl enable ai-code-review
sudo systemctl status ai-code-review
```

---

## Способ 3: Cloud Platforms

### Railway

```bash
npm install -g @railway/cli
railway login
railway up
railway domain
```

### Heroku

```bash
heroku create ai-code-review
heroku config:set GITLAB_TOKEN=xxx
heroku config:set ANTHROPIC_API_KEY=xxx
git push heroku main
```

### DigitalOcean App Platform

1. Connect GitLab repo
2. Add environment variables
3. Deploy (auto-detects Dockerfile)

---

## Настройка безопасности

### Firewall

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Secrets Management

**Не храните secrets в git!**

```bash
# Генерация сильного webhook secret
openssl rand -hex 32
```

### GitLab Webhook Setup

1. Settings → Webhooks
2. URL: `https://code-review.company.com/webhook`
3. Secret Token: из `.env`
4. Events: ✅ Merge request events
5. Test → Merge request events

---

## Мониторинг

### Health Check

```bash
curl https://code-review.company.com/health
```

### Logs

```bash
# Docker
docker-compose logs -f

# Systemd
sudo journalctl -u ai-code-review -f
```

### Prometheus Metrics

Доступны на `/metrics`:

```bash
curl http://localhost:8000/metrics
```

---

## Troubleshooting

### Webhook не работает

1. Проверьте URL доступен извне
2. Проверьте secret token совпадает
3. Проверьте логи: Settings → Webhooks → Recent Deliveries

### AI не находит проблемы

1. Проверьте API key валиден
2. Проверьте модель: `claude-3-haiku-20240307`
3. Проверьте логи сервера

### Комментарии не публикуются

1. Проверьте GitLab token имеет `api` scope
2. Проверьте права на запись в проект
3. Проверьте логи на ошибки

---

## Production Checklist

- [ ] SSL сертификаты настроены
- [ ] Secrets не в git
- [ ] Firewall настроен
- [ ] Логирование работает
- [ ] Health check работает
- [ ] GitLab webhook настроен
- [ ] Автозапуск при перезагрузке

---

## Стоимость

**Claude 3 Haiku**:
- ~$0.25 за MR (обычный)
- ~$0.50 за большой MR (500+ строк)

**Для больших команд**:
- Claude 3.5 Sonnet: точнее, ~$1-2 за MR

---

## Поддержка

- **README.md** - основная документация
- **config/standards.yaml** - профили проверок
- GitLab Issues - баги и предложения
