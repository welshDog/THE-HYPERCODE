import React, { useEffect, useRef, useState } from "react"
import * as monaco from "monaco-editor"
import { setupHypercodeLanguage, applyErrorsToModel } from './hypercodeLang'
import { parse as parseHC } from './hcParser'
import { createMemory, setupQueueFlush } from './memoryClient'

export default function App() {
  const el = useRef<HTMLDivElement | null>(null)
  const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null)
  const [out, setOut] = useState("")
  const [transcripts, setTranscripts] = useState<Array<{ t: string; c: number }>>([])
  const [focusMode, setFocusMode] = useState<boolean>(() => {
    try { return localStorage.getItem('hc_focus_mode') === '1' } catch { return false }
  })
  const [fontScale, setFontScale] = useState<number>(1)
  useEffect(() => {
    setupHypercodeLanguage()
    const editor = monaco.editor.create(el.current as HTMLDivElement, {
      value: 'print "Hello HC"',
      language: "hypercode",
      theme: "hypercode-light",
      automaticLayout: true
    })
    editorRef.current = editor
    const onKey = editor.onKeyDown((k: monaco.IKeyboardEvent) => {
      if (k.ctrlKey && k.keyCode === 3) {
        const src = editor.getValue()
        run(src)
      }
    })
    const onChange = editor.onDidChangeModelContent(() => {
      const src = editor.getValue()
      const res = parseHC(src)
      const model = editor.getModel()
      if (model) applyErrorsToModel(model, res.errors)
      try {
        localStorage.setItem('hc_editor_content', src)
      } catch {}
    })
    const onCursor = editor.onDidChangeCursorPosition(e => {
      try { localStorage.setItem('hc_cursor', JSON.stringify({ line: e.position.lineNumber, col: e.position.column })) } catch {}
    })
    const saved = localStorage.getItem('hc_editor_content')
    if (saved) editor.setValue(saved)
    const savedCursor = localStorage.getItem('hc_cursor')
    if (savedCursor) {
      try {
        const pos = JSON.parse(savedCursor)
        editor.setPosition({ lineNumber: pos.line, column: pos.col })
      } catch {}
    }
    return () => {
      onKey.dispose()
      onChange.dispose()
      onCursor.dispose()
      editor.dispose()
    }
  }, [])
  useEffect(() => {
    setupQueueFlush()
  }, [])
  useEffect(() => {
    setFontScale(focusMode ? 1.1 : 1)
    try { localStorage.setItem('hc_focus_mode', focusMode ? '1' : '0') } catch {}
  }, [focusMode])
  useEffect(() => {
    const size = Math.round(14 * fontScale)
    editorRef.current?.updateOptions({ fontSize: size })
  }, [fontScale])
  async function run(source: string) {
    const core = (import.meta as any).env.VITE_CORE_URL || "http://localhost:8000"
    const r = await fetch(`${core}/execution/execute-hc`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source })
    })
    const j = await r.json()
    setOut(j.stdout || j.stderr || "")
    try {
      const hist = JSON.parse(localStorage.getItem('hc_history') || '[]')
      hist.unshift({ ts: Date.now(), src: source, out: j.stdout || j.stderr || '' })
      localStorage.setItem('hc_history', JSON.stringify(hist.slice(0,50)))
    } catch {}
    const editorCtx = collectSessionContext()
    await createMemory({
      content: source,
      type: 'short-term',
      sessionId: editorCtx.sessionId,
      metadata: { kind: 'task', cursor: editorCtx.cursor, panels: editorCtx.panels },
      keywords: ['task','run']
    })
    await createMemory({
      content: j.stdout || j.stderr || '',
      type: 'short-term',
      sessionId: editorCtx.sessionId,
      metadata: { kind: 'output', status: j.stdout ? 'success' : 'error' },
      keywords: ['output']
    })
  }
  return (
    <div style={{ display: "grid", gridTemplateColumns: focusMode ? "1fr 0px" : "1fr 360px", height: "100vh", transition: 'grid-template-columns 200ms ease' }}>
      <div ref={el} />
      <div style={{ borderLeft: "1px solid #ddd", padding: 12, overflow: 'hidden' }}>
        <div style={{ marginBottom: 8, fontWeight: 600 }}>Output</div>
        <pre style={{ whiteSpace: "pre-wrap" }}>{out}</pre>
        <div style={{ marginTop: 12, color: "#666" }}>Ctrl+Enter to run</div>
        <VoiceButton onTranscript={(t, c) => setTranscripts((prev) => [{ t, c }, ...prev])} />
        <div aria-live="polite" style={{ marginTop: 12 }}>
          <div style={{ marginBottom: 6, fontWeight: 600 }}>Transcript</div>
          <ul>
            {transcripts.map((x, i) => (
              <li key={i}>
                <span>{x.t}</span>
                <span style={{ marginLeft: 8, color: "#666" }}>({Math.round((x.c || 1) * 100)}%)</span>
              </li>
            ))}
          </ul>
          <div style={{ marginTop: 12 }}>
            <div style={{ fontWeight: 600 }}>History</div>
            <ul style={{ maxHeight: 120, overflow: 'auto' }}>
              {(JSON.parse((localStorage.getItem('hc_history')||'[]')) as any[]).map((h,i)=> (
                <li key={i}><span>{new Date(h.ts).toLocaleTimeString()}</span> — <span>{String(h.out).slice(0,60)}</span></li>
              ))}
            </ul>
          </div>
        </div>
      </div>
      <StatusBar focusMode={focusMode} setFocusMode={setFocusMode} fontScale={fontScale} />
    </div>
  )
}

