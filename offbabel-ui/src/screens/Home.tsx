import { ArrowRight, BarChart3, Flame, Hand, Mic, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { LearnSummary } from "@/lib/offbabel"

export function Home({
  summary,
  onSpeak,
  onSign,
  onContinue,
  onProgress,
}: {
  summary: LearnSummary
  onSpeak: () => void
  onSign: () => void
  onContinue: () => void
  onProgress: () => void
}) {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center py-10">
      <img
        src="/mascot.png"
        alt=""
        draggable={false}
        className="mx-auto mb-4 h-36 w-auto select-none"
      />
      <h1 className="text-center text-4xl font-semibold tracking-tight sm:text-5xl">
        One tool, two communities.
      </h1>
      <p className="mx-auto mt-4 max-w-xl text-center text-lg text-muted-foreground">
        Learn a language by speaking, or practice sign language by fingerspelling.
        Everything runs on this device, with no internet.
      </p>

      {/* Today: spaced-repetition status + continue */}
      <div className="mt-8 flex flex-wrap items-center gap-3 rounded-2xl border bg-card p-4">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-warning/10 px-3 py-1.5 font-medium text-warning">
          <Flame className="size-4" /> {summary.streak}-day streak
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-info/10 px-3 py-1.5 font-medium text-info">
          <RotateCcw className="size-4" /> {summary.dueToday} to review today
        </span>
        <Button className="ml-auto h-11 gap-2" onClick={onContinue}>
          Continue learning <ArrowRight className="size-4" />
        </Button>
      </div>

      <div className="mt-5 grid w-full gap-5 sm:grid-cols-2">
        <ModeCard
          onClick={onSpeak}
          Icon={Mic}
          accent="var(--info)"
          title="Speak"
          desc="Hold a conversation and get gently corrected."
        />
        <ModeCard
          onClick={onSign}
          Icon={Hand}
          accent="var(--success)"
          title="Sign"
          desc="Fingerspell BSL to the camera, letter by letter."
        />
      </div>

      <Button variant="ghost" className="mx-auto mt-6 h-12 gap-2 text-base" onClick={onProgress}>
        <BarChart3 className="size-5" />
        View progress
      </Button>
    </div>
  )
}

function ModeCard({
  onClick,
  Icon,
  accent,
  title,
  desc,
}: {
  onClick: () => void
  Icon: typeof Mic
  accent: string
  title: string
  desc: string
}) {
  return (
    <button
      onClick={onClick}
      className="group rounded-2xl border bg-card p-7 text-left transition hover:-translate-y-0.5 hover:border-foreground/20 hover:shadow-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
      style={{ minHeight: 184 }}
    >
      <span
        className="grid size-14 place-items-center rounded-xl"
        style={{ color: accent, background: `color-mix(in oklab, var(--card) 86%, ${accent})` }}
      >
        <Icon className="size-7" strokeWidth={2} />
      </span>
      <div className="mt-6 flex items-center gap-2">
        <span className="text-2xl font-semibold">{title}</span>
        <ArrowRight className="size-5 text-muted-foreground transition group-hover:translate-x-1" />
      </div>
      <p className="mt-1.5 text-muted-foreground">{desc}</p>
    </button>
  )
}
