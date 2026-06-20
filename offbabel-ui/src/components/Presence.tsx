import { Ear, Eye, Moon, Sparkles, Volume2 } from "lucide-react"
import type { Presence as PresenceState } from "@/lib/offbabel"

// The signature element: one calm presence indicator, reused across modes. It mirrors what the
// robot is doing (listening / speaking / watching / celebrating) and carries the only motion in
// the app. Color is always paired with an icon + label (never color alone).
const STATES: Record<
  PresenceState,
  { label: string; color: string; Icon: typeof Ear; pulse: boolean }
> = {
  idle: { label: "Ready", color: "var(--muted-foreground)", Icon: Moon, pulse: false },
  listening: { label: "Listening", color: "var(--info)", Icon: Ear, pulse: true },
  speaking: { label: "Speaking", color: "var(--success)", Icon: Volume2, pulse: true },
  watching: { label: "Watching", color: "var(--info)", Icon: Eye, pulse: false },
  celebrate: { label: "Nice!", color: "var(--warning)", Icon: Sparkles, pulse: false },
}

export function Presence({ state, size = 96 }: { state: PresenceState; size?: number }) {
  const s = STATES[state]
  const Icon = s.Icon
  return (
    <div className="flex flex-col items-center gap-2" role="status" aria-live="polite">
      <div className="relative grid place-items-center" style={{ width: size, height: size }}>
        {s.pulse && (
          <span
            className="absolute inset-2 rounded-full"
            style={{ background: s.color, animation: "offbabel-pulse 1.8s ease-in-out infinite" }}
          />
        )}
        <span
          className="relative grid place-items-center rounded-full border-2"
          style={{
            width: size * 0.72,
            height: size * 0.72,
            color: s.color,
            borderColor: s.color,
            background: `color-mix(in oklab, var(--card) 90%, ${s.color})`,
            animation: state === "celebrate" ? "offbabel-pop .5s ease-out" : undefined,
          }}
        >
          <Icon strokeWidth={2} style={{ width: size * 0.3, height: size * 0.3 }} />
        </span>
      </div>
      <span className="text-sm font-medium" style={{ color: s.color }}>
        {s.label}
      </span>
    </div>
  )
}
