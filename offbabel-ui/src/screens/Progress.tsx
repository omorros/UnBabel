import { ArrowLeft, FileText, Flame, Mic, Hand, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Progress as Bar } from "@/components/ui/progress"
import type { LearnSummary, ReviewItem } from "@/lib/offbabel"

export function Progress({
  review,
  summary,
  onSummary,
  onBack,
}: {
  stats: { words: number; signs: number }
  review: ReviewItem[]
  summary: LearnSummary
  onSummary: () => void
  onBack: () => void
}) {
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col py-6">
      <div className="flex items-center justify-between">
        <Button variant="ghost" className="gap-1.5" onClick={onBack}>
          <ArrowLeft className="size-5" /> Back
        </Button>
        <Button variant="secondary" className="gap-1.5" onClick={onSummary}>
          <FileText className="size-4" /> Review sheet
        </Button>
      </div>

      <h1 className="mt-4 text-3xl font-semibold tracking-tight">Progress</h1>

      {/* streak + due */}
      <div className="mt-5 grid grid-cols-2 gap-4">
        <div className="flex items-center gap-3 rounded-2xl border bg-card p-5">
          <span className="grid size-12 place-items-center rounded-xl bg-warning/10 text-warning">
            <Flame className="size-6" />
          </span>
          <div>
            <div className="text-3xl font-semibold">{summary.streak}</div>
            <div className="text-muted-foreground">day streak</div>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-2xl border bg-card p-5">
          <span className="grid size-12 place-items-center rounded-xl bg-info/10 text-info">
            <RotateCcw className="size-6" />
          </span>
          <div>
            <div className="text-3xl font-semibold">{summary.dueToday}</div>
            <div className="text-muted-foreground">due to review</div>
          </div>
        </div>
      </div>

      {/* mastery bars */}
      <h2 className="mt-8 text-xl font-semibold">Mastery</h2>
      <div className="mt-3 flex flex-col gap-4">
        <MasteryBar Icon={Mic} accent="var(--info)" label="Speaking" pct={summary.masterySpeak} />
        <MasteryBar Icon={Hand} accent="var(--success)" label="Signing" pct={summary.masterySign} />
      </div>

      {/* needs review */}
      <h2 className="mt-8 text-xl font-semibold">Needs review</h2>
      <p className="mt-1 text-muted-foreground">
        What you have struggled with most, kept on this device.
      </p>
      <ul className="mt-4 flex flex-col gap-2">
        {review.length === 0 ? (
          <li className="rounded-xl border bg-card px-4 py-4 text-muted-foreground">
            Nothing to review yet. Go practice!
          </li>
        ) : (
          review.map((it, i) => (
            <li
              key={i}
              className="flex items-center justify-between rounded-xl border bg-card px-4 py-3"
            >
              <span>
                <span className="text-lg font-medium">{it.value}</span>{" "}
                <span className="text-sm text-muted-foreground">
                  ({it.type}, {it.language})
                </span>
              </span>
              <span className="rounded-full bg-warning/10 px-2.5 py-1 text-sm font-medium text-warning">
                missed {it.miss_count}x
              </span>
            </li>
          ))
        )}
      </ul>
    </div>
  )
}

function MasteryBar({
  Icon,
  accent,
  label,
  pct,
}: {
  Icon: typeof Mic
  accent: string
  label: string
  pct: number
}) {
  return (
    <div className="rounded-2xl border bg-card p-5">
      <div className="mb-2 flex items-center justify-between">
        <span className="flex items-center gap-2 font-medium">
          <Icon className="size-5" style={{ color: accent }} /> {label}
        </span>
        <span className="text-muted-foreground">{pct}% mastered</span>
      </div>
      <Bar value={pct} className="h-2.5" />
    </div>
  )
}
