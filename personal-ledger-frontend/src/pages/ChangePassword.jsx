import { Form, Input, Button, Card, message, Typography } from 'antd'
import { LockOutlined } from '@ant-design/icons'
import { updatePassword } from '../api/user'

const { Title } = Typography

export default function ChangePassword() {
  const [form] = Form.useForm()

  const onFinish = async (values) => {
    const res = await updatePassword(values)
    if (res.code === 200) {
      message.success('密码修改成功')
      form.resetFields()
    } else {
      message.error(res.message)
    }
  }

  return (
    <Card bordered={false} style={{ maxWidth: 500, margin: '0 auto', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.03)' }}>
      <Title level={4} style={{ textAlign: 'center', marginBottom: 24, fontWeight: 600 }}>修改密码</Title>
      <Form form={form} onFinish={onFinish} size="large" layout="vertical">
        <Form.Item name="oldPassword" label="原密码" rules={[{ required: true, message: '请输入原密码' }]}>
          <Input.Password prefix={<LockOutlined style={{ color: '#bfbfbf' }} />} placeholder="请输入原密码" />
        </Form.Item>
        <Form.Item name="newPassword" label="新密码" rules={[
          { required: true, message: '请输入新密码' },
          { min: 6, message: '密码长度6-20位' },
          { max: 20, message: '密码长度6-20位' },
        ]}>
          <Input.Password prefix={<LockOutlined style={{ color: '#bfbfbf' }} />} placeholder="请输入新密码（6-20位）" />
        </Form.Item>
        <Form.Item style={{ marginTop: 32 }}>
          <Button type="primary" htmlType="submit" block style={{ height: 44, fontSize: 16 }}>确认修改</Button>
        </Form.Item>
      </Form>
    </Card>
  )
}
