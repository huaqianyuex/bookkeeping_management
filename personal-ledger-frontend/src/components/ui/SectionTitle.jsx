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
    <div className="section-title">
      <div className="section-title__left">
        <span className={`color-dot color-dot--${dotColor}`} />
        <span className="section-title__text">{title}</span>
      </div>
      {extra && <div>{extra}</div>}
    </div>
  )
}
