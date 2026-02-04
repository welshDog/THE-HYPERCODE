export type Token = { type: string; value: string; line: number; col: number }
export type ASTNode = { kind: string; value?: any; children?: ASTNode[]; line?: number; col?: number }
export type ParseResult = { ast: ASTNode[]; errors: { message: string; line: number; column: number }[] }

const KEYWORDS = new Set(['def','return','if','else','elif','for','while','break','continue','match','case','print'])

export function tokenize(src: string): Token[] {
  const tokens: Token[] = []
  const lines = src.split(/\n/)
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    let col = 1
    const re = /\s+|#[^\n]*|"([^"\\]|\\.)*"|\d+|[A-Za-z_][A-Za-z0-9_]*|[=+\-*\/%()]/g
    let m: RegExpExecArray | null
    while ((m = re.exec(line))) {
      const text = m[0]
      const start = m.index + 1
      col = start
      if (/^\s+$/.test(text)) continue
      if (/^#/.test(text)) continue
      let type = 'symbol'
      if (/^\d+$/.test(text)) type = 'number'
      else if (/^"/.test(text)) type = 'string'
      else if (/^[A-Za-z_]/.test(text)) type = KEYWORDS.has(text) ? 'keyword' : 'ident'
      tokens.push({ type, value: text, line: i + 1, col })
    }
  }
  return tokens
}

export function parse(src: string): ParseResult {
  const tokens = tokenize(src)
  const errors: { message: string; line: number; column: number }[] = []
  const ast: ASTNode[] = []
  // simple line-based parse: assignment, call, def
  const byLine = groupByLine(tokens)
  for (const line of Object.keys(byLine).map(n => parseInt(n)).sort((a,b)=>a-b)) {
    const ts = byLine[line]
    if (!ts.length) continue
    // def name ( args )
    if (ts[0].type === 'keyword' && ts[0].value === 'def') {
      const name = ts[1]?.value
      if (!name || ts[1].type !== 'ident') errors.push({ message: 'function name expected', line, column: ts[1]?.col || ts[0].col })
      ast.push({ kind: 'function_def', value: { name }, line, col: ts[0].col })
      continue
    }
    // ident = expr
    const eqIdx = ts.findIndex(t => t.value === '=')
    if (eqIdx > 0 && ts[0].type === 'ident') {
      ast.push({ kind: 'assign', value: { var: ts[0].value }, line, col: ts[0].col })
      continue
    }
    // call: print(
    if (ts[0].type === 'ident' || (ts[0].type === 'keyword' && ts[0].value === 'print')) {
      ast.push({ kind: 'expr', value: { call: ts[0].value }, line, col: ts[0].col })
      continue
    }
    errors.push({ message: 'unrecognized statement', line, column: ts[0].col })
  }
  // rudimentary paren balance check
  let balance = 0
  for (const t of tokens) {
    if (t.value === '(') balance++
    if (t.value === ')') balance--
    if (balance < 0) errors.push({ message: 'unexpected )', line: t.line, column: t.col })
  }
  if (balance > 0) errors.push({ message: 'missing )', line: tokens[tokens.length-1]?.line || 1, column: tokens[tokens.length-1]?.col || 1 })
  return { ast, errors }
}

function groupByLine(tokens: Token[]): Record<number, Token[]> {
  const out: Record<number, Token[]> = {}
  for (const t of tokens) {
    (out[t.line] ||= []).push(t)
  }
  return out
}

