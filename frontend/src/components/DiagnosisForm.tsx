import { useEffect, useState } from 'react'
import type { Config, DiagnoseRequest } from '../types'

interface Props {
  config: Config | null
  running: boolean
  onSubmit: (req: DiagnoseRequest) => void
}

export function DiagnosisForm({ config, running, onSubmit }: Props) {
  const [brand, setBrand] = useState('')
  const [industry, setIndustry] = useState('')
  const [platforms, setPlatforms] = useState<string[]>([])
  const [numQuestions, setNumQuestions] = useState(5)
  const [deepThinking, setDeepThinking] = useState(true)

  // 配置加载后，默认勾选全部可用平台。
  useEffect(() => {
    if (config) {
      setPlatforms(config.platforms_available)
      setNumQuestions(config.num_questions)
    }
  }, [config])

  const togglePlatform = (p: string) =>
    setPlatforms((prev) => (prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]))

  const submit = () => {
    if (!brand.trim() || running) return
    onSubmit({
      brand: brand.trim(),
      industry: industry.trim() || undefined,
      platforms: platforms.length ? platforms : undefined,
      num_questions: numQuestions,
      deep_thinking: deepThinking,
    })
  }

  return (
    <section className="card form-card">
      <div className="form-title">
        <h2>新建品牌诊断</h2>
        <p className="form-sub">输入品牌 → AI 自动生成行业问题 → 多平台提问并分析 → 生成诊断报告</p>
      </div>

      <div className="form-grid">
        <label className="field">
          <span>品牌名称 *</span>
          <input
            value={brand}
            placeholder="例如：瑞泰口腔"
            onChange={(e) => setBrand(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submit()}
          />
        </label>

        <label className="field">
          <span>行业（可选，留空由 AI 推断）</span>
          <input
            value={industry}
            placeholder="例如：口腔医疗"
            onChange={(e) => setIndustry(e.target.value)}
          />
        </label>

        <label className="field field-sm">
          <span>问题数量</span>
          <input
            type="number"
            min={1}
            max={15}
            value={numQuestions}
            onChange={(e) => setNumQuestions(Math.max(1, Math.min(15, Number(e.target.value) || 1)))}
          />
        </label>
      </div>

      <div className="platforms">
        <span className="platforms-label">诊断平台</span>
        {(config?.platforms_available ?? []).map((p) => (
          <button
            key={p}
            type="button"
            className={`pf-chip ${platforms.includes(p) ? 'on' : ''}`}
            onClick={() => togglePlatform(p)}
          >
            {p}
          </button>
        ))}
        <label className="deep-toggle">
          <input
            type="checkbox"
            checked={deepThinking}
            onChange={(e) => setDeepThinking(e.target.checked)}
          />
          深度思考
        </label>
      </div>

      <button className="btn-primary submit" disabled={!brand.trim() || running} onClick={submit}>
        {running ? '诊断中…' : '爱搜一下'}
      </button>

      {config?.mock && (
        <p className="mock-hint">
          当前未配置豆包 API Key，使用<strong>模拟数据</strong>跑通完整流程。配置 <code>ARK_API_KEY</code> 后将自动调用真实豆包。
        </p>
      )}
    </section>
  )
}
