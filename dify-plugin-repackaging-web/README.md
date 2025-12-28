# Dify Plugin Repackaging Web Service

A web application that allows users to repackage Dify plugins with offline dependencies. Users can provide a URL to a `.difypkg` file and receive a repackaged version with all Python dependencies included.

## Features

- 🌐 Web interface for easy plugin repackaging
- 📦 Downloads plugins from Dify Marketplace or GitHub
- 🔄 Real-time progress updates via WebSocket
- 🎯 Platform-specific repackaging support
- 🔒 Security features (rate limiting, domain whitelist)
- 🐳 Docker-based deployment
- ☁️ Ready for Coolify deployment

## Technology Stack

- **Backend**: FastAPI (Python 3.12)
- **Frontend**: React with Tailwind CSS
- **Task Queue**: Celery with Redis
- **Web Server**: Nginx
- **Containerization**: Docker & Docker Compose

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Git

### Local Development

1. Clone the repository:
```bash
git clone <repository-url>
cd dify-plugin-repackaging-web
```

2. Copy environment variables:
```bash
cp .env.example .env
```

3. Start the services:
```bash
docker-compose up --build
```

4. Access the application at http://localhost

### Production Deployment

For production deployment, use the production Docker Compose file:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## 🚀 Deployment on Coolify

### 📋 Opcje Wdrożenia

Aplikacja obsługuje **3 sposoby wdrożenia** na Coolify:

1. **All-in-One (Zalecane)** - `docker-compose.coolify-aio.yml`
2. **Multi-Service** - `docker-compose.coolify.yml` 
3. **Simplified** - `docker-compose.coolify-simple.yml`

### ⚡ Szybki Start (All-in-One)

#### 1. Utwórz aplikację w Coolify
- **Type**: Docker Compose
- **Repository**: URL Twojego repo
- **Docker Compose Location**: `dify-plugin-repackaging-web/docker-compose.coolify-aio.yml`

#### 2. Konfiguracja domeny
```bash
⚠️ WAŻNE: Ustaw domenę TYLKO dla głównej aplikacji!

✅ Główna aplikacja: https://dify-plugin.twoja-domena.pl
❌ Backend/Worker/inne: ZOSTAW PUSTE
```

#### 3. Zmienne środowiskowe
```bash
# WYMAGANE
BACKEND_CORS_ORIGINS=https://dify-plugin.twoja-domena.pl

# OPCJONALNE
RATE_LIMIT_PER_MINUTE=10
FILE_RETENTION_HOURS=24
MAX_FILE_SIZE=524288000
```

#### 4. Deploy
- Kliknij **Deploy**
- Sprawdź endpoint: `https://twoja-domena.pl/health`

### 📚 Szczegółowa Dokumentacja

**Kompletna instrukcja wdrożenia z troubleshooting:**
👉 [COOLIFY_DEPLOYMENT.md](../COOLIFY_DEPLOYMENT.md)

Zawiera:
- Szczegółowe instrukcje dla wszystkich 3 wariantów
- Konfigurację sieci i zmiennych środowiskowych  
- Troubleshooting najczęstszych problemów
- Monitorowanie i logi
- Diagramy architektury

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Port to expose the application | 80 |
| `BACKEND_CORS_ORIGINS` | Allowed CORS origins (JSON array) | ["http://localhost"] |
| `AUTH_PASSWORD` | Authentication password (empty = disabled) | None |
| `RATE_LIMIT_PER_MINUTE` | API rate limit per IP | 10 |
| `FILE_RETENTION_HOURS` | Hours to keep processed files | 24 |
| `MAX_FILE_SIZE` | Maximum file size in bytes | 524288000 (500MB) |

### Supported Platforms

The service supports repackaging for the following platforms:
- `manylinux2014_x86_64` - Linux x86_64 (manylinux2014)
- `manylinux2014_aarch64` - Linux ARM64 (manylinux2014)
- `manylinux_2_17_x86_64` - Linux x86_64 (manylinux 2.17)
- `manylinux_2_17_aarch64` - Linux ARM64 (manylinux 2.17)
- `macosx_10_9_x86_64` - macOS x86_64
- `macosx_11_0_arm64` - macOS ARM64

## API Documentation

Once running, access the API documentation at:
- Swagger UI: http://localhost/api/v1/docs
- ReDoc: http://localhost/api/v1/redoc

### Main Endpoints

- `POST /api/v1/tasks` - Create a new repackaging task
- `GET /api/v1/tasks/{task_id}` - Get task status
- `GET /api/v1/tasks/{task_id}/download` - Download repackaged file
- `WS /ws/tasks/{task_id}` - WebSocket for real-time updates

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│    Nginx    │────▶│   Backend   │
│   (React)   │     │             │     │  (FastAPI)  │
└─────────────┘     └─────────────┘     └─────────────┘
                                                │
                                                ▼
                    ┌─────────────┐     ┌─────────────┐
                    │    Redis    │◀────│   Celery    │
                    │             │     │   Worker    │
                    └─────────────┘     └─────────────┘
```

## Security

- Rate limiting to prevent abuse
- Domain whitelist for plugin downloads
- Automatic cleanup of old files
- Input validation and sanitization
- CORS configuration

## Maintenance

### Logs

View logs for any service:
```bash
docker-compose logs -f [service-name]
```

### Cleanup

Old files are automatically cleaned up every hour. To manually trigger cleanup:
```bash
docker-compose exec worker celery -A app.workers.celery_app call app.workers.celery_app.cleanup_old_files
```

## Troubleshooting

### Common Issues

1. **Port already in use**:
   - Change the `PORT` environment variable
   - Or stop the conflicting service

2. **Permission denied errors**:
   - Ensure the temp directory has proper permissions
   - Check Docker volume permissions

3. **WebSocket connection issues**:
   - Verify Nginx configuration
   - Check CORS settings

## License

[Your License Here]

## Contributing

[Contributing guidelines]