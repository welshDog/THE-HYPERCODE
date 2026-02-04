 
import { describe, it, expect, vi } from 'vitest'
vi.mock('monaco-editor', () => ({
  editor: { setModelMarkers: () => {} },
  MarkerSeverity: { Error: 8 }
}))
import * as monaco from 'monaco-editor'
import { setupHypercodeLanguage, applyErrorsToModel } from '../src/hypercodeLang'
import { parse as parseHC } from '../src/hcParser'

describe('Editor persistence and markers', () => {
  it('applies markers and persists content', () => {
    // mock model
    const model: any = {
      uri: { toString: () => 'inmem://1' },
    }
    const spy = vi.spyOn(monaco.editor, 'setModelMarkers').mockImplementation(() => {})
    const res = parseHC('print("ok")\nprint("oops"')
    applyErrorsToModel(model as any, res.errors)
    expect(spy).toHaveBeenCalled()
    localStorage.setItem('hc_editor_content', 'hello')
    expect(localStorage.getItem('hc_editor_content')).toBe('hello')
  })
})
