// Shared types + small helpers for the OffBabel UI.

export type Screen = "home" | "speak" | "sign" | "progress"
export type Lang = "es" | "en" | "cs"
export type Presence = "idle" | "listening" | "speaking" | "watching" | "celebrate"

export const LANGS: { value: Lang; label: string; flag: string }[] = [
  { value: "es", label: "Spanish", flag: "🇪🇸" },
  { value: "en", label: "English", flag: "🇬🇧" },
  { value: "cs", label: "Czech", flag: "🇨🇿" },
]

export type Bubble = { role: "user" | "tutor"; text: string; translation?: string }
export type Correction = { wrong: string; right: string; note?: string }
export type ReviewItem = {
  type: "word" | "sign"
  language: string
  value: string
  miss_count: number
}

// ---- Learning model (mirrors offbabel/curriculum.py for the UI) ----
export type Scenario = { id: string; level: string; title: string; targets: string[] }
export const SCENARIOS: Scenario[] = [
  {
    id: "greetings",
    level: "A1",
    title: "Greetings & introductions",
    targets: ["Say hello", "Ask how someone is", "Say your name", "Say goodbye"],
  },
  {
    id: "ordering_food",
    level: "A2",
    title: "Ordering food",
    targets: ["Ask for the menu", "Order a dish", "Ask the price", "Ask for the bill"],
  },
  {
    id: "making_plans",
    level: "B1",
    title: "Making plans",
    targets: ["Suggest an activity", "Agree or disagree", "Propose a time", "Give a reason"],
  },
]

export type SignLevel = { id: string; title: string; kind: "letters" | "words"; items: string[] }
// Ids match offbabel/curriculum.py so the spaced-repetition engine groups them consistently.
export const SIGN_LEVELS: SignLevel[] = [
  { id: "L1_vowels", title: "Vowels", kind: "letters", items: ["A", "E", "I", "O", "U"] },
  { id: "L2_distinct", title: "Letters", kind: "letters", items: ["B", "C", "L", "R", "T"] },
  { id: "L3_words", title: "Words", kind: "words", items: ["HELLO", "CAT", "DOG"] },
  { id: "L4_common", title: "Common", kind: "words", items: ["THANK", "NAME", "GOOD"] },
]
export function levelSequence(lv: SignLevel): string[] {
  return lv.kind === "words" ? lv.items[0].split("") : lv.items
}

export type LearnSummary = {
  streak: number
  dueToday: number
  masterySpeak: number // 0..100
  masterySign: number
}
// Honest defaults: everything starts at zero and only grows as you actually practice
// (the real numbers come from the spaced-repetition engine when the backend is running).
export const EMPTY_SUMMARY: LearnSummary = {
  streak: 0,
  dueToday: 0,
  masterySpeak: 0,
  masterySign: 0,
}
