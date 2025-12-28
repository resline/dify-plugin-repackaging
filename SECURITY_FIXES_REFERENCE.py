#!/usr/bin/env python3
"""
Security Fixes Reference - Ready-to-Deploy Code
Dify Plugin Repackaging Application

Usage:
    from SECURITY_FIXES_REFERENCE import safe_extract, validate_requirements_txt

    safe_extract('plugin.difypkg', '/tmp/extract')
    validate_requirements_txt('/tmp/extract/requirements.txt')
"""

import os
import re
import zipfile
import logging
from typing import Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


# =============================================================================
# 1. ZIP SLIP PROTECTION (CVSS 9.8)
# =============================================================================

def safe_extract(
    zip_path: str,
    extract_dir: str,
    max_size_mb: int = 500,
    max_files: int = 10000,
    allowed_extensions: Optional[List[str]] = None
) -> List[str]:
    """
    Bezpieczne rozpakowywanie archiwum ZIP z pełną ochroną przed:
    - ZIP Slip (Path Traversal)
    - ZIP Bomb (Decompression Bomb)
    - Symlink Attack
    - Malicious Executables
    - Hidden Files

    Args:
        zip_path: Ścieżka do pliku ZIP
        extract_dir: Katalog docelowy
        max_size_mb: Maksymalny rozmiar po rozpakowaniu (MB)
        max_files: Maksymalna liczba plików
        allowed_extensions: Lista dozwolonych rozszerzeń (None = wszystkie)

    Returns:
        Lista bezpiecznie rozpakowanych plików

    Raises:
        ValueError: Jeśli archiwum jest niebezpieczne
        zipfile.BadZipFile: Jeśli plik nie jest ZIP
    """

    # Walidacja wejścia
    if not os.path.exists(zip_path):
        raise FileNotFoundError(f"ZIP file not found: {zip_path}")

    if not zipfile.is_zipfile(zip_path):
        raise zipfile.BadZipFile(f"Not a valid ZIP file: {zip_path}")

    # Utwórz katalog docelowy
    os.makedirs(extract_dir, exist_ok=True)
    extract_dir_abs = os.path.abspath(extract_dir)

    extracted_files = []
    blocked_files = []

    with zipfile.ZipFile(zip_path, 'r') as zf:
        # Test integralności ZIP
        bad_file = zf.testzip()
        if bad_file is not None:
            raise ValueError(f"Corrupted file in archive: {bad_file}")

        # Sprawdź liczbę plików
        if len(zf.namelist()) > max_files:
            raise ValueError(
                f"Too many files in archive: {len(zf.namelist())} > {max_files}"
            )

        # Sprawdź całkowity rozmiar (ZIP Bomb protection)
        total_uncompressed = sum(info.file_size for info in zf.infolist())
        total_compressed = os.path.getsize(zip_path)

        max_bytes = max_size_mb * 1024 * 1024
        if total_uncompressed > max_bytes:
            raise ValueError(
                f"Archive too large after decompression: "
                f"{total_uncompressed / (1024*1024):.1f}MB > {max_size_mb}MB"
            )

        # Sprawdź współczynnik kompresji (nested ZIP bomb)
        compression_ratio = total_uncompressed / total_compressed if total_compressed > 0 else 0
        if compression_ratio > 100:  # 100:1 jest podejrzane
            logger.warning(
                f"High compression ratio detected: {compression_ratio:.1f}:1"
            )

        # Przetwórz każdy plik
        for info in zf.infolist():
            filename = info.filename

            # 1. BLOKADA DIRECTORY ENTRIES
            if filename.endswith('/'):
                continue

            # 2. BLOKADA UKRYTYCH PLIKÓW
            basename = os.path.basename(filename)
            if basename.startswith('.'):
                blocked_files.append(f"Hidden file: {filename}")
                logger.warning(f"Blocked hidden file: {filename}")
                continue

            # 3. BLOKADA NIEBEZPIECZNYCH NAZW PLIKÓW
            dangerous_names = [
                '.env', '.git', '.ssh', '.aws', '.npmrc', '.pypirc',
                'id_rsa', 'id_ed25519', 'credentials', 'secrets.yaml',
                'secrets.json', 'config.json', '.htaccess', '.htpasswd'
            ]

            if any(dangerous in filename.lower() for dangerous in dangerous_names):
                blocked_files.append(f"Dangerous file: {filename}")
                logger.warning(f"Blocked dangerous file: {filename}")
                continue

            # 4. PATH TRAVERSAL PROTECTION
            # Normalizuj ścieżkę
            normalized = os.path.normpath(os.path.join(extract_dir, filename))

            # Sprawdź czy nie wykracza poza katalog docelowy
            if not normalized.startswith(extract_dir_abs + os.sep):
                blocked_files.append(f"Path traversal: {filename}")
                logger.error(f"SECURITY: Path traversal blocked: {filename}")
                raise ValueError(f"Path traversal attempt detected: {filename}")

            # 5. SYMLINK PROTECTION
            # Sprawdź external_attr dla Unix permissions/type
            # Format: <file type><permissions> w górnych 16 bitach
            file_attr = info.external_attr >> 16

            # 0o120000 = symbolic link in Unix
            if file_attr == 0o120000:
                blocked_files.append(f"Symlink: {filename}")
                logger.error(f"SECURITY: Symlink blocked: {filename}")
                raise ValueError(f"Symbolic link detected: {filename}")

            # Sprawdź czy to device file lub special file
            if file_attr != 0:
                is_regular_file = (file_attr & 0o100000) != 0  # S_IFREG
                if not is_regular_file and file_attr != 0o040000:  # Not directory
                    blocked_files.append(f"Special file: {filename}")
                    logger.warning(f"Blocked special file: {filename}")
                    continue

            # 6. EXTENSION VALIDATION
            if allowed_extensions is not None:
                _, ext = os.path.splitext(filename)
                if ext.lower() not in allowed_extensions:
                    blocked_files.append(f"Invalid extension: {filename}")
                    logger.warning(f"Blocked file with invalid extension: {filename}")
                    continue

            # 7. FILENAME LENGTH CHECK
            if len(filename) > 255:
                blocked_files.append(f"Filename too long: {filename}")
                logger.warning(f"Blocked file with too long name: {filename}")
                continue

            # 8. BEZPIECZNA EKSTRAKCJA
            try:
                zf.extract(info, extract_dir)
                extracted_path = os.path.join(extract_dir, filename)

                # 9. POST-EXTRACTION VALIDATION
                # Sprawdź czy plik rzeczywiście znajduje się w katalogu docelowym
                real_path = os.path.realpath(extracted_path)
                if not real_path.startswith(extract_dir_abs):
                    os.remove(real_path)
                    raise ValueError(f"Post-extraction path validation failed: {filename}")

                # 10. SANITIZE PERMISSIONS
                # Usuń execute bit ze wszystkich plików
                current_perms = os.stat(extracted_path).st_mode
                safe_perms = current_perms & ~0o111  # Remove execute
                os.chmod(extracted_path, safe_perms)

                # 11. SPRAWDŹ CZY TO NIE BINARY EXECUTABLE
                with open(extracted_path, 'rb') as f:
                    header = f.read(4)

                    # ELF binary
                    if header == b'\x7fELF':
                        os.remove(extracted_path)
                        raise ValueError(f"ELF executable blocked: {filename}")

                    # Shebang script
                    if header[:2] == b'#!':
                        logger.warning(f"Script file detected: {filename}")

                extracted_files.append(filename)
                logger.info(f"Safely extracted: {filename}")

            except Exception as e:
                logger.error(f"Failed to extract {filename}: {e}")
                # Cleanup partial extraction
                if os.path.exists(extracted_path):
                    os.remove(extracted_path)
                raise

    # Log summary
    logger.info(
        f"Extraction complete: {len(extracted_files)} files extracted, "
        f"{len(blocked_files)} files blocked"
    )

    if blocked_files:
        logger.warning(f"Blocked files:\n" + "\n".join(blocked_files))

    return extracted_files


