import { useState } from "react"
import { RefreshCw, VideoOff } from "lucide-react"
import { cn } from "@/lib/utils"

// Live Reachy Mini camera feed. The Python backend reparses the robot's rpicam MJPEG stream into a
// multipart/x-mixed-replace endpoint, so a plain <img> renders it with no extra client code.
// Fails soft: if the robot/tunnel is down the <img> errors and we show an offline state + retry,
// mirroring the rest of the app where the robot is an enhancement, not a dependency.
const STREAM_URL = "/reachy-media/video.mjpeg"

export function ReachyVideo({ className, children }: { className?: string; children?: React.ReactNode }) {
  const [errored, setErrored] = useState(false)
  // Bump to force the <img> to re-request the stream (cache-busting query param) on manual retry.
  const [attempt, setAttempt] = useState(0)

  const retry = () => {
    setErrored(false)
    setAttempt((n) => n + 1)
  }

  return (
    <div
      className={cn(
        "relative grid flex-1 place-items-center overflow-hidden rounded-xl border bg-muted/40",
        className,
      )}
    >
      {errored ? (
        <div className="flex flex-col items-center gap-2 py-10 text-center text-muted-foreground">
          <VideoOff className="size-10" strokeWidth={2} />
          <div className="text-sm font-medium">Robot camera offline</div>
          <button
            onClick={retry}
            className="mt-1 inline-flex items-center gap-1.5 rounded-full bg-muted px-3 py-1 text-sm font-medium text-foreground transition hover:bg-foreground hover:text-background"
          >
            <RefreshCw className="size-4" strokeWidth={2} /> Retry
          </button>
        </div>
      ) : (
        <img
          key={attempt}
          src={`${STREAM_URL}?v=${attempt}`}
          alt="Reachy Mini live camera"
          className="h-full w-full object-cover"
          onError={() => setErrored(true)}
        />
      )}
      {children}
    </div>
  )
}