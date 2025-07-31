# Coolify Deployment Guide - Kompletna Instrukcja

## 🚀 Przegląd Wdrożenia

Ta aplikacja obsługuje **trzy różne sposoby wdrożenia** na Coolify. Wybierz wariant najlepszy dla Twoich potrzeb:

### 1. **All-in-One (Zalecane)** - `docker-compose.coolify-aio.yml`
- ✅ Najprostsze wdrożenie - jeden kontener
- ✅ Supervisor zarządza wszystkimi procesami
- ✅ Idealny dla małych/średnich aplikacji
- ⚡ Szybszy start

### 2. **Multi-Service** - `docker-compose.coolify.yml`
- ✅ Skalowalna architektura mikroserwisów
- ✅ Każdy komponent w osobnym kontenerze
- ✅ Lepsze dla dużych aplikacji
- ⚠️ Wymaga więcej zasobów

### 3. **Simplified** - `docker-compose.coolify-simple.yml`
- ✅ Bardzo uproszczona wersja
- ✅ Minimalny footprint
- ⚠️ Ograniczona funkcjonalność

---

## 📋 Krok-po-Kroku: Wdrożenie All-in-One (Zalecane)

### 1. **Utwórz Aplikację w Coolify**
1. **Projects** → wybierz projekt → **+ New** → **Resource**
2. Wybierz **Docker Compose**
3. **Repository**: URL Twojego repo
4. **Branch**: `main` (lub aktualny branch)
5. **Docker Compose Location**: `dify-plugin-repackaging-web/docker-compose.coolify-aio.yml`

### 2. **Konfiguracja Domeny**
```
⚠️ WAŻNE: Ustaw domenę TYLKO dla głównej aplikacji!

✅ Domains for Main App: https://dify-plugin.twoja-domena.pl
❌ Domains for Backend: ZOSTAW PUSTE
❌ Domains for Worker: ZOSTAW PUSTE  
❌ Domains for Celery Beat: ZOSTAW PUSTE
❌ Domains for Frontend: ZOSTAW PUSTE
❌ Domains for Nginx: ZOSTAW PUSTE
```

### 3. **Zmienne Środowiskowe**

#### Wymagane:
```bash
# CORS - KRYTYCZNE! Ustaw swoją domenę
BACKEND_CORS_ORIGINS=https://dify-plugin.twoja-domena.pl
```

#### Opcjonalne:
```bash
# Limity i optymalizacje
RATE_LIMIT_PER_MINUTE=10
FILE_RETENTION_HOURS=24
MAX_FILE_SIZE=524288000

# Tylko dla wersji multi-service
COMPOSE_PROJECT_NAME=dify-plugin-repackaging
```

### 4. **Ustawienia Sieci**
- **Port**: 80 (automatycznie wystawiony)
- **SSL**: Włącz **Force HTTPS** + **Let's Encrypt**
- **Health Check Path**: `/health`

### 5. **Deploy i Weryfikacja**
1. Kliknij **Deploy**
2. Obserwuj logi w zakładce **Logs**
3. Po zakończeniu sprawdź: `https://twoja-domena.pl/health`

---

## 🔧 Konfiguracja Multi-Service (Zaawansowane)

### Plik: `docker-compose.coolify.yml`

#### Zmienne Środowiskowe:
```bash
# Wymagane
BACKEND_CORS_ORIGINS=https://twoja-domena.pl
COMPOSE_PROJECT_NAME=dify-plugin-repackaging

# Opcjonalne
RATE_LIMIT_PER_MINUTE=10
FILE_RETENTION_HOURS=24
```

#### Architektura Serwisów:
```
┌─────────────┐  Port 80   ┌─────────────┐
│    nginx    │◄──────────►│   Coolify   │
│ (public)    │            │   Traefik   │
└─────────────┘            └─────────────┘
       │
       ▼ (internal network)
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   backend   │    │   worker    │    │ celery-beat │
│  (port 8000)│    │ (no ports)  │    │ (no ports)  │  
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           ▼
                   ┌─────────────┐
                   │    redis    │
                   │ (port 6379) │
                   └─────────────┘
```

---

## 🚨 Troubleshooting - Najczęstsze Problemy

