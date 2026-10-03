import { Form, Input, Button, Typography, App as AntdApp } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { useNavigate, Link } from 'react-router-dom'
import { register } from '../../api/user'
import { AuthLayout } from '../../components/ui'

const { Title, Text } = Typography

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
    <AuthLayout brandTitle="开始记账之旅" brandSubtitle="创建账户，轻松管理您的每一笔收支">
      <div style={{ marginBottom: 48 }}>
        <Title level={3} style={{ marginBottom: 8, fontWeight: 700, color: 'var(--color-text)' }}>
          创建账户
        </Title>
        <Text style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-md)' }}>
          填写以下信息完成注册
        </Text>
      </div>

      <Form form={form} onFinish={onFinish} size="large" layout="vertical">
        <Form.Item name="username" style={{ marginBottom: 20 }}>
          <Input
            prefix={<UserOutlined style={{ color: 'var(--color-text-tertiary)' }} />}
            placeholder="用户名（2-20位中英文或数字）"
            style={{ height: 48, borderRadius: 'var(--radius-md)' }}
          />
        </Form.Item>
        <Form.Item name="password" style={{ marginBottom: 28 }}>
          <Input.Password
            prefix={<LockOutlined style={{ color: 'var(--color-text-tertiary)' }} />}
            placeholder="密码（6位数字）"
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
    </AuthLayout>
  )
}
