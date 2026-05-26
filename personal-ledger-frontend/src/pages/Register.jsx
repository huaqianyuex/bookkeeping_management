import { Form, Input, Button, Card, message, Typography } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { useNavigate, Link } from 'react-router-dom'
import { register } from '../api/user'

const { Title } = Typography

export default function Register() {
  const [form] = Form.useForm()
  const navigate = useNavigate()

  const onFinish = async (values) => {
    const res = await register(values)
    if (res.code === 200) {
      message.success('注册成功，请登录')
      navigate('/login', { replace: true })
    } else {
      message.error(res.message)
    }
  }

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: '#fafafa' }}>
      <Card style={{ width: 400, border: '1px solid #eaeaea', boxShadow: 'none' }} bodyStyle={{ padding: '40px 32px' }}>
        <Title level={3} style={{ textAlign: 'center', marginBottom: 32, fontWeight: 600 }}>注册账号</Title>
        <Form form={form} onFinish={onFinish} size="large">
          <Form.Item name="username" rules={[
            { required: true, message: '请输入用户名' },
            { min: 2, message: '用户名长度2-20位' },
            { max: 20, message: '用户名长度2-20位' },
          ]}>
            <Input prefix={<UserOutlined style={{ color: '#bfbfbf' }} />} placeholder="用户名（2-20位）" />
          </Form.Item>
          <Form.Item name="password" rules={[
            { required: true, message: '请输入密码' },
            { min: 6, message: '密码长度6-20位' },
            { max: 20, message: '密码长度6-20位' },
          ]}>
            <Input.Password prefix={<LockOutlined style={{ color: '#bfbfbf' }} />} placeholder="密码（6-20位）" />
          </Form.Item>
          <Form.Item style={{ marginTop: 32 }}>
            <Button type="primary" htmlType="submit" block style={{ height: 44, fontSize: 16 }}>注册</Button>
          </Form.Item>
          <div style={{ textAlign: 'center', color: '#8c8c8c' }}>
            已有账号？<Link to="/login" style={{ color: '#18181b', fontWeight: 500 }}>返回登录</Link>
          </div>
        </Form>
      </Card>
    </div>
  )
}