### Problem: Błąd CORS
```
Access to XMLHttpRequest blocked by CORS policy
```
**Rozwiązanie:**
```bash
# ✅ Poprawny format
BACKEND_CORS_ORIGINS=https://twoja-domena.pl

# ❌ Błędny format - unikaj
BACKEND_CORS_ORIGINS=[""]  # pusty JSON
BACKEND_CORS_ORIGINS=http://twoja-domena.pl  # brak HTTPS
```

### Problem: 502 Bad Gateway
**Przyczyny i rozwiązania:**
1. **Backend nie startuje** - sprawdź logi aplikacji
2. **Redis nie działa** - sprawdź connection string
3. **Network issues** - sprawdź czy wszystkie serwisy są w tej samej sieci
4. **Czas startu** - poczekaj 1-2 minuty na pełny start

### Problem: Nginx Config Mount Error
```
error mounting nginx.conf to rootfs
```
**Rozwiązanie:** Upewnij się, że używasz:
- `docker-compose.coolify-aio.yml` (wszystko w jednym kontenerze)
- LUB `docker-compose.coolify.yml` (nginx build z Dockerfile)

### Problem: WebSocket nie działa
**Rozwiązanie:**
1. Sprawdź czy używasz HTTPS (nie HTTP)
2. Coolify automatycznie obsługuje WebSocket headers
3. Upewnij się, że nginx ma prawidłową konfigurację proxy

### Problem: Zadania Celery nie wykonują się
**Rozwiązanie:**
1. Sprawdź logi worker: `docker-compose logs worker`
2. Sprawdź połączenie z Redis: `redis-cli ping`
3. Upewnij się, że CELERY_BROKER_URL jest prawidłowy

---

## 📊 Monitorowanie i Logi

### Kluczowe endpointy do monitorowania:
```bash
# Health check
curl https://twoja-domena.pl/health

# API status
curl https://twoja-domena.pl/api/v1/docs

# WebSocket test (w browser developer tools)
new WebSocket('wss://twoja-domena.pl/ws/test-connection')
```

### Logi do sprawdzenia w Coolify:
- **Application logs** - główne logi aplikacji
- **Build logs** - błędy podczas budowy
- **Container logs** - logi poszczególnych kontenerów

## Common Issues

### Nginx Configuration Mount Error

If you see this error:
```
error mounting "/data/coolify/applications/.../nginx.conf" to rootfs at "/etc/nginx/nginx.conf"
```

**Solution**: The nginx service now builds from a Dockerfile instead of mounting the config file. Make sure:
- The `nginx/` directory exists with `Dockerfile` and `nginx.conf`
- Docker Compose uses `build: ./nginx` instead of mounting volumes

### BACKEND_CORS_ORIGINS Error

If you see this error:
```
pydantic_settings.sources.SettingsError: error parsing value for field "BACKEND_CORS_ORIGINS" from source "EnvSettingsSource"
```

**Solution**: Use the simple comma-separated format instead of JSON:
- ❌ Wrong: `BACKEND_CORS_ORIGINS=[""]` (empty JSON array)
- ✅ Correct: `BACKEND_CORS_ORIGINS=https://your-domain.com`
- ✅ Correct: `BACKEND_CORS_ORIGINS=https://domain1.com,https://domain2.com`

### Services Not Connecting

If backend shows "Host is unreachable" or returns 502/500 errors:
1. Ensure all services are in the same Docker network
2. Check that service names match in docker-compose
3. Verify Redis is running and accessible
4. Wait 30-60 seconds after deployment for all services to fully start
5. Check health endpoint: `https://your-domain.com/health`

### API Returns 500 Error

If the API returns error 500:
1. Check backend logs in Coolify for detailed error messages
2. Verify environment variables are set correctly
3. Ensure Redis connection is working
4. Check that all required Python packages are installed

## Docker Compose Configuration

The application uses the following services:
- `backend` - FastAPI application (port 8000)
- `worker` - Celery worker for async tasks
- `celery-beat` - Scheduled task runner
- `frontend` - React application
- `redis` - Message broker and cache
- `nginx` - Reverse proxy (port 80)

All services should be on the same network for inter-service communication.