import { useState, useEffect, useMemo } from 'react'
import { Menu, Avatar, Dropdown, Button, Typography, Modal, Form, Input, Select, InputNumber, DatePicker, Tabs, App as AntdApp } from 'antd'
import {
  BookOutlined,
  AppstoreOutlined,
  UserOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  WalletOutlined,
  LockOutlined,
  SafetyOutlined,
  TeamOutlined,
  FileTextOutlined,
  QuestionCircleOutlined,
  RobotOutlined,
  SettingOutlined,
  PlusCircleOutlined,
  LineChartOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  CrownOutlined,
  TagsOutlined,
  TransactionOutlined,
} from '@ant-design/icons'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { getCategoryList } from '../api/category'
import { addRecord } from '../api/record'
import useMediaQuery from '../hooks/useMediaQuery'
import CommandPalette from './CommandPalette'
import dayjs from 'dayjs'

const { Text } = Typography

const menuItems = [
  { key: '/dashboard',  icon: <LineChartOutlined />, label: '数据概览' },
  { key: '/records',    icon: <BookOutlined />,      label: '账单管理' },
  { key: '/categories', icon: <AppstoreOutlined />,  label: '分类管理' },
  { key: '/ai-chat',   icon: <RobotOutlined />,     label: 'AI助手' },
  { key: '/membership', icon: <CrownOutlined />,     label: '会员中心' },
]

const adminMenuItems = [
  { key: '/admin/dashboard', icon: <SafetyOutlined />,        label: '系统概览' },
  { key: '/admin/users',     icon: <TeamOutlined />,          label: '用户管理' },
  { key: '/admin/records',   icon: <FileTextOutlined />,      label: '全量账单' },
  { key: '/admin/faq',       icon: <QuestionCircleOutlined />, label: 'FAQ管理' },
  { key: '/admin/membership', icon: <TagsOutlined />,         label: '会员管理' },
  { key: '/admin/recharges', icon: <TransactionOutlined />,   label: '充值审批' },
]

const breadcrumbMap = {
  '/dashboard':         '数据概览',
  '/records':           '账单管理',
  '/categories':        '分类管理',
  '/settings/profile':  '设置',
  '/settings/password': '设置',
  '/ai-chat':           'AI助手',
  '/membership':        '会员中心',
  '/admin/dashboard':   '系统概览',
  '/admin/users':       '用户管理',
  '/admin/records':     '全量账单',
  '/admin/faq':         'FAQ管理',
  '/admin/membership':  '会员管理',
  '/admin/recharges':   '充值审批',
}

