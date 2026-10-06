import useMediaQuery from '../../hooks/useMediaQuery'

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
      style={isMobile && action ? { flexDirection: 'column', alignItems: 'stretch' } : undefined}
    >
      <div>
        <h2 className="page-header__title">{title}</h2>
        {subtitle && <p className="page-header__subtitle">{subtitle}</p>}
      </div>
      {action && <div style={{ flexShrink: 0 }}>{action}</div>}
    </div>
  )
}
