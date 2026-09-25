<template>
  <view class="ai-chat-page" :style="{ height: pageHeight + 'px', paddingBottom: tabBarSpace + 'px' }">
    <!-- 状态栏占位 -->
    <view class="status-bar" :style="{ height: statusBarHeight + 'px' }"></view>
    <!-- 顶部栏（设计稿04：左大标题 + 右操作） -->
    <view class="header">
      <text class="title">AI 助手</text>
      <view class="header-actions">
        <view class="header-left" @click="handleNewChat">
          <AppIcon name="compose" :size="36" />
        </view>
        <view class="header-right" @click="goHistory">
          <AppIcon name="history" :size="36" />
        </view>
      </view>
    </view>

    <!-- 消息列表 -->
    <scroll-view
      class="messages"
      scroll-y
      :scroll-into-view="scrollAnchor"
      :scroll-with-animation="!streaming"
    >
      <view v-if="messages.length === 0" class="empty">
        <view class="empty-glyph">
          <AppIcon name="bot" :size="72" />
        </view>
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
        <!-- 消息气泡 -->
        <view class="bubble" :class="'bubble--' + msg.role">
          <text class="bubble-text">{{ msg.content }}</text>
          <text v-if="msg.streaming" class="stream-cursor">▌</text>
        </view>
      </view>

      <!-- 加载中 -->
      <view v-if="loading" class="message-row">
        <view class="bubble bubble--assistant">
          <view class="loading-dots">
            <text class="dot"></text>
            <text class="dot"></text>
            <text class="dot"></text>
          </view>
        </view>
      </view>

      <!-- 滚动锚点：两个 id 交替，实现流式输出时持续贴底 -->
      <view id="scroll-anchor-a" class="scroll-anchor" />
      <view id="scroll-anchor-b" class="scroll-anchor" />
    </scroll-view>

    <!-- 输入框 -->
    <view class="input-bar">
      <input
        class="input"
        v-model="inputText"
        :placeholder="isLoggedIn ? '输入你的问题...' : '登录后即可使用 AI 助手'"
        placeholder-class="input-placeholder"
        confirm-type="send"
        :adjust-position="true"
        :cursor-spacing="24"
        :disabled="loading || streaming || !isLoggedIn"
        @confirm="handleSend"
        @focus="scrollToBottom"
      />
      <view
        class="send-btn"
        :class="{ 'send-btn--disabled': !canSend && !streaming, 'send-btn--stop': streaming }"
        @tap="onSendTap"
      >
        <text class="send-text">{{ sendBtnText }}</text>
      </view>
    </view>

    <!-- 悬浮「+」抬升到输入条上方，避免遮挡发送按钮 -->
    <TabBar currentPage="pages/ai-chat/index" :fab="true" :fab-gap="170" />
  </view>
</template>

<script setup>
import { ref, nextTick, computed } from 'vue'
import { onLoad, onUnload, onShow } from '@dcloudio/uni-app'
import { createSession, sendChatStream, getMessages, aiBookkeeping } from '@/api/ai.js'
import AppIcon from '@/components/AppIcon.vue'

const statusBarHeight = ref(20)
// 页面可视高度 + 底部自定义 TabBar 占位高度（避免输入框被 TabBar 遮挡）
const pageHeight = ref(600)
const tabBarSpace = ref(50)
const inputText = ref('')
const messages = ref([])
const loading = ref(false)      // 等待首字节（创建会话 / 建立连接）
const streaming = ref(false)    // 正在流式输出
const sessionId = ref('')
// 滚动锚点：在两个 id 之间来回切换，保证同一条消息持续更新时也能滚动到底部
const scrollAnchor = ref('scroll-anchor-a')
let streamTask = null           // 当前流式请求控制器（用于中断）
let lastScrollAt = 0
// 语义记账的追问草稿：clarify 返回 draftId，用户补金额的下一条消息带上续写
const pendingDraftId = ref(null)

// 计算页面可用高度与底部安全距离
function calcLayout() {
	const systemInfo = uni.getSystemInfoSync()
	statusBarHeight.value = systemInfo.statusBarHeight || 20
	pageHeight.value = systemInfo.windowHeight || 600
	const safeBottom = systemInfo.safeAreaInsets?.bottom || 0
	// TabBar：悬浮胶囊约 170rpx 内容高度 + 安全区内边距（rpx -> px）
	const tabBarContent = typeof uni.upx2px === 'function' ? uni.upx2px(170) : 85
	tabBarSpace.value = tabBarContent + safeBottom
}

