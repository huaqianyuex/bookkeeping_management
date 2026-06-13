import { Form, Input, Button, Typography, App as AntdApp } from 'antd'
import { UserOutlined, LockOutlined, WalletOutlined } from '@ant-design/icons'
import { useNavigate, Link } from 'react-router-dom'
import { register } from '../api/user'

const { Title, Text } = Typography
const USERNAME_REGEX = /^[A-Za-z0-9\u4e00-\u9fa5]{2,20}$/
const PASSWORD_REGEX = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{8,16}$/

export default function Register() {
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const { message } = AntdApp.useApp()

  const onFinish = async (values) => {
    try {
      const res = await register(values)
      if (res.code === 200) {
        message.success('注册成功，请登录')
        navigate('/login', { replace: true })
      } else {
        message.error(res.message || '注册失败')
      }
    } catch (error) {
      message.error(error?.response?.data?.message || '请求失败，请稍后重试')
    }
  }

  return (
    <div style={{
      display: 'flex',
      minHeight: '100vh',
      background: 'var(--color-bg)',
    }}>
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
            开始记账之旅
          </Title>
          <Text style={{ color: 'rgba(255, 255, 255, 0.7)', fontSize: 16 }}>
            创建账户，轻松管理您的每一笔收支
          </Text>
        </div>
      </div>

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
              创建账户
            </Title>
            <Text style={{ color: 'var(--color-text-secondary)', fontSize: 15 }}>
              填写以下信息完成注册
            </Text>
          </div>

          <Form form={form} onFinish={onFinish} size="large" layout="vertical">
            <Form.Item
              name="username"
              rules={[
                { required: true, message: '请输入用户名' },
                { pattern: USERNAME_REGEX, message: '用户名需为2-20位中英文或数字组合' },
              ]}
              style={{ marginBottom: 20 }}
            >
              <Input
                prefix={<UserOutlined style={{ color: 'var(--color-text-tertiary)' }} />}
                placeholder="用户名（2-20位中英文或数字）"
                style={{ height: 48, borderRadius: 'var(--radius-md)' }}
              />
            </Form.Item>
            <Form.Item
              name="password"
              rules={[
                { required: true, message: '请输入密码' },
                { pattern: PASSWORD_REGEX, message: '密码需为8-16位且包含大小写字母和数字' },
              ]}
              style={{ marginBottom: 28 }}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: 'var(--color-text-tertiary)' }} />}
                placeholder="密码（8-16位，含大小写字母和数字）"
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
                注册
              </Button>
            </Form.Item>
            <div style={{ textAlign: 'center' }}>
              <Text style={{ color: 'var(--color-text-secondary)' }}>
                已有账号？
              </Text>
              <Link
                to="/login"
                style={{
                  color: 'var(--color-primary)',
                  fontWeight: 600,
                  marginLeft: 4,
                }}
              >
                返回登录
              </Link>
            </div>
          </Form>
        </div>
      </div>
    </div>
  )
}
