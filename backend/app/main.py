"""FastAPI 入口：品牌诊断 / 报告 API。"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select

from .config import get_settings
from .database import get_session, init_db
from .models import Diagnosis
from .providers import build_provider, default_targets, platform_registry
from .schemas import (
    BatchCreate,
    BatchStatus,
    ConfigOut,
    DiagnoseRequest,
    DiagnosisReport,
    DiagnosisSummary,
    IngestIn,
    JobOut,
)
from .services.diagnosis import run_diagnosis
from .services.jobs import queue
from .services.questions import generate_questions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    mode = "豆包(真实)" if settings.use_real_provider else "模拟数据"
    logger.info("启动完成，运行模式：%s，模型：%s", mode, settings.ark_model)
    yield


app = FastAPI(title="GEO 品牌诊断 / 报告 API", version="0.2.0", lifespan=lifespan)

# 导入即建表，兼容 uvicorn 启动与 TestClient（后者默认不触发 lifespan）。
init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/config", response_model=ConfigOut)
def get_config() -> ConfigOut:
    return ConfigOut(
        mock=not settings.use_real_provider,
        provider="doubao" if settings.use_real_provider else "mock",
        model=settings.ark_model if settings.use_real_provider else "mock",
        platforms=platform_registry(settings),
        num_questions=settings.num_questions,
    )


def _to_report(d: Diagnosis) -> dict:
    return {
        "id": d.id,
        "brand": d.brand,
        "industry": d.industry,
        "created_at": d.created_at,
        "provider": d.provider,
        "brand_score": d.brand_score,
        "mention_rate": d.mention_rate,
        "avg_rank": d.avg_rank,
        "mention_count": d.mention_count,
        "sentiment_score": d.sentiment_score,
        "total_questions": d.total_questions,
        "total_answers": d.total_answers,
        "questions": d.questions,
        "platforms": d.platforms,
        "platform_metrics": d.platform_metrics,
        "leaderboard": d.leaderboard,
        "answers": d.answers,
        "citations": d.citations,
        "conversations": d.conversations,
    }


@app.post("/api/diagnose", response_model=DiagnosisReport)
def diagnose(req: DiagnoseRequest, session: Session = Depends(get_session)) -> dict:
    provider = build_provider(settings)
    targets = (
        [t.model_dump() for t in req.targets]
        if req.targets
        else default_targets(settings)
    )
    report = run_diagnosis(
        brand=req.brand.strip(),
        industry=(req.industry or "").strip() or None,
        targets=targets,
        num_questions=req.num_questions,
        provider=provider,
        settings=settings,
    )

    record = Diagnosis(
        brand=report["brand"],
        industry=report["industry"],
        provider=report["provider"],
        brand_score=report["brand_score"],
        mention_rate=report["mention_rate"],
        avg_rank=report["avg_rank"],
        mention_count=report["mention_count"],
        sentiment_score=report["sentiment_score"],
        total_questions=report["total_questions"],
        total_answers=report["total_answers"],
        questions=report["questions"],
        platforms=report["platforms"],
        platform_metrics=report["platform_metrics"],
        leaderboard=report["leaderboard"],
        answers=report["answers"],
        citations=report["citations"],
        conversations=report["conversations"],
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return _to_report(record)


@app.get("/api/diagnoses", response_model=list[DiagnosisSummary])
def list_diagnoses(
    session: Session = Depends(get_session),
    brand: str | None = Query(None, description="按品牌名模糊筛选"),
    start: datetime | None = Query(None, description="开始日期"),
    end: datetime | None = Query(None, description="结束日期"),
) -> list[Diagnosis]:
    stmt = select(Diagnosis).order_by(Diagnosis.created_at.desc())
    if brand:
        stmt = stmt.where(Diagnosis.brand.contains(brand))
    if start:
        stmt = stmt.where(Diagnosis.created_at >= start)
    if end:
        stmt = stmt.where(Diagnosis.created_at <= end)
    return list(session.exec(stmt).all())


@app.get("/api/diagnoses/{diagnosis_id}", response_model=DiagnosisReport)
def get_diagnosis(diagnosis_id: int, session: Session = Depends(get_session)) -> dict:
    d = session.get(Diagnosis, diagnosis_id)
    if not d:
        raise HTTPException(status_code=404, detail="诊断记录不存在")
    return _to_report(d)


@app.delete("/api/diagnoses/{diagnosis_id}")
def delete_diagnosis(diagnosis_id: int, session: Session = Depends(get_session)) -> dict:
    d = session.get(Diagnosis, diagnosis_id)
    if not d:
        raise HTTPException(status_code=404, detail="诊断记录不存在")
    session.delete(d)
    session.commit()
    return {"deleted": diagnosis_id}


# ============================================================= #
# 任务队列：本地浏览器 worker 协同（"像爱搜一样"的真实抓取路径）   #
# ============================================================= #
@app.post("/api/batches", response_model=BatchStatus)
def create_batch(req: BatchCreate) -> dict:
    """创建抓取批次：后端生成问题 + 建 jobs，交给本地 worker 抓取。"""
    provider = build_provider(settings)
    targets = (
        [t.model_dump() for t in req.targets]
        if req.targets
        else default_targets(settings)
    )
    n = req.num_questions or settings.num_questions
    resolved_industry, questions = generate_questions(
        req.brand.strip(), (req.industry or "").strip() or None, n, provider
    )
    batch = queue.create_batch(
        brand=req.brand.strip(),
        industry=resolved_industry or (req.industry or None),
        questions=questions,
        targets=targets,
    )
    return queue.batch_status(batch.id)  # type: ignore[return-value]


@app.get("/api/jobs/next")
def next_job():
    """worker 领取下一个待抓取 job；无任务时返回 204。"""
    from fastapi import Response

    job = queue.lease_next()
    if not job:
        return Response(status_code=204)
    return JobOut(
        id=job.id, platform=job.platform, channel=job.channel,
        thinking=job.thinking, question=job.question,
    )


@app.post("/api/ingest")
def ingest(payload: IngestIn) -> dict:
    """worker 回传抓取结果；后端分析该条，批次完成时自动落库。"""
    provider = build_provider(settings)
    try:
        return queue.ingest(
            payload.job_id, text=payload.text, sources=payload.sources, provider=provider
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="job 不存在")


@app.get("/api/batches/{batch_id}", response_model=BatchStatus)
def batch_status(batch_id: str) -> dict:
    st = queue.batch_status(batch_id)
    if not st:
        raise HTTPException(status_code=404, detail="批次不存在")
    return st


# —— 生产环境下，若前端已构建则一并托管 ——
_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
