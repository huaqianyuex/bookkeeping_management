import { Card } from 'antd'

/**
 * StatCard - Reusable statistics card with responsive mobile/desktop variants
 *
 * @param {Object} props
 * @param {ReactNode} props.icon - Icon component (e.g., ArrowUpOutlined)
 * @param {string} props.label - Label text (e.g., "本月收入")
 * @param {number|string} props.value - Numeric value to display
 * @param {'income'|'expense'|'balance'} props.color - Color variant
 * @param {number} [props.balance] - For 'balance' color: used to determine if positive/negative
 * @param {boolean} [props.compact=false] - Use compact/mobile layout (top border style)
 * @param {number} [props.precision=2] - Decimal precision for value display
 */
export default function StatCard({
  icon: Icon,
  label,
  value,
  color = 'income',
  balance,
  compact = false,
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
  }

  const resolved = colorMap[color]
  const displayValue = typeof value === 'number' ? value.toFixed(precision) : value

  /* ── Compact (mobile) variant: top border + inline stat ── */
  if (compact) {
    return (
      <Card
        variant="borderless"
        className="card-base"
        style={{ borderTop: `3px solid ${resolved.borderColor}` }}
      >
        <div style={{ textAlign: compact ? 'center' : 'left' }}>
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
            justifyContent: compact ? 'center' : 'flex-start',
            gap: '4px',
            marginTop: '4px',
          }}>
            {Icon && <Icon style={{ fontSize: 14, color: resolved.accentColor }} />}
            <span style={{
              color: resolved.accentColor,
              fontWeight: 'var(--font-weight-semibold)',
              fontSize: 'var(--font-size-base)',
            }}>
              ¥{displayValue}
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
        <div>
          <span style={{
            color: 'var(--color-text-secondary)',
            fontSize: 'var(--font-size-base)',
          }}>
            {label}
          </span>
          <div style={{
            fontSize: 'var(--font-size-2xl)',
            fontWeight: 'var(--font-weight-bold)',
            color: resolved.accentColor,
            marginTop: '4px',
            letterSpacing: '-0.02em',
          }}>
            ¥{displayValue}
          </div>
        </div>
      </div>
    </Card>
  )
}
