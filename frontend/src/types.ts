export interface PlatformInfo {
  id: string
  name: string
  label: string
  color: string
  channels: string[]
  thinking_label: string
  api_capable: boolean
}

export interface Config {
  mock: boolean
  provider: string
  model: string
  platforms: PlatformInfo[]
  num_questions: number
}

export interface QuestionItem {
  text: string
  intent: string
  heat: number
}

export interface PlatformMetric {
  platform: string
  mention_rate: number
  mention_count: number
  avg_rank: number | null
}

export interface LeaderboardRow {
  brand: string
  mention_rate: number
  mention_count: number
  avg_rank: number | null
  is_target: boolean
}

export interface Leaderboard {
  by_rate: LeaderboardRow[]
  by_count: LeaderboardRow[]
  by_avg_rank: LeaderboardRow[]
}

export interface Source {
  site: string
  category: string
  url: string
  title: string
}

export interface AnswerOut {
  question: string
  platform: string
  channel: string
  engine: string
  text: string
  mentioned: boolean
  rank: number | null
  sentiment: 'positive' | 'neutral' | 'negative'
  brands: string[]
  sources: Source[]
}

export interface CitationSource {
  site: string
  category: string
  url: string
  title: string
  cite_count: number
  questions: number
  platforms: string[]
}

export interface ConversationAnswer {
  platform: string
  engine: string
  text: string
  mentioned: boolean
  rank: number | null
  sentiment: string
  brands: string[]
}

export interface ConversationRecord {
  question: string
  intent: string
  heat: number
  mentioned_brands: string[]
  answers: ConversationAnswer[]
}

export interface DiagnosisSummary {
  id: number
  brand: string
  industry: string | null
  created_at: string
  provider: string
  brand_score: number
  mention_rate: number
  avg_rank: number | null
  mention_count: number
  sentiment_score: number
  total_questions: number
  total_answers: number
}

export interface DiagnosisReport extends DiagnosisSummary {
  questions: QuestionItem[]
  platforms: string[]
  platform_metrics: PlatformMetric[]
  leaderboard: Leaderboard
  answers: AnswerOut[]
  citations: CitationSource[]
  conversations: ConversationRecord[]
}

export interface PlatformTarget {
  platform: string
  channel: string
  thinking: boolean
}

export interface DiagnoseRequest {
  brand: string
  industry?: string
  targets?: PlatformTarget[]
  num_questions?: number
  deep_thinking?: boolean
}

export interface SearchFilters {
  brand?: string
  start?: string
  end?: string
}
