import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import RelatedTerms from '../components/RelatedTerms'
import ResultsTable from '../components/ResultsTable'
import Pagination from '../components/Pagination'
import { fetchSearch, downloadResults } from '../api/client'

const DEFAULT_FILTERS = {
  wave: '',
  questionNumber: '',
  periodFrom: '',
  periodTo: '',
  textSearch: '',
  searchScope: 'both',
  semanticOn: true,
  perPage: 100,
}

const SESSION_KEY = 'enes_search_state'

function loadSession() {
  try { return JSON.parse(sessionStorage.getItem(SESSION_KEY) || '{}') } catch { return {} }
}

export default function SearchView() {
  const [, setSearchParams] = useSearchParams()
  const [filters, setFilters] = useState(() => { const s = loadSession(); return s.filters || DEFAULT_FILTERS })
  const [page, setPage] = useState(() => { const s = loadSession(); return s.page || 1 })
  const [activeTerm, setActiveTerm] = useState(() => { const s = loadSession(); return s.activeTerm || null })

  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [modelReady, setModelReady] = useState(false)

  // Poll /api/model-ready every 3s until the semantic model is loaded
  useEffect(() => {
    if (modelReady) return
    const check = async () => {
      try {
        const r = await fetch('/api/model-ready')
        const d = await r.json()
        if (d.ready) setModelReady(true)
      } catch {}
    }
    check()
    const id = setInterval(check, 3000)
    return () => clearInterval(id)
  }, [modelReady])

  // Persist state so "Back to search" restores it
  useEffect(() => {
    try { sessionStorage.setItem(SESSION_KEY, JSON.stringify({ filters, page, activeTerm })) } catch {}
  }, [filters, page, activeTerm])

  const doSearch = useCallback(async (f, p, term) => {
    setLoading(true)
    try {
      const data = await fetchSearch({
        semantic: f.semanticOn,
        wave: f.wave,
        question_number: f.questionNumber,
        period_from: f.periodFrom,
        period_to: f.periodTo,
        text_contains: f.textSearch,
        search_scope: f.searchScope,
        sem_filter: term || '',
        page: p,
        per_page: f.perPage,
      })
      setResult(data)
    } finally {
      setLoading(false)
    }
  }, [])

  // Search on filter/page/term change (debounced)
  useEffect(() => {
    const t = setTimeout(() => doSearch(filters, page, activeTerm), 300)
    return () => clearTimeout(t)
  }, [filters, page, activeTerm, doSearch])

  const handleFiltersChange = (newFilters) => {
    setFilters(newFilters)
    setPage(1)
    setActiveTerm(null)
  }

  const handleTermClick = (term) => {
    setActiveTerm(term)
    setPage(1)
  }

  const handleShowWave = (wave, rowHash) => {
    setSearchParams({ show_wave: `${wave}___${rowHash}` })
  }

  const handleShowQWaves = (question, mnemo) => {
    setSearchParams({ show_q_waves: question, show_q_mnemo: mnemo || '' })
  }

  const handleDownload = async (fmt) => {
    await downloadResults({
      semantic: filters.semanticOn,
      wave: filters.wave,
      question_number: filters.questionNumber,
      period_from: filters.periodFrom,
      period_to: filters.periodTo,
      text_contains: filters.textSearch,
      search_scope: filters.searchScope,
      sem_filter: activeTerm || '',
    }, fmt)
  }

  // Highlight logic — scope controls which columns get highlighted
  const hasText = filters.textSearch.trim()
  const relatedTerms = result?.related_terms || []
  const allRelated = relatedTerms.map(t => t.term.toLowerCase())

  // Backend-expanded synonyms (e.g. "farming agriculture agricultural" for "farmers"):
  // merged into yellow highlights so they don't appear as exact (green) matches.
  const expandedQueryTerms = result?.expanded_query_terms || []

  let expandedTerms = []
  if (activeTerm) {
    expandedTerms = [activeTerm.toLowerCase()]
  } else if (filters.semanticOn && hasText) {
    expandedTerms = [...new Set([...allRelated, ...expandedQueryTerms])]
  }
  // Highlight the full phrase as a single unit — no partial word matches
  const exactTerms = hasText ? [hasText.toLowerCase().trim()] : []

  const inQ = filters.searchScope === 'both' || filters.searchScope === 'q'
  const inA = filters.searchScope === 'both' || filters.searchScope === 'a'

  const qExact = inQ ? exactTerms : []
  const aExact = inA ? exactTerms : []
  const qExpanded = inQ ? expandedTerms : []
  const aExpanded = inA ? expandedTerms : []

  const total = result?.total ?? 0
  const rows = result?.rows ?? []

  return (
    <div className="app-layout">
      <Sidebar filters={filters} onChange={handleFiltersChange} />
      <main className="main-content">
        <h1>QUESTION BANK - SEARCH TOOL</h1>

        {/* Model loading banner */}
        {filters.semanticOn && !modelReady && (
          <p style={{
            background: '#fff8e1', border: '1px solid #f9a825', borderRadius: 6,
            padding: '6px 12px', fontSize: 13, color: '#6d4c00', margin: '0 0 8px'
          }}>
            ⏳ Semantic model loading… first search may take 1–2 min. Subsequent searches are instant.
          </p>
        )}

        {/* Semantic count */}
        {result?.semantic_count > 0 && (
          <p className="caption">Semantic search: {result.semantic_count} related results found</p>
        )}

        {/* Related terms */}
        {filters.semanticOn && hasText && (
          <RelatedTerms
            terms={relatedTerms}
            activeTerm={activeTerm}
            onTermClick={handleTermClick}
          />
        )}

        {/* Waves in period */}
        {result?.waves_in_period?.length > 0 && (
          <>
            <p className="caption">Waves in this period ({result.waves_in_period.length}):</p>
            <div className="wave-links-container">
              {result.waves_in_period.map(w => (
                <button key={w} className="wave-link" onClick={() => handleShowWave(w, '')}>
                  {w}
                </button>
              ))}
            </div>
          </>
        )}

        {/* Pagination + results header */}
        <Pagination page={page} total={total} perPage={filters.perPage} onPageChange={setPage} />
        <div className="results-header">Results: {total.toLocaleString()}</div>

        {/* Table */}
        {loading ? (
          <div className="loading">Loading…</div>
        ) : (
          <ResultsTable
            rows={rows}
            qExact={qExact}
            qExpanded={qExpanded}
            aExact={aExact}
            aExpanded={aExpanded}
            onShowWave={handleShowWave}
            onShowQWaves={handleShowQWaves}
          />
        )}

        {/* Download */}
        <div className="download-row">
          <button className="download-btn" onClick={() => handleDownload('csv')}>
            Download CSV ({total.toLocaleString()} results)
          </button>
          <button className="download-btn" onClick={() => handleDownload('xlsx')}>
            Download Excel ({total.toLocaleString()} results)
          </button>
        </div>
      </main>
    </div>
  )
}
