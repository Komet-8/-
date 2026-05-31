import { useMemo, useState } from 'react'
import type {
  AnswerOut,
  ConversationRecord,
  DiagnosisReport,
  Leaderboard,
  LeaderboardRow,
} from '../types'
import {
  categoryColor,
  countText,
  heatText,
  pct,
  platformBadge,
  rankText,
  sentimentText,
} from '../format'

// —— 客户端按平台重新聚合榜单，支撑「全部平台 / 单平台」下拉筛选 ——
const norm = (s: string) => s.trim().toLowerCase().replace(/\s/g, '')
const sameBrand = (a: string, b: string) => {
  const na = norm(a)
  const nb = norm(b)
  if (!na || !nb) return false
  return na === nb || na.includes(nb) || nb.includes(na)
}

function buildLeaderboard(answers: AnswerOut[], target: string, platform: string): Leaderboard {
  const filtered = platform === '全部平台' ? answers : answers.filter((a) => a.platform === platform)
  const total = filtered.length
  const map = new Map<string, { brand: string; answers: Set<number>; count: number; ranks: number[] }>()

  filtered.forEach((a, idx) => {
    const seen = new Set<string>()
    a.brands.forEach((b, pos) => {
      const k = norm(b)
      if (!k) return
      if (!map.has(k)) map.set(k, { brand: b.trim(), answers: new Set(), count: 0, ranks: [] })
      const e = map.get(k)!
      e.count += 1
      e.ranks.push(pos + 1)
      seen.add(k)
    })
    seen.forEach((k) => map.get(k)!.answers.add(idx))
  })

  const rows: LeaderboardRow[] = [...map.values()].map((e) => ({
    brand: e.brand,
    mention_rate: total ? e.answers.size / total : 0,
    mention_count: e.count,
    avg_rank: e.ranks.length ? e.ranks.reduce((x, y) => x + y, 0) / e.ranks.length : null,
    is_target: sameBrand(e.brand, target),
  }))

  const byRate = [...rows].sort((a, b) => b.mention_rate - a.mention_rate || b.mention_count - a.mention_count).slice(0, 10)
  const byCount = [...rows].sort((a, b) => b.mention_count - a.mention_count || b.mention_rate - a.mention_rate).slice(0, 10)
  const byAvgRank = [...rows]
    .sort((a, b) => (a.avg_rank ?? 1e9) - (b.avg_rank ?? 1e9) || b.mention_rate - a.mention_rate)
    .slice(0, 10)

  return { by_rate: byRate, by_count: byCount, by_avg_rank: byAvgRank }
}

function BarList({ rows, kind }: { rows: LeaderboardRow[]; kind: 'rate' | 'count' }) {
  const max = Math.max(...rows.map((r) => (kind === 'rate' ? r.mention_rate : r.mention_count)), 1e-9)
  return (
    <div className="bar-list">
      {rows.map((r, i) => {
        const v = kind === 'rate' ? r.mention_rate : r.mention_count
        const w = Math.max(2, (v / max) * 100)
        return (
          <div className="bar-row" key={r.brand}>
            <span className="bar-rank">{i + 1}</span>
            <span className={`bar-name ${r.is_target ? 'target' : ''}`}>{r.brand}</span>
            <span className="bar-track">
              <span className={`bar-fill ${r.is_target ? 'purple' : 'blue'}`} style={{ width: `${w}%` }} />
            </span>
            <span className="bar-val">{kind === 'rate' ? pct(r.mention_rate) : r.mention_count}</span>
          </div>
        )
      })}
    </div>
  )
}

