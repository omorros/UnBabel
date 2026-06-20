import { ArrowLeft, Download } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { Correction, LearnSummary, ReviewItem } from "@/lib/offbabel"

export function Summary({
  mistakes,
  review,
  summary,
  insight,
  onBack,
}: {
  mistakes: Correction[]
  review: ReviewItem[]
  summary: LearnSummary
  insight?: string
  onBack: () => void
}) {
  const date = new Date().toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  })

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col overflow-y-auto py-6 print:overflow-visible">
      <div className="flex items-center justify-between print:hidden">
        <Button variant="ghost" className="gap-1.5" onClick={onBack}>
          <ArrowLeft className="size-5" /> Back
        </Button>
        <Button className="gap-1.5" onClick={() => window.print()}>
          <Download className="size-4" /> Save as PDF
        </Button>
      </div>

      {/* The printable sheet */}
      <div className="mt-4 rounded-2xl border bg-card p-6 print:mt-0 print:border-0 print:p-0 print:shadow-none">
        <div className="flex items-center gap-3">
          <img src="/mascot.png" alt="" className="h-12 w-auto select-none" />
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Your practice summary</h1>
            <p className="text-sm text-muted-foreground">{date} · OffBabel</p>
          </div>
        </div>

        <div className="mt-5 flex flex-wrap gap-6 text-sm">
          <span>
            <b className="text-lg">{summary.streak}</b> day streak
          </span>
          <span>
            <b className="text-lg">{summary.masterySpeak}%</b> speaking mastery
          </span>
          <span>
            <b className="text-lg">{summary.masterySign}%</b> signing mastery
          </span>
        </div>

        {insight && (
          <div className="mt-5 rounded-xl border border-info/40 bg-info/5 px-4 py-3 text-info-foreground">
            <span className="font-semibold text-info">What to focus on: </span>
            <span className="text-foreground">{insight}</span>
          </div>
        )}

        <h2 className="mt-6 text-lg font-semibold">Corrections this session</h2>
        {mistakes.length === 0 ? (
          <p className="mt-1 text-muted-foreground">No mistakes recorded this session, nice.</p>
        ) : (
          <ul className="mt-2 flex flex-col gap-2">
            {mistakes.map((m, i) => (
              <li key={i} className="rounded-xl border px-4 py-2.5">
                <div>
                  <span className="text-warning line-through decoration-warning/60">{m.wrong}</span>
                  <span className="mx-2 text-muted-foreground">{"->"}</span>
                  <span className="font-semibold text-success">{m.right}</span>
                </div>
                {m.note && <div className="mt-0.5 text-sm text-muted-foreground">{m.note}</div>}
              </li>
            ))}
          </ul>
        )}

        <h2 className="mt-6 text-lg font-semibold">Keep practicing</h2>
        {review.length === 0 ? (
          <p className="mt-1 text-muted-foreground">Nothing flagged for review yet.</p>
        ) : (
          <ul className="mt-2 flex flex-col gap-1.5">
            {review.map((it, i) => (
              <li key={i} className="flex items-center justify-between rounded-xl border px-4 py-2">
                <span>
                  {it.value}{" "}
                  <small className="text-muted-foreground">
                    ({it.type}, {it.language})
                  </small>
                </span>
                <span className="text-sm font-medium text-warning">missed {it.miss_count}x</span>
              </li>
            ))}
          </ul>
        )}

        <p className="mt-6 text-sm text-muted-foreground">
          Practiced on-device with OffBabel. Your learning data never left this device.
        </p>
      </div>
    </div>
  )
}
