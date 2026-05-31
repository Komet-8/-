import { useEffect, useState } from 'react'
import type { Config, DiagnoseRequest, PlatformInfo, PlatformTarget } from '../types'

interface Props {
  config: Config | null
  running: boolean
  onSubmit: (req: DiagnoseRequest) => void
}

// 每个平台卡片的勾选状态：哪些渠道被选中、是否开思考
interface CardState {
  channels: Record<string, boolean> // {网页:false, 手机:true}
  thinking: boolean
}

function initStates(platforms: PlatformInfo[]): Record<string, CardState> {
  const s: Record<string, CardState> = {}
  for (const p of platforms) {
    const channels: Record<string, boolean> = {}
    p.channels.forEach((c) => (channels[c] = false))
    // 默认：豆包/DeepSeek/千问 勾选手机端
    if (['豆包', 'DeepSeek', '千问'].includes(p.name) && '手机' in channels) {
      channels['手机'] = true
    }
    s[p.name] = { channels, thinking: true }
  }
  return s
}

export function DiagnosisForm({ config, running, onSubmit }: Props) {
  const [brand, setBrand] = useState('')
  const [states, setStates] = useState<Record<string, CardState>>({})
  const [deepAll, setDeepAll] = useState(true)

  useEffect(() => {
    if (config) setStates(initStates(config.platforms))
  }, [config])

  const platforms = config?.platforms ?? []

  const toggleChannel = (name: string, channel: string) =>
    setStates((prev) => ({
      ...prev,
      [name]: {
        ...prev[name],
        channels: { ...prev[name].channels, [channel]: !prev[name].channels[channel] },
      },
    }))

  const toggleThinking = (name: string) =>
    setStates((prev) => ({ ...prev, [name]: { ...prev[name], thinking: !prev[name].thinking } }))

  const buildTargets = (): PlatformTarget[] => {
    const targets: PlatformTarget[] = []
    for (const p of platforms) {
      const st = states[p.name]
      if (!st) continue
      for (const ch of p.channels) {
        if (st.channels[ch]) {
          targets.push({ platform: p.name, channel: ch, thinking: st.thinking && deepAll })
        }
      }
    }
    return targets
  }

  const targets = buildTargets()
  const allSelected =
    platforms.length > 0 &&
    platforms.every((p) => p.channels.every((c) => states[p.name]?.channels[c]))

  const toggleSelectAll = () => {
    setStates((prev) => {
      const next = { ...prev }
      for (const p of platforms) {
        const channels: Record<string, boolean> = {}
        p.channels.forEach((c) => (channels[c] = !allSelected))
        next[p.name] = { ...next[p.name], channels }
      }
      return next
    })
  }

  const submit = () => {
    if (!brand.trim() || running || targets.length === 0) return
    onSubmit({
      brand: brand.trim(),
      targets,
      deep_thinking: deepAll,
    })
  }

  return (
    <section className="card form-card">
      <div className="brand-input-row">
        <span className="brand-input-label">品牌名称</span>
        <input
          value={brand}
          placeholder="品牌名称，如：爱搜"
          onChange={(e) => setBrand(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submit()}
        />
      </div>

      <div className="pf-cards">
        {platforms.map((p) => {
          const st = states[p.name]
          if (!st) return null
          return (
            <div className="pf-card" key={p.id}>
              <div className="pf-card-avatar" style={{ background: p.color }}>
                {p.label}
              </div>
              <div className="pf-card-name">{p.name}</div>
              {p.channels.map((ch) => (
                <div className="pf-channel" key={ch}>
                  <label className="pf-radio">
                    <input
                      type="checkbox"
                      checked={st.channels[ch]}
                      onChange={() => toggleChannel(p.name, ch)}
                    />
                    <span>{ch}</span>
                  </label>
                  <button
                    type="button"
                    className={`pf-think ${st.thinking ? 'on' : ''}`}
                    onClick={() => toggleThinking(p.name)}
                    title={`${p.thinking_label}模式`}
                  >
                    ✶ {p.thinking_label}
                  </button>
                </div>
              ))}
              {!p.api_capable && (
                <div className="pf-note" title="该平台真实结果需本地浏览器自动化抓取；云端用模拟数据">
                  模拟
                </div>
              )}
            </div>
          )
        })}
      </div>

      <div className="form-actions">
        <label className="select-all">
          <input type="checkbox" checked={allSelected} onChange={toggleSelectAll} />
          全选
        </label>
        <label className="select-all">
          <input type="checkbox" checked={deepAll} onChange={(e) => setDeepAll(e.target.checked)} />
          深度思考
        </label>
        <button
          className="btn-primary submit"
          disabled={!brand.trim() || running || targets.length === 0}
          onClick={submit}
        >
          {running ? '诊断中…' : '爱搜一下'}
        </button>
      </div>

      <p className="targets-hint">
        已选 <strong>{targets.length}</strong> 个运行单元
        {config?.mock && '（当前未配置豆包 API Key，全部走模拟数据跑通流程）'}
        {!config?.mock && '（豆包·手机为真实调用，其余平台需本地 worker 抓取，云端用模拟）'}
      </p>
    </section>
  )
}
