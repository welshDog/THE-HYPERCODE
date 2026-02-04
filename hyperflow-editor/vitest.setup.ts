import { vi } from 'vitest'

vi.mock('monaco-editor', () => ({
  editor: {
    setModelMarkers: () => {},
    defineTheme: (_name: string, _def: any) => {},
    setTheme: (_name: string) => {},
    create: () => ({
      getValue: () => '',
      setValue: (_: string) => {},
      updateOptions: (_opts: any) => {},
      getModel: () => ({
        uri: { toString: () => 'inmem://1' }
      }),
      onKeyDown: () => ({ dispose: () => {} }),
      onDidChangeModelContent: () => ({ dispose: () => {} }),
      onDidChangeCursorPosition: () => ({ dispose: () => {} }),
      setPosition: (_pos: any) => {},
      dispose: () => {}
    }),
  },
  languages: {
    register: () => {},
    setMonarchTokensProvider: () => {}
  },
  MarkerSeverity: { Error: 8 }
}))

class LS {
  store: Record<string, string> = {}
  getItem(k: string) { return this.store[k] ?? null }
  setItem(k: string, v: string) { this.store[k] = String(v) }
  removeItem(k: string) { delete this.store[k] }
  clear() { this.store = {} }
}
;(global as any).localStorage = new LS()

if (!(global as any).crypto) {
  ;(global as any).crypto = {
    getRandomValues: (arr: Uint8Array) => { for (let i=0;i<arr.length;i++) arr[i] = (i*17)%255; return arr },
    subtle: {
      generateKey: async () => ({ k: true }),
      exportKey: async () => new Uint8Array([1,2,3,4]).buffer,
      importKey: async () => ({ k: true }),
      encrypt: async (_algo: any, _key: any, data: Uint8Array) => data.buffer,
      decrypt: async (_algo: any, _key: any, data: Uint8Array) => data.buffer,
    }
  }
}
