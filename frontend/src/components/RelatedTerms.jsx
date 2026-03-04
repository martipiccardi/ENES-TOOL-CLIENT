export default function RelatedTerms({ terms, activeTerm, onTermClick }) {
  if (!terms || terms.length === 0) return null

  return (
    <div className="related-terms">
      <strong>Related terms <em style={{ fontWeight: 400, fontSize: '0.80rem' }}>(click to filter exact matches):</em></strong>
      <div className="terms-grid">
        {terms.map(({ term, score, count }) => (
          <button
            key={term}
            className={`term-chip${activeTerm === term ? ' active' : ''}`}
            onClick={() => onTermClick(activeTerm === term ? null : term)}
          >
            {activeTerm === term ? '>> ' : ''}{term}
            <span style={{ marginLeft: '5px', opacity: 0.75, fontSize: '0.78rem' }}>
              {score}
            </span>
            <span style={{
              marginLeft: '4px',
              fontSize: '0.72rem',
              background: count > 0 ? '#d4edda' : '#f0f0f0',
              color: count > 0 ? '#155724' : '#888',
              borderRadius: '8px',
              padding: '1px 5px',
            }}>
              {count > 0 ? `×${count}` : '∅'}
            </span>
          </button>
        ))}
      </div>
      {activeTerm && (
        <div className="info-box" style={{ marginTop: '0.5rem' }}>
          Filtered by: <strong>{activeTerm}</strong> — click the term again to clear
        </div>
      )}
    </div>
  )
}
