<template>
  <view class="ai-chat-page">
    <!-- 顶部栏 -->
    <view class="header">
      <text class="title">AI记账助手</text>
    </view>

    <!-- 消息列表 -->
    <scroll-view
      class="messages"
      scroll-y
      :scroll-into-view="'msg-' + currentMsgId"
      scroll-with-animation
    >
      <view v-if="messages.length === 0" class="empty">
        <text class="empty-icon">🤖</text>
        <text class="empty-text">你好！我是AI记账助手</text>
        <text class="empty-desc">可以问我关于记账、财务分析等问题</text>

        <!-- 快捷分析按钮（有登录状态才显示） -->
        <view v-if="isLoggedIn" class="quick-actions">
          <view
            v-for="(item, idx) in quickActions"
            :key="idx"
            class="quick-btn"
            @tap="handleQuickAction(item)"
          >
            <text class="quick-icon">{{ item.icon }}</text>
            <text class="quick-label">{{ item.label }}</text>
          </view>
        </view>
      </view>

      <view
        v-for="(msg, index) in messages"
        :key="index"
        :id="'msg-' + index"
        class="message-row"
        :class="{ 'message-row--right': msg.role === 'user' }"
      >
        <!-- 助手头像 -->
        <view v-if="msg.role === 'assistant'" class="avatar avatar-ai">🤖</view>
        <!-- 用户头像 -->
        <view v-if="msg.role === 'user'" class="avatar avatar-user">👤</view>

        <!-- 消息气泡 -->
        <view class="bubble" :class="'bubble--' + msg.role">
          <text class="bubble-text">{{ msg.content }}</text>
        </view>
      </view>

      <!-- 加载中 -->
      <view v-if="loading" class="message-row">
        <view class="avatar avatar-ai">🤖</view>
        <view class="bubble bubble--assistant">
          <view class="loading-dots">
            <text class="dot"></text>
            <text class="dot"></text>
            <text class="dot"></text>
          </view>
        </view>
      </view>

      <view :style="{ height: '100rpx' }" />
    </scroll-view>

    <!-- 输入框 -->
    <view class="input-bar">
      <input
        class="input"
        v-model="inputText"
        placeholder="输入你的问题..."
        confirm-type="send"
        @confirm="handleSend"
        :disabled="loading || !isLoggedIn"
      />
      <view class="send-btn" :class="{ 'send-btn--disabled': !canSend }" @tap="handleSend">
        <text class="send-text">{{ isLoggedIn ? '发送' : '未登录' }}</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, nextTick, computed } from 'vue'
import { onLoad, onUnload, onShow } from '@dcloudio/uni-app'
import { createSession, sendChat } from '@/api/ai.js'

const inputText = ref('')
const messages = ref([])
const loading = ref(false)
const sessionId = ref('')
const currentMsgId = ref(0)

// 登录状态检查
const isLoggedIn = computed(() => !!uni.getStorageSync('token'))
const canSend = computed(() => !!inputText.value.trim() && !loading.value && isLoggedIn.value)

// 快捷分析选项
const quickActions = [
  { icon: '📊', label: '分析本月支出', text: '请帮我分析一下本月的支出情况，给出消费建议' },
  { icon: '💰', label: '储蓄建议', text: '根据我的收支情况，帮我制定一个储蓄计划' },
  { icon: '📈', label: '消费习惯分析', text: '从我的账单数据中分析我的消费习惯和模式' },
  { icon: '🎯', label: '预算规划', text: '根据我最近的消费记录，帮我做一个下月预算规划' }
]

// 快捷按钮点击：自动填入预设问题并发送
function handleQuickAction(item) {
	if (loading.value || !isLoggedIn.value) return
	inputText.value = item.text
	handleSend()
}

