import { Button, Typography } from 'antd'
import { WarningOutlined, ReloadOutlined } from '@ant-design/icons'

const { Text } = Typography

/**
 * ErrorState - 请求失败时的常驻可见错误状态
 *
 * 存在的理由：页面原先只在 toast 里报错。axios 拦截器对 4xx/5xx/断网一律
 * Promise.reject，而各页 fetchData 未包 try/catch —— 一旦请求失败，
 * setLoading(false) 不会执行，界面会永久停在骨架屏且无任何重试入口。
 * 本组件把失败显式呈现出来，并提供重试。
 *
 * 与 EmptyState 保持同一套版式语言（同 padding / min-height / 字号 token），
 * 二者构成「无数据」与「取不到数据」两个并列状态。
 *
 * @param {Object} props
 * @param {string} [props.title='加载失败'] - 主标题
 * @param {string} [props.description] - 错误详情，优先传后端返回的 message
 * @param {() => void} [props.onRetry] - 重试回调；提供时才渲染重试按钮
 * @param {string} [props.retryText='重试'] - 重试按钮文案
 */
export default function ErrorState({
  title = '加载失败',
  description,
  onRetry,
  retryText = '重试',
}) {
  return (
    <div
      role="alert"
      aria-live="assertive"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 'var(--space-4xl) var(--space-xl)',
        minHeight: '240px',
        textAlign: 'center',
      }}
    >
      <div
        aria-hidden="true"
        style={{
          width: 56,
          height: 56,
          borderRadius: 'var(--radius-xl)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--color-danger-bg)',
          color: 'var(--color-danger)',
          fontSize: 26,
          marginBottom: 'var(--space-lg)',
          flexShrink: 0,
        }}
      >
        <WarningOutlined />
      </div>

      <Text
        strong
        style={{
          fontSize: 'var(--font-size-lg)',
          color: 'var(--color-text)',
          display: 'block',
          marginBottom: description ? 'var(--space-xs)' : 0,
        }}
      >
        {title}
      </Text>

      {description && (
        <Text
          type="secondary"
          style={{
            fontSize: 'var(--font-size-base)',
            lineHeight: 'var(--line-height-relaxed)',
            maxWidth: 420,
            marginTop: 'var(--space-sm)',
            marginBottom: onRetry ? 'var(--space-lg)' : 0,
          }}
        >
          {description}
        </Text>
      )}

      {onRetry && (
        <Button icon={<ReloadOutlined />} onClick={onRetry}>
          {retryText}
        </Button>
      )}
    </div>
  )
}