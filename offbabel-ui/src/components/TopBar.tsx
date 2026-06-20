import { WifiOff } from "lucide-react"
import { Badge } from "@/components/ui/badge"

export function TopBar() {
  return (
    <header className="flex items-center gap-4 border-b bg-card px-6 py-3 print:hidden">
      <div className="flex items-center gap-2">
        <img src="/mascot.png" alt="" draggable={false} className="h-9 w-auto select-none object-contain" />
        <span className="text-2xl font-semibold tracking-tight">OffBabel</span>
      </div>
      <Badge
        variant="outline"
        className="ml-auto gap-1.5 border-info/40 bg-info/5 text-info"
        title="No internet is used. Everything runs on this device."
      >
        <WifiOff className="size-3.5" />
        On-device · No internet
      </Badge>
    </header>
  )
}
