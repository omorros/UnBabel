import { ArrowLeft, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { ReviewItem } from "@/lib/offbabel"

export function Progress({
  stats,
  review,
  onBack,
}: {
  stats: { words: number; signs: number }
  review: ReviewItem[]
  onBack: () => void
}) {
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col py-6">
      <div className="flex items-center">
        <Button variant="ghost" className="gap-1.5" onClick={onBack}>
          <ArrowLeft className="size-5" /> Back
        </Button>
      </div>

      <h1 className="mt-4 text-3xl font-semibold tracking-tight">Progress</h1>

      <div className="mt-5 grid grid-cols-2 gap-4">
        <Stat n={stats.words} label="words practiced" />
        <Stat n={stats.signs} label="signs practiced" />
      </div>

      <div className="mt-8 flex items-center gap-2">
        <RotateCcw className="size-5 text-muted-foreground" />
        <h2 className="text-xl font-semibold">Needs review</h2>
      </div>
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

function Stat({ n, label }: { n: number; label: string }) {
  return (
    <div className="rounded-2xl border bg-card p-6">
      <div className="text-4xl font-semibold">{n}</div>
      <div className="mt-1 text-muted-foreground">{label}</div>
    </div>
  )
}
