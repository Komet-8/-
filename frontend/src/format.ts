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

export function formatDateTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(
    d.getMinutes(),
  )}:${p(d.getSeconds())}`
}

/** 平台展示样式（头像文字 + 颜色），对齐截图里的豆包/DeepSeek/千问。 */
export function platformBadge(name: string): { label: string; color: string } {
  const map: Record<string, { label: string; color: string }> = {
    豆包: { label: '豆', color: '#3b82f6' },
    DeepSeek: { label: 'DS', color: '#4f46e5' },
    千问: { label: '千', color: '#7c3aed' },
  }
  return map[name] ?? { label: name.slice(0, 2), color: '#6b7280' }
}