# =============================================================================
# 2. REQUIREMENTS.TXT VALIDATION (CVSS 9.8)
# =============================================================================

def validate_requirements_txt(
    requirements_path: str,
    allow_git: bool = False,
    allow_local: bool = False,
    max_packages: int = 100
) -> bool:
    """
    Walidacja requirements.txt przed użyciem z pip download/install.
    Blokuje:
    - Git URLs (git+https://, git+ssh://)
    - Local file URLs (file://)
    - HTTP URLs (tylko HTTPS dozwolone)
    - Editable installs (-e)
    - Pip flags (--extra-index-url, --trusted-host, etc.)
    - Command injection attempts
    - Dependency confusion attacks

    Args:
        requirements_path: Ścieżka do requirements.txt
        allow_git: Czy dozwolić Git URLs (default: False)
        allow_local: Czy dozwolić local paths (default: False)
        max_packages: Maksymalna liczba pakietów

    Returns:
        True jeśli plik jest bezpieczny

    Raises:
        ValueError: Jeśli wykryto niebezpieczne konstrukcje
    """

    if not os.path.exists(requirements_path):
        raise FileNotFoundError(f"Requirements file not found: {requirements_path}")

    # Dozwolone formaty package specifiers
    ALLOWED_PATTERNS = [
        r'^[a-zA-Z0-9_-]+\s*$',                          # package
        r'^[a-zA-Z0-9_-]+\s*[<>=!~]+\s*[\d.]+\s*$',    # package==1.0.0
        r'^[a-zA-Z0-9_-]+\s*\[[\w,-]+\]\s*[<>=!~]+\s*[\d.]+\s*$',  # package[extra]==1.0.0
    ]

    # Zabronione wzorce (injection patterns)
    FORBIDDEN_PATTERNS = {
        r'git\+': 'Git URLs are not allowed',
        r'git@': 'Git SSH URLs are not allowed',
        r'ssh://': 'SSH URLs are not allowed',
        r'file://': 'Local file URLs are not allowed',
        r'http://': 'HTTP URLs are not allowed (use HTTPS)',
        r'^-e\s': 'Editable installs (-e) are not allowed',
        r'^--': 'Pip flags are not allowed',
        r'#egg=': 'Egg specifiers are not allowed',
        r'\$\{': 'Variable expansion is not allowed',
        r'`': 'Command substitution is not allowed',
        r'\|': 'Pipes are not allowed',
        r';': 'Semicolons are not allowed',
        r'&&': 'Command chaining is not allowed',
        r'\n.*\n': 'Multiline entries are suspicious',
    }

    # Dozwolone Git URLs jeśli allow_git=True
    if allow_git:
        del FORBIDDEN_PATTERNS[r'git\+']
        del FORBIDDEN_PATTERNS[r'git@']

    # Dozwolone local paths jeśli allow_local=True
    if allow_local:
        del FORBIDDEN_PATTERNS[r'file://']

    valid_packages = []
    issues = []

    with open(requirements_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line_num, line in enumerate(lines, 1):
        original_line = line
        line = line.strip()

        # Pomiń puste linie i komentarze
        if not line or line.startswith('#'):
            continue

        # Sprawdź zabronione wzorce
        for pattern, reason in FORBIDDEN_PATTERNS.items():
            if re.search(pattern, line, re.IGNORECASE):
                issue = (
                    f"Line {line_num}: {reason}\n"
                    f"  Content: {line}"
                )
                issues.append(issue)
                logger.error(f"SECURITY: Requirements validation failed - {issue}")

        # Jeśli nie ma issues, sprawdź czy pasuje do dozwolonych wzorców
        if not issues:
            # Sprawdź czy to HTTPS URL (dozwolone tylko z hash)
            if line.startswith('https://'):
                if '#' not in line:
                    issues.append(
                        f"Line {line_num}: HTTPS URLs must include hash (#sha256=...)\n"
                        f"  Content: {line}"
                    )
                else:
                    valid_packages.append(line)
            # Sprawdź standard package specifiers
            elif any(re.match(pattern, line) for pattern in ALLOWED_PATTERNS):
                valid_packages.append(line)
            else:
                issues.append(
                    f"Line {line_num}: Invalid package specifier format\n"
                    f"  Content: {line}\n"
                    f"  Expected format: package==1.0.0"
                )

    # Sprawdź limit pakietów
    if len(valid_packages) > max_packages:
        issues.append(
            f"Too many packages: {len(valid_packages)} > {max_packages}"
        )

    # Jeśli są issues, zgłoś błąd
    if issues:
        error_msg = (
            f"Requirements.txt validation failed with {len(issues)} issue(s):\n\n" +
            "\n".join(issues)
        )
        raise ValueError(error_msg)

    logger.info(
        f"Requirements.txt validated successfully: "
        f"{len(valid_packages)} packages approved"
    )

    return True


# =============================================================================
# 3. PLATFORM PARAMETER VALIDATION (CVSS 8.1)
# =============================================================================

ALLOWED_PLATFORMS = [
    'manylinux2014_x86_64',
    'manylinux2014_aarch64',
    'manylinux2014_i686',
    'manylinux_2_17_x86_64',
    'manylinux_2_17_aarch64',
    'manylinux_2_17_i686',
    'manylinux_2_28_x86_64',
    'manylinux_2_28_aarch64',
    'musllinux_1_1_x86_64',
    'musllinux_1_1_aarch64',
    'macosx_10_9_x86_64',
    'macosx_11_0_arm64',
    'win_amd64',
    'win32',
    'win_arm64',
]


def validate_platform(platform: str) -> str:
    """
    Walidacja parametru platform dla pip download.
    Zapobiega command injection.

    Args:
        platform: String platformy (np. 'manylinux2014_x86_64')

    Returns:
        Zwalidowany platform string

    Raises:
        ValueError: Jeśli platform jest nieprawidłowy
    """
    if not platform:
        return ""

    # Sprawdź whitelist
    if platform not in ALLOWED_PLATFORMS:
        raise ValueError(
            f"Invalid platform '{platform}'. "
            f"Allowed platforms: {', '.join(ALLOWED_PLATFORMS)}"
        )

    # Dodatkowa walidacja pattern (defense in depth)
    if not re.match(r'^[a-z0-9_]+$', platform):
        raise ValueError(
            f"Platform contains invalid characters: {platform}"
        )

    return platform


# =============================================================================
# 4. SAFE FILENAME SANITIZATION
# =============================================================================

def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanityzacja nazwy pliku do bezpiecznej postaci.

    Args:
        filename: Oryginalna nazwa pliku
        max_length: Maksymalna długość nazwy

    Returns:
        Bezpieczna nazwa pliku
    """
    # Usuń ścieżkę, zostaw tylko nazwę
    filename = os.path.basename(filename)

    # Usuń niebezpieczne znaki
    safe_chars = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)

    # Usuń wielokrotne podkreślniki
    safe_chars = re.sub(r'_+', '_', safe_chars)

    # Ogranicz długość
    if len(safe_chars) > max_length:
        name, ext = os.path.splitext(safe_chars)
        max_name_len = max_length - len(ext)
        safe_chars = name[:max_name_len] + ext

    # Upewnij się że nazwa nie jest pusta
    if not safe_chars:
        safe_chars = 'unnamed_file'

    return safe_chars


# =============================================================================
# 5. COMPREHENSIVE PACKAGE VALIDATION
# =============================================================================

def validate_difypkg_package(
    package_path: str,
    extract_to: str,
    max_size_mb: int = 100
) -> dict:
    """
    Kompleksowa walidacja pakietu .difypkg:
    1. Bezpieczna ekstrakcja
    2. Walidacja requirements.txt
    3. Sprawdzenie struktury
    4. Walidacja manifest

    Args:
        package_path: Ścieżka do .difypkg
        extract_to: Katalog do ekstrakcji
        max_size_mb: Maksymalny rozmiar

    Returns:
        Dict z informacjami o pakiecie

    Raises:
        ValueError: Jeśli pakiet jest niebezpieczny
    """

    logger.info(f"Validating package: {package_path}")

    # 1. Bezpieczna ekstrakcja
    try:
        extracted_files = safe_extract(
            package_path,
            extract_to,
            max_size_mb=max_size_mb,
            allowed_extensions=['.py', '.yaml', '.yml', '.txt', '.md', '.json']
        )
    except Exception as e:
        raise ValueError(f"Package extraction failed: {e}")

    # 2. Sprawdź czy requirements.txt istnieje
    requirements_path = os.path.join(extract_to, 'requirements.txt')
    if os.path.exists(requirements_path):
        try:
            validate_requirements_txt(requirements_path)
        except Exception as e:
            raise ValueError(f"Requirements validation failed: {e}")
    else:
        logger.info("No requirements.txt found (optional)")

    # 3. Sprawdź czy manifest istnieje
    manifest_candidates = [
        'manifest.json',
        'manifest.yaml',
        'plugin.yaml',
        '_plugin.yaml'
    ]

    manifest_path = None
    for candidate in manifest_candidates:
        path = os.path.join(extract_to, candidate)
        if os.path.exists(path):
            manifest_path = path
            break

    if not manifest_path:
        logger.warning("No manifest file found")

    # 4. Sprawdź strukturę pakietu
    has_python_files = any(f.endswith('.py') for f in extracted_files)
    if not has_python_files:
        logger.warning("No Python files found in package")

    # 5. Zwróć informacje
    package_info = {
        'package_path': package_path,
        'extracted_to': extract_to,
        'file_count': len(extracted_files),
        'has_requirements': os.path.exists(requirements_path),
        'has_manifest': manifest_path is not None,
        'has_python': has_python_files,
        'files': extracted_files,
    }

    logger.info(f"Package validation successful: {package_info}")

    return package_info


# =============================================================================
# 6. SAFE PIP DOWNLOAD WRAPPER
# =============================================================================

def safe_pip_download(
    requirements_path: str,
    output_dir: str,
    platform: Optional[str] = None,
    timeout: int = 300
) -> tuple[bool, str]:
    """
    Bezpieczne wywołanie pip download z pełną walidacją.

    Args:
        requirements_path: Ścieżka do requirements.txt
        output_dir: Katalog na wheel files
        platform: Optional platform string
        timeout: Timeout w sekundach

    Returns:
        (success: bool, output: str)
    """
    import subprocess
    import shlex

    # 1. Walidacja requirements.txt
    validate_requirements_txt(requirements_path)

    # 2. Walidacja platform
    if platform:
        platform = validate_platform(platform)

    # 3. Utwórz output directory
    os.makedirs(output_dir, exist_ok=True)

    # 4. Zbuduj bezpieczne polecenie
    cmd = [
        'pip', 'download',
        '--no-deps',                      # Nie pobieraj zależności rekursywnie
        '--only-binary=:all:',            # Tylko wheels (bez source distributions)
        '--disable-pip-version-check',    # Nie sprawdzaj wersji pip
        '--no-input',                     # Nie proś o input
        '--index-url', 'https://pypi.org/simple/',  # Tylko oficjalne PyPI (HTTPS!)
        '-r', requirements_path,
        '-d', output_dir,
    ]

    # Dodaj platform jeśli podany
    if platform:
        cmd.extend(['--platform', platform])

    logger.info(f"Executing: {' '.join(shlex.quote(str(x)) for x in cmd)}")

    # 5. Wykonaj z timeoutem
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )

        if result.returncode != 0:
            logger.error(f"pip download failed:\n{result.stderr}")
            return False, result.stderr

        logger.info("pip download completed successfully")
        return True, result.stdout

    except subprocess.TimeoutExpired:
        logger.error(f"pip download timed out after {timeout}s")
        return False, f"Timeout after {timeout}s"
    except Exception as e:
        logger.error(f"pip download error: {e}")
        return False, str(e)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Example 1: Safe extraction
    print("\n=== Example 1: Safe ZIP extraction ===")
    try:
        extracted = safe_extract(
            'example.difypkg',
            '/tmp/plugin_extract',
            max_size_mb=100
        )
        print(f"Successfully extracted {len(extracted)} files")
    except ValueError as e:
        print(f"Security violation detected: {e}")

    # Example 2: Requirements validation
    print("\n=== Example 2: Requirements.txt validation ===")
    try:
        validate_requirements_txt('/tmp/plugin_extract/requirements.txt')
        print("Requirements.txt is safe")
    except ValueError as e:
        print(f"Dangerous requirements.txt: {e}")

    # Example 3: Platform validation
    print("\n=== Example 3: Platform validation ===")
    try:
        safe_platform = validate_platform('manylinux2014_x86_64')
        print(f"Platform validated: {safe_platform}")
    except ValueError as e:
        print(f"Invalid platform: {e}")

    # Example 4: Complete package validation
    print("\n=== Example 4: Complete package validation ===")
    try:
        info = validate_difypkg_package(
            'plugin.difypkg',
            '/tmp/validated_plugin'
        )
        print(f"Package validated: {info}")
    except ValueError as e:
        print(f"Package validation failed: {e}")
