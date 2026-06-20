import { useCallback, useRef, useState } from "react"
import { TopBar } from "@/components/TopBar"
import { Home } from "@/screens/Home"
import { Speak } from "@/screens/Speak"
import { Sign } from "@/screens/Sign"
import { Progress } from "@/screens/Progress"
import { useSocket } from "@/hooks/useSocket"
import {
  DEMO_WORD,
  SAMPLE_REVIEW,
  type Bubble,
  type Correction,
  type Lang,
  type Presence,
  type ReviewItem,
  type Screen,
} from "@/lib/offbabel"

// Canned content for preview mode (no backend), so the flow is demoable.
const REPLY: Record<Lang, string> = {
  es: "¡Muy bien! ¿Qué te gusta hacer los fines de semana?",
  en: "Nice! What do you like to do on the weekend?",
  cs: "Skvělé! Co rád děláš o víkendu?",
}
const SAMPLE_CORR: Record<Lang, Correction> = {
  es: { wrong: "yo tiene", right: "yo tengo", note: "First person of 'tener' is 'tengo'." },
  en: { wrong: "he go", right: "he goes", note: "Third person adds -s." },
  cs: { wrong: "já mít", right: "já mám", note: "Present tense of 'mít' is 'mám'." },
}

function mapEmote(emotion: string): Presence {
  if (emotion === "listening") return "listening"
  if (emotion === "speaking") return "speaking"
  if (emotion === "happy") return "celebrate"
  return "idle"
}

export default function App() {
  const [screen, setScreen] = useState<Screen>("home")
  const [lang, setLang] = useState<Lang>("es")
  const [presence, setPresence] = useState<Presence>("idle")
  const [transcript, setTranscript] = useState<Bubble[]>([])
  const [correction, setCorrection] = useState<Correction | null>(null)
  const [index, setIndex] = useState(0)
  const idxRef = useRef(0)
  const [detect, setDetect] = useState({ label: "-", conf: 0, stable: false })
  const [stats, setStats] = useState({ words: 0, signs: 0 })
  const [review, setReview] = useState<ReviewItem[]>([])

  const applyDetection = useCallback((label: string, conf: number, stable: boolean) => {
    setDetect({ label, conf, stable })
    if (!(stable && label && label !== "_")) return
    if (label !== DEMO_WORD[idxRef.current]) return
    const next = idxRef.current + 1
    idxRef.current = next
    setIndex(next)
    setStats((s) => ({ ...s, signs: s.signs + 1 }))
    if (next >= DEMO_WORD.length) setPresence("celebrate")
  }, [])

  const onMessage = useCallback(
    (m: any) => {
      switch (m.type) {
        case "status":
          if (m.stats) setStats(m.stats)
          break
        case "transcript":
          setTranscript((t) => [...t, { role: m.role, text: m.text }])
          break
        case "correction":
          setCorrection({ wrong: m.wrong, right: m.right, note: m.note })
          break
        case "emote":
          setPresence(mapEmote(m.emotion))
          break
        case "sign_detect":
          applyDetection(m.label, m.confidence ?? m.conf ?? 0, !!m.stable)
          break
        case "progress":
          if (m.stats) setStats(m.stats)
          if (m.review) setReview(m.review)
          break
      }
    },
    [applyDetection]
  )

  const { send, connected, status } = useSocket(onMessage)

  const go = useCallback(
    (s: Screen) => {
      setScreen(s)
      setCorrection(null)
      if (s === "sign") {
        idxRef.current = 0
        setIndex(0)
        setDetect({ label: "-", conf: 0, stable: false })
        setPresence("watching")
      } else {
        setPresence("idle")
      }
      if (connected) {
        send({ type: "set_mode", mode: s })
        if (s === "progress") send({ type: "get_progress" })
      } else if (s === "progress") {
        setReview(SAMPLE_REVIEW)
        setStats((st) => (st.words || st.signs ? st : { words: 12, signs: 8 }))
      }
    },
    [connected, send]
  )

  const speakSend = useCallback(
    (text: string) => {
      if (connected) {
        send({ type: "speak_text", text, language: lang })
        return
      }
      setTranscript((t) => [...t, { role: "user", text }])
      setPresence("speaking")
      setStats((s) => ({ ...s, words: s.words + 1 }))
      window.setTimeout(() => {
        setTranscript((t) => [...t, { role: "tutor", text: REPLY[lang] }])
        setCorrection(SAMPLE_CORR[lang])
        setPresence("idle")
      }, 700)
    },
    [connected, send, lang]
  )

  const ptt = useCallback(
    (active: boolean) => {
      if (connected) {
        send({ type: active ? "speak_ptt_start" : "speak_ptt_stop" })
      }
      setPresence(active ? "listening" : "idle")
    },
    [connected, send]
  )

  const signDemo = useCallback(
    (letter: string) => {
      if (connected) {
        send({ type: "sign_demo_letter", label: letter })
        return
      }
      applyDetection(letter, 0.98, true)
    },
    [connected, send, applyDetection]
  )

  return (
    <div className="flex min-h-screen flex-col">
      <TopBar lang={lang} onLang={setLang} />

      <main className="flex flex-1 flex-col px-6">
        {screen === "home" && <Home go={go} />}
        {screen === "speak" && (
          <Speak
            presence={presence}
            transcript={transcript}
            correction={correction}
            onBack={() => go("home")}
            onSend={speakSend}
            onPtt={ptt}
          />
        )}
        {screen === "sign" && (
          <Sign
            presence={presence}
            index={index}
            detect={detect}
            onBack={() => go("home")}
            onDemoLetter={signDemo}
          />
        )}
        {screen === "progress" && (
          <Progress stats={stats} review={review} onBack={() => go("home")} />
        )}
      </main>

      <footer className="border-t bg-card px-6 py-2.5 text-sm text-muted-foreground">
        {status === "connected"
          ? "Connected to on-device engine"
          : "Preview mode: engine not running (screens and flow still work)"}
        {" · No internet"}
      </footer>
    </div>
  )
}
