import { Tag } from 'antd'

/**
 * SemanticTag - 语义色标签的统一实现
 *
 * 存在的理由：原先表格里的标签有三套互不相同的写法 ——
 *   · AdminUsers：   <Tag color="gold">          → antd 预设金，与调色板完全无关
 *   · Records 等：   <Tag color="success|error"> → 走 antd 默认绿/红
 *   · AdminFaq：     <Tag style={{...}}>          → 内联手写 var(--color-primary)
 * 结果同一行表格里「类型」标签的绿和「金额」的绿不是同一个绿。
 * 本组件把「文字色 + 底色 + 描边色」三件套收敛成一份映射。
 *
 * 用内联样式而非 CSS 类：antd 的 .ant-tag 在运行时注入 <head>，
 * 与外部样式表的层叠顺序不受本仓库控制；内联样式可确定性地覆盖。
 *
 * @param {Object} props
 * @param {'primary'|'success'|'danger'|'warning'|'info'|'accent'|'neutral'} [props.variant='neutral']
 * @param {ReactNode} props.children
 */
const VARIANTS = {
  primary: {
    color: 'var(--color-primary)',
    background: 'var(--color-primary-bg)',
    borderColor: 'var(--color-primary-border)',
  },
  success: {
    color: 'var(--color-success)',
    background: 'var(--color-success-bg)',
    borderColor: 'var(--color-success-border)',
  },
  danger: {
    color: 'var(--color-danger)',
    background: 'var(--color-danger-bg)',
    borderColor: 'var(--color-danger-border)',
  },
  warning: {
    color: 'var(--color-warning)',
    background: 'var(--color-warning-bg)',
    borderColor: 'var(--color-warning-border)',
  },
  info: {
    color: 'var(--color-info)',
    background: 'var(--color-info-bg)',
    borderColor: 'var(--color-info-border)',
  },
  accent: {
    color: 'var(--color-accent)',
    background: 'var(--color-accent-bg)',
    borderColor: 'var(--color-accent-border)',
  },
  neutral: {
    color: 'var(--color-text-secondary)',
    background: 'var(--color-bg-subtle)',
    borderColor: 'var(--color-border)',
  },
}

export default function SemanticTag({ variant = 'neutral', children, style, ...rest }) {
  const variantStyle = VARIANTS[variant] || VARIANTS.neutral

  return (
    <Tag
      {...rest}
      style={{
        ...variantStyle,
        fontWeight: 'var(--font-weight-medium)',
        ...style,
      }}
    >
      {children}
    </Tag>
  )
}