// 登录状态检查
const isLoggedIn = computed(() => !!uni.getStorageSync('token'))
const canSend = computed(() => !!inputText.value.trim() && !loading.value && !streaming.value && isLoggedIn.value)

// 发送按钮：流式输出中变为“停止”
const sendBtnText = computed(() => {
	if (streaming.value) return '停止'
	return isLoggedIn.value ? '发送' : '未登录'
})

// 快捷分析选项
const quickActions = [
  { label: '分析本月支出', text: '请帮我分析一下本月的支出情况，给出消费建议' },
  { label: '储蓄建议', text: '根据我的收支情况，帮我制定一个储蓄计划' },
  { label: '消费习惯分析', text: '从我的账单数据中分析我的消费习惯和模式' },
  { label: '预算规划', text: '根据我最近的消费记录，帮我做一个下月预算规划' }
]

// 快捷按钮点击：自动填入预设问题并发送
function handleQuickAction(item) {
	if (loading.value || streaming.value || !isLoggedIn.value) return
	inputText.value = item.text
	handleSend()
}

// 发送 / 停止
function onSendTap() {
	if (streaming.value) {
		handleStop()
	} else {
		handleSend()
	}
}

// 中断当前流式输出（已生成的内容保留）
function handleStop() {
	if (streamTask) {
		try { streamTask.abort() } catch (e) {}
		streamTask = null
	}
	finishStream()
}

// 跳转历史会话
function goHistory() {
	uni.navigateTo({ url: '/pages/ai-history/index' })
}

// 新建对话
function handleNewChat() {
	if (streaming.value) handleStop()
	sessionId.value = ''
	messages.value = []
	inputText.value = ''
	pendingDraftId.value = null
}

// 滚动到列表底部（切换锚点 id 以触发 scroll-into-view 重新滚动）
function scrollToBottom() {
	nextTick(() => {
		scrollAnchor.value = scrollAnchor.value === 'scroll-anchor-a' ? 'scroll-anchor-b' : 'scroll-anchor-a'
	})
}

// 流式输出时高频调用，做简单节流避免滚动抖動
function throttledScroll() {
	const now = Date.now()
	if (now - lastScrollAt < 120) return
	lastScrollAt = now
	scrollToBottom()
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

// 生成客户端幂等键（同一条消息弱网重发时，后端 5 分钟窗口内只记一笔）
function genClientMsgId() {
	return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
		const r = (Math.random() * 16) | 0
		const v = c === 'x' ? r : (r & 0x3) | 0x8
		return v.toString(16)
	})
}

/**
 * 先走语义记账（05 §6：前端据 action 分支渲染，非记账才降级对话）：
 * - created / duplicate / clarify（及部分 ignored 提示）→ 返回要展示的助手文案
 * - 纯聊天/查询（ignored: not_expense/query）或记账服务异常 → 返回 null，走对话流
 */
async function tryBookkeeping(text) {
	try {
		const res = await aiBookkeeping({
			sessionId: sessionId.value,
			message: text,
			clientMsgId: genClientMsgId(),
			draftId: pendingDraftId.value || undefined
		})
		if (!res || res.error) {
			// 会话失效（被删/过期清理）时重置，让对话流重建新会话
			if (res && res.error === '会话不存在') sessionId.value = ''
			pendingDraftId.value = null
			return null
		}
		if (res.action === 'created' || res.action === 'duplicate') {
			pendingDraftId.value = null
			return res.echo || (res.action === 'created' ? '已记下这笔消费。' : '这条已经记过啦，没有重复记账。')
		}
		if (res.action === 'clarify') {
			// 缺金额：展示追问，draftId 挂起，用户下一句「500块」自动续写
			pendingDraftId.value = res.draftId || null
			return res.question || '这笔消费的金额是多少？比如「35元」。'
		}
		if (res.action === 'ignored') {
			pendingDraftId.value = null
			// 找不到要修正/撤销的目标记录等服务端提示，比闲聊回复更有用
			const hintReasons = ['no_recent_record', 'income_unsupported', 'too_ambiguous']
			if (hintReasons.includes(res.reason) && res.echo) return res.echo
			return null   // not_expense / query → 降级为对话
		}
		pendingDraftId.value = null
		return null
	} catch (e) {
		// 网络失败/登录过期：交由对话流统一展示错误（其内含 401 弹窗逻辑）
		return null
	}
}

