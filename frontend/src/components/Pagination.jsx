export default function Pagination({ page, total, perPage, onPageChange }) {
  const totalPages = Math.ceil(total / perPage) || 1
  return (
    <div className="pagination">
      <button onClick={() => onPageChange(page - 1)} disabled={page <= 1}>⬅️ Previous</button>
      <span className="page-info">
        Page {page} / {totalPages} — {total.toLocaleString()} results
      </span>
      <button onClick={() => onPageChange(page + 1)} disabled={page >= totalPages}>Next ➡️</button>
    </div>
  )
}
