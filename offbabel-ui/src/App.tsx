import { useCallback, useRef, useState } from "react"
import { TopBar } from "@/components/TopBar"
import { Home } from "@/screens/Home"
import { Speak } from "@/screens/Speak"
import { Sign } from "@/screens/Sign"
import { Progress } from "@/screens/Progress"
import { Summary } from "@/screens/Summary"
import { useSocket } from "@/hooks/useSocket"
import {
  EMPTY_SUMMARY,
  levelSequence,
  SCENARIOS,
  SIGN_LEVELS,
  type Bubble,
  type Correction,
  type Lang,
  type Presence,
  type ReviewItem,
  type Scenario,
  type Screen,
  type SignLevel,
} from "@/lib/offbabel"

// Canned content for preview mode (no backend), so the flow is demoable.
const REPLY: Record<Lang, string> = {
  es: "¡Muy bien! ¿Y cómo te llamas?",
  en: "Nice! And what is your name?",
  cs: "Skvělé! A jak se jmenuješ?",
}
const LESSON_DONE: Record<Lang, string> = {
  es: "¡Lo lograste! Has practicado todo el tema.",
  en: "You did it! You practiced the whole lesson.",
  cs: "Dokázal jsi to! Procvičil jsi celé téma.",
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

  // Speak lesson state
  const [scenario, setScenario] = useState<Scenario>(SCENARIOS[0])
  const [hits, setHits] = useState(0)
  const hitsRef = useRef(0)
  const [transcript, setTranscript] = useState<Bubble[]>([])
  const [correction, setCorrection] = useState<Correction | null>(null)
  const [mistakes, setMistakes] = useState<Correction[]>([]) // accumulated for the review sheet

  // Sign lesson state
  const [signLevel, setSignLevel] = useState<SignLevel>(SIGN_LEVELS[0])
  const seqRef = useRef<string[]>(levelSequence(SIGN_LEVELS[0]))
  const [index, setIndex] = useState(0)
  const idxRef = useRef(0)
  const [detect, setDetect] = useState({ label: "-", conf: 0, stable: false })

  const [stats, setStats] = useState({ words: 0, signs: 0 })
  const [review, setReview] = useState<ReviewItem[]>([])
  const [summary, setSummary] = useState(EMPTY_SUMMARY)

  const applyDetection = useCallback((label: string, conf: number, stable: boolean) => {
    setDetect({ label, conf, stable })
    if (!(stable && label && label !== "_")) return
    const seq = seqRef.current
    if (label !== seq[idxRef.current]) return
    const next = idxRef.current + 1
    idxRef.current = next
    setIndex(next)
    setStats((s) => ({ ...s, signs: s.signs + 1 }))
    if (next >= seq.length) setPresence("celebrate")
  }, [])

  const onMessage = useCallback(
    (m: any) => {
      switch (m.type) {
        case "status":
          if (m.stats) setStats(m.stats)
          if (m.summary) setSummary(m.summary)
          break
        case "summary":
          if (m.summary) setSummary(m.summary)
          break
        case "targets":
          hitsRef.current = m.count ?? 0
          setHits(m.count ?? 0)
          break
        case "transcript":
          setTranscript((t) => [...t, { role: m.role, text: m.text, translation: m.translation }])
          break
        case "correction": {
          const c = { wrong: m.wrong, right: m.right, note: m.note }
          setCorrection(c)
          setMistakes((arr) => [...arr, c])
          break
        }
        case "emote":
          setPresence(mapEmote(m.emotion))
          break
        case "sign_detect":
          applyDetection(m.label, m.confidence ?? m.conf ?? 0, !!m.stable)
          break
        case "progress":
          if (m.stats) setStats(m.stats)
          if (m.summary) setSummary(m.summary)
          if (m.review) setReview(m.review)
          break
      }
    },
    [applyDetection]
  )

  const { send, connected, status } = useSocket(onMessage)

  const startSpeak = useCallback(
    (scn: Scenario) => {
      setScenario(scn)
      hitsRef.current = 0
      setHits(0)
      setTranscript([])
      setCorrection(null)
      setMistakes([])
      setPresence("idle")
      setScreen("speak")
      // Reachy opens the conversation server-side (the greeting arrives as a tutor transcript).
      if (connected)
        send({ type: "set_mode", mode: "speak", scenario: scn.id, level: scn.level, language: lang })
    },
    [connected, send, lang]
  )

  const startSign = useCallback(
    (lv: SignLevel) => {
      setSignLevel(lv)
      seqRef.current = levelSequence(lv)
      idxRef.current = 0
      setIndex(0)
      setDetect({ label: "-", conf: 0, stable: false })
      setPresence("watching")
      setScreen("sign")
      if (connected) send({ type: "set_mode", mode: "sign", level: lv.id })
    },
    [connected, send]
  )

  const go = useCallback(
    (s: Screen) => {
      if (s === "speak") return startSpeak(scenario)
      if (s === "sign") return startSign(signLevel)
      setScreen(s)
      setPresence("idle")
      if (connected) {
        send({ type: "set_mode", mode: s })
        if (s === "progress" || s === "summary") send({ type: "get_progress" })
      }
    },
    [connected, send, scenario, signLevel, startSpeak, startSign]
  )

  const speakSend = useCallback(
    (text: string) => {
      if (connected) {
        send({ type: "speak_text", text, language: lang, scenario: scenario.id })
        return
      }
      const nh = Math.min(hitsRef.current + 1, scenario.targets.length)
      hitsRef.current = nh
      setHits(nh)
      setTranscript((t) => [...t, { role: "user", text }])
      setPresence("speaking")
      setStats((s) => ({ ...s, words: s.words + 1 }))
      const complete = nh >= scenario.targets.length
      window.setTimeout(() => {
        setTranscript((t) => [...t, { role: "tutor", text: complete ? LESSON_DONE[lang] : REPLY[lang] }])
        if (complete) {
          setCorrection(null)
        } else {
          setCorrection(SAMPLE_CORR[lang])
          setMistakes((arr) => [...arr, SAMPLE_CORR[lang]])
        }
        setPresence(complete ? "celebrate" : "idle")
      }, 700)
    },
    [connected, send, lang, scenario]
  )

  const converse = useCallback(
    (activeConv: boolean) => {
      // Hands-free: begins/stops the mic+VAD listening loop (wired on the Mac).
      if (connected) send({ type: activeConv ? "conversation_start" : "conversation_stop" })
      setPresence(activeConv ? "listening" : "idle")
    },
    [connected, send]
  )

  const speakHelp = useCallback(() => {
    if (connected) {
      send({ type: "speak_help" })
      return
    }
    setPresence("speaking")
    window.setTimeout(() => {
      setTranscript((t) => [...t, { role: "tutor", text: "Let me say that again, more simply." }])
      setPresence("idle")
    }, 500)
  }, [connected, send])

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
    <div className="flex h-screen flex-col overflow-hidden print:h-auto print:overflow-visible">
      <TopBar />

      <main className="flex min-h-0 flex-1 flex-col overflow-y-auto px-6 print:overflow-visible">
        {screen === "home" && (
          <Home
            lang={lang}
            onLang={setLang}
            onSpeak={() => startSpeak(scenario)}
            onSign={() => startSign(signLevel)}
            onProgress={() => go("progress")}
          />
        )}
        {screen === "speak" && (
          <Speak
            presence={presence}
            lang={lang}
            onLang={setLang}
            scenario={scenario}
            scenarios={SCENARIOS}
            hits={hits}
            transcript={transcript}
            correction={correction}
            onSelectScenario={startSpeak}
            onBack={() => go("home")}
            onSend={speakSend}
            onConverse={converse}
            onHelp={speakHelp}
          />
        )}
        {screen === "sign" && (
          <Sign
            presence={presence}
            level={signLevel}
            levels={SIGN_LEVELS}
            index={index}
            detect={detect}
            onSelectLevel={startSign}
            onBack={() => go("home")}
            onDemoLetter={signDemo}
          />
        )}
        {screen === "progress" && (
          <Progress
            stats={stats}
            review={review}
            summary={summary}
            onSummary={() => go("summary")}
            onBack={() => go("home")}
          />
        )}
        {screen === "summary" && (
          <Summary mistakes={mistakes} review={review} summary={summary} onBack={() => go("home")} />
        )}
      </main>

      <footer className="border-t bg-card px-6 py-2.5 text-sm text-muted-foreground print:hidden">
        {status === "connected"
          ? "Connected to on-device engine"
          : "Preview mode: engine not running (screens and flow still work)"}
        {" · No internet"}
      </footer>
    </div>
  )
}
