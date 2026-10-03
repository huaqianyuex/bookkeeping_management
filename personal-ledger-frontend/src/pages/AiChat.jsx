import { useState, useRef, useEffect } from 'react'
import { Card, Input, Button, Avatar, App as AntdApp, Select, Empty, Checkbox, Modal, Drawer } from 'antd'
import {
  RobotOutlined, SendOutlined, PlusOutlined, UserOutlined,
  SearchOutlined, DeleteOutlined, EditOutlined,
  MenuFoldOutlined, MenuUnfoldOutlined,
} from '@ant-design/icons'
import {
  listSessions, createSession, renameSession,
  deleteSession, batchDeleteSessions, getSessionMessages,
} from '../api/ai-session'
import { AnimatedRoute } from '../components/ui'
import useMediaQuery from '../hooks/useMediaQuery'

const API_BASE = '/api/ai'

/** 时间戳 → 相对时间文本 */
function formatRelative(ts) {
  const diff = Date.now() - ts
  const min = Math.floor(diff / 60000)
  if (min < 1) return '刚刚'
  if (min < 60) return `${min}分钟前`
  const hour = Math.floor(min / 60)
  if (hour < 24) return `${hour}小时前`
  const day = Math.floor(hour / 24)
  if (day < 7) return `${day}天前`
  const d = new Date(ts)
  return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export default function AiChatPage() {
  // —— 对话核心状态 ——
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)
  const { message, modal } = AntdApp.useApp()
  const isMobile = useMediaQuery('(max-width: 767px)')

  // —— 侧边栏状态 ——（移动端默认收起为抽屉，桌面默认展开）
  const [sidebarOpen, setSidebarOpen] = useState(() => window.innerWidth >= 768)
  const [keyword, setKeyword] = useState('')
  const [sort, setSort] = useState('updated')
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const [listLoading, setListLoading] = useState(false)

  // 批量选择模式
  const [batchMode, setBatchMode] = useState(false)
  const [selected, setSelected] = useState([])

  // 重命名
  const [renamingId, setRenamingId] = useState(null)
  const [renameValue, setRenameValue] = useState('')

  const PAGE_SIZE = 20

  // —— 数据加载 ——
  const fetchList = async (p = 1, kw = keyword, append = false) => {
    setListLoading(true)
    try {
      const res = await listSessions({ keyword: kw || undefined, sort, order: 'desc', page: p, size: PAGE_SIZE })
      setItems((prev) => (append ? [...prev, ...(res.items || [])] : res.items || []))
      setTotal(res.total || 0)
      setPage(p)
      setHasMore(p * PAGE_SIZE < (res.total || 0))
    } catch {
      message.error('加载会话列表失败')
    } finally {
      setListLoading(false)
    }
  }

  // 侧边栏打开、切排序时拉第一页
  useEffect(() => {
    if (sidebarOpen) fetchList(1)
  }, [sidebarOpen, sort])

  // 搜索防抖 300ms
  useEffect(() => {
    const t = setTimeout(() => { if (sidebarOpen) fetchList(1, keyword) }, 300)
    return () => clearTimeout(t)
  }, [keyword])

  // 消息自动滚底
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // —— 事件处理 ——
  const handleNewSession = async () => {
    setLoading(true)
    try {
      const data = await createSession('新对话')
      if (data.id) {
        setSessionId(data.id)
        setMessages([])
        if (isMobile) setSidebarOpen(false)
        if (sidebarOpen) fetchList(1)
      }
    } catch {
      message.error('创建会话失败')
    }
    setLoading(false)
  }

  const handleOpenSession = async (sid) => {
    if (sid === sessionId) return
    try {
      const msgs = await getSessionMessages(sid)
      setSessionId(sid)
      setMessages(msgs || [])
      if (isMobile) setSidebarOpen(false)
    } catch {
      message.error('加载对话失败')
    }
  }

  const handleRename = async (sid) => {
    const title = renameValue.trim().slice(0, 50)
    setRenamingId(null)
    if (!title) return
    try {
      await renameSession(sid, title)
      message.success('已重命名')
      fetchList(page)
    } catch {
      message.error('重命名失败')
    }
  }

  const handleDeleteOne = (s) => {
    modal.confirm({
      title: '删除该对话？',
      content: `「${s.title || '新对话'}」及其全部消息将被永久移除，无法恢复。`,
      okText: '删除', okType: 'danger', cancelText: '取消',
      onOk: async () => {
        try {
          await deleteSession(s.id)
          message.success('已删除')
          if (s.id === sessionId) { setSessionId(null); setMessages([]) }
          fetchList(1)
        } catch {
          message.error('删除失败')
        }
      },
    })
  }

  const toggleSelect = (id) =>
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))

  const handleBatchDelete = () => {
    modal.confirm({
      title: `删除选中的 ${selected.length} 条对话？`,
      content: '所选对话及全部消息将被永久移除，无法恢复。',
      okText: '全部删除', okType: 'danger', cancelText: '取消',
      onOk: async () => {
        try {
          await batchDeleteSessions(selected)
          message.success(`已删除 ${selected.length} 条`)
          selected.forEach((id) => { if (id === sessionId) { setSessionId(null); setMessages([]) } })
          setBatchMode(false); setSelected([])
          fetchList(1)
        } catch {
          message.error('批量删除失败')
        }
      },
    })
  }

  // —— 发送消息（POST + JSON body，修复 @RequestBody 问题）——
  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const userMsg = { role: 'user', content: input.trim() }
    setMessages((prev) => [...prev, userMsg])
    const currentInput = input.trim()
    setInput('')
    setLoading(true)

    if (!sessionId) {
      try {
        const data = await createSession(currentInput.slice(0, 20))
        if (data.id) setSessionId(data.id)
      } catch {
        message.error('创建会话失败')
        setLoading(false)
        return
      }
    }

    try {
      const res = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({ sessionId, message: currentInput }),
      })

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
                    return [...prev.slice(0, -1), { ...last, content: last.content + data.content }]
                  }
                  return prev
                })
              } else if (data.type === 'error') {
                message.error(data.error || '对话失败')
              }
            } catch {
              // skip malformed SSE
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
      // 流式 done 后延迟 3s 拉一次列表（等 AI 标题生成）
      if (sidebarOpen) setTimeout(() => fetchList(1), 3000)
    }
  }

  // —— 列表项渲染 ——
  const renderSessionItem = (s) => {
    const active = s.id === sessionId
    const isSelected = selected.includes(s.id)
    const itemClass = [
      'session-item',
      active ? 'session-item--active' : '',
      isSelected ? 'session-item--selected' : '',
    ].filter(Boolean).join(' ')
    return (
      <div
        key={s.id}
        className={itemClass}
        onClick={() => batchMode ? toggleSelect(s.id) : handleOpenSession(s.id)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {batchMode && (
            <Checkbox checked={isSelected} onClick={(e) => e.stopPropagation()}
                      onChange={() => toggleSelect(s.id)} />
          )}
          {renamingId === s.id ? (
            <Input
              size="small" autoFocus value={renameValue}
              onClick={(e) => e.stopPropagation()}
              onChange={(e) => setRenameValue(e.target.value)}
              onPressEnter={() => handleRename(s.id)}
              onKeyDown={(e) => e.key === 'Escape' && setRenamingId(null)}
              onBlur={() => renameValue.trim() && handleRename(s.id)}
              style={{ flex: 1 }}
            />
          ) : (
            <span style={{
              flex: 1, fontSize: 14, fontWeight: active ? 600 : 400,
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}>
              {s.title || '新对话'}
            </span>
          )}
          {!batchMode && (
            <span className="session-item-actions">
              <Button type="text" size="small" icon={<EditOutlined />}
                      onClick={(e) => { e.stopPropagation(); setRenamingId(s.id); setRenameValue(s.title) }} />
              <Button type="text" size="small" danger icon={<DeleteOutlined />}
                      onClick={(e) => { e.stopPropagation(); handleDeleteOne(s) }} />
            </span>
          )}
        </div>
        <div style={{ fontSize: 12, color: 'var(--color-text-tertiary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginTop: 4 }}>
          {s.preview || '（暂无消息）'}
        </div>
        <div style={{ fontSize: 12, color: 'var(--color-text-tertiary)', marginTop: 2 }}>
          {formatRelative(s.updatedAt)} · {s.messageCount}条
        </div>
      </div>
    )
  }

  // —— 会话侧边栏内容（桌面 aside 与移动 Drawer 共用） ——
  const sidebarContent = (
    <>
      <div style={{ display: 'flex', gap: 8, padding: 12, borderBottom: '1px solid var(--color-border)' }}>
        <Button type="primary" icon={<PlusOutlined />} block onClick={handleNewSession}>新对话</Button>
        {!isMobile && <Button icon={<MenuFoldOutlined />} onClick={() => setSidebarOpen(false)} />}
      </div>

      <div style={{ padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
        <Input prefix={<SearchOutlined />} placeholder="搜索标题或内容" allowClear
               value={keyword} onChange={(e) => setKeyword(e.target.value)} />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Select size="small" value={sort} onChange={setSort}
                  options={[{ value: 'updated', label: '最后更新' }, { value: 'created', label: '创建时间' }]}
                  style={{ width: 120 }} />
          <Button size="small" type={batchMode ? 'primary' : 'default'}
                  onClick={() => { setBatchMode(!batchMode); setSelected([]) }}>
            {batchMode ? '取消' : '管理'}
          </Button>
        </div>
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: '0 8px' }}>
        {items.length === 0 && !listLoading && (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无历史对话" style={{ marginTop: 40 }} />
        )}
        {items.map((s) => renderSessionItem(s))}
        {hasMore && (
          <Button block style={{ margin: 8 }} loading={listLoading}
                  onClick={() => fetchList(page + 1, keyword, true)}>加载更多</Button>
        )}
      </div>

      {batchMode && (
        <div style={{ padding: 12, borderTop: '1px solid var(--color-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>已选 {selected.length} 条</span>
          <Button danger icon={<DeleteOutlined />} disabled={selected.length === 0} onClick={handleBatchDelete}>删除</Button>
        </div>
      )}
    </>
  )

  const pageHeight = isMobile
    ? 'calc(100vh - var(--header-height) - 40px)'
    : 'calc(100vh - var(--header-height) - 48px)'

  // —— JSX ——
  return (
    <AnimatedRoute>
      <div style={{ height: pageHeight, display: 'flex', background: 'transparent', boxSizing: 'border-box', gap: 16 }}>
        {/* ====== 左：历史会话侧边栏（桌面） / 抽屉（移动） ====== */}
        {isMobile ? (
          <Drawer
            placement="left"
            width={300}
            open={sidebarOpen}
            onClose={() => setSidebarOpen(false)}
            title="历史对话"
            styles={{ body: { padding: 0, display: 'flex', flexDirection: 'column' } }}
          >
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              {sidebarContent}
            </div>
          </Drawer>
        ) : (
          <aside style={{
            width: sidebarOpen ? 280 : 0,
            flexShrink: 0,
            overflow: 'hidden',
            opacity: sidebarOpen ? 1 : 0,
            transition: `width var(--transition-base) ease, opacity var(--transition-base) ease`,
          }}>
            <div style={{
              width: 280, height: '100%', display: 'flex', flexDirection: 'column',
              background: 'var(--color-surface)', border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-lg)', overflow: 'hidden',
            }}>
              {sidebarContent}
            </div>
          </aside>
        )}

        {/* ====== 右：主对话区 ====== */}
        <Card
          variant="borderless"
          className="card-base"
          style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', minWidth: 0 }}
          styles={{ body: { flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', padding: 0 } }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 16, borderBottom: '1px solid var(--color-border)' }}>
            <h2 style={{ margin: 0, color: 'var(--color-text)', fontSize: 'var(--font-size-lg)', display: 'flex', alignItems: 'center', gap: 10 }}>
              <RobotOutlined style={{ color: 'var(--color-primary)' }} />
              AI记账助手
            </h2>
            {(isMobile || !sidebarOpen) && (
              <Button
                type="text"
                icon={<MenuUnfoldOutlined />}
                onClick={() => setSidebarOpen(true)}
              />
            )}
          </div>

          <div style={{ flex: 1, overflow: 'auto', padding: isMobile ? 16 : 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
            {messages.length === 0 && (
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-tertiary)' }}>
                <RobotOutlined style={{ fontSize: 64, color: 'var(--color-text-tertiary)', opacity: 0.5, marginBottom: 16 }} />
                <div style={{ fontSize: 16, marginBottom: 8, color: 'var(--color-text)' }}>你好！我是AI记账助手</div>
                <div style={{ fontSize: 13, color: 'var(--color-text-secondary)', display: 'inline-block', textAlign: 'left' }}>
                  我可以帮你：
                  <ul style={{ textAlign: 'left', margin: '8px 0 0', padding: '0 0 0 18px' }}>
                    <li>回答记账和财务相关问题</li>
                    <li>提供消费建议和预算规划</li>
                    <li>分析你的消费习惯</li>
                  </ul>
                </div>
              </div>
            )}
            {messages.map((msg, i) => {
              const isUser = msg.role === 'user'
              const typing = !isUser && msg.streaming && !msg.content
              return (
                <div key={i} style={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start', gap: 10 }}>
                  {!isUser && (
                    <Avatar size={40} icon={<RobotOutlined />} style={{ background: 'var(--color-primary)', flexShrink: 0 }} />
                  )}
                  <div style={{
                    maxWidth: isMobile ? '85%' : '70%', padding: '12px 16px',
                    borderRadius: isUser
                      ? 'var(--radius-2xl) var(--radius-2xl) 4px var(--radius-2xl)'
                      : 'var(--radius-2xl) var(--radius-2xl) var(--radius-2xl) 4px',
                    background: isUser ? 'var(--gradient-primary)' : 'var(--color-surface)',
                    border: isUser ? 'none' : '1px solid var(--color-border)',
                    color: isUser ? 'var(--color-text-inverse)' : 'var(--color-text)',
                    fontSize: 14, lineHeight: 1.7, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                    boxShadow: 'var(--shadow-sm)',
                  }}>
                    {typing ? (
                      <span className="chat-typing"><i /><i /><i /></span>
                    ) : (
                      <>
                        {msg.content}
                        {msg.streaming && <span className="chat-cursor" />}
                      </>
                    )}
                  </div>
                  {isUser && (
                    <Avatar size={40} icon={<UserOutlined />} style={{ background: 'var(--color-text-secondary)', flexShrink: 0 }} />
                  )}
                </div>
              )
            })}
            <div ref={messagesEndRef} />
          </div>

          <div style={{ padding: 16, borderTop: '1px solid var(--color-border)', display: 'flex', gap: 12 }}>
            <Input
              value={input} onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() } }}
              placeholder="输入你的问题..." size="large" disabled={loading}
            />
            <Button type="primary" size="large" icon={<SendOutlined />}
                    onClick={sendMessage} loading={loading} disabled={!input.trim()}
                    style={{ minWidth: 80 }}>发送</Button>
          </div>
        </Card>
      </div>
    </AnimatedRoute>
  )
}