// 发送消息（先语义记账，未命中再走流式对话）
async function handleSend() {
	const text = inputText.value.trim()
	if (!text || loading.value || streaming.value) return

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
	scrollToBottom()
	loading.value = true

	// 如果还没有 session，先懒创建（bookkeeping 也会把消息写进会话，历史可回看）
	if (!sessionId.value) {
		const ok = await handleNewSession(text.slice(0, 20))
		if (!ok) {
			loading.value = false
			messages.value.pop()
			return
		}
	}

	// ① 语义记账：命中（created/clarify/duplicate 等）直接渲染服务端回显
	const handled = await tryBookkeeping(text)
	if (handled) {
		loading.value = false
		messages.value.push({ role: 'assistant', content: handled })
		scrollToBottom()
		return
	}

	// ② 非记账消息 → 占位助手消息，走原流式对话
	messages.value.push({ role: 'assistant', content: '', streaming: true })
	loading.value = false
	streaming.value = true
	scrollToBottom()

	streamTask = sendChatStream(sessionId.value, text, {
		onDelta: (delta) => {
			const last = messages.value[messages.value.length - 1]
			if (last && last.role === 'assistant') {
				last.content += delta
				throttledScroll()
			}
		},
		onDone: () => {
			finishStream()
		},
		onError: (err) => {
			console.error('[AI 流式对话失败]', err?.message || err)
			const errMsg = err?.message || ''
			const last = messages.value[messages.value.length - 1]
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
				uni.showToast({ title: '网络连接失败，请稍后重试', icon: 'none', duration: 2500 })
			} else {
				uni.showToast({ title: '对话失败: ' + errMsg, icon: 'none', duration: 2500 })
			}
			// 没输出任何内容时给一条兜底提示
			if (last && last.role === 'assistant' && !last.content.trim()) {
				last.content = '对话失败，请稍后重试。'
			}
			finishStream()
		}
	})
}

// 结束流式状态：保留已生成内容
function finishStream() {
	streaming.value = false
	loading.value = false
	streamTask = null
	const last = messages.value[messages.value.length - 1]
	if (last && last.role === 'assistant') {
		last.streaming = false
		if (!last.content.trim()) {
			last.content = '抱歉，暂时无法回复，请稍后再试。'
		}
	}
	scrollToBottom()
}

// 页面显示时检查登录状态
// 未登录/登录过期由 App.vue onLaunch 与 request.js 的全局 401 拦截统一处理，
// 此处不再主动 reLaunch，避免启动瞬间多个页面同时跳转造成 "do not operate continuously" 卡死。
onShow(() => {
	calcLayout()
	if (!isLoggedIn.value) {
		// 不主动跳转，由全局拦截器处理
	}
})

onLoad((options) => {
	calcLayout()
	// 从历史页面跳转过来时携带 sessionId，直接恢复上下文
	if (options && options.sessionId) {
		sessionId.value = options.sessionId
		loadHistoryMessages(options.sessionId)
	}
	// 概览「AI 解读」入口带问题跳入：预填输入框，由用户确认发送
	if (options && options.q) {
		try {
			inputText.value = decodeURIComponent(options.q)
		} catch (e) {
			inputText.value = options.q
		}
	}
})

// 加载历史会话的消息
async function loadHistoryMessages(sid) {
	try {
		const msgs = await getMessages(sid)
		if (Array.isArray(msgs) && msgs.length > 0) {
			messages.value = msgs.map(m => ({ role: m.role, content: m.content }))
			scrollToBottom()
		}
	} catch (e) {
		console.error('加载历史消息失败:', e)
	}
}

onUnload(() => {
	// 离开页面时中断流式请求，避免回调继续操作已销毁的页面
	if (streamTask) {
		try { streamTask.abort() } catch (e) {}
		streamTask = null
	}
})
</script>

<style scoped>
.ai-chat-page {
	display: flex;
	flex-direction: column;
	background: var(--color-bg);
	overflow: hidden;
}

.status-bar {
	width: 100%;
	background-color: var(--color-bg);
}

/* 设计稿04：透明顶栏 + 左侧大标题 */
.header {
	height: 96rpx;
	flex-shrink: 0;
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 0 var(--space-2xl);
	background: transparent;
	border-bottom: none;
}

.header-actions {
	display: flex;
	align-items: center;
	gap: var(--space-md);
}

