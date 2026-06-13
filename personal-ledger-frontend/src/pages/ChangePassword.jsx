import { Form, Input, Button, Card, Typography, App as AntdApp } from 'antd'
import { LockOutlined, SaveOutlined } from '@ant-design/icons'
import { updatePassword } from '../api/user'
import AnimatedRoute from '../components/ui/AnimatedRoute'

const { Title, Text } = Typography
const PASSWORD_REGEX = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{8,16}$/

export default function ChangePassword() {
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()

  const onFinish = async (values) => {
    try {
      const res = await updatePassword({
        oldPassword: values.oldPassword,
        newPassword: values.newPassword,
      })
      if (res.code === 200) {
        message.success('密码修改成功')
        form.resetFields()
      } else {
        message.error(res.message || '密码修改失败')
      }
    } catch (error) {
      message.error(error?.response?.data?.message || '请求失败，请稍后重试')
    }
  }

  return (
    <AnimatedRoute>
      <div style={{ maxWidth: 500, margin: '0 auto' }}>
        <Card variant="borderless" className="card-base">
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            marginBottom: 'var(--space-2xl)',
          }}>
            <div style={{
              width: 64,
              height: 64,
              borderRadius: 'var(--radius-xl)',
              background: 'var(--color-primary-bg)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: 'var(--space-base)',
            }}>
              <LockOutlined style={{ fontSize: 28, color: 'var(--color-primary)' }} />
            </div>
            <Title level={3} style={{ margin: 0, color: 'var(--color-text)' }}>
              修改密码
            </Title>
            <Text style={{ color: 'var(--color-text-secondary)', marginTop: 'var(--space-sm)' }}>
              新密码需为8-16位，包含大小写字母和数字
            </Text>
          </div>

          <Form form={form} onFinish={onFinish} size="large" layout="vertical">
            <Form.Item
              name="oldPassword"
              label="原密码"
              rules={[{ required: true, message: '请输入原密码' }]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: 'var(--color-text-tertiary)' }} />}
                placeholder="请输入原密码"
                style={{ height: 48, borderRadius: 'var(--radius-md)' }}
              />
            </Form.Item>
            <Form.Item
              name="newPassword"
              label="新密码"
              rules={[
                { required: true, message: '请输入新密码' },
                { pattern: PASSWORD_REGEX, message: '密码需为8-16位且包含大小写字母和数字' },
              ]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: 'var(--color-text-tertiary)' }} />}
                placeholder="请输入新密码"
                style={{ height: 48, borderRadius: 'var(--radius-md)' }}
              />
            </Form.Item>
            <Form.Item
              name="confirmPassword"
              label="确认新密码"
              dependencies={['newPassword']}
              rules={[
                { required: true, message: '请再次输入新密码' },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || getFieldValue('newPassword') === value) {
                      return Promise.resolve()
                    }
                    return Promise.reject(new Error('两次输入的密码不一致'))
                  },
                }),
              ]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: 'var(--color-text-tertiary)' }} />}
                placeholder="请再次输入新密码"
                style={{ height: 48, borderRadius: 'var(--radius-md)' }}
              />
            </Form.Item>
            <Form.Item style={{ marginTop: 32 }}>
              <Button
                type="primary"
                htmlType="submit"
                block
                icon={<SaveOutlined />}
                style={{ height: 48, fontSize: 16, fontWeight: 600 }}
              >
                确认修改
              </Button>
            </Form.Item>
          </Form>
        </Card>
      </div>
    </AnimatedRoute>
  )
}
