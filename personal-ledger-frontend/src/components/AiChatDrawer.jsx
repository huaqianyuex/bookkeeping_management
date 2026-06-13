import { useState, useRef, useEffect } from 'react'
import { Button, Input, Avatar, Spin, App as AntdApp } from 'antd'
import {
  RobotOutlined,
  SendOutlined,
  CloseOutlined,
  PlusOutlined,
  MenuOutlined,
} from '@ant-design/icons'

// AI对话API基础地址
const API_BASE = '/api/ai'

export default function AiChatDrawer({ open, onClose }) {
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [sessions, setSessions] = useState([])
  const [showSessions, setShowSessions] = useState(false)
  const messagesEndRef = useRef(null)
  const { message } = AntdApp.useApp()

  // 滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // 创建新会话
  const createSession = async (title) => {
    setCreating(true)
    try {
      const res = await fetch(`${API_BASE}/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({ title }),
      })
      const data = await res.json()
      if (data.id) {
        setSessionId(data.id)
        setMessages([])
        setCreating(false)
      }
    } catch (e) {
      message.error('创建会话失败')
      setCreating(false)
    }
  }

  // 加载会话列表
  const loadSessions = async () => {
    try {
      const res = await fetch(`${API_BASE}/sessions`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      })
      const data = await res.json()
      if (data.sessions?.length > 0) {
        setSessions(data.sessions)
      } else {
        setSessions([])
      }
    } catch {
      setSessions([])
    }
  }

  // 加载会话消息
  const loadMessages = async (sid) => {
    try {
      const res = await fetch(`${API_BASE}/sessions/${sid}/messages`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      })
      const msgs = await res.json()
      setSessionId(sid)
      setMessages(msgs || [])
      setShowSessions(false)
    } catch {
      message.error('加载对话失败')
    }
  }

  // 发送消息（SSE流式）
  const sendMessage = async () => {
    if (!input.trim() || loading) return
    if (!sessionId) {
      await createSession(input.slice(0, 20))
      return
    }

    const userMsg = { role: 'user', content: input.trim() }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch(
        `${API_BASE}/chat/stream?sessionId=${sessionId}&message=${encodeURIComponent(input.trim())}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`,
          },
        }
      )

      // 创建空的AI消息用于接收流式内容
      setMessages((prev) => [...prev, { role: 'assistant', content: '', streaming: true }])

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
              // skip parse errors
            }
          }
        }
      }

      // 标记为非streaming
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

  // 处理Enter发送
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <>
      {/* AI助手浮动按钮 */}
      <Button
        type="primary"
        icon={<RobotOutlined />}
        onClick={() => {
          if (!showSessions) {
            setShowSessions(true)
            loadSessions()
          }
        }}
        style={{
          position: 'fixed',
          bottom: 24,
          right: 24,
          width: 56,
          height: 56,
          borderRadius: '50%',
          boxShadow: '0 4px 12px rgba(26,26,46,0.3)',
          zIndex: 1000,
          display: open ? 'none' : 'flex',
        }}
      />

      {/* AI对话面板 */}
      {showSessions && (
        <div
          style={{
            position: 'fixed',
            bottom: 92,
            right: 24,
            width: 420,
            height: 600,
            background: '#fff',
            borderRadius: 16,
            boxShadow: '0 8px 32px rgba(0,0,0,0.15)',
            display: 'flex',
            flexDirection: 'column',
            zIndex: 1001,
            overflow: 'hidden',
          }}
        >
          {/* 头部 */}
          <div
            style={{
              padding: '16px 20px',
              background: '#1a1a2e',
              color: '#fff',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <RobotOutlined style={{ fontSize: 22 }} />
              <span style={{ fontWeight: 600, fontSize: 16 }}>AI记账助手</span>
            </div>
            <Button
              type="text"
              icon={<CloseOutlined />}
              onClick={() => setShowSessions(false)}
              style={{ color: '#fff' }}
            />
          </div>

          {/* 会话列表 */}
          {!sessionId && (
            <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'center',
                  marginBottom: 16,
                }}
              >
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => createSession('新对话')}
                  loading={creating}
                  block
                >
                  新对话
                </Button>
              </div>
              {sessions.map((s) => (
                <div
                  key={s.id}
                  onClick={() => loadMessages(s.id)}
                  style={{
                    padding: '10px 14px',
                    marginBottom: 8,
                    background: '#f5f5f7',
                    borderRadius: 8,
                    cursor: 'pointer',
                    transition: 'background 0.2s',
                  }}
                  onMouseEnter={(e) => (e.target.style.background = '#e8e8f0')}
                  onMouseLeave={(e) => (e.target.style.background = '#f5f5f7')}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <MenuOutlined style={{ color: '#999' }} />
                    <span style={{ fontSize: 14 }}>{s.title || '新对话'}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* 消息列表 */}
          {sessionId && (
            <>
              <div
                style={{
                  flex: 1,
                  overflow: 'auto',
                  padding: '16px 20px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 12,
                }}
              >
                {messages.length === 0 && (
                  <div style={{ textAlign: 'center', color: '#999', marginTop: 60 }}>
                    <RobotOutlined style={{ fontSize: 48, color: '#ccc', display: 'block', marginBottom: 12 }} />
                    <div>你好！我是AI记账助手</div>
                    <div style={{ fontSize: 13, marginTop: 4 }}>
                      可以问我关于记账、财务分析等问题
                    </div>
                  </div>
                )}
                {messages.map((msg, i) => (
                  <div
                    key={i}
                    style={{
                      display: 'flex',
                      justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                      gap: 8,
                    }}
                  >
                    {msg.role === 'assistant' && (
                      <Avatar
                        size={32}
                        icon={<RobotOutlined />}
                        style={{ background: '#1a1a2e', marginTop: 2 }}
                      />
                    )}
                    <div
                      style={{
                        maxWidth: '75%',
                        padding: '10px 14px',
                        borderRadius: 12,
                        background:
                          msg.role === 'user' ? '#1a1a2e' : '#f0f0f5',
                        color: msg.role === 'user' ? '#fff' : '#1a1a2e',
                        fontSize: 14,
                        lineHeight: 1.6,
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                      }}
                    >
                      {msg.content || (msg.streaming ? <Spin size="small" /> : '')}
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>

              {/* 输入框 */}
              <div
                style={{
                  padding: 12,
                  borderTop: '1px solid #f0f0f0',
                  display: 'flex',
                  gap: 8,
                }}
              >
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="输入消息..."
                  disabled={loading}
                  allowClear
                />
                <Button
                  type="primary"
                  icon={<SendOutlined />}
                  onClick={sendMessage}
                  loading={loading}
                  disabled={!input.trim()}
                />
              </div>
            </>
          )}
        </div>
      )}
    </>
  )
}
