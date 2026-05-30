import type {
  Config,
  DiagnoseRequest,
  DiagnosisReport,
  DiagnosisSummary,
  SearchFilters,
} from './types'

const BASE = '/api'

async function asJson<T>(r: Response): Promise<T> {
  if (!r.ok) {
    const detail = await r.text().catch(() => '')
    throw new Error(detail || `${r.status} ${r.statusText}`)
  }
  return r.json() as Promise<T>
}

export const api = {
  config: () => fetch(`${BASE}/config`).then(asJson<Config>),

  diagnose: (body: DiagnoseRequest) =>
    fetch(`${BASE}/diagnose`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(asJson<DiagnosisReport>),

  list: (f?: SearchFilters) => {
    const q = new URLSearchParams()
    if (f?.brand) q.set('brand', f.brand)
    if (f?.start) q.set('start', f.start)
    if (f?.end) q.set('end', `${f.end}T23:59:59`)
    const qs = q.toString()
    return fetch(`${BASE}/diagnoses${qs ? `?${qs}` : ''}`).then(asJson<DiagnosisSummary[]>)
  },

  get: (id: number) => fetch(`${BASE}/diagnoses/${id}`).then(asJson<DiagnosisReport>),

  remove: (id: number) =>
    fetch(`${BASE}/diagnoses/${id}`, { method: 'DELETE' }).then(asJson<{ deleted: number }>),
}
