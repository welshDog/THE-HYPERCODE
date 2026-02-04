export const editor = {
  setModelMarkers: () => {},
  defineTheme: (_name: string, _def: any) => {},
  setTheme: (_name: string) => {},
  create: () => ({
    getValue: () => '',
    setValue: (_: string) => {},
    updateOptions: (_opts: any) => {},
    getModel: () => ({ uri: { toString: () => 'inmem://1' } }),
    onKeyDown: () => ({ dispose: () => {} }),
    onDidChangeModelContent: () => ({ dispose: () => {} }),
    onDidChangeCursorPosition: () => ({ dispose: () => {} }),
    setPosition: (_pos: any) => {},
    dispose: () => {}
  }),
}
export const languages = {
  register: () => {},
  setMonarchTokensProvider: () => {}
}
export const MarkerSeverity = { Error: 8 }
export default { editor, languages, MarkerSeverity }
