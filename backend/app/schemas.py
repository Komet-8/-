"""API 请求 / 响应模型。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# —— 请求 ——
class PlatformTarget(BaseModel):
    platform: str = Field(..., description="平台名，如 豆包 / DeepSeek")
    channel: str = Field("手机", description="渠道：网页 / 手机")
    thinking: bool = Field(True, description="是否开启 思考/深度思考")


class DiagnoseRequest(BaseModel):
    brand: str = Field(..., min_length=1, description="品牌名称")
    industry: str | None = Field(None, description="行业（可选，留空则由 AI 推断）")
    targets: list[PlatformTarget] | None = Field(None, description="要诊断的平台运行单元；留空用默认")
    num_questions: int | None = Field(None, ge=1, le=15, description="生成的问题数量")
    deep_thinking: bool = Field(True, description="全局深度思考开关")


# —— 响应 ——
class QuestionItem(BaseModel):
    text: str
    intent: str          # 对比/选择 | 咨询/查询
    heat: int            # 问题热度（搜索量近似）


class AnswerOut(BaseModel):
    question: str
    platform: str        # 运行单元名，如 「豆包·手机」
    channel: str = "手机"
    engine: str = "mock"  # doubao | mock
    text: str
    mentioned: bool
    rank: int | None
    sentiment: str       # positive | neutral | negative
    brands: list[str]
    sources: list[dict] = []


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


class CitationSource(BaseModel):
    site: str
    category: str
    url: str
    title: str
    cite_count: int
    questions: int
    platforms: list[str]


class ConversationAnswer(BaseModel):
    platform: str
    engine: str = "mock"
    text: str
    mentioned: bool
    rank: int | None
    sentiment: str
    brands: list[str]


class ConversationRecord(BaseModel):
    question: str
    intent: str
    heat: int
    mentioned_brands: list[str]
    answers: list[ConversationAnswer]


class PlatformInfo(BaseModel):
    id: str
    name: str
    label: str
    color: str
    channels: list[str]
    thinking_label: str
    api_capable: bool


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
    questions: list[QuestionItem]
    platforms: list[str]
    platform_metrics: list[PlatformMetric]
    leaderboard: Leaderboard
    answers: list[AnswerOut]
    citations: list[CitationSource]
    conversations: list[ConversationRecord]


class ConfigOut(BaseModel):
    mock: bool
    provider: str
    model: str
    platforms: list[PlatformInfo]
    num_questions: int


# —— 任务队列（本地 worker 协同）——
class BatchCreate(BaseModel):
    brand: str = Field(..., min_length=1)
    industry: str | None = None
    targets: list[PlatformTarget] | None = None
    num_questions: int | None = Field(None, ge=1, le=15)


class BatchStatus(BaseModel):
    batch_id: str
    brand: str
    total: int
    done: int
    errored: int
    finished: bool
    diagnosis_id: int | None


class JobOut(BaseModel):
    id: str
    platform: str
    channel: str
    thinking: bool
    question: str


class IngestIn(BaseModel):
    job_id: str
    text: str
    sources: list[dict] = []
    # 下面字段 worker 会带上，但后端以 job 记录为准，仅作核对/日志
    platform: str | None = None
    channel: str | None = None
    question: str | None = None
