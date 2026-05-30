import { useState } from 'react'
import type { DiagnosisReport, DiagnosisSummary, SearchFilters } from '../types'
import { RecordCard } from './RecordCard'

interface Props {
  records: DiagnosisSummary[]
  reports: Record<number, DiagnosisReport>
  expandedId: number | null
  onSearch: (f: SearchFilters) => void
  onToggle: (id: number) => void
  onDelete: (id: number) => void
}

export function RecordsList({ records, reports, expandedId, onSearch, onToggle, onDelete }: Props) {
  const [brand, setBrand] = useState('')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>诊断记录</h2>
        <div className="search-bar">
          <input placeholder="品牌" value={brand} onChange={(e) => setBrand(e.target.value)} />
          <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
          <span className="to">至</span>
          <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
          <button className="btn-primary sm" onClick={() => onSearch({ brand, start, end })}>
            搜索
          </button>
        </div>
      </div>

      {records.length === 0 ? (
        <div className="empty">暂无诊断记录，先在上方新建一次诊断吧。</div>
      ) : (
        records.map((r) => (
          <RecordCard
            key={r.id}
            summary={r}
            report={reports[r.id]}
            expanded={expandedId === r.id}
            onToggle={() => onToggle(r.id)}
            onDelete={() => onDelete(r.id)}
          />
        ))
      )}
    </section>
  )
}
