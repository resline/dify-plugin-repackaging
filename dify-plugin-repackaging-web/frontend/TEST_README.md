# Frontend Testing Documentation

## Test Setup

The frontend testing infrastructure uses the following tools:

- **Vitest** - Fast unit test framework, Vite-native
- **React Testing Library** - For testing React components with user-centric approach
- **MSW (Mock Service Worker)** - For mocking API and WebSocket requests
- **@testing-library/user-event** - For simulating user interactions

## Running Tests

```bash
# Run all tests once
npm test

# Run tests in watch mode
npm run test

# Run tests with UI
npm run test:ui

# Run tests with coverage
npm run test:coverage
```

## Test Structure

```
src/
├── test/
│   ├── setup.ts              # Global test setup
│   ├── mocks/
│   │   ├── server.ts         # MSW server setup
│   │   └── handlers.ts       # API mock handlers
│   └── utils/
│       └── test-utils.tsx    # Custom render and utilities
├── components/__tests__/     # Component tests
├── services/__tests__/       # Service tests
└── hooks/__tests__/          # Hook tests
```

## Key Test Files

### Components
- `UploadForm.test.tsx` - Tests URL validation, file upload, platform selection
- `FileUpload.test.tsx` - Tests drag & drop, file validation, size limits
- `MarketplaceBrowser.test.tsx` - Tests plugin search, selection, error handling
- `TaskStatus.test.tsx` - Tests WebSocket updates, progress display, completion

### Services
- `api.test.ts` - Tests REST API calls, error handling
- `websocket.test.ts` - Tests WebSocket reconnection, heartbeat, message handling
- `marketplace.test.ts` - Tests marketplace API integration
- `files.test.ts` - Tests file management operations

### Hooks
- `useCopyToClipboard.test.ts` - Tests clipboard functionality
- `useDeepLink.test.ts` - Tests URL parameter parsing

## Test Utilities

### Custom Render
```typescript
import { render } from '@/test/utils/test-utils'

// Automatically wraps components with necessary providers
render(<MyComponent />)
```

### Mock Utilities
```typescript
// Create mock files
const file = createMockFile('plugin.difypkg', 1024000, 'application/octet-stream')

// Mock WebSocket messages
mockWebSocketMessage(ws, { type: 'log', message: 'Test' })
```

## Writing Tests

### Component Testing Example
```typescript
describe('MyComponent', () => {
  it('handles user interaction', async () => {
    const user = userEvent.setup()
    render(<MyComponent />)
    
    await user.click(screen.getByRole('button'))
    
    expect(screen.getByText('Result')).toBeInTheDocument()
  })
})
```

### API Mocking Example
```typescript
server.use(
  http.get('/api/v1/endpoint', () => {
    return HttpResponse.json({ data: 'test' })
  })
)
```

## Known Issues & Limitations

1. **WebSocket Testing**: WebSocket connections in tests use a mock implementation. Real WebSocket behavior may differ.

2. **File Upload**: File upload tests use MSW which may not perfectly replicate multipart/form-data handling.

3. **Timeouts**: Some async operations may require extended timeouts. Use the timeout parameter:
   ```typescript
   it('long running test', async () => {
     // test code
   }, 10000)
   ```

4. **Component Versions**: Some components have both `.jsx` and `.tsx` versions. Tests target the `.jsx` versions when they exist.

## Accessibility Testing

All components include accessibility tests to ensure:
- Proper ARIA labels and roles
- Keyboard navigation support
- Screen reader compatibility

## Coverage Goals

- Components: 80%+ coverage
- Services: 90%+ coverage
- Hooks: 100% coverage

Run `npm run test:coverage` to generate coverage reports.

## Debugging Tests

1. Use `test.only()` to run a single test
2. Add `console.log()` statements (will appear in test output)
3. Use `screen.debug()` to print current DOM
4. Run `npm run test:ui` for interactive debugging

## Best Practices

1. **Test User Behavior**: Focus on how users interact with components
2. **Avoid Implementation Details**: Don't test internal state or methods
3. **Use Accessible Queries**: Prefer `getByRole`, `getByLabelText` over `getByTestId`
4. **Mock External Dependencies**: Use MSW for API calls, mock timers for delays
5. **Clean Up**: Tests automatically clean up, but cancel any pending async operations