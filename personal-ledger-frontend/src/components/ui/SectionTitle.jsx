import { Typography } from 'antd'

const { Text } = Typography

/**
 * SectionTitle - Section header with a colored dot decoration
 *
 * @param {Object} props
 * @param {string} props.title - Title text
 * @param {'primary'|'success'|'danger'|'info'|'warning'} [props.dotColor='primary'] - Dot color variant
 * @param {ReactNode} [props.extra] - Extra content rendered on the right side
 */
export default function SectionTitle({ title, dotColor = 'primary', extra }) {
  return (
    <div
      className="section-title"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span className={`color-dot color-dot--${dotColor}`} />
        <Text strong style={{
          color: 'var(--color-text)',
          fontSize: 'var(--font-size-md)',
          letterSpacing: '0.01em',
        }}>
          {title}
        </Text>
      </div>
      {extra && <div>{extra}</div>}
    </div>
  )
}
