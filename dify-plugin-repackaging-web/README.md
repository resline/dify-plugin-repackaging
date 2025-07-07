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

## Deployment on Coolify - Szczegółowa instrukcja

### Wymagania wstępne
- Działająca instancja Coolify (v4)
- Repozytorium Git z kodem aplikacji (GitHub, GitLab, Gitea, etc.)
- Domena skierowana na serwer z Coolify

### Krok po kroku

#### 1. Przygotowanie repozytorium
Upewnij się, że w repozytorium znajdują się wszystkie pliki, w tym:
- `docker-compose.prod.yml` (używany przez Coolify)
- Wszystkie foldery źródłowe (`backend/`, `frontend/`)
- Plik `.env.example` jako wzór konfiguracji

#### 2. Utworzenie nowej aplikacji w Coolify

1. Zaloguj się do panelu Coolify
2. Przejdź do **Projects** → wybierz swój projekt
3. Kliknij **+ New** → **Resource**
4. Wybierz **Docker Compose** jako typ aplikacji
5. Wybierz **Public Repository** lub **Private Repository** (w zależności od typu repo)

#### 3. Konfiguracja źródła (Source)

1. **Repository URL**: Podaj URL swojego repozytorium
   ```
   https://github.com/yourusername/dify-plugin-repackaging-web.git
   ```

2. **Branch**: Wybierz branch (np. `main`)

3. **Build Pack**: Upewnij się, że wybrane jest **Docker Compose**

4. **Docker Compose Location**: Wpisz:
   ```
   docker-compose.prod.yml
   ```

#### 4. Konfiguracja zmiennych środowiskowych

W sekcji **Environment Variables** dodaj następujące zmienne:

```env
# Port - jeśli chcesz użyć innego niż 80
PORT=80

# CORS - Ważne! Ustaw swoją domenę
BACKEND_CORS_ORIGINS=["https://twoja-domena.pl","https://www.twoja-domena.pl"]

# Opcjonalne - limity i retencja
RATE_LIMIT_PER_MINUTE=10
FILE_RETENTION_HOURS=24
MAX_FILE_SIZE=524288000

# Jeśli używasz zewnętrznego Redis (opcjonalne)
# REDIS_URL=redis://your-redis-host:6379/0
```

**Uwaga**: `BACKEND_CORS_ORIGINS` musi być poprawnym JSON array!

#### 5. Konfiguracja sieci i portów

1. W sekcji **Network**:
   - **Port Exposes**: Dodaj `80:80` (lub inny port jeśli zmieniłeś w ENV)
   - **Domains**: Dodaj swoją domenę, np. `dify-repack.twoja-domena.pl`

2. Włącz **HTTPS**:
   - Zaznacz **Force HTTPS**
   - Zaznacz **Auto Generate SSL** (Let's Encrypt)

#### 6. Konfiguracja zasobów (opcjonalnie)

W sekcji **Resources** możesz ustawić limity:
- **CPU**: np. 2 CPU
- **Memory**: np. 2048 MB
- **Storage**: np. 10 GB

#### 7. Ustawienia zaawansowane

1. **Health Check**:
   - Path: `/health`
   - Interval: `30`
   - Timeout: `10`
   - Retries: `3`

2. **Build Configuration**:
   - Jeśli masz wolny serwer, możesz zwiększyć **Build Timeout** do `30` minut

#### 8. Deploy aplikacji

1. Kliknij **Save** aby zapisać konfigurację
2. Kliknij **Deploy** aby rozpocząć wdrożenie
3. Obserwuj logi w zakładce **Logs** aby śledzić postęp

#### 9. Weryfikacja wdrożenia

Po zakończeniu deploymentu:

1. Sprawdź status kontenerów w zakładce **Containers**
2. Wszystkie 6 kontenerów powinno mieć status **Running**:
   - backend
   - worker
   - celery-beat
   - frontend
   - redis
   - nginx

3. Otwórz aplikację pod adresem: `https://dify-repack.twoja-domena.pl`

### Przykładowa konfiguracja w Coolify UI

```yaml
# Environment Variables (w formacie Coolify)
PORT=80
BACKEND_CORS_ORIGINS=["https://dify-repack.example.com"]
RATE_LIMIT_PER_MINUTE=20
FILE_RETENTION_HOURS=48
```

### Troubleshooting w Coolify

#### Problem: Aplikacja nie startuje
1. Sprawdź logi w zakładce **Logs**
2. Upewnij się, że `docker-compose.prod.yml` jest w głównym katalogu repo
3. Sprawdź czy wszystkie zmienne środowiskowe są poprawnie ustawione

#### Problem: Błąd CORS
1. Upewnij się, że `BACKEND_CORS_ORIGINS` zawiera dokładną domenę z https://
2. Format musi być JSON array: `["https://example.com"]`

#### Problem: Brak dostępu do plików
1. Sprawdź uprawnienia volumenów w logach
2. Coolify automatycznie zarządza volumenami, ale możesz je sprawdzić w zakładce **Storages**

#### Problem: WebSocket nie działa
1. Upewnij się, że Coolify Proxy prawidłowo przekazuje nagłówki WebSocket
2. W razie problemów, możesz dodać dodatkowe labels do nginx w docker-compose.prod.yml:
   ```yaml
   nginx:
     labels:
       - "coolify.websocket=true"
   ```

### Aktualizacja aplikacji

1. Po wprowadzeniu zmian w kodzie i push do repozytorium
2. W Coolify przejdź do aplikacji
3. Kliknij **Redeploy** lub włącz **Auto Deploy** dla automatycznych wdrożeń

### Backup i przywracanie

1. **Volumes**: Coolify automatycznie tworzy volumes dla Redis i temp
2. Możesz je znaleźć w zakładce **Storages**
3. Dla backupu bazy Redis, użyj Coolify backup features lub własne skrypty

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Port to expose the application | 80 |
| `BACKEND_CORS_ORIGINS` | Allowed CORS origins (JSON array) | ["http://localhost"] |
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