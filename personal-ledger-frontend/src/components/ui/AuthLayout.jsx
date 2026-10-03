import { Typography } from 'antd'
import { WalletOutlined } from '@ant-design/icons'
import useMediaQuery from '../../hooks/useMediaQuery'

const { Title, Text } = Typography

/**
 * AuthLayout - 登录/注册共享外壳
 * 桌面端：左侧品牌区（深蓝渐变 + 账本横线纹理）+ 右侧表单区
 * 移动端：顶部紧凑品牌横幅 + 全宽表单
 *
 * @param {string} props.brandTitle - 品牌区主标题
 * @param {string} props.brandSubtitle - 品牌区副标题
 * @param {ReactNode} props.children - 表单内容（渲染在右侧/下方）
 */
export default function AuthLayout({ brandTitle, brandSubtitle, children }) {
  const isMobile = useMediaQuery('(max-width: 767px)')

  /* 账本横线纹理：叠加在品牌渐变上的极淡水平细线 */
  const brandBackground = {
    backgroundColor: 'var(--color-primary)',
    backgroundImage:
      'repeating-linear-gradient(0deg, rgba(255, 255, 255, 0.045) 0px, rgba(255, 255, 255, 0.045) 1px, transparent 1px, transparent 32px), var(--gradient-primary)',
  }

  const brandContent = (compact) => (
    <div style={{
      textAlign: 'center',
      position: 'relative',
      zIndex: 1,
      padding: compact ? 'var(--space-3xl) var(--space-xl)' : 0,
    }}>
      <div style={{
        width: compact ? 56 : 80,
        height: compact ? 56 : 80,
        borderRadius: 'var(--radius-lg)',
        background: 'rgba(255, 255, 255, 0.1)',
        border: '1px solid rgba(255, 255, 255, 0.15)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        margin: '0 auto',
        marginBottom: compact ? 'var(--space-base)' : 'var(--space-2xl)',
      }}>
        <WalletOutlined style={{ fontSize: compact ? 26 : 36, color: '#fff' }} />
      </div>
      <Title level={compact ? 4 : 2} style={{ color: '#fff', marginBottom: compact ? 4 : 16, fontWeight: 700 }}>
        {brandTitle}
      </Title>
      <Text style={{ color: 'rgba(255, 255, 255, 0.7)', fontSize: compact ? 'var(--font-size-base)' : 16 }}>
        {brandSubtitle}
      </Text>
    </div>
  )

  if (isMobile) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        minHeight: '100vh',
        background: 'var(--color-surface)',
      }}>
        <div style={{ ...brandBackground, position: 'relative', overflow: 'hidden' }}>
          <div style={{
            position: 'absolute',
            top: -40,
            right: -40,
            width: 160,
            height: 160,
            borderRadius: '50%',
            background: 'rgba(255, 255, 255, 0.04)',
          }} />
          {brandContent(true)}
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

  return (
    <div style={{
      display: 'flex',
      minHeight: '100vh',
      background: 'var(--color-bg)',
    }}>
      {/* 左侧品牌区域 */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '60px',
        position: 'relative',
        overflow: 'hidden',
        ...brandBackground,
      }}>
        <div style={{
          position: 'absolute',
          top: '10%',
          left: '10%',
          width: 300,
          height: 300,
          borderRadius: '50%',
          background: 'rgba(255, 255, 255, 0.03)',
        }} />
        <div style={{
          position: 'absolute',
          bottom: '20%',
          right: '15%',
          width: 200,
          height: 200,
          borderRadius: '50%',
          background: 'rgba(255, 255, 255, 0.03)',
        }} />
        {brandContent(false)}
      </div>

      {/* 右侧表单区域 */}
      <div style={{
        width: 480,
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        padding: 60,
        background: 'var(--color-surface)',
      }}>
        <div style={{ width: '100%', maxWidth: 360 }}>
          {children}
        </div>
      </div>
    </div>
  )
}
