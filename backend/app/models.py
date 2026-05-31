"""数据库模型。一条 Diagnosis 记录 = 对一个品牌的一次完整诊断。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel


class Diagnosis(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    brand: str = Field(index=True)
    industry: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    provider: str = "mock"  # "doubao" | "mock"

    # —— 汇总指标 ——
    brand_score: int = 0            # 品牌得分 0~100
    mention_rate: float = 0.0       # 品牌提及率 0~1
    avg_rank: float | None = None   # 平均提及排名
    mention_count: int = 0          # 品牌提及次数
    sentiment_score: float = 0.0    # 正面/中性情感占比 0~1
    total_questions: int = 0
    total_answers: int = 0          # 问题数 × 运行单元数

    # —— 明细（JSON）——
    questions: list = Field(default_factory=list, sa_column=Column(JSON))        # [{text,intent,heat}]
    platforms: list = Field(default_factory=list, sa_column=Column(JSON))        # 运行单元名列表，如 ["豆包·手机", ...]
    platform_metrics: list = Field(default_factory=list, sa_column=Column(JSON))
    leaderboard: dict = Field(default_factory=dict, sa_column=Column(JSON))
    answers: list = Field(default_factory=list, sa_column=Column(JSON))
    citations: list = Field(default_factory=list, sa_column=Column(JSON))        # 引用来源榜单
    conversations: list = Field(default_factory=list, sa_column=Column(JSON))    # AI对话记录（按问题分组）
