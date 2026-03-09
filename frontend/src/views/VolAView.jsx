import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'

const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api'

export default function VolAView() {
  const [searchParams, setSearchParams] = useSearchParams()
  const volAParam = searchParams.get('show_vol_a') || ''
  const [showCharts, setShowCharts] = useState(false)
  const [loading, setLoading] = useState(true)

  const sepIdx = volAParam.lastIndexOf('___')
  const wave = sepIdx >= 0 ? volAParam.slice(0, sepIdx) : volAParam
  const question = sepIdx >= 0 ? volAParam.slice(sepIdx + 3) : ''

  const baseUrl = `${API_BASE}/volume-a?wave=${encodeURIComponent(wave)}&question=${encodeURIComponent(question)}`
  const iframeSrc = baseUrl + (showCharts ? '&charts=1' : '')

  // Reset loading spinner whenever the URL changes
  useEffect(() => { setLoading(true) }, [iframeSrc])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', padding: '0.75rem 1.5rem', boxSizing: 'border-box' }}>
      <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginBottom: '8px' }}>
        <button className="back-link" onClick={() => setSearchParams({})}>
          Back to search
        </button>
        <button className="back-link" onClick={() => setShowCharts(v => !v)}>
          {showCharts ? 'Hide charts' : 'Volume A charts'}
        </button>
        {loading && (
          <span style={{ fontSize: '12px', color: '#666' }}>Loading Volume A…</span>
        )}
      </div>
      <iframe
        key={iframeSrc}
        src={iframeSrc}
        style={{ flex: 1, border: 'none', width: '100%' }}
        title={`Volume A — ${wave} / ${question}`}
        onLoad={() => setLoading(false)}
      />
    </div>
  )
}