// 创建新会话（带详细错误信息）
async function handleNewSession(title) {
	try {
		const res = await createSession(title || '新对话')
		if (res && res.id) {
			sessionId.value = res.id
			return true
		}
		console.warn('创建会话返回异常:', res)
		return false
	} catch (e) {
		const errMsg = e?.message || ''
		console.error('创建会话失败详情:', errMsg)

		if (errMsg.includes('未登录') || errMsg.includes('过期') || errMsg.includes('401')) {
			uni.showModal({
				title: '请先登录',
				content: '使用 AI 助手需要先登录账号',
				confirmText: '去登录',
				success: (res) => {
					if (res.confirm) {
						uni.reLaunch({ url: '/pages/login/index' })
					}
				}
			})
		} else if (errMsg.includes('网络') || errMsg.includes('fail') || errMsg.includes('timeout')) {
			uni.showToast({ title: '网络连接失败，请稍后重试', icon: 'none', duration: 2500 })
		} else {
			uni.showToast({ title: '创建会话失败: ' + errMsg, icon: 'none', duration: 3000 })
		}
		return false
	}
}

// 发送消息（合并创建会话 + 发送）
async function handleSend() {
	const text = inputText.value.trim()
	if (!text || loading.value) return

	// 未登录拦截
	if (!isLoggedIn.value) {
		uni.showModal({
			title: '请先登录',
			content: '使用 AI 助手需要先登录账号',
			confirmText: '去登录',
			success: (res) => {
				if (res.confirm) {
					uni.reLaunch({ url: '/pages/login/index' })
				}
			}
		})
		return
	}

	// 显示用户消息
	messages.value.push({ role: 'user', content: text })
	inputText.value = ''
	currentMsgId.value = messages.value.length - 1
	loading.value = true

	try {
		// 如果还没有 session，先懒创建
		if (!sessionId.value) {
			const ok = await handleNewSession(text.slice(0, 20))
			if (!ok) {
				loading.value = false
				messages.value.pop()
				return
			}
		}

		const res = await sendChat(sessionId.value, text)

		// 提取回复文本
		let assistantContent = ''
		if (typeof res === 'string') {
			assistantContent = res
		} else if (res && typeof res === 'object') {
			assistantContent = res.content || res.answer || res.text || res.message || res.reply || ''
		}

		messages.value.push({
			role: 'assistant',
			content: assistantContent || '抱歉，暂时无法回复，请稍后再试。'
		})

		// 滚动到最新消息
		nextTick(() => { currentMsgId.value = messages.value.length - 1 })
	} catch (e) {
		console.error('AI 对话失败:', e?.message || e)
		const errMsg = e?.message || ''
		if (errMsg.includes('未登录') || errMsg.includes('过期')) {
			uni.showModal({
				title: '登录已失效',
				content: '请重新登录后继续使用 AI 助手',
				confirmText: '去登录',
				success: (res) => {
					if (res.confirm) uni.reLaunch({ url: '/pages/login/index' })
				}
			})
		} else if (errMsg.includes('网络') || errMsg.includes('fail') || errMsg.includes('timeout')) {
			uni.showToast({ title: 'AI 分析可能需要较长时间，请耐心等待...', icon: 'none', duration: 3000 })
		} else {
			uni.showToast({ title: '对话失败: ' + errMsg, icon: 'none', duration: 2500 })
		}
		messages.value.push({ role: 'assistant', content: '对话失败，请稍后重试。' })
	} finally {
		loading.value = false
	}
}

// 页面显示时检查登录状态
onShow(() => {
	if (!isLoggedIn.value) {
		console.log('[AI Chat] 当前未登录，将在发送消息时引导登录')
	}
})

onLoad(() => {
	// 不在加载时自动请求
})

onUnload(() => {
	// 清理
})
</script>

<style scoped>
.ai-chat-page {
	display: flex;
	flex-direction: column;
	height: 100vh;
	background: var(--color-bg);
}

.header {
	height: 88rpx;
	display: flex;
	align-items: center;
	justify-content: center;
	background: var(--color-primary);
	padding-top: env(safe-area-inset-top);
}

.title {
	color: var(--color-text-inverse);
	font-size: var(--font-xl);
	font-weight: var(--weight-semibold);
}

.messages {
	flex: 1;
	padding: var(--space-lg) var(--space-xl);
}

