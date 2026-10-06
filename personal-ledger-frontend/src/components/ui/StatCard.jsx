import { Card } from 'antd'

/**
 * StatCard - Reusable statistics card with responsive mobile/desktop variants
 *
 * @param {Object} props
 * @param {ReactNode} props.icon - Icon component (e.g., ArrowUpOutlined)
 * @param {string} props.label - Label text (e.g., "本月收入")
 * @param {number|string} props.value - Numeric value to display
 * @param {'income'|'expense'|'balance'|'primary'|'info'|'warning'|'accent'} props.color - Color variant
 * @param {number} [props.balance] - For 'balance' color: used to determine if positive/negative
 * @param {boolean} [props.compact=false] - Use compact/mobile layout (top border style)
 * @param {string} [props.prefix='¥'] - Value prefix; pass '' for count stats
 * @param {number} [props.precision=2] - Decimal precision for money values
 */
export default function StatCard({
  icon: Icon,
  label,
  value,
  color = 'income',
  balance,
  compact = false,
  prefix = '¥',
  precision = 2,
}) {
  /* 每个语义位只求解一次色值。
     结余（balance）此前数字用主色、顶部色条却用成功/危险色，同一张卡片出现两种
     语义——现统一按正负取主色 / 危险色：结余是派生指标，不该与"收入"共用绿色。 */
  const isBalancePositive = (balance ?? 0) >= 0
  const colorMap = {
    income: { accentColor: 'var(--color-success)' },
    expense: { accentColor: 'var(--color-danger)' },
    balance: { accentColor: isBalancePositive ? 'var(--color-primary)' : 'var(--color-danger)' },
    primary: { accentColor: 'var(--color-primary)' },
    info: { accentColor: 'var(--color-info)' },
    warning: { accentColor: 'var(--color-warning)' },
    accent: { accentColor: 'var(--color-accent)' },
  }

  const resolved = colorMap[color] || colorMap.income
  const isMoney = prefix === '¥'
  const num = typeof value === 'number' ? value : null
  const displayValue = num !== null
    ? Math.abs(num).toLocaleString('zh-CN', {
        minimumFractionDigits: isMoney ? precision : 0,
        maximumFractionDigits: isMoney ? precision : 0,
      })
    : value
  const sign = num !== null && num < 0 ? '-' : ''

  /* ── Compact (mobile) variant: top border + inline stat ── */
  if (compact) {
    return (
      <Card
        variant="borderless"
        className="card-base"
        styles={{ body: { padding: 'var(--space-md) var(--space-sm)' } }}
        style={{ borderTop: `3px solid ${resolved.accentColor}` }}
      >
        <div style={{ textAlign: 'center' }}>
          <span style={{
            color: 'var(--color-text-secondary)',
            fontSize: 'var(--font-size-xs)',
            fontWeight: 'var(--font-weight-normal)',
            display: 'block',
            marginBottom: 'var(--space-xs)',
          }}>
            {label}
          </span>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 'var(--space-xs)',
          }}>
            {Icon && <Icon style={{ fontSize: 'var(--font-size-sm)', color: resolved.accentColor }} />}
            <span className="money" style={{
              color: resolved.accentColor,
              fontWeight: 'var(--font-weight-semibold)',
              fontSize: 'var(--font-size-base)',
              lineHeight: 'var(--line-height-tight)',
            }}>
              {sign}{prefix}{displayValue}
            </span>
          </div>
        </div>
      </Card>
    )
  }

  /* ── Desktop variant: number-first, no decorative icon block ── */
  return (
    <Card
      variant="borderless"
      className="card-base"
      styles={{ body: { padding: 'var(--space-md) var(--space-lg)' } }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)' }}>
        {Icon && <Icon style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-tertiary)' }} />}
        <span style={{
          color: 'var(--color-text-secondary)',
          fontSize: 'var(--font-size-sm)',
          fontWeight: 'var(--font-weight-medium)',
        }}>
          {label}
        </span>
      </div>
      <div className="money" style={{
        fontSize: 'var(--font-size-2xl)',
        fontWeight: 'var(--font-weight-semibold)',
        color: resolved.accentColor,
        marginTop: 'var(--space-xs)',
        lineHeight: 'var(--line-height-tight)',
        letterSpacing: '-0.02em',
      }}>
        {sign}{prefix}{displayValue}
      </div>
    </Card>
  )
}
