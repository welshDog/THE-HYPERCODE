class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// @ts-expect-error
global.ResizeObserver = ResizeObserver;
