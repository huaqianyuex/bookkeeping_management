import { Descriptions, Card, Button, Typography, Avatar, Form, Input, Upload, App as AntdApp } from 'antd'
import { UserOutlined, EditOutlined, UploadOutlined } from '@ant-design/icons'
import { useAuth } from '../context/AuthContext'
import { useNavigate } from 'react-router-dom'
import { updateUserInfo, uploadAvatar } from '../api/user'
import SectionTitle from '../components/ui/SectionTitle'
import AnimatedRoute from '../components/ui/AnimatedRoute'

const { Title, Text } = Typography
const USERNAME_REGEX = /^[A-Za-z0-9\u4e00-\u9fa5]{2,20}$/
const MAX_AVATAR_SIZE = 2 * 1024 * 1024

export default function UserInfo() {
  const { user, setUser } = useAuth()
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()

  if (!user) return null

  const avatarSrc = user.avatarUrl || undefined

  const onUpdateProfile = async (values) => {
    try {
      const res = await updateUserInfo({ username: values.username })
      if (res.code === 200) {
        setUser(res.data)
        message.success('用户名更新成功')
      } else {
        message.error(res.message || '用户名更新失败')
      }
    } catch (error) {
      message.error(error?.response?.data?.message || '请求失败，请稍后重试')
    }
  }

  const beforeUpload = (file) => {
    const isAllowedType = file.type === 'image/jpeg' || file.type === 'image/png'
    if (!isAllowedType) {
      message.error('头像仅支持 JPG/PNG 格式')
      return Upload.LIST_IGNORE
    }

    const isLt2M = file.size <= MAX_AVATAR_SIZE
    if (!isLt2M) {
      message.error('头像大小不能超过 2MB')
      return Upload.LIST_IGNORE
    }

    return true
  }

  const customUpload = async ({ file, onSuccess, onError }) => {
    try {
      const res = await uploadAvatar(file)
      if (res.code === 200) {
        setUser(res.data)
        message.success('头像上传成功')
        onSuccess?.(res)
      } else {
        const err = new Error(res.message || '头像上传失败')
        onError?.(err)
      }
    } catch (error) {
      message.error(error?.response?.data?.message || '头像上传失败，请稍后重试')
      onError?.(error)
    }
  }

  return (
    <AnimatedRoute>
      <div style={{ maxWidth: 680, margin: '0 auto' }}>
        <Card
          variant="borderless"
          className="card-base"
          style={{ marginBottom: 'var(--space-xl)' }}
        >
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            padding: 'var(--space-xl) 0',
            gap: 12,
          }}>
            <Avatar
              size={88}
              src={avatarSrc}
              icon={<UserOutlined />}
              style={{
                backgroundColor: 'var(--color-primary)',
                marginBottom: 'var(--space-xs)',
              }}
            />
            <Upload
              showUploadList={false}
              beforeUpload={beforeUpload}
              customRequest={customUpload}
              accept=".jpg,.jpeg,.png,image/jpeg,image/png"
            >
              <Button icon={<UploadOutlined />}>上传头像（JPG/PNG，≤2MB）</Button>
            </Upload>
            <Title level={3} style={{ margin: 0, color: 'var(--color-text)' }}>
              {user.username}
            </Title>
            <Text style={{ color: 'var(--color-text-secondary)' }}>
              ID: {user.id}
            </Text>
          </div>
        </Card>

        <Card
          title={<SectionTitle title="资料设置" />}
          variant="borderless"
          className="card-base"
          style={{ marginBottom: 'var(--space-xl)' }}
        >
          <Form
            form={form}
            layout="vertical"
            initialValues={{ username: user.username }}
            onFinish={onUpdateProfile}
          >
            <Form.Item
              name="username"
              label="用户名"
              rules={[
                { required: true, message: '请输入用户名' },
                { pattern: USERNAME_REGEX, message: '用户名需为2-20位中英文或数字组合' },
              ]}
            >
              <Input
                placeholder="请输入2-20位中英文或数字组合"
                maxLength={20}
              />
            </Form.Item>
            <Form.Item style={{ marginBottom: 0 }}>
              <Button type="primary" htmlType="submit" icon={<EditOutlined />}>
                保存用户名
              </Button>
            </Form.Item>
          </Form>
        </Card>

        <Card
          title={<SectionTitle title="账户信息" />}
          variant="borderless"
          className="card-base"
        >
          <Descriptions
            column={1}
            variant="bordered"
            size="middle"
            style={{ marginTop: 16 }}
          >
            <Descriptions.Item label="用户ID">
              <Text>{user.id}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="用户名">
              <Text strong>{user.username}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="创建时间">
              <Text>{user.createTime}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="更新时间">
              <Text>{user.updateTime}</Text>
            </Descriptions.Item>
          </Descriptions>
          <div style={{ textAlign: 'center', marginTop: 32 }}>
            <Button
              type="primary"
              icon={<EditOutlined />}
              onClick={() => navigate('/change-password')}
              style={{ height: 44, padding: '0 32px' }}
            >
              修改密码
            </Button>
          </div>
        </Card>
      </div>
    </AnimatedRoute>
  )
}
