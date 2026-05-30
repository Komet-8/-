import type { DiagnosisReport, DiagnosisSummary } from '../types'
import { countText, formatDateTime, pct, rankText } from '../format'
import { ReportView } from './ReportView'

interface Props {
  summary: DiagnosisSummary
  report?: DiagnosisReport
  expanded: boolean
  onToggle: () => void
  onDelete: () => void
}

function Metric({ value, unit, label }: { value: string; unit?: string; label: string }) {
  return (
    <div className="metric">
      <div className="metric-num">
        {value}
        {unit && <span className="metric-unit">{unit}</span>}
      </div>
      <div className="metric-label">{label}</div>
    </div>
  )
}

export function RecordCard({ summary: s, report, expanded, onToggle, onDelete }: Props) {
  return (
    <div className={`record ${expanded ? 'open' : ''}`}>
      <div className="record-top">
        <div className="record-brand">
          <span className="brand-badge">{s.brand.slice(0, 1)}</span>
          <div className="brand-info">
            <div className="brand-name">{s.brand}</div>
            <button className="chip-btn" onClick={onToggle}>
              {expanded ? '收起结果 ▲' : '查看结果 ▼'}
            </button>
          </div>
        </div>

        <div className="metric-strip">
          <Metric value={String(s.brand_score)} unit="/100" label="品牌得分" />
          <Metric value={pct(s.mention_rate)} label="品牌提及率" />
          <Metric value={rankText(s.avg_rank)} label="平均提及排名" />
          <Metric value={countText(s.mention_count)} label="品牌提及次数" />
          <Metric value={pct(s.sentiment_score)} label="正面/中性情感倾向" />
        </div>

        <div className="record-meta">
          <span className="time">{formatDateTime(s.created_at)}</span>
          <span className={`provider-tag ${s.provider}`}>
            {s.provider === 'doubao' ? '豆包' : '模拟'}
          </span>
          <button className="btn-del" onClick={onDelete}>
            删除
          </button>
        </div>
      </div>

      {expanded &&
        (report ? <ReportView report={report} /> : <div className="loading-inline">加载报告中…</div>)}
    </div>
  )
}
