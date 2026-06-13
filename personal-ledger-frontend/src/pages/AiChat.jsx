import { useState, useRef, useEffect } from 'react'
import { Card, Input, Button, Avatar, Spin, App as AntdApp } from 'antd'
import {
  RobotOutlined,
  SendOutlined,
  PlusOutlined,
  UserOutlined,
} from '@ant-design/icons'

const API_BASE = '/api/ai'

export default function AiChatPage() {
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessions, setSessions] = useState([])
  const [showSessionList, setShowSessionList] = useState(false)
  const messagesEndRef = useRef(null)
  const { message } = AntdApp.useApp()

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    if (!sessionId) {
      handleNewSession()
    }
  }, [messages, sessionId])

  const handleNewSession = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({ title: '新对话' }),
      })
      const data = await res.json()
      if (data.id) {
        setSessionId(data.id)
        setMessages([])
        setShowSessionList(false)
      }
    } catch (e) {
      message.error('创建会话失败')
    }
    setLoading(false)
  }

  const loadSessions = async () => {
    try {
      const res = await fetch(`${API_BASE}/sessions`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      })
      const data = await res.json()
      if (data.sessions) setSessions(data.sessions)
    } catch {
      message.error('加载会话列表失败')
    }
  }

  const loadSessionMessages = async (sid) => {
    try {
      const res = await fetch(`${API_BASE}/sessions/${sid}/messages`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      })
      const msgs = await res.json()
      setSessionId(sid)
      setMessages(msgs || [])
      setShowSessionList(false)
    } catch {
      message.error('加载对话失败')
    }
  }

  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const userMsg = { role: 'user', content: input.trim() }
    setMessages((prev) => [...prev, userMsg])
    const currentInput = input.trim()
    setInput('')
    setLoading(true)

    if (!sessionId) {
      const res = await fetch(`${API_BASE}/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({ title: currentInput.slice(0, 20) }),
      })
      const data = await res.json()
      if (data.id) {
        setSessionId(data.id)
      }
    }

    try {
      const res = await fetch(
        `${API_BASE}/chat/stream?sessionId=${sessionId}&message=${encodeURIComponent(currentInput)}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`,
          },
        }
      )

      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: '', streaming: true },
      ])

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.substring(6))
              if (data.type === 'content') {
                setMessages((prev) => {
                  const last = prev[prev.length - 1]
                  if (last && last.role === 'assistant' && last.streaming) {
                    return [
                      ...prev.slice(0, -1),
                      { ...last, content: last.content + data.content },
                    ]
                  }
                  return prev
                })
              } else if (data.type === 'error') {
                message.error(data.error || '对话失败')
              }
            } catch {
              // skip
            }
          }
        }
      }

      setMessages((prev) => {
        const last = prev[prev.length - 1]
        if (last && last.role === 'assistant') {
          return [...prev.slice(0, -1), { ...last, streaming: false }]
        }
        return prev
      })
    } catch (e) {
      message.error('对话失败: ' + e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--color-bg)',
      padding: 24,
      boxSizing: 'border-box',
    }}>
      {/* 顶部栏 */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 16,
      }}>
        <h2 style={{
          margin: 0,
          color: 'var(--color-text)',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
        }}>
          <RobotOutlined style={{ color: 'var(--color-primary)' }} />
          AI记账助手
        </h2>
        <Button
          icon={<PlusOutlined />}
          onClick={() => {
            setShowSessionList(true)
            loadSessions()
          }}
        >
          新对话
        </Button>
      </div>

      {/* 内容区域 */}
      <Card
        style={{
          flex: 1,
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          borderRadius: 'var(--radius-lg)',
        }}
      >
        {/* 会话列表弹窗 */}
        {showSessionList && (
          <div style={{
            padding: 16,
            borderBottom: '1px solid var(--color-border)',
            maxHeight: 200,
            overflow: 'auto',
            background: 'var(--color-bg-subtle)',
          }}>
            <div style={{ marginBottom: 8, fontSize: 13, color: 'var(--color-text-tertiary)' }}>
              选择历史对话：
            </div>
            {sessions.map((s) => (
              <div
                key={s.id}
                onClick={() => loadSessionMessages(s.id)}
                style={{
                  padding: '8px 12px',
                  marginBottom: 4,
                  background: 'var(--color-surface)',
                  borderRadius: 'var(--radius-sm)',
                  cursor: 'pointer',
                  fontSize: 14,
                  color: 'var(--color-text)',
                }}
              >
                {s.title || '新对话'}
              </div>
            ))}
          </div>
        )}

        {/* 消息列表 */}
        <div style={{
          flex: 1,
          overflow: 'auto',
          padding: 20,
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
        }}>
          {messages.length === 0 && (
            <div style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--color-text-tertiary)',
            }}>
              <RobotOutlined style={{
                fontSize: 64,
                color: 'var(--color-text-tertiary)',
                opacity: 0.5,
                marginBottom: 16,
              }} />
              <div style={{ fontSize: 16, marginBottom: 8, color: 'var(--color-text)' }}>
                你好！我是AI记账助手
              </div>
              <div style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>
                我可以帮你：
                <ul style={{ textAlign: 'left', marginTop: 8, display: 'inline-block' }}>
                  <li>回答记账和财务相关问题</li>
                  <li>提供消费建议和预算规划</li>
                  <li>分析你的消费习惯</li>
                </ul>
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              style={{
                display: 'flex',
                justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                gap: 10,
              }}
            >
              {msg.role === 'assistant' && (
                <Avatar
                  size={40}
                  icon={<RobotOutlined />}
                  style={{ background: 'var(--color-primary)', flexShrink: 0 }}
                />
              )}
              <div style={{
                maxWidth: '70%',
                padding: '12px 16px',
                borderRadius: 16,
                background: msg.role === 'user' ? 'var(--color-primary)' : 'var(--color-surface)',
                color: msg.role === 'user' ? 'var(--color-text-inverse)' : 'var(--color-text)',
                fontSize: 14,
                lineHeight: 1.7,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                boxShadow: 'var(--shadow-sm)',
              }}>
                {msg.content || (msg.streaming ? <Spin size="small" /> : '')}
              </div>
              {msg.role === 'user' && (
                <Avatar
                  size={40}
                  icon={<UserOutlined />}
                  style={{ background: 'var(--color-text-secondary)', flexShrink: 0 }}
                />
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* 输入框 */}
        <div style={{
          padding: 16,
          borderTop: '1px solid var(--color-border)',
          display: 'flex',
          gap: 12,
        }}>
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                sendMessage()
              }
            }}
            placeholder="输入你的问题..."
            size="large"
            disabled={loading}
          />
          <Button
            type="primary"
            size="large"
            icon={<SendOutlined />}
            onClick={sendMessage}
            loading={loading}
            disabled={!input.trim()}
            style={{ minWidth: 80 }}
          >
            发送
          </Button>
        </div>
      </Card>
    </div>
  )
}
