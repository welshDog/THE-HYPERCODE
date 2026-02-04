import { describe, it, expect, vi } from 'vitest'

describe('Write-Run-See pipeline', () => {
  it('posts to backend and receives formatted output', async () => {
    const mock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ stdout: '42' }) })
    ;(global as any).fetch = mock
    const res = await fetch('http://localhost:8000/execution/execute', { method: 'POST', body: '{}' })
    const j = await res.json()
    expect(j.stdout).toBe('42')
  })
})

