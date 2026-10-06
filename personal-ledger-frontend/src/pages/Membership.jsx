import { useCallback, useEffect, useState } from 'react'
import { App as AntdApp, Button, Card, Input, Skeleton, Typography } from 'antd'
import {
  BarChartOutlined,
  CrownFilled,
  EditOutlined,
  GiftOutlined,
  MessageOutlined,
  RocketOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { getMembershipStatus, redeemMembership } from '../api/membership'
import {
  AnimatedRoute,
  ErrorState,
  PageHeader,
  SectionTitle,
  SemanticTag,
  SkeletonCard,
} from '../components/ui'
import useMediaQuery from '../hooks/useMediaQuery'
import { extractErrorMessage } from '../utils/error'

const { Text } = Typography

/**
 * 会员中心 — 等级 / 状态 / 有效期 / 今日用量 / 权益明细 / 兑换续费
 *
 * 数据契约：GET /api/membership/status（见 src/api/membership.js），
 *   data = { tier, tierName, expiresAt, benefits, usage }
 *   benefits 为后端 _benefits() 下发的 camelCase 键（dailyChat / concurrency /
 *   dailyAnalyze / dailyBookkeeping / premiumModel）。
 *
 * 渲染原则：额度、并发等具体数值一律来自接口响应，本文件不硬编码任何档位数值，
 * 后端 MEMBERSHIP_PLANS 调整时页面自动跟随。
 */

// 兑换码前端归一化（与服务端一致）：去空格/连字符、转大写，粘贴可友好
const normalizeCode = (raw) => (raw || '').replace(/[\s-]/g, '').toUpperCase()

/** 即将到期阈值（天）：剩余不超过该天数时状态徽章转为提醒 */
const EXPIRING_SOON_DAYS = 7

/**
 * 状态徽章：dark = 置于品牌渐变（等级卡深色态），此时用半透明白胶囊 +
 * 彩色圆点承载语义（白字对深底对比已由色板 onBrand 层校准）。
 */
function StatusBadge({ dark = false, dotColor, children }) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: '2px 10px',
        borderRadius: 'var(--radius-full)',
        fontSize: 'var(--font-size-sm)',
        fontWeight: 'var(--font-weight-medium)',
        whiteSpace: 'nowrap',
        ...(dark
          ? {
              background: 'var(--color-on-brand-weak)',
              border: '1px solid var(--color-on-brand-line)',
              color: 'var(--color-on-brand-text)',
            }
          : {
              background: 'var(--color-bg-subtle)',
              border: '1px solid var(--color-border)',
              color: 'var(--color-text-secondary)',
            }),
      }}
    >
      <span
        aria-hidden="true"
        className="color-dot"
        style={{ width: 6, height: 6, background: dotColor }}
      />
      {children}
    </span>
  )
}

/** 今日用量行：键与后端 usage 组包一致 */
const USAGE_ROWS = [
  { key: 'chat', icon: MessageOutlined, label: 'AI 对话' },
  { key: 'analyze', icon: BarChartOutlined, label: '账单分析' },
  { key: 'bookkeeping', icon: EditOutlined, label: 'AI 记账' },
]

/** 权益明细行：render 只做格式化，数值全部来自 status.benefits */
const BENEFIT_ROWS = [
  {
    key: 'dailyChat',
    icon: MessageOutlined,
    color: 'var(--color-primary)',
    label: 'AI 对话',
    render: (v) => `${v} 次 / 日`,
  },
  {
    key: 'dailyAnalyze',
    icon: BarChartOutlined,
    color: 'var(--color-info)',
    label: '账单智能分析',
    render: (v) => `${v} 次 / 日`,
  },
  {
    key: 'dailyBookkeeping',
    icon: EditOutlined,
    color: 'var(--color-success)',
    label: 'AI 智能记账',
    render: (v) => `${v} 次 / 日`,
  },
  {
    key: 'concurrency',
    icon: ThunderboltOutlined,
    color: 'var(--color-warning)',
    label: '并发请求',
    render: (v) => `${v} 路`,
  },
  {
    key: 'premiumModel',
    icon: RocketOutlined,
    color: 'var(--color-accent)',
    label: '高级 AI 模型',
    render: (v) =>
      v ? <SemanticTag variant="success">已启用</SemanticTag> : <SemanticTag variant="neutral">未启用</SemanticTag>,
  },
]

