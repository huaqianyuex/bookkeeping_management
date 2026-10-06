import { Skeleton, Card, Row, Col } from 'antd'

/**
 * SkeletonCard - Loading skeleton matching the shape of a StatCard or data card
 *
 * ⚠ 形状必须与真实内容同构，否则加载完成的瞬间会跳版。
 *   历史上桌面统计卡片的骨架渲染了一个 56×56 的图标方块，
 *   而 StatCard 桌面版早已改成"标签 + 大数字"的纯文字版式 ——
 *   骨架多出一个方块、少两行文字，加载完成时整行高度会缩水。
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
              borderBottom: i < rows - 1 ? '1px solid var(--color-border)' : 'none',
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

  /* Compact（移动端）变体：对齐 StatCard compact —— 顶部语义色条 + 居中两行 */
  if (compact) {
    return (
      <Card
        variant="borderless"
        className="card-base"
        style={{ borderTop: '3px solid var(--color-border)' }}
        styles={{ body: { padding: '12px 8px' } }}
      >
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 'var(--space-xs)',
        }}>
          <Skeleton.Input active={active} size="small" style={{ width: 48, minWidth: 48 }} />
          <Skeleton.Input active={active} size="small" style={{ width: 72, minWidth: 72 }} />
        </div>
      </Card>
    )
  }

  /* 桌面变体：对齐 StatCard 桌面版 —— 一行小标签 + 一行大数字，无图标方块 */
  return (
    <Card
      variant="borderless"
      className="card-base"
      styles={{ body: { padding: '14px 18px' } }}
    >
      <Skeleton.Input active={active} size="small" style={{ width: 76, minWidth: 76 }} />
      <div style={{ marginTop: 'var(--space-xs)' }}>
        <Skeleton.Input active={active} style={{ width: 132, minWidth: 132, height: 24 }} />
      </div>
    </Card>
  )
}

/**
 * Grid of SkeletonCards for the stats row.
 *
 * 用 Row/Col 而非 CSS Grid：Dashboard 的真实统计行用的是 Row/Col，
 * 骨架若用 .stats-grid 则两者的 gutter 与列宽算法不同（Row 的 gutter 走负外边距），
 * 加载前后会有细微位移。
 */
export function StatsRowSkeleton({ count = 3, compact = false }) {
  const span = Math.max(1, Math.floor(24 / count))
  const gutter = compact ? [8, 8] : [16, 16]

  return (
    <Row gutter={gutter} style={{ marginBottom: 'var(--space-base)' }}>
      {Array.from({ length: count }).map((_, i) => (
        <Col xs={span} md={span} key={i}>
          <SkeletonCard type="stat" compact={compact} />
        </Col>
      ))}
    </Row>
  )
}
