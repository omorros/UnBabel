import { useState, type FormEvent } from "react"
import { ArrowLeft, ArrowRight, Check, HelpCircle, Mic, Send } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Presence } from "@/components/Presence"
import { LanguageToggle } from "@/components/LanguageToggle"
import type {
  Bubble,
  Correction,
  Lang,
  Presence as PresenceState,
  Scenario,
} from "@/lib/offbabel"

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
  onPtt,
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
  onPtt: (active: boolean) => void
  onHelp: () => void
}) {
  const [text, setText] = useState("")
  const submit = (e: FormEvent) => {
    e.preventDefault()
    const t = text.trim()
    if (!t) return
    onSend(t)
    setText("")
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col py-6">
      <div className="flex items-center justify-between">
        <Button variant="ghost" className="gap-1.5" onClick={onBack}>
          <ArrowLeft className="size-5" /> Back
        </Button>
        <Presence state={presence} size={84} />
        <LanguageToggle value={lang} onChange={onLang} />
      </div>

      {/* Lesson header: scenario + level + lesson switcher */}
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-info/10 px-2.5 py-1 text-sm font-semibold text-info">
          {scenario.level}
        </span>
        <span className="text-lg font-semibold">{scenario.title}</span>
        <div className="ml-auto flex gap-1">
          {scenarios.map((s) => (
            <button
              key={s.id}
              onClick={() => onSelectScenario(s)}
              className={
                "rounded-full px-2.5 py-1 text-xs font-medium transition " +
                (s.id === scenario.id
                  ? "bg-foreground text-background"
                  : "bg-muted text-muted-foreground hover:text-foreground")
              }
            >
              {s.level}
            </button>
          ))}
        </div>
      </div>

      {/* Target checklist: the goals the tutor steers you toward */}
      <div className="mt-3 flex flex-wrap gap-2">
        {scenario.targets.map((t, i) => {
          const done = i < hits
          return (
            <span
              key={t}
              className={
                "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm transition " +
                (done
                  ? "border-success/40 bg-success/10 text-success"
                  : "border-border text-muted-foreground")
              }
            >
              {done ? <Check className="size-3.5" /> : <span className="size-3.5 rounded-full border" />}
              {t}
            </span>
          )
        })}
      </div>

      <div className="mt-3 flex min-h-0 flex-1 flex-col overflow-y-auto rounded-2xl border bg-card p-4">
        {transcript.length === 0 ? (
          <div className="m-auto max-w-sm text-center text-muted-foreground">
            <p className="text-lg font-medium text-foreground">Your turn</p>
            <p className="mt-1">
              Talk to the tutor (or type). It replies in {scenario.level} {""}
              and steers you toward the goals above, correcting gently.
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-2.5">
            {transcript.map((b, i) => (
              <div
                key={i}
                className={
                  b.role === "user"
                    ? "max-w-[78%] self-end rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-primary-foreground"
                    : "max-w-[78%] self-start rounded-2xl rounded-bl-md bg-muted px-4 py-2.5"
                }
              >
                <div>{b.text}</div>
                {b.role === "tutor" && b.translation ? (
                  <div className="mt-1 border-t border-border/60 pt-1 text-sm text-muted-foreground">
                    {b.translation}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </div>

      {correction && (
        <div className="mt-3 flex flex-wrap items-center gap-2 rounded-xl border border-warning/40 bg-warning/5 px-4 py-3">
          <span className="text-warning line-through decoration-warning/60">{correction.wrong}</span>
          <ArrowRight className="size-4 text-muted-foreground" />
          <span className="font-semibold text-success">{correction.right}</span>
          {correction.note && (
            <span className="w-full text-sm text-muted-foreground">{correction.note}</span>
          )}
        </div>
      )}

      <div className="mt-3 flex justify-center">
        <Button variant="ghost" size="sm" className="gap-1.5 text-muted-foreground" onClick={onHelp}>
          <HelpCircle className="size-4" /> I don't understand
        </Button>
      </div>

      <div className="mt-4 flex flex-col gap-3">
        <Button
          className="h-16 gap-2 text-lg"
          onMouseDown={() => onPtt(true)}
          onMouseUp={() => onPtt(false)}
          onMouseLeave={() => onPtt(false)}
        >
          <Mic className="size-6" /> Hold to talk
        </Button>
        <form onSubmit={submit} className="flex gap-2">
          <Input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="...or type here"
            className="h-12 text-base"
            aria-label="Type a message"
          />
          <Button type="submit" variant="secondary" className="h-12 gap-1.5">
            <Send className="size-4" /> Send
          </Button>
        </form>
      </div>
    </div>
  )
}
