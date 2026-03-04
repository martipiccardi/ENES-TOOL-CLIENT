import { useEffect, useState } from 'react'
import { fetchDistinctValues } from '../api/client'

export default function Sidebar({ filters, onChange }) {
  const [waves, setWaves] = useState([])
  const [qnums, setQnums] = useState([])

  useEffect(() => {
    fetchDistinctValues('Wave').then(setWaves).catch(() => {})
    fetchDistinctValues('Question Number').then(setQnums).catch(() => {})
  }, [])

  const set = (key, val) => onChange({ ...filters, [key]: val })

  return (
    <aside className="sidebar">
      <h2>Filters</h2>

      <label>Wave</label>
      <select value={filters.wave} onChange={e => set('wave', e.target.value)}>
        <option value="">All</option>
        {waves.map(w => <option key={w} value={w}>{w}</option>)}
      </select>

      <label>Question Number</label>
      <select value={filters.questionNumber} onChange={e => set('questionNumber', e.target.value)}>
        <option value="">All</option>
        {qnums.map(q => <option key={q} value={q}>{q}</option>)}
      </select>

      <hr className="divider" />
      <div className="section-title">Period</div>

      <label>From (MM/YYYY)</label>
      <input
        type="text"
        placeholder="e.g. 01/2020"
        value={filters.periodFrom}
        onChange={e => set('periodFrom', e.target.value)}
      />

      <label>To (MM/YYYY)</label>
      <input
        type="text"
        placeholder="e.g. 12/2024"
        value={filters.periodTo}
        onChange={e => set('periodTo', e.target.value)}
      />

      <hr className="divider" />
      <div className="section-title">Text Search</div>

      <label>Search</label>
      <input
        type="text"
        value={filters.textSearch}
        onChange={e => set('textSearch', e.target.value)}
      />

      <label>Search in</label>
      <select value={filters.searchScope} onChange={e => set('searchScope', e.target.value)}>
        <option value="both">Questions &amp; Answers</option>
        <option value="q">Questions only</option>
        <option value="a">Answers only</option>
      </select>

      <div className="toggle-row">
        <input
          type="checkbox"
          id="semantic-toggle"
          checked={filters.semanticOn}
          onChange={e => set('semanticOn', e.target.checked)}
        />
        <label htmlFor="semantic-toggle">Semantic search</label>
      </div>

      <hr className="divider" />
      <div className="section-title">Results per page: {filters.perPage}</div>
      <input
        type="range"
        min={25}
        max={500}
        step={25}
        value={filters.perPage}
        onChange={e => set('perPage', Number(e.target.value))}
      />
    </aside>
  )
}
