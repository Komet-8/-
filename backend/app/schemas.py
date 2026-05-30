"""API 请求 / 响应模型。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DiagnoseRequest(BaseModel):
    brand: str = Field(..., min_length=1, description="品牌名称")
    industry: str | None = Field(None, description="行业（可选，留空则由 AI 推断）")
    platforms: list[str] | None = Field(None, description="要诊断的 AI 平台，留空则用全部可用平台")
    num_questions: int | None = Field(None, ge=1, le=15, description="生成的问题数量")
    deep_thinking: bool = Field(False, description="是否开启深度思考")


class AnswerOut(BaseModel):
    question: str
    platform: str
    text: str
    mentioned: bool
    rank: int | None
    sentiment: str  # positive | neutral | negative
    brands: list[str]


class PlatformMetric(BaseModel):
    platform: str
    mention_rate: float
    mention_count: int
    avg_rank: float | None


class LeaderboardRow(BaseModel):
    brand: str
    mention_rate: float
    mention_count: int
    avg_rank: float | None
    is_target: bool


class Leaderboard(BaseModel):
    by_rate: list[LeaderboardRow]
    by_count: list[LeaderboardRow]
    by_avg_rank: list[LeaderboardRow]


class DiagnosisSummary(BaseModel):
    id: int
    brand: str
    industry: str | None
    created_at: datetime
    provider: str
    brand_score: int
    mention_rate: float
    avg_rank: float | None
    mention_count: int
    sentiment_score: float
    total_questions: int
    total_answers: int


class DiagnosisReport(DiagnosisSummary):
    questions: list[str]
    platforms: list[str]
    platform_metrics: list[PlatformMetric]
    leaderboard: Leaderboard
    answers: list[AnswerOut]


class ConfigOut(BaseModel):
    mock: bool
    provider: str
    model: str
    platforms_available: list[str]
    num_questions: int
