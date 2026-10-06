import { Typography } from 'antd'
import { WalletOutlined } from '@ant-design/icons'
import useMediaQuery from '../../hooks/useMediaQuery'

const { Title, Text } = Typography

/**
 * AuthLayout - 登录/注册共享外壳
 * 桌面端：左侧品牌区（主色渐变 + 账本横线纹理）+ 右侧表单区
 * 移动端：顶部紧凑品牌横幅 + 全宽表单
 *
 * 品牌区叠在深色渐变之上，其上的白系层次（卡片底、描边、次要文字）统一取
 * --color-on-brand-* 令牌，不再各处手写 rgba(255,255,255,0.x) ——
 * 换主色时这些层次会随渐变一起保持正确的对比关系。
 *
 * @param {string} props.brandTitle - 品牌区主标题
 * @param {string} props.brandSubtitle - 品牌区副标题
 * @param {ReactNode} props.children - 表单内容（渲染在右侧/下方）
 */
export default function AuthLayout({ brandTitle, brandSubtitle, children }) {
  const isMobile = useMediaQuery('(max-width: 767px)')

  /* 账本横线纹理：叠加在品牌渐变上的极淡水平细线 */
  const brandBg = {
    background: 'var(--gradient-brand)',
    backgroundImage:
      'repeating-linear-gradient(0deg, var(--color-on-brand-faint) 0px, var(--color-on-brand-faint) 1px, transparent 1px, transparent 32px), var(--gradient-brand)',
  }

  const logoBlock = (compact) => (
    <div style={{
      textAlign: 'center',
      position: 'relative',
      zIndex: 1,
      padding: compact ? 'var(--space-2xl) var(--space-xl)' : 0,
    }}>
      {/* Icon box */}
      <div style={{
        width: compact ? 56 : 80,
        height: compact ? 56 : 80,
        borderRadius: compact ? 'var(--radius-lg)' : 'var(--radius-xl)',
        background: 'var(--color-on-brand-soft)',
        border: '1px solid var(--color-on-brand-line)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        margin: '0 auto',
        marginBottom: compact ? 'var(--space-base)' : 'var(--space-xl)',
      }}>
        <WalletOutlined style={{ fontSize: compact ? 26 : 36, color: 'var(--color-on-brand-text-strong)' }} />
      </div>

      <Title
        level={compact ? 4 : 2}
        style={{
          color: 'var(--color-on-brand-text-strong)',
          marginBottom: compact ? 'var(--space-xs)' : 'var(--space-md)',
          fontWeight: 'var(--font-weight-bold)',
        }}
      >
        {brandTitle}
      </Title>
      <Text style={{
        color: 'var(--color-on-brand-text)',
        fontSize: compact ? 'var(--font-size-base)' : 'var(--font-size-md)',
      }}>
        {brandSubtitle}
      </Text>

      {/* Feature pills (desktop only) */}
      {!compact && (
        <div style={{
          display: 'flex',
          gap: 'var(--space-sm)',
          justifyContent: 'center',
          marginTop: 'var(--space-2xl)',
          flexWrap: 'wrap',
        }}>
          {['可视化统计', 'AI智能记账', '多设备同步'].map(tag => (
            <span key={tag} style={{
              padding: 'var(--space-xs) var(--space-md)',
              borderRadius: 'var(--radius-full)',
              background: 'var(--color-on-brand-weak)',
              border: '1px solid var(--color-on-brand-line)',
              fontSize: 'var(--font-size-sm)',
              color: 'var(--color-on-brand-text-strong)',
              fontWeight: 'var(--font-weight-medium)',
            }}>
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  )

  /* ── Mobile Layout ── */
  if (isMobile) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', background: 'var(--color-surface)' }}>
        <div style={{ ...brandBg, position: 'relative', overflow: 'hidden' }}>
          {/* Decorative circle */}
          <div style={{
            position: 'absolute', top: -40, right: -40,
            width: 160, height: 160, borderRadius: '50%',
            background: 'var(--color-on-brand-faint)',
          }} />
          {logoBlock(true)}
        </div>
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'flex-start',
          padding: 'var(--space-3xl) var(--space-xl) var(--space-xl)',
        }}>
          <div style={{ width: '100%', maxWidth: 360, margin: '0 auto' }}>
            {children}
          </div>
        </div>
      </div>
    )
  }

  /* ── Desktop Layout: left brand + right form ── */
  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--color-bg)' }}>
      {/* Left brand panel */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        padding: 'var(--space-5xl)',
        position: 'relative',
        overflow: 'hidden',
        ...brandBg,
      }}>
        {/* Decorative blobs */}
        <div style={{ position: 'absolute', top: '8%', left: '8%', width: 280, height: 280, borderRadius: '50%', background: 'var(--color-on-brand-faint)' }} />
        <div style={{ position: 'absolute', bottom: '18%', right: '12%', width: 180, height: 180, borderRadius: '50%', background: 'var(--color-on-brand-faint)' }} />
        {logoBlock(false)}
      </div>

      {/* Right form panel */}
      <div style={{
        width: 480,
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        padding: 'var(--space-5xl)',
        background: 'var(--color-surface)',
        borderLeft: '1px solid var(--color-border)',
      }}>
        <div style={{ width: '100%', maxWidth: 360 }}>
          {children}
        </div>
      </div>
    </div>
  )
}
