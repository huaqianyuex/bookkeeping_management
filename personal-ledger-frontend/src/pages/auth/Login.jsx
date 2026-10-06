import { Form, Input, Button, Typography, App as AntdApp } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { useNavigate, Link } from 'react-router-dom'
import { login } from '../../api/user'
import { useAuth } from '../../context/AuthContext'
import { AuthLayout } from '../../components/ui'

const { Title, Text } = Typography

export default function Login() {
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const { setUser, fetchUserInfo } = useAuth()
  const { message } = AntdApp.useApp()

  const onFinish = async (values) => {
    try {
      const res = await login(values)
      if (res.code === 200) {
        localStorage.setItem('token', res.data.token)
        message.success('登录成功')
        await fetchUserInfo()
        navigate('/', { replace: true })
      } else {
        message.error(res.message)
      }
    } catch (error) {
      message.error(error?.response?.data?.message || '登录失败，请稍后重试')
    }
  }

  return (
    <AuthLayout brandTitle="个人记账本" brandSubtitle="简洁高效的个人财务管理工具">
      <div style={{ marginBottom: 'var(--space-4xl)' }}>
        <Title level={3} style={{ marginBottom: 'var(--space-sm)', fontWeight: 'var(--font-weight-bold)', color: 'var(--color-text)' }}>
          欢迎回来
        </Title>
        <Text style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-md)' }}>
          登录您的账户以继续
        </Text>
      </div>

      <Form form={form} onFinish={onFinish} size="large" layout="vertical">
        <Form.Item name="username" style={{ marginBottom: 'var(--space-lg)' }}>
          <Input
            prefix={<UserOutlined style={{ color: 'var(--color-text-tertiary)' }} />}
            placeholder="用户名"
            style={{ borderRadius: 'var(--radius-md)' }}
          />
        </Form.Item>
        <Form.Item name="password" style={{ marginBottom: 'var(--space-2xl)' }}>
          <Input.Password
            prefix={<LockOutlined style={{ color: 'var(--color-text-tertiary)' }} />}
            placeholder="密码"
            style={{ borderRadius: 'var(--radius-md)' }}
          />
        </Form.Item>
        <Form.Item style={{ marginBottom: 'var(--space-lg)' }}>
          <Button
            type="primary"
            htmlType="submit"
            block
            style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)' }}
          >
            登录
          </Button>
        </Form.Item>
        <div style={{ textAlign: 'center' }}>
          <Text style={{ color: 'var(--color-text-secondary)' }}>
            还没有账号？
          </Text>
          <Link
            to="/register"
            style={{
              color: 'var(--color-primary)',
              fontWeight: 'var(--font-weight-semibold)',
              marginLeft: 'var(--space-xs)',
            }}
          >
            立即注册
          </Link>
        </div>
      </Form>
    </AuthLayout>
  )
}