.header-left,
.header-right {
	width: 72rpx;
	height: 72rpx;
	border-radius: var(--radius-full);
	background: var(--color-surface);
	border: var(--hairline) solid var(--color-border);
	display: flex;
	align-items: center;
	justify-content: center;
}

.header-left:active,
.header-right:active {
	background: var(--color-surface-raised);
}

.title {
	color: var(--color-text-heading);
	font-size: var(--font-3xl);
	font-weight: var(--weight-extrabold);
}

.messages {
	flex: 1;
	padding: var(--space-lg) var(--space-xl);
	overflow: hidden;
	min-height: 0;
}

.empty {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	padding-top: 160rpx;
}

/* 空态字形：绘制图标置于纸面浅盒 */
.empty-glyph {
	width: 140rpx;
	height: 140rpx;
	border-radius: var(--radius-full);
	background: var(--color-surface-raised);
	border: var(--hairline) solid var(--color-border);
	display: flex;
	align-items: center;
	justify-content: center;
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

/* 快捷提问（设计稿04：白色胶囊，无边框） */
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
	gap: var(--space-sm);
	padding: var(--space-md) var(--space-lg);
	background: var(--color-surface);
	border: var(--hairline) solid var(--color-border);
	border-radius: var(--radius-full);
}

.quick-btn:active {
	background: var(--color-surface-raised);
}

.quick-label {
	font-size: var(--font-sm);
	color: var(--color-text);
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

/* 用户气泡：墨黑胶囊；助手气泡：白面 + 发丝线 */
.bubble {
	max-width: 82%;
	padding: var(--space-lg) var(--space-xl);
	border-radius: var(--radius-2xl);
	margin: 0 var(--space-md);
}

.bubble--user {
	background: var(--color-primary);
	border-radius: var(--radius-full);
	border-bottom-right-radius: var(--radius-xs);
}

.bubble--assistant {
	background: var(--color-surface);
	border: var(--hairline) solid var(--color-border);
	box-shadow: none;
	border-radius: var(--radius-xl);
	border-bottom-left-radius: var(--radius-xs);
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

/* 流式输出光标（设计稿02：黄色光标） */
.stream-cursor {
	display: inline;
	font-size: var(--font-base);
	line-height: var(--leading-relaxed);
	color: var(--color-accent-deep);
	animation: cursor-blink 1s step-end infinite;
}

@keyframes cursor-blink {
	0%, 100% {
		opacity: 1;
	}
	50% {
		opacity: 0;
	}
}

/* 滚动锚点（高度为 0，仅用于 scroll-into-view 定位） */
.scroll-anchor {
	height: 1rpx;
	width: 100%;
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
	border-radius: var(--radius-full);
	background: var(--color-text-secondary);
	animation: dot-pulse 1.4s ease-in-out infinite;
}

.dot:nth-child(2) {
	animation-delay: 0.2s;
}

.dot:nth-child(3) {
	animation-delay: 0.4s;
}

/* 实为缩放+透明度脉冲（无位移），命名与动画一致 */
@keyframes dot-pulse {
	0%, 80%, 100% {
		transform: scale(0.6);
		opacity: 0.4;
	}
	40% {
		transform: scale(1);
		opacity: 1;
	}
}

/* 输入条：纸面 + 顶部结构线 */
.input-bar {
	display: flex;
	align-items: center;
	padding: var(--space-md) var(--space-2xl) var(--space-md);
	background: var(--color-bg);
	border-top: var(--hairline) solid var(--color-border);
	flex-shrink: 0;
}

.input {
	flex: 1;
	height: 88rpx;
	background: var(--color-surface-raised);
	border-radius: var(--radius-full);
	padding: 0 var(--space-xl);
	font-size: var(--font-base);
	margin-right: var(--space-md);
}

.send-btn {
	width: 88rpx;
	height: 88rpx;
	padding: 0;
	background: var(--color-primary);
	border-radius: var(--radius-full);
	box-shadow: var(--shadow-primary);
	display: flex;
	align-items: center;
	justify-content: center;
	flex-shrink: 0;
}

.send-btn--disabled {
	background: var(--color-disabled-bg);
}

/* 生成中的停止按钮 */
.send-btn--stop {
	background: var(--color-text-secondary);
}

.send-text {
	color: var(--color-text-inverse);
	font-size: var(--font-base);
	font-weight: var(--weight-medium);
}

.send-btn--disabled .send-text {
	color: var(--color-disabled-text);
}

.input-placeholder {
	color: var(--color-text-tertiary);
	font-size: var(--font-base);
}
</style>
