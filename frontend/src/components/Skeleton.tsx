/** โครงร่างสีจางระหว่างโหลด แทนข้อความ "กำลังโหลด…" */
export function SkeletonList({ rows = 4 }: { rows?: number }) {
  return (
    <div className="list" aria-busy="true" aria-label="กำลังโหลด">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="list-item skeleton-item">
          <span className="sk sk-square" />
          <span className="list-main">
            <span className="sk sk-line" style={{ width: `${60 - i * 7}%` }} />
            <span className="sk sk-line sk-thin" style={{ width: '40%' }} />
          </span>
          <span className="sk sk-pill" />
        </div>
      ))}
    </div>
  );
}

export function SkeletonCard({ lines = 3 }: { lines?: number }) {
  return (
    <div className="card stack-sm" aria-busy="true" aria-label="กำลังโหลด">
      <span className="sk sk-line" style={{ width: '45%', height: 22 }} />
      {Array.from({ length: lines }, (_, i) => (
        <span key={i} className="sk sk-line" style={{ width: `${90 - i * 15}%` }} />
      ))}
    </div>
  );
}