export default function Membership() {
  const { message } = AntdApp.useApp()
  const isMobile = useMediaQuery('(max-width: 767px)')

  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [code, setCode] = useState('')
  const [redeeming, setRedeeming] = useState(false)

  const fetchStatus = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getMembershipStatus()
      if (res?.code === 200 && res.data) {
        setStatus(res.data)
      } else {
        throw new Error(res?.message || '会员服务返回为空')
      }
    } catch (e) {
      setError(extractErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStatus()
  }, [fetchStatus])

  const handleRedeem = async () => {
    const normalized = normalizeCode(code)
    if (!normalized) {
      message.warning('请输入兑换码')
      return
    }
    setRedeeming(true)
    try {
      const res = await redeemMembership(normalized)
      if (res?.code === 200) {
        message.success(res.message || '兑换成功')
        setCode('')
        fetchStatus()
      } else {
        message.error(res?.message || '兑换失败，请稍后重试')
      }
    } catch (e) {
      message.error(extractErrorMessage(e))
    } finally {
      setRedeeming(false)
    }
  }

  // 粘贴即归一化：整段带空格/连字符的码粘贴进输入框时直接转为可提交格式
  const handlePaste = (e) => {
    const text = e.clipboardData?.getData('text') || ''
    if (/[\s-]/.test(text)) {
      e.preventDefault()
      setCode(normalizeCode(text))
    }
  }

  // 后端 tier=1 必带 expiresAt；万一天段数据缺失，按免费展示，避免 "Invalid Date"
  const isMember = status?.tier === 1 && !!status?.expiresAt
  const tierName = status?.tierName || '免费版'
  const expiresAt = status?.expiresAt ? dayjs(status.expiresAt) : null
  const daysLeft = expiresAt ? expiresAt.startOf('day').diff(dayjs().startOf('day'), 'day') : null
  const expiringSoon = isMember && daysLeft !== null && daysLeft >= 0 && daysLeft <= EXPIRING_SOON_DAYS
  const expired = isMember && daysLeft !== null && daysLeft < 0

  const heroDark = isMember && !expired
  const statusMeta = !isMember
    ? { label: '未开通', dot: 'var(--color-border-strong)' }
    : expired
      ? { label: '已到期', dot: 'var(--color-warning-border)' }
      : expiringSoon
        ? { label: '即将到期', dot: 'var(--color-warning-border)' }
        : { label: '生效中', dot: 'var(--color-success-border)' }

  const validityText = !isMember
    ? '兑换会员码，解锁更高 AI 额度与高级模型'
    : expired
      ? `已于 ${expiresAt.format('YYYY-MM-DD')} 到期，兑换续费码即可恢复会员权益`
      : `${expiresAt.format('YYYY-MM-DD')} 到期 · ${daysLeft === 0 ? '剩余不足 1 天' : `剩余 ${daysLeft} 天`}`

  const benefitRows = BENEFIT_ROWS.filter(
    (row) => status?.benefits && Object.prototype.hasOwnProperty.call(status.benefits, row.key),
  )

  const heroPadding = isMobile ? 'var(--space-lg)' : 'var(--space-xl)'

  if (loading) {
    return (
      <AnimatedRoute>
        <PageHeader title="会员中心" subtitle="会员等级、专属权益与今日 AI 用量" />
        <Card variant="borderless" className="card-base" style={{ marginBottom: 'var(--space-base)' }}>
          <div className="flex items-start gap-lg">
            <Skeleton.Avatar active size={48} shape="square" />
            <div className="flex-1">
              <Skeleton.Input active size="small" style={{ width: 120 }} />
              <div style={{ marginTop: 'var(--space-sm)' }}>
                <Skeleton.Input active size="small" style={{ width: 240 }} />
              </div>
            </div>
          </div>
          <div className="flex gap-sm" style={{ marginTop: 'var(--space-lg)' }}>
            <Skeleton.Input active style={{ flex: 1, maxWidth: 360 }} />
            <Skeleton.Button active />
          </div>
        </Card>
        <div className="col-7-3-grid">
          <SkeletonCard type="table" rows={3} />
          <SkeletonCard type="table" rows={3} />
        </div>
      </AnimatedRoute>
    )
  }

  if (error) {
    return (
      <AnimatedRoute>
        <PageHeader title="会员中心" subtitle="会员等级、专属权益与今日 AI 用量" />
        <ErrorState title="会员信息加载失败" description={error} onRetry={fetchStatus} />
      </AnimatedRoute>
    )
  }

  return (
    <AnimatedRoute>
      <PageHeader title="会员中心" subtitle="会员等级、专属权益与今日 AI 用量" />

      {/* ── 等级卡：等级 + 状态 + 有效期 + 兑换行 ── */}
      <div
        style={{
          position: 'relative',
          overflow: 'hidden',
          borderRadius: 'var(--radius-lg)',
          padding: heroPadding,
          marginBottom: 'var(--space-base)',
          background: heroDark ? 'var(--gradient-brand)' : 'var(--color-surface)',
          border: heroDark ? 'none' : '1px solid var(--color-border)',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        {heroDark && (
          <CrownFilled
            aria-hidden="true"
            style={{
              position: 'absolute',
              right: -16,
              bottom: -32,
              fontSize: 140,
              color: 'var(--color-on-brand-weak)',
              pointerEvents: 'none',
            }}
          />
        )}

        <div style={{ position: 'relative' }} className="flex items-start gap-lg">
          <div className={`gradient-icon${heroDark ? '' : ' gradient-icon--primary'}`}>
            <CrownFilled
              style={{
                fontSize: 22,
                color: heroDark ? 'var(--color-warning-border)' : 'var(--color-text-inverse)',
              }}
            />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center flex-wrap gap-sm">
              <span
                style={{
                  fontSize: 'var(--font-size-2xl)',
                  fontWeight: 'var(--font-weight-bold)',
                  lineHeight: 'var(--line-height-tight)',
                  color: heroDark ? 'var(--color-on-brand-text-strong)' : 'var(--color-text)',
                }}
              >
                {tierName}
              </span>
              <StatusBadge dark={heroDark} dotColor={statusMeta.dot}>
                {statusMeta.label}
              </StatusBadge>
            </div>
            <div
              style={{
                marginTop: 'var(--space-xs)',
                fontSize: 'var(--font-size-sm)',
                color: heroDark ? 'var(--color-on-brand-text)' : 'var(--color-text-secondary)',
              }}
            >
              {validityText}
            </div>
          </div>
        </div>

        <div
          style={{
            height: 1,
            background: heroDark ? 'var(--color-on-brand-line)' : 'var(--color-border)',
            margin: 'var(--space-lg) 0 var(--space-base)',
          }}
        />

        <div style={{ position: 'relative' }} className={isMobile ? 'flex-col gap-sm' : 'flex gap-sm'}>
          <Input
            className={isMobile ? '' : 'flex-1'}
            style={isMobile ? undefined : { maxWidth: 420 }}
            prefix={<GiftOutlined style={{ color: 'var(--color-text-tertiary)' }} />}
            placeholder="粘贴或输入 16 位兑换码"
            maxLength={32}
            allowClear
            value={code}
            onChange={(e) => setCode(e.target.value)}
            onPaste={handlePaste}
            onPressEnter={handleRedeem}
            disabled={redeeming}
          />
          <Button
            type={heroDark ? 'default' : 'primary'}
            loading={redeeming}
            onClick={handleRedeem}
            className={isMobile ? '' : 'shrink-0'}
            style={heroDark ? { color: 'var(--color-primary-deep)', fontWeight: 'var(--font-weight-semibold)' } : undefined}
          >
            {isMember ? '立即续费' : '立即开通'}
          </Button>
        </div>
        <div
          style={{
            position: 'relative',
            marginTop: 'var(--space-sm)',
            fontSize: 'var(--font-size-xs)',
            color: heroDark ? 'var(--color-on-brand-text)' : 'var(--color-text-tertiary)',
          }}
        >
          {isMember
            ? '续费天数自动叠加，会员未到期时兑换不损失剩余天数'
            : '兑换码由管理员发放，开通立即生效，有效期按码内天数累计'}
        </div>
      </div>

      {/* ── 今日用量 + 权益明细 ── */}
      <div className="col-7-3-grid">
        <div
          className="card-base"
          style={{
            padding: isMobile ? 'var(--space-base)' : 'var(--space-base) var(--space-xl)',
            height: '100%',
            boxSizing: 'border-box',
          }}
        >
          <SectionTitle
            title="今日用量"
            dotColor="primary"
            extra={
              <Text style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-tertiary)' }}>
                每日零点重置
              </Text>
            }
          />
          <div style={{ marginTop: 'var(--space-md)' }}>
            {USAGE_ROWS.map(({ key, icon: Icon, label }, idx) => {
              const item = status?.usage?.[key] ?? {}
              const used = Number(item.used ?? 0)
              const limit = Number(item.limit ?? 0)
              const pct = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0
              const exhausted = limit > 0 && used >= limit
              const hot = !exhausted && pct >= 80
              const color = exhausted
                ? 'var(--color-danger)'
                : hot
                  ? 'var(--color-warning)'
                  : 'var(--color-primary)'
              return (
                <div
                  key={key}
                  style={{
                    padding: 'var(--space-sm) 0',
                    borderBottom:
                      idx < USAGE_ROWS.length - 1 ? '1px solid var(--color-border-secondary)' : 'none',
                  }}
                >
                  <div className="flex-between gap-sm" style={{ marginBottom: 'var(--space-sm)' }}>
                    <span
                      className="flex items-center gap-sm min-w-0"
                      style={{ fontSize: 'var(--font-size-base)', color: 'var(--color-text)' }}
                    >
                      <Icon style={{ color, fontSize: 16, flexShrink: 0 }} />
                      <span className="truncate">{label}</span>
                      {exhausted && <SemanticTag variant="danger">已用尽</SemanticTag>}
                    </span>
                    <span
                      className="money shrink-0"
                      style={{
                        fontSize: 'var(--font-size-base)',
                        fontWeight: 'var(--font-weight-semibold)',
                        color: 'var(--color-text)',
                      }}
                    >
                      {used}
                      <span
                        style={{
                          color: 'var(--color-text-tertiary)',
                          fontWeight: 'var(--font-weight-normal)',
                        }}
                      >
                        {' '}
                        / {limit} 次
                      </span>
                    </span>
                  </div>
                  <div
                    className="progress-bar-track--wide"
                    role="progressbar"
                    aria-label={label}
                    aria-valuenow={used}
                    aria-valuemin={0}
                    aria-valuemax={limit}
                  >
                    <div className="progress-bar-fill" style={{ width: `${pct}%`, background: color }} />
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        <div
          className="card-base"
          style={{
            padding: isMobile ? 'var(--space-base)' : 'var(--space-base) var(--space-xl)',
            height: '100%',
            boxSizing: 'border-box',
          }}
        >
          <SectionTitle title="我的权益" dotColor="accent" />
          <div style={{ marginTop: 'var(--space-sm)' }}>
            {benefitRows.map(({ key, icon: Icon, color, label, render }, idx) => (
              <div
                key={key}
                className="flex-between gap-sm"
                style={{
                  padding: 'var(--space-sm) 0',
                  borderBottom:
                    idx < benefitRows.length - 1 ? '1px solid var(--color-border-secondary)' : 'none',
                }}
              >
                <span
                  className="flex items-center gap-sm min-w-0"
                  style={{ fontSize: 'var(--font-size-base)', color: 'var(--color-text)' }}
                >
                  <Icon style={{ color, fontSize: 16, flexShrink: 0 }} />
                  <span className="truncate">{label}</span>
                </span>
                <span
                  className="money shrink-0"
                  style={{
                    fontSize: 'var(--font-size-base)',
                    fontWeight: 'var(--font-weight-semibold)',
                    color: 'var(--color-text)',
                  }}
                >
                  {render(status.benefits[key])}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AnimatedRoute>
  )
}
