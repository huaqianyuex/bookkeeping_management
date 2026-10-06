import { Descriptions, Card, Button, Typography, Avatar, Form, Input, Upload, Skeleton, App as AntdApp } from 'antd'
import { UserOutlined, EditOutlined, UploadOutlined, LockOutlined } from '@ant-design/icons'
import { useAuth } from '../context/AuthContext'
import { useNavigate } from 'react-router-dom'
import { updateUserInfo, uploadAvatar } from '../api/user'
import { SectionTitle, AnimatedRoute } from '../components/ui'
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
        <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '280px 1fr', gap: 'var(--space-base)' }}>
          <Card variant="borderless" className="card-base" styles={{ body: { padding: 'var(--space-xl)' } }}>
            <Skeleton avatar active paragraph={{ rows: 2 }} />
          </Card>
          <Card variant="borderless" className="card-base" styles={{ body: { padding: 'var(--space-xl)' } }}>
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
      {/* Modern Responsive Grid: Sidebar profile card + Content panels */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: isMobile ? '1fr' : '280px 1fr',
        gap: isMobile ? 'var(--space-base)' : 'var(--space-xl)',
        alignItems: 'start',
      }}>
        {/* Left Column: Profile Card */}
        <Card
          variant="borderless"
          className="card-base"
          styles={{ body: { padding: isMobile ? 'var(--space-lg) var(--space-base)' : 'var(--space-xl) var(--space-lg)', textAlign: 'center' } }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--space-md)' }}>
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

            <div style={{ marginTop: 'var(--space-xs)' }}>
              <Title level={4} style={{ margin: 0, color: 'var(--color-text)', fontWeight: 'var(--font-weight-bold)' }}>
                {user.username}
              </Title>
              {/* 与用户管理页的角色标签同色（accent），角色标识全站一致 */}
              <span style={{
                display: 'inline-block',
                marginTop: 'var(--space-xs)',
                padding: '2px var(--space-md)',
                borderRadius: 'var(--radius-full)',
                background: 'var(--color-accent-bg)',
                border: '1px solid var(--color-accent-border)',
                color: 'var(--color-accent)',
                fontSize: 'var(--font-size-xs)',
                fontWeight: 'var(--font-weight-semibold)',
              }}>
                {user.role === 1 ? '系统管理员' : '标准用户'}
              </span>
            </div>

            <div style={{
              width: '100%',
              marginTop: 'var(--space-md)',
              paddingTop: 'var(--space-base)',
              borderTop: '1px solid var(--color-border)',
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: 'var(--font-size-sm)',
            }}>
              <span style={{ color: 'var(--color-text-secondary)' }}>用户ID</span>
              <span className="money" style={{ color: 'var(--color-text)', fontWeight: 'var(--font-weight-semibold)' }}>{user.id}</span>
            </div>
          </div>
        </Card>

        {/* Right Column: Settings and Metadata */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-base)' }}>
          {/* Edit Form */}
          <Card
            title={<SectionTitle title="资料设置" dotColor="primary" />}
            variant="borderless"
            className="card-base"
            styles={{ body: { padding: isMobile ? 'var(--space-base)' : 'var(--space-lg) var(--space-xl)' } }}
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
                style={{ marginBottom: 'var(--space-base)' }}
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
            styles={{ body: { padding: isMobile ? 'var(--space-base)' : 'var(--space-lg) var(--space-xl)' } }}
          >
            <Descriptions
              column={isMobile ? 1 : 2}
              size="middle"
              styles={{ label: { color: 'var(--color-text-secondary)' } }}
            >
              <Descriptions.Item label="注册时间">
                <Text>{formatDateTime(user.created_at)}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="最近更新">
                <Text>{formatDateTime(user.updated_at)}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="账户状态">
                <span style={{ color: 'var(--color-success)', fontWeight: 'var(--font-weight-semibold)' }}>正常</span>
              </Descriptions.Item>
            </Descriptions>

            <div style={{ marginTop: 'var(--space-lg)', paddingTop: 'var(--space-base)', borderTop: '1px solid var(--color-border)', display: 'flex', justifyContent: 'flex-end' }}>
              <Button
                icon={<LockOutlined />}
                onClick={() => navigate('/settings/password')}
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