function ConversationItem({ rec }: { rec: ConversationRecord }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="conv-item">
      <div className="conv-head">
        <div className="conv-q">
          <span className="conv-intent">{rec.intent}</span>
          <span className="conv-qtext">{rec.question}</span>
          <span className="conv-heat">🔥 {heatText(rec.heat)}</span>
        </div>
        <button className="conv-detail-btn" onClick={() => setOpen((v) => !v)}>
          {open ? '收起' : 'AI对话详情'}
        </button>
      </div>
      <div className="conv-brands">
        <span className="conv-brands-label">提及品牌：</span>
        {rec.mentioned_brands.length === 0 && <span className="conv-none">—</span>}
        {rec.mentioned_brands.slice(0, 6).map((b) => (
          <span className="conv-brand-chip" key={b}>
            {b}
          </span>
        ))}
        {rec.mentioned_brands.length > 6 && <span className="conv-brand-chip">…</span>}
      </div>
      {open && (
        <div className="conv-answers">
          {rec.answers.map((a, i) => (
            <div className="conv-answer" key={i}>
              <div className="conv-answer-head">
                <span className="ca-platform">{a.platform}</span>
                <span className={`ca-tag ${a.engine}`}>{a.engine === 'doubao' ? '真实' : '模拟'}</span>
                {a.mentioned ? (
                  <span className="ca-hit">命中 · 第{a.rank ?? '-'}名 · {sentimentText(a.sentiment)}</span>
                ) : (
                  <span className="ca-miss">未提及</span>
                )}
              </div>
              <div className="conv-answer-text">{a.text}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function ReportView({ report }: { report: DiagnosisReport }) {
  const platformOptions = ['全部平台', ...report.platforms]
  const [platform, setPlatform] = useState('全部平台')

  const lb = useMemo(
    () => buildLeaderboard(report.answers, report.brand, platform),
    [report.answers, report.brand, platform],
  )

  return (
    <div className="report">
      {/* AI 问题（含意图标签 + 热度） */}
      <section className="report-sec">
        <div className="sec-label">AI问题</div>
        <div className="questions">
          {report.questions.map((q, i) => (
            <div className="q-chip" key={i} title={q.text}>
              <span className="q-index">{i + 1}</span>
              <span className="q-text">{q.text}</span>
              <span className="q-intent">{q.intent}</span>
              <span className="q-heat">🔥{heatText(q.heat)}</span>
            </div>
          ))}
        </div>
      </section>

      {/* 各平台运行单元表现 */}
      <section className="platform-grid">
        {report.platform_metrics.map((p) => {
          const badge = platformBadge(p.platform)
          return (
            <div className="platform-card" key={p.platform}>
              <div className="pf-head">
                <span className="pf-avatar" style={{ background: badge.color }}>
                  {badge.label}
                </span>
                <span className="pf-name">{p.platform}</span>
              </div>
              <div className="pf-row">
                <span>品牌提及率</span>
                <b>{pct(p.mention_rate)}</b>
              </div>
              <div className="pf-row">
                <span>品牌提及次数</span>
                <b>{countText(p.mention_count)}</b>
              </div>
              <div className="pf-row">
                <span>平均提及排名</span>
                <b>{rankText(p.avg_rank)}</b>
              </div>
            </div>
          )
        })}
      </section>

      {/* 品牌表现 */}
      <section className="brand-perf">
        <div className="perf-head">
          <h3>品牌表现</h3>
          <select value={platform} onChange={(e) => setPlatform(e.target.value)}>
            {platformOptions.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>

        <div className="lb-grid">
          <div className="lb-col">
            <h4>品牌提及率</h4>
            <BarList rows={lb.by_rate} kind="rate" />
          </div>
          <div className="lb-col">
            <h4>品牌提及次数</h4>
            <BarList rows={lb.by_count} kind="count" />
          </div>
          <div className="lb-col">
            <h4>平均提及排名</h4>
            <table className="rank-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>品牌</th>
                  <th>提及率</th>
                  <th>平均排名</th>
                </tr>
              </thead>
              <tbody>
                {lb.by_avg_rank.map((r, i) => (
                  <tr key={r.brand} className={r.is_target ? 'target' : ''}>
                    <td>{i + 1}</td>
                    <td>{r.brand}</td>
                    <td>{pct(r.mention_rate)}</td>
                    <td>{rankText(r.avg_rank)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* 引用来源 + AI对话记录 双栏 */}
      <section className="bottom-grid">
        <div className="cite-col">
          <h3>引用来源</h3>
          <div className="cite-list">
            {report.citations.length === 0 && <div className="empty-sm">暂无引用来源</div>}
            {report.citations.slice(0, 12).map((c, i) => (
              <div className="cite-item" key={i}>
                <span className="cite-favicon" style={{ background: categoryColor(c.category) }}>
                  {c.site.slice(0, 1)}
                </span>
                <div className="cite-main">
                  <div className="cite-title-row">
                    <span className="cite-cat" style={{ background: categoryColor(c.category) }}>
                      {c.category}
                    </span>
                    <span className="cite-title">{c.title}</span>
                  </div>
                  <div className="cite-sub">
                    引用AI问题：{c.questions} · 引用次数：{c.cite_count} · 平台：{c.platforms.join('、')}
                  </div>
                </div>
                {c.url && (
                  <a className="cite-link" href={c.url} target="_blank" rel="noreferrer">
                    原文
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="conv-col">
          <h3>AI对话记录</h3>
          <div className="conv-list">
            {report.conversations.map((rec, i) => (
              <ConversationItem rec={rec} key={i} />
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}
