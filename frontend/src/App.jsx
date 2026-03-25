import { useEffect, useRef, useState } from 'react'
import './App.css'
import { chat, health, uploadFiles } from './api'

function App() {
  const [sessionId, setSessionId] = useState(() => localStorage.getItem('session_id') || '')
  const [files, setFiles] = useState([])
  const [uploadState, setUploadState] = useState({ status: 'idle', message: '' })
  const [messages, setMessages] = useState(() => [
    {
      role: 'assistant',
      content:
        'Upload your project PDFs + CSV/Excel, then ask about status, risks, and budget. I will show which agent handled your question and cite sources.',
    },
  ])
  const [input, setInput] = useState('')
  const [meta, setMeta] = useState({ apiOk: false, apiEnv: '' })
  const [busy, setBusy] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    localStorage.setItem('session_id', sessionId || '')
  }, [sessionId])

  useEffect(() => {
    health()
      .then((d) => setMeta({ apiOk: true, apiEnv: d.env || '' }))
      .catch(() => setMeta({ apiOk: false, apiEnv: '' }))
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, busy])

  const canUpload = files.length > 0 && !busy
  const canSend = input.trim().length > 0 && !busy

  async function onUpload() {
    setUploadState({ status: 'uploading', message: 'Uploading & indexing…' })
    setBusy(true)
    try {
      const res = await uploadFiles({ files, sessionId: sessionId || null })
      setSessionId(res.session_id)
      setUploadState({
        status: 'done',
        message: `Indexed ${res.ingested_files.length} file(s) • docs: ${res.documents_indexed} • tables: ${res.tables_loaded}`,
      })
      setMessages((m) => [
        ...m,
        { role: 'system', content: `Upload complete for session ${res.session_id}.` },
      ])
      setFiles([])
    } catch (e) {
      setUploadState({ status: 'error', message: e?.message || String(e) })
    } finally {
      setBusy(false)
    }
  }

  async function onSend() {
    const text = input.trim()
    if (!text) return
    setInput('')
    setBusy(true)
    setMessages((m) => [...m, { role: 'user', content: text }])
    try {
      const res = await chat({ message: text, sessionId: sessionId || null })
      setSessionId(res.session_id)
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          content: res.answer,
          agent: res.agent,
          traceId: res.trace_id,
          latencyMs: res.latency_ms,
          sources: res.sources || [],
        },
      ])
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: `Request failed: ${e?.message || String(e)}` },
      ])
    } finally {
      setBusy(false)
    }
  }

  function onKeyDown(e) {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) onSend()
  }

  return (
    <div className="layout">
      <header className="topbar">
        <div className="brand">
          <div className="dot" />
          <div>
            <div className="title">Project Intelligence Assistant</div>
            <div className="subtitle">
              Backend: {meta.apiOk ? `online (${meta.apiEnv || 'env'})` : 'offline'} • Session:{' '}
              <code>{sessionId ? sessionId.slice(0, 8) : 'not set'}</code>
            </div>
          </div>
        </div>
        <div className="hint">Send with <kbd>Ctrl</kbd>+<kbd>Enter</kbd></div>
      </header>

      <main className="main">
        <section className="panel">
          <h2>Documents</h2>
          <p className="muted">Upload PDFs + CSV/Excel. Indexing is per session.</p>

          <div className="card">
            <label className="label">Session ID (optional)</label>
            <input
              value={sessionId}
              onChange={(e) => setSessionId(e.target.value)}
              placeholder="Leave blank to auto-create"
            />

            <label className="label">Files</label>
            <input
              type="file"
              multiple
              accept=".pdf,.csv,.xlsx,.xls"
              onChange={(e) => setFiles(Array.from(e.target.files || []))}
            />
            {files.length > 0 && (
              <ul className="fileList">
                {files.map((f) => (
                  <li key={f.name}>
                    <span className="mono">{f.name}</span>
                    <span className="muted">{Math.round(f.size / 1024)} KB</span>
                  </li>
                ))}
              </ul>
            )}

            <button disabled={!canUpload} onClick={onUpload}>
              {uploadState.status === 'uploading' ? 'Indexing…' : 'Upload & Index'}
            </button>
            {uploadState.message && (
              <div className={`status ${uploadState.status}`}>{uploadState.message}</div>
            )}
          </div>

          <div className="card">
            <h3>Try questions</h3>
            <ul className="muted">
              <li>“What are the top 3 schedule risks and mitigations?”</li>
              <li>“What is the current total budget vs forecast variance?”</li>
              <li>“Based on the latest status report, what is the critical path issue?”</li>
            </ul>
          </div>
        </section>

        <section className="chat">
          <div className="messages">
            {messages.map((m, idx) => (
              <div key={idx} className={`msg ${m.role}`}>
                <div className="msgHeader">
                  <span className="role">{m.role}</span>
                  {m.agent && (
                    <span className="pill">
                      agent: <span className="mono">{m.agent}</span>
                    </span>
                  )}
                  {m.latencyMs != null && <span className="pill">{m.latencyMs}ms</span>}
                  {m.traceId && (
                    <span className="pill">
                      trace: <span className="mono">{m.traceId.slice(0, 8)}</span>
                    </span>
                  )}
                </div>
                <div className="msgBody">{m.content}</div>
                {m.sources?.length > 0 && (
                  <details className="sources">
                    <summary>Sources ({m.sources.length})</summary>
                    <ul>
                      {m.sources.map((s) => (
                        <li key={s.source_id}>
                          <div className="srcTop">
                            <span className="mono">[{s.source_id}]</span>
                            <span className="mono">{s.filename}</span>
                            {s.page != null && <span className="muted">p.{s.page}</span>}
                            {s.sheet && <span className="muted">sheet: {s.sheet}</span>}
                          </div>
                          <div className="srcExcerpt">{s.excerpt}</div>
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
            ))}
            {busy && <div className="msg assistant"><div className="msgBody">Thinking…</div></div>}
            <div ref={bottomRef} />
          </div>

          <div className="composer">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Ask a question about project status, risks, and budgets…"
              rows={3}
            />
            <button disabled={!canSend} onClick={onSend}>
              Send
            </button>
          </div>
        </section>
      </main>
    </div>
  )
}

export default App
