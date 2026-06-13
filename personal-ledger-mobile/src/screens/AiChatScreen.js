import { useState, useRef, useCallback } from 'react'
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Alert,
  StyleSheet,
} from 'react-native'
import AsyncStorage from '@react-native-async-storage/async-storage'
import { API_BASE_URL } from '../config'
import { theme } from '../config/theme'
import ScaleButton from '../components/ScaleButton'

export default function AiChatScreen() {
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const scrollRef = useRef(null)

  // 创建新会话
  const createSession = async (title) => {
    try {
      const token = await AsyncStorage.getItem('token')
      const res = await fetch(`${API_BASE_URL}/ai/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ title }),
      })
      const data = await res.json()
      if (data.id) {
        setSessionId(data.id)
        setMessages([])
      }
    } catch (e) {
      Alert.alert('错误', '创建会话失败')
    }
  }

  // 发送消息（SSE流式）
  const sendMessage = async () => {
    const text = input.trim()
    if (!text || loading) return

    const userMsg = { role: 'user', content: text, id: Date.now() }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)

    let sid = sessionId
    if (!sid) {
      await createSession(text.slice(0, 20))
      sid = sessionId
    }

    if (!sid) {
      setLoading(false)
      return
    }

    // 添加空的AI消息占位
    const aiMsgId = Date.now() + 1
    setMessages((prev) => [
      ...prev,
      { role: 'assistant', content: '', id: aiMsgId, streaming: true },
    ])

    try {
      const token = await AsyncStorage.getItem('token')
      const res = await fetch(
        `${API_BASE_URL}/ai/chat/stream?sessionId=${sid}&message=${encodeURIComponent(text)}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      )

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
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === aiMsgId
                      ? { ...m, content: m.content + data.content }
                      : m
                  )
                )
              }
            } catch {
              // skip
            }
          }
        }
      }

      setMessages((prev) =>
        prev.map((m) => (m.id === aiMsgId ? { ...m, streaming: false } : m))
      )
    } catch (e) {
      Alert.alert('错误', '对话失败: ' + e.message)
      setMessages((prev) =>
        prev.filter((m) => m.id !== aiMsgId)
      )
    } finally {
      setLoading(false)
    }
  }

  const renderItem = (msg) => (
    <View
      key={msg.id}
      style={[
        styles.messageRow,
        msg.role === 'user' ? styles.messageRowRight : styles.messageRowLeft,
      ]}
    >
      <View
        style={[
          styles.avatar,
          msg.role === 'user' ? styles.avatarUser : styles.avatarAi,
        ]}
      >
        <Text style={styles.avatarText}>
          {msg.role === 'user' ? '👤' : '🤖'}
        </Text>
      </View>
      <View
        style={[
          styles.bubble,
          msg.role === 'user' ? styles.bubbleUser : styles.bubbleAi,
        ]}
      >
        {msg.streaming ? (
          <ActivityIndicator size="small" color={theme.colors.textLight} />
        ) : (
          <Text style={[styles.bubbleText, msg.role === 'user' && styles.bubbleTextUser]}>
            {msg.content}
          </Text>
        )}
      </View>
    </View>
  )

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={0}
    >
      {/* 空状态 */}
      {messages.length === 0 && !loading ? (
        <View style={styles.empty}>
          <Text style={styles.emptyIcon}>🤖</Text>
          <Text style={styles.emptyTitle}>AI记账助手</Text>
          <Text style={styles.emptyDesc}>
            可以问我关于记账、财务分析等问题
          </Text>
        </View>
      ) : (
        <ScrollView
          ref={scrollRef}
          style={styles.scrollView}
          onContentSizeChange={() =>
            scrollRef.current?.scrollToEnd({ animated: true })
          }
          contentContainerStyle={styles.messageList}
        >
          {messages.map(renderItem)}
          {loading && messages[messages.length - 1]?.role !== 'assistant' && (
            <View style={styles.messageRowLeft}>
              <View style={[styles.avatar, styles.avatarAi]}>
                <Text style={styles.avatarText}>🤖</Text>
              </View>
              <View style={[styles.bubble, styles.bubbleAi]}>
                <ActivityIndicator size="small" color={theme.colors.textLight} />
              </View>
            </View>
          )}
        </ScrollView>
      )}

      {/* 输入框 */}
      <View style={styles.inputBar}>
        <TextInput
          style={styles.input}
          value={input}
          onChangeText={setInput}
          placeholder="输入你的问题..."
          placeholderTextColor={theme.colors.textLight}
          multiline
          editable={!loading}
          onSubmitEditing={sendMessage}
        />
        <ScaleButton
          style={[
            styles.sendBtn,
            (!input.trim() || loading) && styles.sendBtnDisabled,
          ]}
          onPress={sendMessage}
          disabled={!input.trim() || loading}
        >
          <Text style={[styles.sendText, !input.trim() && styles.sendTextDisabled]}>
            发送
          </Text>
        </ScaleButton>
      </View>
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  empty: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: theme.spacing.xl,
  },
  emptyIcon: {
    fontSize: 72,
    marginBottom: theme.spacing.md,
  },
  emptyTitle: {
    ...theme.typography.h2,
    color: theme.colors.text,
    marginBottom: theme.spacing.sm,
  },
  emptyDesc: {
    fontSize: 14,
    color: theme.colors.textLight,
    textAlign: 'center',
  },
  scrollView: {
    flex: 1,
  },
  messageList: {
    padding: theme.spacing.md,
    gap: 12,
  },
  messageRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    maxWidth: '85%',
  },
  messageRowLeft: {
    alignSelf: 'flex-start',
  },
  messageRowRight: {
    alignSelf: 'flex-end',
    flexDirection: 'row-reverse',
  },
  avatar: {
    width: 36,
    height: 36,
    borderRadius: 18,
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarAi: {
    backgroundColor: theme.colors.primary,
  },
  avatarUser: {
    backgroundColor: theme.colors.textSecondary,
  },
  avatarText: {
    fontSize: 18,
  },
  bubble: {
    marginHorizontal: 10,
    padding: 12,
    borderRadius: theme.borderRadius.lg,
    minHeight: 24,
    maxHeight: 300,
  },
  bubbleAi: {
    backgroundColor: theme.colors.surface,
    borderTopLeftRadius: 4,
    ...theme.shadows.small,
  },
  bubbleUser: {
    backgroundColor: theme.colors.primary,
    borderTopRightRadius: 4,
  },
  bubbleText: {
    fontSize: 15,
    lineHeight: 22,
    color: theme.colors.text,
  },
  bubbleTextUser: {
    color: theme.colors.surface,
  },
  inputBar: {
    flexDirection: 'row',
    padding: theme.spacing.md,
    paddingBottom: Platform.OS === 'ios' ? theme.spacing.md : 8,
    borderTopWidth: 1,
    borderTopColor: theme.colors.borderLight,
    backgroundColor: theme.colors.surface,
    gap: 10,
    alignItems: 'flex-end',
  },
  input: {
    flex: 1,
    backgroundColor: theme.colors.background,
    borderRadius: 20,
    padding: 12,
    fontSize: 15,
    maxHeight: 120,
    textAlignVertical: 'top',
    minHeight: 44,
    color: theme.colors.text,
  },
  sendBtn: {
    backgroundColor: theme.colors.primary,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 20,
    minHeight: 44,
  },
  sendBtnDisabled: {
    backgroundColor: theme.colors.border,
  },
  sendText: {
    color: theme.colors.surface,
    fontSize: 15,
    fontWeight: '600',
  },
  sendTextDisabled: {
    color: theme.colors.surface,
    opacity: 0.5,
  },
})