function VoiceButton({ onTranscript }: { onTranscript: (t: string, c: number) => void }) {
  const [recording, setRecording] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const API_URL = (import.meta as any).env.VITE_CORE_URL || "http://localhost:8000"
  const API_KEY = (import.meta as any).env.VITE_API_KEY || ""

  const connect = () => {
    if (wsRef.current) return
    const url = `${API_URL.replace("http", "ws")}/voice/ws${API_KEY ? `?api_key=${API_KEY}` : ""}`
    const ws = new WebSocket(url)
    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data)
        if (data.transcript) {
          onTranscript(data.transcript, data.confidence ?? 1)
        }
      } catch {}
    }
    ws.onopen = () => {
      ws.send(JSON.stringify({ type: "ping" }))
    }
    ws.onclose = () => {
      wsRef.current = null
    }
    wsRef.current = ws
  }

  const disconnect = () => {
    wsRef.current?.close()
    wsRef.current = null
  }

  const handleHold = async () => {
    if (!wsRef.current) connect()
    setRecording(true)
    wsRef.current?.send(JSON.stringify({ text: "print('voice from UI')" }))
  }

  const handleRelease = async () => {
    setRecording(false)
    disconnect()
  }

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.code === "Space") {
        handleHold()
        setTimeout(handleRelease, 500)
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [])

  return (
    <button
      onMouseDown={handleHold}
      onMouseUp={handleRelease}
      aria-pressed={recording}
      style={{
        marginTop: 12,
        padding: "8px 12px",
        borderRadius: 8,
        border: "1px solid #888",
        background: recording ? "#ff3366" : "#ffffff",
        color: recording ? "#fff" : "#111"
      }}
    >
      {recording ? "Recording…" : "Hold to speak (Ctrl+Space)"}
    </button>
  )
}

function collectSessionContext() {
  const sessionId = 'session-' + new Date().toISOString().slice(0,10)
  const cursor = { line: 1, column: 1 }
  const panels = { sidebar: false, bottom: false, toolbars: false }
  return { sessionId, cursor, panels }
}

function StatusBar({ focusMode, setFocusMode, fontScale }: { focusMode: boolean; setFocusMode: (v: boolean) => void; fontScale: number }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.code === 'KeyF') {
        e.preventDefault()
        setFocusMode(!focusMode)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [focusMode])
  return (
    <div style={{ position: 'fixed', bottom: 8, right: 8, display: 'flex', gap: 12, alignItems: 'center' }}>
      <button aria-pressed={focusMode} onClick={() => setFocusMode(!focusMode)} style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid #ddd' }}>
        {focusMode ? 'Exit Focus Mode' : 'Focus Mode'}
      </button>
      <span style={{ fontSize: 12, color: '#666' }}>Font x{fontScale.toFixed(2)}</span>
    </div>
  )
}
