/** 展示用格式化工具，规则对齐爱搜导出的报告。 */

export const pct = (x: number | null | undefined): string =>
  x == null ? '—' : `${Math.round(x * 100)}%`

const fmtRank = (r: number): string => (Number.isInteger(r) ? `${r}` : r.toFixed(1))

/** 平均排名：未提及显示「未提及」，否则「N名」。 */
export const rankText = (r: number | null | undefined): string =>
  r == null ? '未提及' : `${fmtRank(r)}名`

/** 提及次数：0 次显示「未提及」。 */
export const countText = (n: number): string => (n > 0 ? `${n}次` : '未提及')

export const sentimentText = (s: string): string =>
  ({ positive: '正面', neutral: '中性', negative: '负面' }[s] ?? s)

/** 问题热度：>=10000 显示 N.Nw，否则原数。 */
export const heatText = (n: number): string =>
  n >= 10000 ? `${(n / 10000).toFixed(1)}w` : `${n}`

export function formatDateTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(
    d.getMinutes(),
  )}:${p(d.getSeconds())}`
}

/** 平台展示样式（头像文字 + 颜色）。先用注册表，回退到名字推断。 */
const FALLBACK: Record<string, { label: string; color: string }> = {
  豆包: { label: '豆', color: '#3b82f6' },
  DeepSeek: { label: 'DS', color: '#4f46e5' },
  元宝: { label: '元', color: '#12b76a' },
  千问: { label: '千', color: '#615ced' },
  百度AI: { label: '百', color: '#7c5cfc' },
  文心: { label: '文', color: '#3b82f6' },
  Kimi: { label: 'Km', color: '#111827' },
  AI抖音: { label: '抖', color: '#111827' },
}

export function platformBadge(runKey: string): { label: string; color: string } {
  const name = runKey.split('·')[0]
  return FALLBACK[name] ?? { label: name.slice(0, 2), color: '#6b7280' }
}

/** 网站分类的标签底色。 */
export function categoryColor(cat: string): string {
  if (cat.includes('政府')) return '#fee2e2'
  if (cat.includes('央媒') || cat.includes('媒体')) return '#dbeafe'
  if (cat.includes('教育')) return '#e0e7ff'
  if (cat.includes('视频')) return '#fce7f3'
  if (cat.includes('社区')) return '#fef3c7'
  if (cat.includes('门户')) return '#dcfce7'
  return '#f3e8ff'
}