.empty {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	padding-top: 160rpx;
}

.empty-icon {
	font-size: 100rpx;
	margin-bottom: var(--space-xl);
}

.empty-text {
	font-size: var(--font-lg);
	color: var(--color-text-secondary);
	margin-bottom: var(--space-sm);
}

.empty-desc {
	font-size: var(--font-sm);
	color: var(--color-text-tertiary);
	margin-bottom: var(--space-3xl);
}

/* 快捷分析按钮 */
.quick-actions {
	display: flex;
	flex-wrap: wrap;
	justify-content: center;
	gap: var(--space-md);
	width: 100%;
	padding: 0 var(--space-xs);
}

.quick-btn {
	display: flex;
	align-items: center;
	gap: 10rpx;
	padding: 18rpx var(--space-lg);
	background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
	border-radius: var(--radius-full);
	box-shadow: 0 4rpx 12rpx rgba(102, 126, 234, 0.3);
}

.quick-btn:active {
	opacity: 0.85;
	transform: scale(0.97);
}

.quick-icon {
	font-size: var(--font-xl);
}

.quick-label {
	font-size: var(--font-sm);
	color: var(--color-text-inverse);
	font-weight: var(--weight-medium);
}

.message-row {
	display: flex;
	align-items: flex-start;
	margin-bottom: var(--space-xl);
}

.message-row--right {
	flex-direction: row-reverse;
}

.avatar {
	width: 64rpx;
	height: 64rpx;
	border-radius: 50%;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: var(--font-lg);
	flex-shrink: 0;
}

.avatar-ai {
	background: var(--color-primary);
}

.avatar-user {
	background: var(--color-text-secondary);
}

.bubble {
	max-width: 65%;
	padding: var(--space-lg) var(--space-lg);
	border-radius: var(--radius-2xl);
	margin: 0 var(--space-md);
}

.bubble--user {
	background: var(--color-primary);
}

.bubble--assistant {
	background: var(--color-surface);
}

.bubble-text {
	font-size: var(--font-base);
	line-height: var(--leading-relaxed);
	word-break: break-all;
}

.bubble--user .bubble-text {
	color: var(--color-text-inverse);
}

.bubble--assistant .bubble-text {
	color: var(--color-text);
}

/* 加载动画 */
.loading-dots {
	display: flex;
	gap: var(--space-xs);
	padding: var(--space-xs) 0;
}

.dot {
	width: 12rpx;
	height: 12rpx;
	border-radius: 50%;
	background: var(--color-text-secondary);
	animation: dot-bounce 1.4s ease-in-out infinite;
}

.dot:nth-child(2) {
	animation-delay: 0.2s;
}

.dot:nth-child(3) {
	animation-delay: 0.4s;
}

@keyframes dot-bounce {
	0%, 80%, 100% {
		transform: scale(0.6);
		opacity: 0.4;
	}
	40% {
		transform: scale(1);
		opacity: 1;
	}
}

.input-bar {
	display: flex;
	align-items: end;
	padding: var(--space-lg) var(--space-lg);
	padding-bottom: calc(20rpx + env(safe-area-inset-bottom));
	background: var(--color-surface);
	border-top: 1rpx solid var(--color-border);
}

.input {
	flex: 1;
	height: 72rpx;
	background: var(--color-bg);
	border-radius: var(--radius-full);
	padding: 0 var(--space-lg);
	font-size: var(--font-base);
	margin-right: var(--space-md);
}

.send-btn {
	height: 72rpx;
	padding: 0 var(--space-xl);
	background: var(--color-primary);
	border-radius: var(--radius-full);
	display: flex;
	align-items: center;
	justify-content: center;
	flex-shrink: 0;
}

.send-btn--disabled {
	background: var(--color-disabled-bg);
}

.send-text {
	color: var(--color-text-inverse);
	font-size: var(--font-base);
	font-weight: var(--weight-medium);
}

.send-btn--disabled .send-text {
	color: var(--color-disabled-text);
}
</style>
