import axios from 'axios'

// In production (Cloudflare Pages), VITE_API_URL points to the Azure backend.
// In development, requests go through Vite's proxy to localhost:8000.
const BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api'

const api = axios.create({ baseURL: BASE })

export async function fetchDistinctValues(column) {
  const res = await api.get(`/distinct-values/${encodeURIComponent(column)}`)
  return res.data.values
}

export async function fetchSearch(params) {
  const res = await api.post('/search', params)
  return res.data
}

export async function fetchWave(wave) {
  const res = await api.get(`/waves/${encodeURIComponent(wave)}`)
  return res.data
}

export async function fetchWavesForQuestion(question, mnemo) {
  const res = await api.get('/waves-for-question', { params: { q: question, mnemo: mnemo || '' } })
  return res.data.waves
}

export async function downloadResults(params, fmt) {
  const res = await api.post('/download', { ...params, fmt }, { responseType: 'blob' })
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = fmt === 'xlsx' ? 'question_bank_results.xlsx' : 'question_bank_results.csv'
  a.click()
  URL.revokeObjectURL(url)
}
