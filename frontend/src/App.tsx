import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import { DiagnosisForm } from './components/DiagnosisForm'
import { RecordsList } from './components/RecordsList'
import type {
  Config,
  DiagnoseRequest,
  DiagnosisReport,
  DiagnosisSummary,
  SearchFilters,
} from './types'

export default function App() {
  const [config, setConfig] = useState<Config | null>(null)
  const [records, setRecords] = useState<DiagnosisSummary[]>([])
  const [reports, setReports] = useState<Record<number, DiagnosisReport>>({})
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadList = useCallback(async (f?: SearchFilters) => {
    try {
      setRecords(await api.list(f))
    } catch (e) {
      setError(String(e))
    }
  }, [])

  useEffect(() => {
    api.config().then(setConfig).catch((e) => setError(String(e)))
    loadList()
  }, [loadList])

  const handleSubmit = async (req: DiagnoseRequest) => {
    setRunning(true)
    setError(null)
    try {
      const report = await api.diagnose(req)
      setReports((prev) => ({ ...prev, [report.id]: report }))
      await loadList()
      setExpandedId(report.id)
    } catch (e) {
      setError(String(e))
    } finally {
      setRunning(false)
    }
  }

  const handleToggle = async (id: number) => {
    if (expandedId === id) {
      setExpandedId(null)
      return
    }
    setExpandedId(id)
    if (!reports[id]) {
      try {
        const r = await api.get(id)
        setReports((prev) => ({ ...prev, [id]: r }))
      } catch (e) {
        setError(String(e))
      }
    }
  }

  const handleDelete = async (id: number) => {
    if (!window.confirm('确认删除该诊断记录？')) return
    try {
      await api.remove(id)
      if (expandedId === id) setExpandedId(null)
      await loadList()
    } catch (e) {
      setError(String(e))
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="logo">
          <span className="logo-mark">AiDSO</span>
          <span className="logo-badge">GEO</span>
          <span className="logo-text">品牌诊断 / 报告</span>
        </div>
        {config && (
          <span className={`mode ${config.mock ? 'mock' : 'real'}`}>
            {config.mock ? '● 模拟数据模式' : `● 豆包真实模式 · ${config.model}`}
          </span>
        )}
      </header>

      <main className="container">
        {error && (
          <div className="error" onClick={() => setError(null)} title="点击关闭">
            ⚠ {error}
          </div>
        )}

        <DiagnosisForm config={config} running={running} onSubmit={handleSubmit} />

        <RecordsList
          records={records}
          reports={reports}
          expandedId={expandedId}
          onSearch={loadList}
          onToggle={handleToggle}
          onDelete={handleDelete}
        />
      </main>
    </div>
  )
}
