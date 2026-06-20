import { useCallback, useEffect, useRef, useState } from "react"

export type WsStatus = "connecting" | "connected" | "disconnected"

// Connects to the Python backend at ws://<host>/ws (proxied to :8500 in dev).
// The UI does not depend on it: if it never connects, screens still work and
// interactions simulate locally. When it connects, real events flow through onMessage.
export function useSocket(onMessage: (m: any) => void) {
  const ws = useRef<WebSocket | null>(null)
  const onMsg = useRef(onMessage)
  onMsg.current = onMessage
  const [status, setStatus] = useState<WsStatus>("connecting")

  const send = useCallback((msg: object) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(msg))
      return true
    }
    return false
  }, [])

  useEffect(() => {
    let stop = false
    let timer: ReturnType<typeof setTimeout>
    const connect = () => {
      let sock: WebSocket
      try {
        sock = new WebSocket(`ws://${location.host}/ws`)
      } catch {
        setStatus("disconnected")
        return
      }
      ws.current = sock
      sock.onopen = () => setStatus("connected")
      sock.onmessage = (e) => {
        try {
          onMsg.current(JSON.parse(e.data))
        } catch {
          /* ignore malformed */
        }
      }
      sock.onerror = () => {
        try {
          sock.close()
        } catch {
          /* noop */
        }
      }
      sock.onclose = () => {
        setStatus("disconnected")
        if (!stop) timer = setTimeout(connect, 1500)
      }
    }
    connect()
    return () => {
      stop = true
      clearTimeout(timer)
      ws.current?.close()
    }
  }, [])

  return { send, status, connected: status === "connected" }
}
