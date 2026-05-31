"""任务队列：让本地浏览器 worker 即插即用。

流程：
  1. POST /api/batches 创建一个「抓取批次」：后端生成问题 + 为每个(问题×运行单元)建 job
  2. worker 轮询 GET /api/jobs/next 领取 pending job
  3. worker 抓取后 POST /api/ingest 回传正文+来源；后端分析该条
  4. 当批次内所有 job 完成，自动 assemble 成 Diagnosis 落库

为保持零额外依赖，队列用内存结构 + 线程锁实现（单进程足够；
多进程部署可换 Redis）。批次结果最终写入 Diagnosis 表，持久化。
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from sqlmodel import Session

from ..database import engine
from ..models import Diagnosis
from ..platforms import platform_of_key, run_key
from .. import sources as sources_mod
from .analyze import analyze_answer
from .diagnosis import assemble_report

JobStatus = Literal["pending", "running", "done", "error"]


@dataclass
class Job:
    id: str
    batch_id: str
    platform: str          # 平台 id 或显示名（传给 worker）
    platform_name: str     # 显示名
    channel: str
    thinking: bool
    question: str
    status: JobStatus = "pending"
    result: dict | None = None  # 分析后的 answer dict
    leased_at: datetime | None = None


@dataclass
class Batch:
    id: str
    brand: str
    industry: str | None
    questions: list[dict]
    platform_keys: list[str]
    job_ids: list[str] = field(default_factory=list)
    diagnosis_id: int | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


class JobQueue:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}
        self._batches: dict[str, Batch] = {}

    # —— 创建批次 ——
    def create_batch(
        self,
        *,
        brand: str,
        industry: str | None,
        questions: list[dict],
        targets: list[dict],
    ) -> Batch:
        bid = uuid.uuid4().hex[:12]
        platform_keys: list[str] = []
        for t in targets:
            key = run_key(t["platform"], t.get("channel", "网页"))
            if key not in platform_keys:
                platform_keys.append(key)

        batch = Batch(id=bid, brand=brand, industry=industry,
                      questions=questions, platform_keys=platform_keys)
        with self._lock:
            self._batches[bid] = batch
            for t in targets:
                for q in questions:
                    jid = uuid.uuid4().hex[:12]
                    job = Job(
                        id=jid, batch_id=bid,
                        platform=t["platform"],
                        platform_name=t["platform"],
                        channel=t.get("channel", "网页"),
                        thinking=t.get("thinking", True),
                        question=q["text"],
                    )
                    self._jobs[jid] = job
                    batch.job_ids.append(jid)
        return batch

    # —— worker 领取 ——
    def lease_next(self) -> Job | None:
        with self._lock:
            for job in self._jobs.values():
                if job.status == "pending":
                    job.status = "running"
                    job.leased_at = datetime.utcnow()
                    return job
        return None

    # —— worker 回传 ——
    def ingest(self, job_id: str, *, text: str, sources: list[dict], provider) -> dict:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise KeyError(job_id)
            batch = self._batches[job.batch_id]

        # 分析（在锁外做，可能调用 LLM）
        analysis = analyze_answer(batch.brand, job.question, text, provider)
        norm_sources = [sources_mod.normalize_source(s) for s in (sources or [])]
        answer = {
            "question": job.question,
            "platform": run_key(job.platform_name, job.channel),
            "channel": job.channel,
            "engine": "browser",
            "text": text,
            "mentioned": analysis["mentioned"],
            "rank": analysis["rank"],
            "sentiment": analysis["sentiment"],
            "brands": analysis["brands"],
            "sources": norm_sources,
        }

        with self._lock:
            job.result = answer
            job.status = "done"
            done = all(self._jobs[j].status in ("done", "error") for j in batch.job_ids)

        if done and batch.diagnosis_id is None:
            self._finalize(batch)
        return {"job_id": job_id, "batch_id": job.batch_id, "batch_done": done}

    def fail(self, job_id: str, error: str = "") -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = "error"
                job.result = None

    # —— 汇总落库 ——
    def _finalize(self, batch: Batch) -> None:
        answers = [self._jobs[j].result for j in batch.job_ids if self._jobs[j].result]
        report = assemble_report(
            brand=batch.brand,
            industry=batch.industry,
            provider_name="browser",
            questions=batch.questions,
            answers=answers,
            platform_keys=batch.platform_keys,
        )
        with Session(engine) as session:
            record = Diagnosis(
                brand=report["brand"], industry=report["industry"], provider=report["provider"],
                brand_score=report["brand_score"], mention_rate=report["mention_rate"],
                avg_rank=report["avg_rank"], mention_count=report["mention_count"],
                sentiment_score=report["sentiment_score"], total_questions=report["total_questions"],
                total_answers=report["total_answers"], questions=report["questions"],
                platforms=report["platforms"], platform_metrics=report["platform_metrics"],
                leaderboard=report["leaderboard"], answers=report["answers"],
                citations=report["citations"], conversations=report["conversations"],
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            batch.diagnosis_id = record.id

    # —— 查询批次进度 ——
    def batch_status(self, batch_id: str) -> dict | None:
        with self._lock:
            batch = self._batches.get(batch_id)
            if not batch:
                return None
            jobs = [self._jobs[j] for j in batch.job_ids]
            total = len(jobs)
            done = sum(1 for j in jobs if j.status == "done")
            errored = sum(1 for j in jobs if j.status == "error")
            return {
                "batch_id": batch_id,
                "brand": batch.brand,
                "total": total,
                "done": done,
                "errored": errored,
                "finished": batch.diagnosis_id is not None,
                "diagnosis_id": batch.diagnosis_id,
            }


# 单例
queue = JobQueue()
