import { Typography } from 'antd'
import useMediaQuery from '../../hooks/useMediaQuery'

const { Title } = Typography

/**
 * PageHeader - Responsive page header with title and optional action area
 *
 * @param {Object} props
 * @param {string} props.title - Page title
 * @param {ReactNode} [props.action] - Optional action element(s) on the right side
 * @param {string} [props.subtitle] - Optional subtitle text below the title
 */
export default function PageHeader({ title, action, subtitle }) {
  const isMobile = useMediaQuery('(max-width: 767px)')

  return (
    <div
      className="page-header"
      style={{
        marginBottom: 'var(--space-xl)',
        display: 'flex',
        justifyContent: isMobile ? 'center' : 'space-between',
        alignItems: isMobile && !action ? 'center' : 'flex-start',
        flexDirection: isMobile && action ? 'column' : 'row',
        gap: isMobile && action ? 'var(--space-base)' : 0,
      }}
    >
      <div>
        <Title
          level={isMobile ? 5 : 4}
          style={{
            margin: 0,
            color: 'var(--color-text)',
            fontWeight: 'var(--font-weight-bold)',
            letterSpacing: '-0.01em',
          }}
        >
          {title}
        </Title>
        {subtitle && (
          <p
            style={{
              margin: 'var(--space-xs) 0 0',
              color: 'var(--color-text-secondary)',
              fontSize: 'var(--font-size-base)',
            }}
          >
            {subtitle}
          </p>
        )}
      </div>
      {action && <div style={{ flexShrink: 0 }}>{action}</div>}
    </div>
  )
}
