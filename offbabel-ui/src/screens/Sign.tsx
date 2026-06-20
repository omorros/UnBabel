import { ArrowLeft, Check, Hand } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Presence } from "@/components/Presence"
import { levelSequence, type Presence as PresenceState, type SignLevel } from "@/lib/offbabel"

export function Sign({
  presence,
  level,
  levels,
  index,
  detect,
  onSelectLevel,
  onBack,
  onDemoLetter,
}: {
  presence: PresenceState
  level: SignLevel
  levels: SignLevel[]
  index: number
  detect: { label: string; conf: number; stable: boolean }
  onSelectLevel: (lv: SignLevel) => void
  onBack: () => void
  onDemoLetter: (letter: string) => void
}) {
  const seq = levelSequence(level)
  const done = index >= seq.length
  const target = done ? "✓" : seq[index]
  const uniqueLetters = Array.from(new Set(seq))
  const pct = Math.round((detect.conf || 0) * 100)
  const good = detect.stable || detect.conf >= 0.6
  const isWord = level.kind === "words"

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col py-6">
      <div className="flex items-center justify-between">
        <Button variant="ghost" className="gap-1.5" onClick={onBack}>
          <ArrowLeft className="size-5" /> Back
        </Button>
        <Presence state={done ? "celebrate" : presence} size={84} />
        <div className="w-[84px]" aria-hidden />
      </div>

      {/* Skill levels */}
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <span className="text-sm text-muted-foreground">Level</span>
        {levels.map((lv) => (
          <button
            key={lv.id}
            onClick={() => onSelectLevel(lv)}
            className={
              "rounded-full px-3 py-1 text-sm font-medium transition " +
              (lv.id === level.id
                ? "bg-foreground text-background"
                : "bg-muted text-muted-foreground hover:text-foreground")
            }
          >
            {lv.title}
          </button>
        ))}
      </div>

      <div className="mt-3 grid flex-1 gap-5 md:grid-cols-2">
        {/* Target + progress */}
        <div className="flex flex-col rounded-2xl border bg-card p-7">
          <div className="text-muted-foreground">{isWord ? "Spell this word" : "Sign each letter"}</div>
          <div className="mt-4 flex flex-wrap gap-2">
            {seq.map((ch, i) => (
              <div
                key={i}
                className={
                  "grid h-14 w-12 place-items-center rounded-xl border-2 text-2xl font-bold " +
                  (i < index
                    ? "border-success bg-success/10 text-success"
                    : i === index
                      ? "border-info text-foreground"
                      : "border-border text-muted-foreground")
                }
              >
                {ch}
              </div>
            ))}
          </div>
          <div className="mt-auto pt-6 text-center">
            <div className="text-muted-foreground">{done ? "Complete" : "Now sign"}</div>
            <div
              className="font-bold leading-none"
              style={{ fontSize: "clamp(72px, 18vw, 140px)", color: done ? "var(--success)" : undefined }}
            >
              {target}
            </div>
          </div>
        </div>

        {/* Detection panel */}
        <div className="flex flex-col rounded-2xl border bg-card p-7">
          <div className="text-muted-foreground">Camera (on device)</div>
          <div className="mt-4 grid flex-1 place-items-center rounded-xl border border-dashed bg-muted/40">
            <div className="flex flex-col items-center gap-2 py-10 text-center">
              <Hand className="size-10 text-muted-foreground" />
              <div className="text-7xl font-bold" style={{ color: good ? "var(--success)" : "var(--foreground)" }}>
                {detect.label}
              </div>
              <div
                className="flex items-center gap-1.5 text-sm font-medium"
                style={{ color: good ? "var(--success)" : "var(--warning)" }}
              >
                {detect.stable ? <Check className="size-4" /> : null}
                {detect.stable ? "Got it" : detect.label === "-" ? "Show your hands" : "Hold steady..."}
              </div>
            </div>
          </div>
          <div className="mt-4">
            <div className="mb-1 flex justify-between text-sm text-muted-foreground">
              <span>Confidence</span>
              <span>{pct}%</span>
            </div>
            <Progress value={pct} className="h-2.5" />
          </div>
        </div>
      </div>

      {/* Demo keys: simulate detections until the live classifier streams them */}
      <div className="mt-5">
        <div className="mb-2 text-sm text-muted-foreground">
          Demo: tap a letter to simulate a recognition (real webcam runs on the Mac)
        </div>
        <div className="flex flex-wrap gap-2">
          {uniqueLetters.map((ch) => (
            <Button
              key={ch}
              variant="outline"
              className="h-12 w-12 text-lg font-bold"
              onClick={() => onDemoLetter(ch)}
            >
              {ch}
            </Button>
          ))}
        </div>
      </div>
    </div>
  )
}
