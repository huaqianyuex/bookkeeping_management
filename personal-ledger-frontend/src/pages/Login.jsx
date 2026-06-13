import { Form, Input, Button, Typography, App as AntdApp } from 'antd'
import { UserOutlined, LockOutlined, WalletOutlined } from '@ant-design/icons'
import { useNavigate, Link } from 'react-router-dom'
import { login } from '../api/user'
import { useAuth } from '../context/AuthContext'

const { Title, Text } = Typography

export default function Login() {
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const { setUser, fetchUserInfo } = useAuth()
  const { message } = AntdApp.useApp()

  const onFinish = async (values) => {
    const res = await login(values)
    if (res.code === 200) {
      localStorage.setItem('token', res.data)
      message.success('登录成功')
      await fetchUserInfo()
      navigate('/', { replace: true })
    } else {
      message.error(res.message)
    }
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
        background: 'linear-gradient(135deg, var(--color-primary) 0%, #16213e 100%)',
        padding: '60px',
        position: 'relative',
        overflow: 'hidden',
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
        <div style={{ textAlign: 'center', position: 'relative', zIndex: 1 }}>
          <div style={{
            width: 80,
            height: 80,
            borderRadius: 'var(--radius-lg)',
            background: 'rgba(255, 255, 255, 0.1)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: 32,
            margin: '0 auto 32px',
          }}>
            <WalletOutlined style={{ fontSize: 36, color: '#fff' }} />
          </div>
          <Title level={2} style={{ color: '#fff', marginBottom: 16, fontWeight: 700 }}>
            个人记账本
          </Title>
          <Text style={{ color: 'rgba(255, 255, 255, 0.7)', fontSize: 16 }}>
            简洁高效的个人财务管理工具
          </Text>
        </div>
      </div>

      {/* 右侧登录表单 */}
      <div style={{
        width: 480,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        padding: 60,
        background: 'var(--color-surface)',
      }}>
        <div style={{ width: '100%', maxWidth: 360 }}>
          <div style={{ marginBottom: 48 }}>
            <Title level={3} style={{ marginBottom: 8, fontWeight: 700, color: 'var(--color-text)' }}>
              欢迎回来
            </Title>
            <Text style={{ color: 'var(--color-text-secondary)', fontSize: 15 }}>
              登录您的账户以继续
            </Text>
          </div>

          <Form form={form} onFinish={onFinish} size="large" layout="vertical">
            <Form.Item
              name="username"
              rules={[{ required: true, message: '请输入用户名' }]}
              style={{ marginBottom: 20 }}
            >
              <Input
                prefix={<UserOutlined style={{ color: 'var(--color-text-tertiary)' }} />}
                placeholder="用户名"
                style={{ height: 48, borderRadius: 'var(--radius-md)' }}
              />
            </Form.Item>
            <Form.Item
              name="password"
              rules={[{ required: true, message: '请输入密码' }]}
              style={{ marginBottom: 28 }}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: 'var(--color-text-tertiary)' }} />}
                placeholder="密码"
                style={{ height: 48, borderRadius: 'var(--radius-md)' }}
              />
            </Form.Item>
            <Form.Item style={{ marginBottom: 20 }}>
              <Button
                type="primary"
                htmlType="submit"
                block
                style={{ height: 48, fontSize: 16, fontWeight: 600 }}
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
                  fontWeight: 600,
                  marginLeft: 4,
                }}
              >
                立即注册
              </Link>
            </div>
          </Form>
        </div>
      </div>
    </div>
  )
}
