import { useState, type FormEvent } from "react"
import { ArrowLeft, ArrowRight, Mic, Send } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Presence } from "@/components/Presence"
import type { Bubble, Correction, Presence as PresenceState } from "@/lib/offbabel"

export function Speak({
  presence,
  transcript,
  correction,
  onBack,
  onSend,
  onPtt,
}: {
  presence: PresenceState
  transcript: Bubble[]
  correction: Correction | null
  onBack: () => void
  onSend: (text: string) => void
  onPtt: (active: boolean) => void
}) {
  const [text, setText] = useState("")
  const submit = (e: FormEvent) => {
    e.preventDefault()
    const t = text.trim()
    if (!t) return
    onSend(t)
    setText("")
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col py-6">
      <div className="flex items-center justify-between">
        <Button variant="ghost" className="gap-1.5" onClick={onBack}>
          <ArrowLeft className="size-5" /> Back
        </Button>
        <Presence state={presence} size={84} />
        <div className="w-[84px]" aria-hidden />
      </div>

      <div className="mt-4 flex min-h-0 flex-1 flex-col overflow-y-auto rounded-2xl border bg-card p-4">
        {transcript.length === 0 ? (
          <div className="m-auto max-w-sm text-center text-muted-foreground">
            <p className="text-lg font-medium text-foreground">Your turn</p>
            <p className="mt-1">
              Hold the button to talk, or type below. The tutor replies in your
              chosen language and corrects gently.
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-2.5">
            {transcript.map((b, i) => (
              <div
                key={i}
                className={
                  b.role === "user"
                    ? "max-w-[78%] self-end rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-primary-foreground"
                    : "max-w-[78%] self-start rounded-2xl rounded-bl-md bg-muted px-4 py-2.5"
                }
              >
                {b.text}
              </div>
            ))}
          </div>
        )}
      </div>

      {correction && (
        <div className="mt-3 flex flex-wrap items-center gap-2 rounded-xl border border-warning/40 bg-warning/5 px-4 py-3">
          <span className="text-warning line-through decoration-warning/60">{correction.wrong}</span>
          <ArrowRight className="size-4 text-muted-foreground" />
          <span className="font-semibold text-success">{correction.right}</span>
          {correction.note && (
            <span className="w-full text-sm text-muted-foreground">{correction.note}</span>
          )}
        </div>
      )}

      <div className="mt-4 flex flex-col gap-3">
        <Button
          className="h-16 gap-2 text-lg"
          onMouseDown={() => onPtt(true)}
          onMouseUp={() => onPtt(false)}
          onMouseLeave={() => onPtt(false)}
        >
          <Mic className="size-6" /> Hold to talk
        </Button>
        <form onSubmit={submit} className="flex gap-2">
          <Input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="...or type here"
            className="h-12 text-base"
            aria-label="Type a message"
          />
          <Button type="submit" variant="secondary" className="h-12 gap-1.5">
            <Send className="size-4" /> Send
          </Button>
        </form>
      </div>
    </div>
  )
}
