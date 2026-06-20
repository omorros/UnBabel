import { LANGS, type Lang } from "@/lib/offbabel"

// Visual segmented control for language (replaces the small dropdown).
// flag + name; the selected language is clearly highlighted.
export function LanguageToggle({
  value,
  onChange,
}: {
  value: Lang
  onChange: (l: Lang) => void
}) {
  return (
    <div
      role="radiogroup"
      aria-label="Language"
      className="inline-flex items-center gap-1 rounded-full border bg-muted/50 p-1"
    >
      {LANGS.map((l) => {
        const active = l.value === value
        return (
          <button
            key={l.value}
            role="radio"
            aria-checked={active}
            onClick={() => onChange(l.value)}
            className={
              "flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring " +
              (active
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground")
            }
          >
            <span aria-hidden className="text-base leading-none">
              {l.flag}
            </span>
            <span className="hidden sm:inline">{l.label}</span>
          </button>
        )
      })}
    </div>
  )
}
