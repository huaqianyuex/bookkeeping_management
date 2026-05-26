import { Descriptions, Card, Button, Typography } from 'antd'
import { useAuth } from '../context/AuthContext'
import { useNavigate } from 'react-router-dom'

const { Title } = Typography

export default function UserInfo() {
  const { user } = useAuth()
  const navigate = useNavigate()

  if (!user) return null

  return (
    <Card bordered={false} style={{ maxWidth: 600, margin: '0 auto', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.03)' }}>
      <Title level={4} style={{ textAlign: 'center', marginBottom: 24, fontWeight: 600 }}>个人信息</Title>
      <Descriptions column={1} bordered size="middle">
        <Descriptions.Item label="用户ID">{user.id}</Descriptions.Item>

        <Descriptions.Item label="用户名">{user.username}</Descriptions.Item>
        <Descriptions.Item label="创建时间">{user.createTime}</Descriptions.Item>
        <Descriptions.Item label="更新时间">{user.updateTime}</Descriptions.Item>
      </Descriptions>
      <div style={{ textAlign: 'center', marginTop: 24 }}>
        <Button type="primary" onClick={() => navigate('/change-password')}>修改密码</Button>
      </div>
    </Card>
  )
}
