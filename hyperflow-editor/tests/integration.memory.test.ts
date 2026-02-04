import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createMemory, flushQueue } from '../src/memoryClient'

describe('Memory client offline queue', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('queues on network error and flushes when back online', async () => {
    const item = { content: 'Task A', type: 'short-term' }
    vi.spyOn(global, 'fetch').mockRejectedValueOnce(new Error('offline'))
    const res = await createMemory(item as any)
    expect(res).toBeNull()
    const q = JSON.parse(localStorage.getItem('hc_mem_queue_v1') || '[]')
    expect(q.length).toBe(1)
    ;(global.fetch as any).mockResolvedValueOnce({ ok: true, json: async () => ({ id: 'x' }) })
    const flushed = await flushQueue()
    expect(flushed).toBe(1)
    const q2 = JSON.parse(localStorage.getItem('hc_mem_queue_v1') || '[]')
    expect(q2.length).toBe(0)
  })
})
