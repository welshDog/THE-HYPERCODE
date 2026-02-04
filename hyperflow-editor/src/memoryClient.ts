export type MemoryItem = {
  content: string
  type: string
  userId?: string
  sessionId?: string
  metadata?: Record<string, any>
  keywords?: string[]
  missionId?: string | null
  expiresAt?: string | null
  version?: number
}

const CORE = (import.meta as any).env.VITE_CORE_URL || 'http://localhost:8000'
const BASE = `${CORE}/memory`

const QUEUE_KEY = 'hc_mem_queue_v1'
const KEY_KEY = 'hc_crypto_key_v1'

async function getKey(): Promise<CryptoKey> {
  const enc = new TextEncoder()
  const b64 = localStorage.getItem(KEY_KEY)
  if (b64) {
    const raw = Uint8Array.from(atob(b64), c => c.charCodeAt(0))
    return await crypto.subtle.importKey('raw', raw, { name: 'AES-GCM' }, false, ['encrypt','decrypt'])
  }
  const k = await crypto.subtle.generateKey({ name: 'AES-GCM', length: 256 }, true, ['encrypt','decrypt'])
  const raw = await crypto.subtle.exportKey('raw', k)
  const b = String.fromCharCode(...new Uint8Array(raw))
  localStorage.setItem(KEY_KEY, btoa(b))
  return k
}

async function encryptString(plain: string): Promise<{ iv: string; data: string }> {
  const key = await getKey()
  const iv = crypto.getRandomValues(new Uint8Array(12))
  const ct = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, new TextEncoder().encode(plain))
  const ivb = String.fromCharCode(...iv)
  const ctb = String.fromCharCode(...new Uint8Array(ct))
  return { iv: btoa(ivb), data: btoa(ctb) }
}

async function decryptString(ivB64: string, dataB64: string): Promise<string> {
  const key = await getKey()
  const iv = Uint8Array.from(atob(ivB64), c => c.charCodeAt(0))
  const ct = Uint8Array.from(atob(dataB64), c => c.charCodeAt(0))
  const pt = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, ct)
  return new TextDecoder().decode(pt)
}

function nextVersion(): number {
  try {
    const v = parseInt(localStorage.getItem('hc_mem_version') || '0')
    const nv = isNaN(v) ? 1 : v + 1
    localStorage.setItem('hc_mem_version', String(nv))
    return nv
  } catch {
    return Date.now()
  }
}

export async function createMemory(item: MemoryItem) {
  try {
    item.version = nextVersion()
    const r = await fetch(`${BASE}/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(item)
    })
    if (!r.ok) throw new Error(await r.text())
    return await r.json()
  } catch (e) {
    enqueue(item)
    return null
  }
}

export function enqueue(item: MemoryItem) {
  const q = JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]')
  const payload = { ...item, version: item.version ?? nextVersion() }
  const s = JSON.stringify(payload)
  const nq = Array.isArray(q) ? q : []
  const idx = nq.push({ iv: '', data: '', ts: Date.now(), raw: s }) - 1
  localStorage.setItem(QUEUE_KEY, JSON.stringify(nq))
  ;(async () => {
    const enc = await encryptString(s)
    const cur = JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]')
    if (cur[idx]) {
      cur[idx].iv = enc.iv
      cur[idx].data = enc.data
      localStorage.setItem(QUEUE_KEY, JSON.stringify(cur))
    }
  })()
}

export async function flushQueue() {
  const q = JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]') as Array<{ iv: string; data: string; ts: number; raw?: string }>
  if (!q.length) return 0
  const kept: typeof q = []
  for (const rec of q) {
    try {
      const s = rec.iv && rec.data ? await decryptString(rec.iv, rec.data) : String(rec.raw || '')
      if (!s) throw new Error('empty')
      const item = JSON.parse(s)
      const r = await fetch(`${BASE}/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(item)
      })
      if (!r.ok) throw new Error(await r.text())
    } catch {
      kept.push({ iv: rec.iv, data: rec.data, ts: Date.now() })
    }
  }
  localStorage.setItem(QUEUE_KEY, JSON.stringify(kept))
  return q.length - kept.length
}

export function setupQueueFlush() {
  window.addEventListener('online', () => { flushQueue() })
}
