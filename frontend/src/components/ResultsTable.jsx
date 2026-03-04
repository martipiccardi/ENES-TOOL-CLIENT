import { highlightText } from '../utils/highlight'

const VISIBLE_COLS = ['Wave', 'Question Number', 'Mnemo', 'Question(s)', 'Answer(s)', 'FW start date', 'FW end date']

const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api'

export default function ResultsTable({ rows, qExact, qExpanded, aExact, aExpanded, highlightId, highlightQuestion, highlightMnemo, onShowWave, onShowQWaves }) {
  if (!rows || rows.length === 0) {
    return <div style={{ padding: '1rem', color: '#888' }}>No results.</div>
  }

  return (
    <div className="wrapped-table">
      <table>
        <thead>
          <tr>
            {VISIBLE_COLS.map(col => (
              <th key={col} style={{ color: '#000', background: '#f0f0f0' }}>{col}</th>
            ))}
            <th style={{ color: '#000', background: '#f0f0f0' }}></th>
          </tr>
        </thead>
        <tbody>
          {rows.map(row => {
            const normPrefix = (s) => { const t = (s || '').replace(/\s+/g, ' ').trim().toLowerCase(); const i = t.indexOf('?'); return i >= 0 ? t.slice(0, i) : t }
            const isHl = (highlightId && row._row_hash === highlightId) ||
                         (highlightMnemo && row['Mnemo'] === highlightMnemo) ||
                         (highlightQuestion && normPrefix(row['Question(s)']) === normPrefix(highlightQuestion))
            const hlBg = isHl ? '#FFFF99' : '#fff'
            return (
              <tr key={row._row_hash} className={isHl ? 'hl-row' : ''}>
                {VISIBLE_COLS.map(col => {
                  let cellHtml
                  if (col === 'Question(s)') {
                    cellHtml = highlightText(row[col] || '', qExact, qExpanded)
                  } else if (col === 'Answer(s)') {
                    cellHtml = highlightText(row[col] || '', aExact, aExpanded)
                  } else {
                    cellHtml = escapeHtml(row[col] || '')
                  }
                  return (
                    <td
                      key={col}
                      style={{ color: '#000', background: hlBg }}
                      dangerouslySetInnerHTML={{ __html: cellHtml }}
                    />
                  )
                })}
                <td style={{ background: hlBg, textAlign: 'center' }}>
                  <ActionCell row={row} onShowWave={onShowWave} onShowQWaves={onShowQWaves} />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function ActionCell({ row, onShowWave, onShowQWaves }) {
  const parts = []

  if (row['Wave']?.trim()) {
    parts.push(
      <button
        key="wave"
        className="wave-action-link"
        onClick={() => onShowWave(row['Wave'], row._row_hash)}
      >
        Show complete wave
      </button>
    )
  }

  if (row['Wave']?.trim() && row['Question Number']?.trim()) {
    const url = `${API_BASE}/volume-a?wave=${encodeURIComponent(row['Wave'])}&question=${encodeURIComponent(row['Question Number'])}`
    parts.push(
      <button
        key="vola"
        className="wave-action-link"
        onClick={() => window.open(url, '_blank')}
      >
        Show volume A results
      </button>
    )
  }

  if (row['Question(s)']?.trim()) {
    parts.push(
      <button
        key="qwaves"
        className="q-waves-action-link"
        onClick={() => onShowQWaves(row['Question(s)'], row['Mnemo'] || '')}
      >
        Waves with this Q
      </button>
    )
  }

  if (row._source_url) {
    parts.push(
      <a
        key="source"
        className="source-link"
        href={row._source_url}
        target="_blank"
        rel="noopener noreferrer"
      >
        Show official source
      </a>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
      {parts}
    </div>
  )
}

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}
