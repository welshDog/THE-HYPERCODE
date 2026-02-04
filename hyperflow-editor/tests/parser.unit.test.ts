import { describe, it, expect } from 'vitest'
import { tokenize, parse } from '../src/hcParser'

describe('HyperCode TS parser', () => {
  it('tokenizes keywords, idents, numbers, strings', () => {
    const tks = tokenize('def add(a, b)\nprint "hi"\nx = 42')
    expect(tks.find(t => t.value === 'def')?.type).toBe('keyword')
    expect(tks.find(t => t.value === 'add')?.type).toBe('ident')
    expect(tks.find(t => t.value === 'print')?.type).toBe('keyword')
    expect(tks.find(t => t.value === '"hi"')?.type).toBe('string')
    expect(tks.find(t => t.value === '42')?.type).toBe('number')
  })

  it('parses assignment and call', () => {
    const res = parse('x = 1\nprint "ok"')
    expect(res.errors.length).toBe(0)
    expect(res.ast[0].kind).toBe('assign')
    expect(res.ast[1].kind).toBe('expr')
  })

  it('detects missing paren', () => {
    const res = parse('print("oops"')
    expect(res.errors.some(e => e.message.includes('missing'))).toBe(true)
  })
})

