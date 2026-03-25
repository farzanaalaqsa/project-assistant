const API_BASE = import.meta.env.VITE_API_BASE || ''

export async function health() {
  const res = await fetch(`${API_BASE}/api/health`)
  if (!res.ok) throw new Error(`health failed: ${res.status}`)
  return res.json()
}

export async function uploadFiles({ files, sessionId }) {
  const fd = new FormData()
  for (const f of files) fd.append('files', f)
  const url = new URL(`${API_BASE}/api/upload`, window.location.origin)
  if (sessionId) url.searchParams.set('session_id', sessionId)
  const res = await fetch(url.toString(), { method: 'POST', body: fd })
  if (!res.ok) {
    let text = await res.text()
    try {
      const data = JSON.parse(text)
      throw new Error(data.detail || text)
    } catch {
      throw new Error(text || `upload failed: ${res.status}`)
    }
  }
  return res.json()
}

export async function chat({ message, sessionId }) {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId }),
  })
  if (!res.ok) {
    let text = await res.text()
    try {
      const data = JSON.parse(text)
      throw new Error(data.detail || text)
    } catch {
      throw new Error(text || `chat failed: ${res.status}`)
    }
  }
  return res.json()
}

