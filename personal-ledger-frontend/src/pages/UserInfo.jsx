import { Descriptions, Card, Button, Typography, Avatar, Form, Input, Upload, Skeleton, App as AntdApp } from 'antd'
import { UserOutlined, EditOutlined, UploadOutlined, LockOutlined } from '@ant-design/icons'
import { useAuth } from '../context/AuthContext'
import { useNavigate } from 'react-router-dom'
import { updateUserInfo, uploadAvatar } from '../api/user'
import { SectionTitle, PageHeader, AnimatedRoute } from '../components/ui'
import useMediaQuery from '../hooks/useMediaQuery'
import { formatDateTime } from '../utils/format'

const { Title, Text } = Typography
const USERNAME_REGEX = /^[A-Za-z0-9\u4e00-\u9fa5]{2,20}$/
const MAX_AVATAR_SIZE = 2 * 1024 * 1024

export default function UserInfo() {
  const { user, setUser } = useAuth()
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()
  const isMobile = useMediaQuery('(max-width: 767px)')

  // 会话恢复期间展示骨架屏，避免白屏
  if (!user) {
    return (
      <AnimatedRoute>
        <PageHeader title="个人信息" />
        <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '280px 1fr', gap: 16 }}>
          <Card variant="borderless" className="card-base" styles={{ body: { padding: 24 } }}>
            <Skeleton avatar active paragraph={{ rows: 2 }} />
          </Card>
          <Card variant="borderless" className="card-base" styles={{ body: { padding: 24 } }}>
            <Skeleton active paragraph={{ rows: 5 }} />
          </Card>
        </div>
      </AnimatedRoute>
    )
  }

  const avatarSrc = user.avatar || undefined

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
      <PageHeader title="个人信息" subtitle="查看与管理您的个人账户基本资料" />

      {/* Modern Responsive Grid: Sidebar profile card + Content panels */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: isMobile ? '1fr' : '280px 1fr',
        gap: isMobile ? 16 : 24,
        alignItems: 'start',
      }}>
        {/* Left Column: Profile Card */}
        <Card
          variant="borderless"
          className="card-base"
          styles={{ body: { padding: isMobile ? '20px 16px' : '24px 20px', textAlign: 'center' } }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
            <Avatar
              size={88}
              src={avatarSrc}
              icon={<UserOutlined />}
              style={{
                backgroundColor: 'var(--color-primary)',
                boxShadow: 'var(--shadow-sm)',
              }}
            />
            <Upload
              showUploadList={false}
              beforeUpload={beforeUpload}
              customRequest={customUpload}
              accept=".jpg,.jpeg,.png,image/jpeg,image/png"
            >
              <Button size="small" icon={<UploadOutlined />} style={{ borderRadius: 'var(--radius-md)' }}>
                更换头像
              </Button>
            </Upload>
            <Text style={{ color: 'var(--color-text-tertiary)', fontSize: 'var(--font-size-xs)' }}>
              支持 JPG/PNG，小于 2MB
            </Text>

            <div style={{ marginTop: 4 }}>
              <Title level={4} style={{ margin: 0, color: 'var(--color-text)', fontWeight: 700 }}>
                {user.username}
              </Title>
              <span style={{
                display: 'inline-block',
                marginTop: 6,
                padding: '2px 10px',
                borderRadius: 'var(--radius-full)',
                background: 'var(--color-primary-bg)',
                color: 'var(--color-primary)',
                fontSize: 'var(--font-size-xs)',
                fontWeight: 600,
              }}>
                {user.role === 1 ? '系统管理员' : '标准用户'}
              </span>
            </div>

            <div style={{
              width: '100%',
              marginTop: 12,
              paddingTop: 16,
              borderTop: '1px solid var(--color-border)',
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: 'var(--font-size-sm)',
            }}>
              <span style={{ color: 'var(--color-text-secondary)' }}>用户ID</span>
              <span className="money" style={{ color: 'var(--color-text)', fontWeight: 600 }}>{user.id}</span>
            </div>
          </div>
        </Card>

        {/* Right Column: Settings and Metadata */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Edit Form */}
          <Card
            title={<SectionTitle title="资料设置" dotColor="primary" />}
            variant="borderless"
            className="card-base"
            styles={{ body: { padding: isMobile ? '16px' : '20px 24px' } }}
          >
            <Form
              form={form}
              layout="vertical"
              initialValues={{ username: user.username }}
              onFinish={onUpdateProfile}
            >
              <Form.Item
                name="username"
                label="用户昵称"
                rules={[
                  { required: true, message: '请输入用户名' },
                  { pattern: USERNAME_REGEX, message: '用户名需为2-20位中英文或数字组合' },
                ]}
                style={{ marginBottom: 16 }}
              >
                <Input
                  size="large"
                  placeholder="请输入2-20位中英文或数字组合"
                  maxLength={20}
                  style={{ borderRadius: 'var(--radius-md)' }}
                />
              </Form.Item>
              <Form.Item style={{ marginBottom: 0 }}>
                <Button type="primary" htmlType="submit" icon={<EditOutlined />} size="large" style={{ borderRadius: 'var(--radius-md)' }}>
                  保存修改
                </Button>
              </Form.Item>
            </Form>
          </Card>

          {/* Account Metadata */}
          <Card
            title={<SectionTitle title="账户详情" dotColor="info" />}
            variant="borderless"
            className="card-base"
            styles={{ body: { padding: isMobile ? '16px' : '20px 24px' } }}
          >
            <Descriptions
              column={isMobile ? 1 : 2}
              size="middle"
              labelStyle={{ color: 'var(--color-text-secondary)' }}
            >
              <Descriptions.Item label="注册时间">
                <Text>{formatDateTime(user.created_at)}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="最近更新">
                <Text>{formatDateTime(user.updated_at)}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="账户状态">
                <span style={{ color: 'var(--color-success)', fontWeight: 600 }}>正常</span>
              </Descriptions.Item>
            </Descriptions>

            <div style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid var(--color-border)', display: 'flex', justifyContent: 'flex-end' }}>
              <Button
                icon={<LockOutlined />}
                onClick={() => navigate('/change-password')}
                style={{ borderRadius: 'var(--radius-md)' }}
              >
                修改安全密码
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </AnimatedRoute>
  )
}
