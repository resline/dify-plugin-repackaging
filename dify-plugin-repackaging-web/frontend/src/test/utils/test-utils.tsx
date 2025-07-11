import React, { ReactElement } from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { ThemeProvider } from '../../contexts/ThemeContext'

interface TestProviderProps {
  children: React.ReactNode
}

// Custom provider that includes all necessary context providers
function TestProvider({ children }: TestProviderProps) {
  return (
    <ThemeProvider>
      {children}
    </ThemeProvider>
  )
}

// Custom render method
const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) => render(ui, { wrapper: TestProvider, ...options })

// Re-export everything
export * from '@testing-library/react'
export { customRender as render }

// Utility functions for testing
export const waitForLoadingToFinish = () => {
  return new Promise((resolve) => setTimeout(resolve, 0))
}

export const createMockFile = (name: string, size: number, type: string): File => {
  const file = new File(['test content'], name, { type })
  Object.defineProperty(file, 'size', { value: size })
  return file
}

export const mockWebSocketMessage = (ws: any, data: any) => {
  if (ws.onmessage) {
    ws.onmessage(new MessageEvent('message', {
      data: JSON.stringify(data)
    }))
  }
}