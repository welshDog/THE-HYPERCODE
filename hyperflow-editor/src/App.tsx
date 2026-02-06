import React, { useEffect, useRef, useState } from "react"
import * as monaco from "monaco-editor"
import { setupHypercodeLanguage, applyErrorsToModel } from './hypercodeLang'
import { parse as parseHC } from './hcParser'
import { createMemory, setupQueueFlush } from './memoryClient'
import HyperLayout from './components/HyperLayout'

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
      theme: "vs-dark", // Changed to vs-dark for better contrast with new theme
      automaticLayout: true,
      minimap: { enabled: false },
      scrollBeyondLastLine: false,
      fontSize: 14,
      fontFamily: "'Courier New', monospace",
      padding: { top: 16, bottom: 16 }
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
    <HyperLayout>
      <div style={{ display: "grid", gridTemplateColumns: focusMode ? "1fr 0px" : "1fr 360px", height: "100%", transition: 'grid-template-columns 200ms ease' }}>
        <div className="hc-panel" style={{ margin: '10px', display: 'flex', flexDirection: 'column' }}>
          <div ref={el} style={{ flex: 1 }} />
        </div>
        
        <div className="hc-panel" style={{ margin: '10px 10px 10px 0', borderLeft: "1px solid var(--color-secondary)", padding: 12, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <div style={{ marginBottom: 8, fontWeight: 600, color: 'var(--color-primary)', textTransform: 'uppercase', letterSpacing: '1px' }}>/ TERMINAL OUTPUT</div>
          <pre style={{ whiteSpace: "pre-wrap", flex: 1, overflow: 'auto', fontFamily: 'var(--font-mono)', fontSize: '12px', color: '#fff' }}>{out || "> Ready..."}</pre>
          <div style={{ marginTop: 12, color: "rgba(255,255,255,0.5)", fontSize: '11px' }}>Ctrl+Enter to execute</div>
          
          <div style={{ borderTop: '1px solid rgba(6,182,212,0.2)', margin: '10px 0', paddingTop: 10 }}>
             <VoiceButton onTranscript={(t, c) => setTranscripts((prev) => [{ t, c }, ...prev])} />
          </div>

          <div aria-live="polite" style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ marginBottom: 6, fontWeight: 600, color: 'var(--color-secondary)' }}>/ TRANSCRIPT</div>
            <ul style={{ maxHeight: 100, overflow: 'auto', listStyle: 'none', padding: 0 }}>
              {transcripts.map((x, i) => (
                <li key={i} style={{ marginBottom: 4, fontSize: '12px' }}>
                  <span style={{ color: '#00ff88' }}>&gt; {x.t}</span>
                  <span style={{ marginLeft: 8, color: "#666" }}>({Math.round((x.c || 1) * 100)}%)</span>
                </li>
              ))}
            </ul>
            <div style={{ marginTop: 12, flex: 1, display: 'flex', flexDirection: 'column' }}>
              <div style={{ fontWeight: 600, color: 'var(--color-secondary)' }}>/ HISTORY</div>
              <ul style={{ flex: 1, overflow: 'auto', listStyle: 'none', padding: 0 }}>
                {(JSON.parse((localStorage.getItem('hc_history')||'[]')) as any[]).map((h,i)=> (
                  <li key={i} style={{ marginBottom: 4, fontSize: '11px', borderBottom: '1px dashed rgba(255,255,255,0.1)', paddingBottom: 2 }}>
                    <span style={{ color: '#888' }}>{new Date(h.ts).toLocaleTimeString()}</span> <span style={{ color: '#aaa' }}>{String(h.out).slice(0,60)}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
        <StatusBar focusMode={focusMode} setFocusMode={setFocusMode} fontScale={fontScale} />
      </div>
    </HyperLayout>
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
      className={`hc-button ${recording ? 'active' : ''}`}
      style={{ width: '100%' }}
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
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [focusMode])
  return (
    <div style={{ position: 'fixed', bottom: 15, right: 20, display: 'flex', gap: 12, alignItems: 'center', zIndex: 10 }}>
      <button 
        aria-pressed={focusMode} 
        onClick={() => setFocusMode(!focusMode)} 
        className="hc-button"
        style={{ padding: '4px 10px', fontSize: '10px' }}
      >
        {focusMode ? 'EXIT FOCUS' : 'FOCUS MODE'}
      </button>
      <span style={{ fontSize: 12, color: 'var(--color-secondary)', fontFamily: 'var(--font-mono)' }}>MAG: x{fontScale.toFixed(2)}</span>
    </div>
  )
}
