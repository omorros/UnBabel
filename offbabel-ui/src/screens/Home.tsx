import { ArrowRight, Hand, Mic } from "lucide-react"
import { Button } from "@/components/ui/button"
import { LanguageToggle } from "@/components/LanguageToggle"
import { LANGS, type Lang } from "@/lib/offbabel"

export function Home({
  lang,
  onLang,
  onSpeak,
  onSign,
  onProgress,
}: {
  lang: Lang
  onLang: (l: Lang) => void
  onSpeak: () => void
  onSign: () => void
  onProgress: () => void
}) {
  const langLabel = LANGS.find((l) => l.value === lang)?.label ?? "your language"
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col items-center justify-center py-6">
      <img
        src="/mascot.png"
        alt=""
        draggable={false}
        className="mb-3 h-40 w-auto select-none"
      />
      <h1 className="text-center text-4xl font-semibold tracking-tight sm:text-5xl">
        One tool, two communities.
      </h1>
      <p className="mt-3 max-w-xl text-center text-lg text-muted-foreground">
        Practice a language by speaking, or sign language by fingerspelling. On-device, no internet.
      </p>

      {/* Get started: pick the spoken language (Sign is always BSL) */}
      <div className="mt-6 flex flex-col items-center gap-2">
        <span className="text-sm font-medium text-muted-foreground">Practice in</span>
        <LanguageToggle value={lang} onChange={onLang} />
      </div>

      <div className="mt-6 grid w-full gap-4 sm:grid-cols-2">
        <ModeCard
          onClick={onSpeak}
          Icon={Mic}
          accent="var(--info)"
          title="Speak"
          desc={`Conversation in ${langLabel}, corrected gently.`}
        />
        <ModeCard
          onClick={onSign}
          Icon={Hand}
          accent="var(--success)"
          title="Sign"
          desc="Fingerspell British Sign Language to the camera."
        />
      </div>

      <Button variant="ghost" className="mt-5 h-11 text-base text-muted-foreground" onClick={onProgress}>
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
      className="group rounded-2xl border bg-card p-6 text-left transition hover:-translate-y-0.5 hover:border-foreground/20 hover:shadow-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
      style={{ minHeight: 150 }}
    >
      <span
        className="grid size-14 place-items-center rounded-xl"
        style={{ color: accent, background: `color-mix(in oklab, var(--card) 86%, ${accent})` }}
      >
        <Icon className="size-7" strokeWidth={2} />
      </span>
      <div className="mt-4 flex items-center gap-2">
        <span className="text-2xl font-semibold">{title}</span>
        <ArrowRight className="size-5 text-muted-foreground transition group-hover:translate-x-1" />
      </div>
      <p className="mt-1.5 text-muted-foreground">{desc}</p>
    </button>
  )
}
