// Browser APIs jsdom lacks. Plain functions/classes, not jest.fn(): CRA runs
// Jest with resetMocks: true, which wipes jest.fn() implementations before
// every test (matchMedia then returned undefined and MUI useMediaQuery threw).

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  configurable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {}, // deprecated
    removeListener: () => {}, // deprecated
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

class NoopObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords() {
    return [];
  }
}

(global as any).ResizeObserver = NoopObserver;
(global as any).IntersectionObserver = NoopObserver;

export {};
