import { ArrowRight, BarChart3, Hand, Mic } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { Screen } from "@/lib/offbabel"

export function Home({ go }: { go: (s: Screen) => void }) {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col items-center justify-center py-10">
      <h1 className="text-center text-4xl font-semibold tracking-tight sm:text-5xl">
        One tool, two communities.
      </h1>
      <p className="mt-4 max-w-xl text-center text-lg text-muted-foreground">
        Learn a language by speaking, or practice sign language by fingerspelling.
        Everything runs on this device, with no internet.
      </p>

      <div className="mt-10 grid w-full gap-5 sm:grid-cols-2">
        <ModeCard
          onClick={() => go("speak")}
          Icon={Mic}
          accent="var(--info)"
          title="Speak"
          desc="Hold a conversation and get gently corrected."
        />
        <ModeCard
          onClick={() => go("sign")}
          Icon={Hand}
          accent="var(--success)"
          title="Sign"
          desc="Fingerspell BSL to the camera, letter by letter."
        />
      </div>

      <Button
        variant="ghost"
        className="mt-8 h-12 gap-2 text-base"
        onClick={() => go("progress")}
      >
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
      style={{ minHeight: 196 }}
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
