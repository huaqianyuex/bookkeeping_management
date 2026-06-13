import { Empty, Button, Typography } from 'antd'

const { Text } = Typography

/**
 * EmptyState - Styled empty state with icon, title, description & optional CTA
 *
 * @param {Object} props
 * @param {string} [props.title='暂无数据'] - Main heading
 * @param {string} [props.description] - Subtitle / descriptive paragraph
 * @param {ReactNode} [props.action] - Action button or custom node
 * @param {string|ReactNode} [props.image] - Custom image (uses AntD default if omitted)
 * @param {string} [props.size='large'] - Size of the empty illustration
 */
export default function EmptyState({
  title = '暂无数据',
  description,
  action,
  image,
  size = 'large',
}) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 'var(--space-4xl) var(--space-xl)',
      minHeight: '240px',
    }}>
      <Empty
        image={image || Empty.PRESENTED_IMAGE_SIMPLE}
        imageStyle={{
          height: size === 'large' ? 96 : 60,
          marginBottom: 'var(--space-lg)',
          opacity: 0.6,
        }}
        description={
          <div style={{ textAlign: 'center' }}>
            <Text strong style={{
              fontSize: 'var(--font-size-lg)',
              color: 'var(--color-text)',
              display: 'block',
              marginBottom: description ? 'var(--space-xs)' : 0,
            }}>
              {title}
            </Text>
            {description && (
              <Text type="secondary" style={{
                fontSize: 'var(--font-size-base)',
                lineHeight: 'var(--line-height-relaxed)',
              }}>
                {description}
              </Text>
            )}
          </div>
        }
      >
        {action}
      </Empty>
    </div>
  )
}
