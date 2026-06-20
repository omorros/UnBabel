import { WifiOff } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { LanguageToggle } from "@/components/LanguageToggle"
import { type Lang } from "@/lib/offbabel"

export function TopBar({
  lang,
  onLang,
}: {
  lang: Lang
  onLang: (l: Lang) => void
}) {
  return (
    <header className="flex items-center gap-4 border-b bg-card px-6 py-3">
      <div className="flex items-center gap-2">
        <img src="/mascot.png" alt="" draggable={false} className="size-9 select-none" />
        <span className="text-2xl font-semibold tracking-tight">OffBabel</span>
      </div>
      <Badge
        variant="outline"
        className="gap-1.5 border-info/40 bg-info/5 text-info"
        title="No internet is used. Everything runs on this device."
      >
        <WifiOff className="size-3.5" />
        On-device · No internet
      </Badge>
      <div className="ml-auto">
        <LanguageToggle value={lang} onChange={onLang} />
      </div>
    </header>
  )
}
