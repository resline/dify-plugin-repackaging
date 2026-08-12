# E2E regression tests

The Playwright suite covers the production regressions that are most important to keep stable:

- password login renders the authenticated application without a React hook-order crash;
- the first completed-file entry remains above the sticky application header;
- a completed task still reads as completed after the processing panel is minimized.

The tests mock their API responses at browser level, so their state is deterministic. Vite is started automatically by Playwright. For a local run:

```bash
npm ci
npx playwright install chromium
npm run test:e2e -- --project=chromium
```

The lightweight API server is still available for manual browser testing:

```bash
npm run mock:start
npm run dev:test
# when finished
npm run mock:stop
```

It implements the authentication-session and list endpoints needed by the current frontend contract.
