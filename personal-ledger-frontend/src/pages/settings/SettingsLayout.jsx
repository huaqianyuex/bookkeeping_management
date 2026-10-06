import { Tabs } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { PageHeader, AnimatedRoute } from '../../components/ui'

const tabItems = [
  { key: '/settings/profile',  label: <span><UserOutlined style={{ marginRight: 'var(--space-xs)' }} />个人资料</span> },
  { key: '/settings/password', label: <span><LockOutlined style={{ marginRight: 'var(--space-xs)' }} />修改密码</span> },
]

export default function SettingsLayout() {
  const location = useLocation()
  const navigate = useNavigate()

  return (
    <AnimatedRoute>
      <PageHeader title="设置" />
      <Tabs
        activeKey={tabItems.some(t => t.key === location.pathname) ? location.pathname : '/settings/profile'}
        items={tabItems}
        onChange={key => navigate(key)}
      />
      <Outlet />
    </AnimatedRoute>
  )
}
