// Shared types + small helpers for the OffBabel UI.

export type Screen = "home" | "speak" | "sign" | "progress"
export type Lang = "es" | "en" | "cs"
export type Presence = "idle" | "listening" | "speaking" | "watching" | "celebrate"

export const LANGS: { value: Lang; label: string; flag: string }[] = [
  { value: "es", label: "Spanish", flag: "🇪🇸" },
  { value: "en", label: "English", flag: "🇬🇧" },
  { value: "cs", label: "Czech", flag: "🇨🇿" },
]

export type Bubble = { role: "user" | "tutor"; text: string }
export type Correction = { wrong: string; right: string; note?: string }
export type ReviewItem = {
  type: "word" | "sign"
  language: string
  value: string
  miss_count: number
}

export const DEMO_WORD = "HELLO"

// Sample content so every screen reads well even with no backend (flow-testing).
export const SAMPLE_REVIEW: ReviewItem[] = [
  { type: "word", language: "es", value: "tener", miss_count: 3 },
  { type: "sign", language: "bsl", value: "O", miss_count: 2 },
  { type: "word", language: "es", value: "estar", miss_count: 2 },
  { type: "word", language: "cs", value: "děkuji", miss_count: 1 },
]
