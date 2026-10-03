import { Card } from 'antd'

/**
 * StatCard - Reusable statistics card with responsive mobile/desktop variants
 *
 * @param {Object} props
 * @param {ReactNode} props.icon - Icon component (e.g., ArrowUpOutlined)
 * @param {string} props.label - Label text (e.g., "本月收入")
 * @param {number|string} props.value - Numeric value to display
 * @param {'income'|'expense'|'balance'|'primary'|'info'|'warning'} props.color - Color variant
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
  const colorMap = {
    income: {
      iconBg: 'gradient-icon--success',
      accentColor: 'var(--color-success)',
      borderColor: 'var(--color-success)',
    },
    expense: {
      iconBg: 'gradient-icon--danger',
      accentColor: 'var(--color-danger)',
      borderColor: 'var(--color-danger)',
    },
    balance: {
      iconBg: (balance ?? 0) >= 0 ? 'gradient-icon--balance-positive' : 'gradient-icon--balance-negative',
      accentColor: (balance ?? 0) >= 0 ? 'var(--color-primary)' : 'var(--color-danger)',
      borderColor: (balance ?? 0) >= 0 ? 'var(--color-success)' : 'var(--color-danger)',
    },
    primary: {
      iconBg: 'gradient-icon--primary',
      accentColor: 'var(--color-primary)',
      borderColor: 'var(--color-primary)',
    },
    info: {
      iconBg: 'gradient-icon--info',
      accentColor: 'var(--color-info)',
      borderColor: 'var(--color-info)',
    },
    warning: {
      iconBg: 'gradient-icon--warning',
      accentColor: '#d3a000',
      borderColor: 'var(--color-warning)',
    },
  }

  const resolved = colorMap[color]
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
        style={{ borderTop: `3px solid ${resolved.borderColor}` }}
      >
        <div style={{ textAlign: 'center' }}>
          <span style={{
            color: 'var(--color-text-secondary)',
            fontSize: 'var(--font-size-sm)',
            fontWeight: 'var(--font-weight-normal)',
          }}>
            {label}
          </span>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '4px',
            marginTop: '4px',
          }}>
            {Icon && <Icon style={{ fontSize: 14, color: resolved.accentColor }} />}
            <span className="money" style={{
              color: resolved.accentColor,
              fontWeight: 'var(--font-weight-semibold)',
              fontSize: 'var(--font-size-base)',
            }}>
              {sign}{prefix}{displayValue}
            </span>
          </div>
        </div>
      </Card>
    )
  }

  /* ── Desktop variant: gradient icon + large value ── */
  return (
    <Card variant="borderless" className="card-base">
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div className={`gradient-icon ${resolved.iconBg}`}>
          <Icon style={{ fontSize: '24px', color: '#fff' }} />
        </div>
        <div style={{ minWidth: 0 }}>
          <span style={{
            color: 'var(--color-text-secondary)',
            fontSize: 'var(--font-size-base)',
          }}>
            {label}
          </span>
          <div className="money" style={{
            fontSize: 'var(--font-size-2xl)',
            fontWeight: 'var(--font-weight-bold)',
            color: resolved.accentColor,
            marginTop: '4px',
            letterSpacing: '-0.02em',
          }}>
            {sign}{prefix}{displayValue}
          </div>
        </div>
      </div>
    </Card>
  )
}
