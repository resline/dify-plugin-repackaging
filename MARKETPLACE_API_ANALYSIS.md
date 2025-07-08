# Analiza API Dify Marketplace

## Podsumowanie

Na podstawie przeprowadzonej analizy, oto najważniejsze informacje o nowym Dify Marketplace:

### 1. Struktura URL

- **Główna strona**: `https://marketplace.dify.ai/`
- **Strona pluginu**: `https://marketplace.dify.ai/plugins/{author}/{name}` (obecnie zwraca 404)
- **Ikony pluginów**: Hostowane na Cloudflare R2 Storage z podpisanymi URL-ami

### 2. API Endpoints

#### Główne API (REST)
- **Base URL**: `https://marketplace.dify.ai/api/v1/`
- **Szczegóły pluginu**: `GET /api/v1/plugins/{author}/{name}`
- **Pobieranie pluginu**: `GET /api/v1/plugins/{author}/{name}/{version}/download`
- **Ikona pluginu**: `GET /api/v1/plugins/{author}/{name}/icon` (przekierowanie 307)

#### Nowe API (prawdopodobnie)
- **Base URL**: `https://marketplace-plugin.dify.dev/api/v1/`
- **Wyszukiwanie zaawansowane**: `POST /plugins/search/advanced`
  - Body: `{page, page_size, query, sort_by, sort_order, category, tags, type}`

### 3. Format odpowiedzi API

#### Plugin Details Response
```json
{
  "code": 0,
  "data": {
    "plugin": {
      "type": "plugin",
      "name": "openai_api_compatible",
      "org": "langgenius",
      "plugin_id": "langgenius/openai_api_compatible",
      "icon": "langgenius/packages/openai_api_compatible/_assets/icon.svg",
      "label": {"en_US": "..."},
      "brief": {"en_US": "...", "zh_Hans": "..."},
      "introduction": "...",
      "category": "model",
      "created_at": "2024-11-29T09:17:34.657912Z",
      "updated_at": "2025-05-29T14:46:36.763383Z",
      "badges": [],
      "verification": {"authorized_category": "langgenius"},
      "plugins": {
        "models": ["provider/openai_api_compatible.yaml"],
        "tools": null
      }
    }
  }
}
```

### 4. Technologia

- **Frontend**: Next.js z React Server Components (RSC)
- **Hosting**: Cloudflare (CDN + Workers)
- **Storage**: Cloudflare R2 dla zasobów statycznych
- **Zabezpieczenia**: Podpisane URL-e z czasem ważności dla dostępu do plików

### 5. Pobieranie plików .difypkg

Pliki można pobrać bezpośrednio używając wzorca:
```
https://marketplace.dify.ai/api/v1/plugins/{author}/{name}/{version}/download
```

Przykład działającego pobierania:
```bash
curl -L -o agent.difypkg "https://marketplace.dify.ai/api/v1/plugins/langgenius/agent/0.0.19/download"
```

### 6. Format pliku .difypkg

- To standardowy plik ZIP z dodatkowymi metadanymi
- Zawiera sygnaturę cyfrową na początku pliku
- Struktura:
  - `.env.example`
  - `README.md`
  - `manifest.yaml`
  - `requirements.txt`
  - `_assets/` - zasoby graficzne
  - Pliki Python z kodem pluginu

### 7. Obserwacje

1. **Brak oficjalnej dokumentacji API** - API nie jest publicznie udokumentowane
2. **Zmiany w API** - Wygląda na to, że API przeszło migrację z `marketplace.dify.ai` na `marketplace-plugin.dify.dev`
3. **Fallback na web scraping** - Nasz kod już obsługuje fallback gdy API nie działa
4. **Cachowanie** - Ikony i zasoby są agresywnie cachowane przez Cloudflare

### 8. Rekomendacje

1. **Używać istniejącego kodu** - Nasz `MarketplaceService` już obsługuje oba API endpoints
2. **Implementować retry logic** - API może być niestabilne
3. **Cachować odpowiedzi** - Aby zmniejszyć obciążenie API
4. **Monitorować zmiany** - API może się zmienić bez ostrzeżenia

## Przykłady użycia

### Pobranie pluginu przez API
```python
# Używając naszego serwisu
from app.services.marketplace import MarketplaceService

# Pobierz szczegóły
details = await MarketplaceService.get_plugin_details("langgenius", "agent")

# Zbuduj URL do pobrania
download_url = MarketplaceService.build_download_url("langgenius", "agent", "0.0.19")
```

### Bezpośrednie pobranie
```bash
# Pobierz plugin
./plugin_repackaging.sh market langgenius agent 0.0.19

# Lub przez curl
curl -L -o plugin.difypkg "https://marketplace.dify.ai/api/v1/plugins/langgenius/agent/0.0.19/download"
```