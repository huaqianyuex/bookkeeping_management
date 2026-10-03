import { Skeleton, Card } from 'antd'

/**
 * SkeletonCard - Loading skeleton matching the shape of a StatCard or data card
 *
 * @param {Object} props
 * @param {'stat'|'table'} [props.type='stat'] - Skeleton shape: stat card or table-like
 * @param {number} [props.rows=1] - Number of skeleton rows for table type
 * @param {boolean} [props.active=true] - Show shimmer animation
 * @param {boolean} [props.compact=false] - Match the compact (mobile) StatCard shape
 */
export default function SkeletonCard({ type = 'stat', rows = 1, active = true, compact = false }) {
  if (type === 'table') {
    return (
      <Card variant="borderless" className="card-base">
        <Skeleton active={active}>
          {/* Table header row */}
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-base)' }}>
            <Skeleton.Input active={active} size="small" style={{ width: 120 }} />
            <Skeleton.Button active={active} size="small" />
          </div>
          {/* Data rows */}
          {Array.from({ length: rows }).map((_, i) => (
            <div key={i} style={{
              display: 'flex',
              alignItems: 'center',
              padding: '12px 0',
              borderBottom: i < rows - 1 ? `1px solid var(--color-border)` : 'none',
            }}>
              <Skeleton.Avatar active={active} size="small" style={{ marginRight: 12 }} />
              <Skeleton.Input active={active} size="small" style={{ width: '40%', marginRight: 16 }} />
              <Skeleton.Input active={active} size="small" style={{ width: '30%' }} />
            </div>
          ))}
        </Skeleton>
      </Card>
    )
  }

  /* Compact stat skeleton: matches the mobile StatCard (top accent border) */
  if (compact) {
    return (
      <Card variant="borderless" className="card-base" style={{ borderTop: '3px solid var(--color-border)' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
          <Skeleton.Input active={active} size="small" style={{ width: 56 }} />
          <Skeleton.Input active={active} size="small" style={{ width: 72 }} />
        </div>
      </Card>
    )
  }

  /* Stat-card shaped skeleton (desktop variant with icon placeholder) */
  return (
    <Card variant="borderless" className="card-base">
      <Skeleton active={active}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <Skeleton.Node active={active} style={{ width: 56, height: 56, borderRadius: 'var(--radius-xl)' }} />
          <div style={{ flex: 1 }}>
            <Skeleton.Input active={active} size="small" style={{ width: 100, marginBottom: 8 }} />
            <Skeleton.Input active={active} size="default" style={{ width: 140 }} />
          </div>
        </div>
      </Skeleton>
    </Card>
  )
}

/** Grid of SkeletonCards for the stats row (3 columns, matches the StatCard row) */
export function StatsRowSkeleton({ count = 3, compact = false }) {
  const items = Array.from({ length: count })

  return (
    <div className="stats-grid">
      {items.map((_, i) => (
        <SkeletonCard key={i} type="stat" compact={compact} />
      ))}
    </div>
  )
}
