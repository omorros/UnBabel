import { useState, type FormEvent } from "react"
import { ArrowLeft, ArrowRight, Ear, HelpCircle, Mic, Send } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Presence } from "@/components/Presence"
import { LanguageToggle } from "@/components/LanguageToggle"
import { LANGS, type Bubble, type Correction, type Lang, type Presence as PresenceState, type Scenario } from "@/lib/offbabel"

export function Speak({
  presence,
  lang,
  onLang,
  scenario,
  scenarios,
  hits,
  transcript,
  correction,
  onSelectScenario,
  onBack,
  onSend,
  onConverse,
  onHelp,
}: {
  presence: PresenceState
  lang: Lang
  onLang: (l: Lang) => void
  scenario: Scenario
  scenarios: Scenario[]
  hits: number
  transcript: Bubble[]
  correction: Correction | null
  onSelectScenario: (s: Scenario) => void
  onBack: () => void
  onSend: (text: string) => void
  onConverse: (active: boolean) => void
  onHelp: () => void
}) {
  const [text, setText] = useState("")
  const [active, setActive] = useState(false)
  const total = scenario.targets.length
  const langLabel = LANGS.find((l) => l.value === lang)?.label ?? "your language"

  // Subtitle view: only the current exchange, so nothing scrolls and you watch Reachy.
  const lastTutor = [...transcript].reverse().find((b) => b.role === "tutor")
  const lastUser = [...transcript].reverse().find((b) => b.role === "user")

  const toggle = () => {
    const next = !active
    setActive(next)
    onConverse(next)
  }
  const submit = (e: FormEvent) => {
    e.preventDefault()
    const t = text.trim()
    if (!t) return
    onSend(t)
    setText("")
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col py-5">
      <div className="flex items-center justify-between">
        <Button variant="ghost" className="gap-1.5" onClick={onBack}>
          <ArrowLeft className="size-5" /> Back
        </Button>
        <LanguageToggle value={lang} onChange={onLang} />
      </div>

      {/* Reachy is the focus */}
      <div className="mt-1 flex flex-col items-center gap-2">
        <Presence state={presence} size={108} />
        <div className="flex items-center gap-2">
          <span className="text-base font-semibold">{scenario.title}</span>
          <span className="rounded-full bg-info/10 px-2 py-0.5 text-xs font-semibold text-info">
            {scenario.level}
          </span>
        </div>
        <div className="flex items-center gap-1.5" title={`${hits} of ${total} goals`}>
          {scenario.targets.map((t, i) => (
            <span
              key={t}
              className={"size-2.5 rounded-full transition " + (i < hits ? "bg-success" : "bg-border")}
            />
          ))}
          <span className="ml-1 text-xs text-muted-foreground">{hits}/{total} goals</span>
        </div>
      </div>

      {/* Current exchange as subtitles (no scroll) */}
      <div className="mt-4 flex flex-1 flex-col items-center justify-center gap-5 rounded-2xl border bg-card px-6 py-6 text-center">
        {!lastTutor ? (
          <div className="max-w-sm text-muted-foreground">
            <p className="text-lg font-medium text-foreground">Talking to Reachy</p>
            <p className="mt-1">
              Tap Start and just talk. Reachy replies in {langLabel}, corrects you gently, and
              keeps the conversation going. The screen only shows captions.
            </p>
          </div>
        ) : (
          <>
            {lastUser && (
              <div className="max-w-lg text-sm text-muted-foreground">You said: "{lastUser.text}"</div>
            )}
            <div className="max-w-xl">
              <div className="text-3xl font-semibold leading-tight">{lastTutor.text}</div>
              {lastTutor.translation && (
                <div className="mt-2 text-lg text-muted-foreground">{lastTutor.translation}</div>
              )}
            </div>
            {correction && (
              <div className="flex flex-wrap items-center justify-center gap-2 rounded-xl border border-warning/40 bg-warning/5 px-4 py-2">
                <span className="text-warning line-through decoration-warning/60">{correction.wrong}</span>
                <ArrowRight className="size-4 text-muted-foreground" />
                <span className="font-semibold text-success">{correction.right}</span>
              </div>
            )}
          </>
        )}
      </div>

      {/* Controls: one hands-free action, everything else quiet */}
      <div className="mt-4 flex flex-col gap-3">
        <Button
          className={"h-16 gap-2 text-lg " + (active ? "bg-info text-info-foreground hover:bg-info/90" : "")}
          onClick={toggle}
        >
          {active ? <Ear className="size-6" /> : <Mic className="size-6" />}
          {active ? "Listening, tap to pause" : "Start conversation"}
        </Button>
        <div className="flex items-center gap-2">
          <form onSubmit={submit} className="flex flex-1 gap-2">
            <Input
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="...or type instead"
              className="h-11 text-base"
              aria-label="Type a message"
            />
            <Button type="submit" variant="secondary" className="h-11 gap-1.5">
              <Send className="size-4" /> Send
            </Button>
          </form>
          <Button
            variant="ghost"
            size="sm"
            className="h-11 gap-1.5 whitespace-nowrap text-muted-foreground"
            onClick={onHelp}
          >
            <HelpCircle className="size-4" /> Help
          </Button>
        </div>
        <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
          <span>Lesson</span>
          {scenarios.map((s) => (
            <button
              key={s.id}
              onClick={() => onSelectScenario(s)}
              className={
                "rounded-full px-2 py-0.5 font-medium transition " +
                (s.id === scenario.id ? "bg-foreground text-background" : "hover:text-foreground")
              }
            >
              {s.level}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