export default function MainLayout() {
  const [collapsed, setCollapsed]     = useState(false)
  const [drawerOpen, setDrawerOpen]   = useState(false)
  const isMobile                      = useMediaQuery('(max-width: 767px)')
  const isMidWidth                    = useMediaQuery('(min-width: 768px) and (max-width: 1279px)')
  const [addModalOpen, setAddModalOpen] = useState(false)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [categories, setCategories]   = useState([])
  const [form]                        = Form.useForm()
  const [addLoading, setAddLoading]   = useState(false)
  const [quickType, setQuickType]     = useState('0')
  const navigate                      = useNavigate()
  const location                      = useLocation()
  const { user, fetchUserInfo, logout } = useAuth()
  const { message }                   = AntdApp.useApp()

  // 管理员的功能范围是管理后台，不参与记账与对话（权限矩阵见 utils/auth.py）
  const isAdmin = user?.role === 1

  useEffect(() => {
    // 等登录态就绪再判断：管理员无记账功能，拉分类列表会被后端 403，直接跳过
    if (!user || isAdmin) return
    getCategoryList().then(res => { if (res.code === 200) setCategories(res.data) })
  }, [user, isAdmin])

  useEffect(() => { if (!isMobile) setDrawerOpen(false) }, [isMobile])

  // 三档响应式：笔电/平板宽度自动收起为 icon rail，宽屏自动展开（用户仍可手动切换）
  useEffect(() => { if (!isMobile) setCollapsed(isMidWidth) }, [isMidWidth, isMobile])

  const handleQuickAdd = async () => {
    try {
      const values = await form.validateFields()
      setAddLoading(true)
      const res = await addRecord({ ...values, recordDate: values.recordDate.format('YYYY-MM-DD') })
      if (res.code === 200) {
        message.success('记账成功')
        setAddModalOpen(false)
        form.resetFields()
        setQuickType('0')
        window.dispatchEvent(new CustomEvent('record-added'))
      } else {
        message.error(res.message)
      }
    } catch { /* validation */ } finally { setAddLoading(false) }
  }

  useEffect(() => { fetchUserInfo() }, [])

  const handleLogout = () => { logout(); navigate('/login', { replace: true }) }

  const userMenuItems = [
    { key: 'info',     icon: <UserOutlined />,   label: '个人信息', onClick: () => navigate('/settings/profile') },
    { key: 'password', icon: <LockOutlined />,   label: '修改密码', onClick: () => navigate('/settings/password') },
    { type: 'divider' },
    { key: 'logout',   icon: <LogoutOutlined />, label: '退出登录', onClick: handleLogout },
  ]

  const allMenuItems = useMemo(() => {
    // 管理员只看到管理菜单：记账 / 分类 / AI 助手 / 会员中心对管理员均不可用（后端 403）
    if (isAdmin) return adminMenuItems
    return menuItems
  }, [isAdmin])

  const currentPageTitle = useMemo(() => breadcrumbMap[location.pathname] || '', [location.pathname])
  const quickCategories  = categories.filter(c => c.type === Number(quickType))

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setPaletteOpen(o => !o)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const paletteCommands = useMemo(() => {
    const navCmds = (isAdmin ? adminMenuItems : menuItems)
      .map(m => ({ key: m.key, label: m.label, icon: m.icon, hint: '跳转', run: () => navigate(m.key) }))
    const baseCmds = [
      { key: '/settings/profile', label: '设置', icon: <SettingOutlined />, hint: '跳转', run: () => navigate('/settings/profile') },
      ...navCmds,
    ]
    // 「快速记账」是用户侧功能，管理员不提供该入口
    if (isAdmin) return baseCmds
    return [
      { key: 'quick-add', label: '快速记账', icon: <PlusCircleOutlined />, hint: '操作', run: () => setAddModalOpen(true) },
      ...baseCmds,
    ]
  }, [isAdmin])

  /* ── Mobile Overlay ── */
  const mobileDrawer = drawerOpen && isMobile && (
    <>
      {/* Backdrop —— 遮罩配色/模糊度由 .overlay-mask 统一提供 */}
      <div
        className="overlay-mask"
        aria-hidden="true"
        onClick={() => setDrawerOpen(false)}
        style={{ zIndex: 'var(--z-overlay)' }}
      />
      {/* Sidebar Panel */}
      <nav style={{
        position: 'fixed', top: 0, left: 0, bottom: 0,
        width: 260,
        background: 'var(--color-surface)',
        borderRight: '1px solid var(--color-border)',
        boxShadow: 'var(--shadow-xl)',
        zIndex: 'calc(var(--z-overlay) + 1)',
        display: 'flex', flexDirection: 'column',
        transform: 'translateX(0)',
        transition: 'transform var(--transition-slow)',
      }}>
        {sidebarInner(true)}
      </nav>
    </>
  )

  function sidebarInner(isMobilePanel = false) {
    const logoHidden = !isMobilePanel && collapsed
    return (
      <>
        {/* Logo */}
        <div style={{
          height: 'var(--header-height)',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: logoHidden ? '0 18px' : '0 20px',
          borderBottom: '1px solid var(--color-border)',
          flexShrink: 0,
          justifyContent: logoHidden ? 'center' : 'flex-start',
          transition: 'padding var(--transition-slow)',
        }}>
          <div
            className="gradient-icon gradient-icon--primary"
            style={{ width: 36, height: 36, borderRadius: 'var(--radius-md)', flexShrink: 0 }}
          >
            <WalletOutlined style={{ fontSize: 'var(--font-size-lg)', color: 'var(--color-text-inverse)' }} />
          </div>
          {!logoHidden && (
            <div style={{ overflow: 'hidden', flex: 1 }}>
              <Text style={{
                fontSize: 'var(--font-size-md)',
                fontWeight: 'var(--font-weight-bold)',
                color: 'var(--color-text)',
                letterSpacing: '0.3px',
                whiteSpace: 'nowrap',
                display: 'block',
              }}>
                记账本
              </Text>
              <Text style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-tertiary)', whiteSpace: 'nowrap' }}>
                Personal Ledger
              </Text>
            </div>
          )}
        </div>

        {/* CTA Button —— 记账入口，仅普通用户可见 */}
        {!isAdmin && (
          <div style={{ padding: logoHidden ? '12px 8px 6px' : '12px 12px 6px' }}>
            <Button
              type="primary"
              icon={<PlusCircleOutlined />}
              block
              aria-label="快速记账"
              onClick={() => { setAddModalOpen(true); if (isMobilePanel) setDrawerOpen(false) }}
              style={{
                height: 36,
                /* 收起态只隐藏文案即可（下方已条件渲染），
                   不能再靠 fontSize: 0 隐藏 —— 图标字号继承自按钮，
                   会被一起清零，rail 里只剩一个空的色块。 */
                fontSize: 'var(--font-size-base)',
                fontWeight: 'var(--font-weight-semibold)',
                borderRadius: 'var(--radius-md)',
                boxShadow: 'var(--shadow-primary)',
                transition: 'all var(--transition-base)',
                paddingInline: logoHidden ? 0 : undefined,
              }}
            >
              {!logoHidden && '快速记账'}
            </Button>
          </div>
        )}

        {/* Nav Menu */}
        <div style={{ flex: 1, overflow: 'auto', paddingBottom: 12 }}>
          <Menu
            theme="light"
            mode="inline"
            selectedKeys={[location.pathname]}
            items={allMenuItems}
            inlineCollapsed={!isMobilePanel && collapsed}
            style={{ borderRight: 0, padding: '4px 8px' }}
            onClick={({ key }) => { navigate(key); if (isMobilePanel) setDrawerOpen(false) }}
          />
        </div>

        {/* User entry at bottom — the single user/menu affordance (visible when collapsed too) */}
        <Dropdown menu={{ items: userMenuItems }} placement="topLeft" trigger={['click']}>
          <div
            role="button"
            tabIndex={0}
            onKeyDown={e => { if (e.key === 'Enter') e.currentTarget.click() }}
            style={{
              padding: logoHidden ? '12px 0' : '12px 16px',
              borderTop: '1px solid var(--color-border)',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              justifyContent: logoHidden ? 'center' : 'flex-start',
              cursor: 'pointer',
              transition: 'background-color var(--transition-fast)',
            }}
            onMouseEnter={e => { e.currentTarget.style.backgroundColor = 'var(--color-bg-subtle)' }}
            onMouseLeave={e => { e.currentTarget.style.backgroundColor = '' }}
          >
            <Avatar
              size={32}
              src={user?.avatar}
              icon={<UserOutlined />}
              style={{ backgroundColor: 'var(--color-primary)', flexShrink: 0 }}
            />
            {!logoHidden && (
              <div style={{ minWidth: 0, flex: 1 }}>
                <Text style={{
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 'var(--font-weight-semibold)',
                  color: 'var(--color-text)',
                  display: 'block',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}>
                  {user?.username || '加载中...'}
                </Text>
                <Text style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-tertiary)' }}>
                  {user?.role === 1 ? '管理员' : '普通用户'}
                </Text>
              </div>
            )}
          </div>
        </Dropdown>
      </>
    )
  }

  return (
    /* ── App Shell: full-height flex row ── */
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--color-bg)' }}>

      {/* ── Desktop Sidebar ── */}
      {!isMobile && (
        <aside style={{
          width: collapsed ? 'var(--sider-collapsed-width)' : 'var(--sider-width)',
          flexShrink: 0,
          background: 'var(--color-surface)',
          borderRight: '1px solid var(--color-border)',
          display: 'flex',
          flexDirection: 'column',
          transition: 'width var(--transition-slow)',
          position: 'sticky',
          top: 0,
          height: '100vh',
          overflow: 'hidden',
        }}>
          {sidebarInner(false)}
        </aside>
      )}

      {/* ── Mobile Sidebar Overlay ── */}
      {mobileDrawer}

      {/* ── Main Column: Header + Content ── */}
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>

        {/* ── Sticky Top Header ── */}
        <header style={{
          height: 'var(--header-height)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: isMobile ? '0 var(--space-base)' : '0 var(--space-xl)',
          background: 'var(--color-surface)',
          borderBottom: '1px solid var(--color-border)',
          position: 'sticky',
          top: 0,
          zIndex: 'var(--z-sticky)',
          flexShrink: 0,
          gap: 12,
        }}>
          {/* Left: toggle (+ mobile page title only; desktop titles live in page content) */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
            <Button
              type="text"
              icon={isMobile
                ? <MenuUnfoldOutlined />
                : (collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />)
              }
              onClick={() => isMobile ? setDrawerOpen(true) : setCollapsed(!collapsed)}
              aria-label={isMobile ? '打开导航菜单' : (collapsed ? '展开侧边栏' : '收起侧边栏')}
              style={{ fontSize: 'var(--font-size-lg)', flexShrink: 0 }}
            />
            {isMobile && currentPageTitle && (
              <Text style={{
                fontSize: 'var(--font-size-md)',
                fontWeight: 'var(--font-weight-semibold)',
                color: 'var(--color-text)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}>
                {currentPageTitle}
              </Text>
            )}
          </div>
        </header>

        {/* ── Scrollable Content Area ── */}
        <main style={{
          flex: 1,
          padding: isMobile
            ? 'var(--space-base) var(--space-base) var(--space-2xl)'
            : 'var(--space-xl)',
          maxWidth: 'calc(var(--content-max-width) + 48px)',
          width: '100%',
          margin: '0 auto',
          boxSizing: 'border-box',
        }}>
          <Outlet />
        </main>
      </div>

      {/* ── Mobile FAB —— 记账入口，仅普通用户可见 ── */}
      {isMobile && !isAdmin && (
        <button
          className="fab"
          onClick={() => setAddModalOpen(true)}
          aria-label="快速记账"
        >
          <PlusCircleOutlined style={{ fontSize: 'var(--font-size-2xl)', color: 'var(--color-text-inverse)' }} />
        </button>
      )}

      {/* ── Command Palette (⌘K / Ctrl+K) ── */}
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        commands={paletteCommands}
      />

      {/* ── Quick-Add Modal —— 记账入口，仅普通用户可见 ── */}
      {!isAdmin && (
        <Modal
          title="快速记账"
          open={addModalOpen}
          onOk={handleQuickAdd}
          onCancel={() => { setAddModalOpen(false); form.resetFields(); setQuickType('0') }}
          confirmLoading={addLoading}
          okText="保存"
          cancelText="取消"
          width={480}
          styles={{ body: { paddingTop: 'var(--space-sm)' } }}
        >
          <Tabs
            activeKey={quickType}
            onChange={k => { setQuickType(k); form.setFieldValue('categoryId', undefined) }}
            items={[
              { key: '0', label: <span><ArrowUpOutlined style={{ color: 'var(--color-expense)' }} /> 支出</span> },
              { key: '1', label: <span><ArrowDownOutlined style={{ color: 'var(--color-income)' }} /> 收入</span> },
            ]}
            style={{ marginBottom: 'var(--space-sm)' }}
          />
          <Form form={form} layout="vertical" initialValues={{ recordDate: dayjs() }}>
            <Form.Item name="categoryId" label="分类" rules={[{ required: true, message: '请选择分类' }]}>
              <Select placeholder="选择分类">
                {quickCategories.map(c => <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>)}
              </Select>
            </Form.Item>
            <Form.Item name="amount" label="金额" rules={[{ required: true, message: '请输入金额' }]}>
              <InputNumber min={0.01} precision={2} placeholder="0.00" style={{ width: '100%' }} prefix="¥" size="large" />
            </Form.Item>
            <Form.Item name="recordDate" label="日期" rules={[{ required: true, message: '请选择日期' }]}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="remark" label="备注">
              <Input.TextArea placeholder="添加备注（可选）" rows={2} />
            </Form.Item>
          </Form>
        </Modal>
      )}
    </div>
  )
}
