import * as monaco from 'monaco-editor'

export function setupHypercodeLanguage() {
  monaco.languages.register({ id: 'hypercode' })
  monaco.languages.setMonarchTokensProvider('hypercode', {
    defaultToken: 'invalid',
    keywords: [
      'def','return','if','else','elif','for','while','break','continue','match','case','print'
    ],
    operators: ['=','+','-','*','/','%','==','!=','<','>','<=','>=','&&','||','!'],
    symbols: /[=><!~?:&|+\-*\/\^%]+/,
    escapes: /\\(?:[abfnrtv\\"'0-9xuv]|x[0-9A-Fa-f]{2}|u[0-9A-Fa-f]{4})/,
    tokenizer: {
      root: [
        [/\s+/, 'white'],
        [/#[^\n]*/, 'comment'],
        [/"([^"\\]|\\.)*$/, 'string.invalid'],
        [/"/, { token: 'string.quote', bracket: '@open', next: '@string' }],
        [/\d+(_\d+)?/, 'number'],
        [/(@symbols)/, {
          cases: {
            '@operators': 'operator',
            '@default': 'delimiter'
          }
        }],
        [/\b[\w_]+\b/, {
          cases: {
            '@keywords': 'keyword',
            '@default': 'identifier'
          }
        }],
        [/\(/, 'delimiter.parenthesis'],
        [/\)/, 'delimiter.parenthesis']
      ],
      string: [
        [/[^\\"]+/, 'string'],
        [/@escapes/, 'string.escape'],
        [/"/, { token: 'string.quote', bracket: '@close', next: '@pop' }]
      ]
    }
  } as any)

  monaco.editor.defineTheme('hypercode-light', {
    base: 'vs',
    inherit: true,
    rules: [
      { token: 'keyword', foreground: '5A67D8', fontStyle: 'bold' },
      { token: 'string', foreground: '2B6CB0' },
      { token: 'number', foreground: '805AD5' },
      { token: 'comment', foreground: '718096', fontStyle: 'italic' },
      { token: 'operator', foreground: '4A5568' }
    ],
    colors: {
      'editorLineNumber.foreground': '#A0AEC0',
      'editorIndentGuides.stroke': '#EDF2F7'
    }
  })

  monaco.editor.defineTheme('hypercode-dark', {
    base: 'vs-dark',
    inherit: true,
    rules: [
      { token: 'keyword', foreground: 'A3BFFA', fontStyle: 'bold' },
      { token: 'string', foreground: '90CDF4' },
      { token: 'number', foreground: 'B794F4' },
      { token: 'comment', foreground: 'A0AEC0', fontStyle: 'italic' },
      { token: 'operator', foreground: 'CBD5E0' }
    ],
    colors: {
      'editorLineNumber.foreground': '#CBD5E0',
      'editorIndentGuides.stroke': '#2D3748'
    }
  })
}

export type ParseError = { message: string; line: number; column: number }

export function applyErrorsToModel(model: monaco.editor.ITextModel, errors: ParseError[]) {
  const markers = errors.map(e => ({
    severity: monaco.MarkerSeverity.Error,
    startLineNumber: e.line,
    startColumn: e.column,
    endLineNumber: e.line,
    endColumn: e.column + 1,
    message: e.message
  }))
  monaco.editor.setModelMarkers(model, 'hypercode', markers as any)
}

