export interface Config {
  mock: boolean
  provider: string
  model: string
  platforms_available: string[]
  num_questions: number
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

export interface AnswerOut {
  question: string
  platform: string
  text: string
  mentioned: boolean
  rank: number | null
  sentiment: 'positive' | 'neutral' | 'negative'
  brands: string[]
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
  questions: string[]
  platforms: string[]
  platform_metrics: PlatformMetric[]
  leaderboard: Leaderboard
  answers: AnswerOut[]
}

export interface DiagnoseRequest {
  brand: string
  industry?: string
  platforms?: string[]
  num_questions?: number
  deep_thinking?: boolean
}

export interface SearchFilters {
  brand?: string
  start?: string
  end?: string
}
