# Playwright tests

The suite in `tests/regressions.spec.ts` is a small deterministic browser-level safety net for the reported production regressions. API and WebSocket traffic is intercepted by Playwright, while the real React application runs through Vite.

Run Chromium locally:

```bash
npx playwright install chromium
npm run test:e2e -- --project=chromium
```

CI additionally runs Firefox and WebKit. Failure screenshots, videos, traces, and reports are written under `test-results/` and `playwright-report/`.
