import { Form, Input, Button, Card, Typography, App as AntdApp } from 'antd'
import { LockOutlined, SaveOutlined } from '@ant-design/icons'
import { updatePassword } from '../api/user'
import { AnimatedRoute } from '../components/ui'

const { Text } = Typography
const PASSWORD_REGEX = /^\d{6}$/

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
          <Text type="secondary" style={{ display: 'block', marginBottom: 'var(--space-base)' }}>
            新密码需为6位数字
          </Text>
          <Form form={form} onFinish={onFinish} size="large" layout="vertical">
            <Form.Item
              name="oldPassword"
              label="原密码"
              rules={[{ required: true, message: '请输入原密码' }]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: 'var(--color-text-tertiary)' }} />}
                placeholder="请输入原密码"
                style={{ borderRadius: 'var(--radius-md)' }}
              />
            </Form.Item>
            <Form.Item
              name="newPassword"
              label="新密码"
              rules={[
                { required: true, message: '请输入新密码' },
                { pattern: PASSWORD_REGEX, message: '密码需为6位数字' },
              ]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: 'var(--color-text-tertiary)' }} />}
                placeholder="请输入新密码"
                style={{ borderRadius: 'var(--radius-md)' }}
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
                style={{ borderRadius: 'var(--radius-md)' }}
              />
            </Form.Item>
            <Form.Item style={{ marginTop: 'var(--space-2xl)' }}>
              <Button
                type="primary"
                htmlType="submit"
                block
                icon={<SaveOutlined />}
                style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)' }}
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
