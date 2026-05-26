import { Form, Input, Button, Card, message, Typography } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { useNavigate, Link } from 'react-router-dom'
import { login } from '../api/user'
import { useAuth } from '../context/AuthContext'

const { Title } = Typography

export default function Login() {
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const { setUser, fetchUserInfo } = useAuth()

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
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: '#fafafa' }}>
      <Card style={{ width: 400, border: '1px solid #eaeaea', boxShadow: 'none' }} bodyStyle={{ padding: '40px 32px' }}>
        <Title level={3} style={{ textAlign: 'center', marginBottom: 32, fontWeight: 600 }}>个人记账本</Title>
        <Form form={form} onFinish={onFinish} size="large">
          <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined style={{ color: '#bfbfbf' }} />} placeholder="用户名" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined style={{ color: '#bfbfbf' }} />} placeholder="密码" />
          </Form.Item>
          <Form.Item style={{ marginTop: 32 }}>
            <Button type="primary" htmlType="submit" block style={{ height: 44, fontSize: 16 }}>登录</Button>
          </Form.Item>
          <div style={{ textAlign: 'center', color: '#8c8c8c' }}>
            还没有账号？<Link to="/register" style={{ color: '#18181b', fontWeight: 500 }}>立即注册</Link>
          </div>
        </Form>
      </Card>
    </div>
  )
}
