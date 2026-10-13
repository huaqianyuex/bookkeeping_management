<template>
  <view class="ai-chat-page" :style="{ height: pageHeight + 'px', paddingBottom: (keyboardHeight > 0 ? 0 : tabBarSpace) + 'px' }">
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

    <!-- 输入条：话筒（按住说话）+ 输入框 + 发送 -->
    <view class="input-bar">
      <!-- 录音状态：悬浮在输入条上方，不挤压布局 -->
      <view v-if="recording" class="recording-pill">
        <view class="recording-dot"></view>
        <text class="recording-pill-text">{{ recordSeconds }}s · 松开结束</text>
      </view>
      <view
        v-if="voiceEnabled"
        class="mic-btn"
        :class="{ 'mic-btn--rec': recording }"
        @touchstart.prevent="startRecord"
        @touchend.prevent="stopRecord"
        @touchcancel="stopRecord"
        @mousedown="startRecord"
        @mouseup="stopRecord"
        @mouseleave="stopRecord"
      >
        <AppIcon :name="recording ? 'mic-rec' : 'mic'" :size="44" />
      </view>
      <input
        class="input"
        v-model="inputText"
        :placeholder="recording ? '正在听写，请讲话...' : (isLoggedIn ? '输入你的问题...' : '登录后即可使用 AI 助手')"
        placeholder-class="input-placeholder"
        confirm-type="send"
        :adjust-position="false"
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

    <!-- 金额确认框：语音/文字记账预览命中后弹出，改完金额再入账 -->
    <AmountConfirmPanel
      :visible="confirmVisible"
      :items="confirmItems"
      :warnings="confirmWarnings"
      :source="confirmSource"
      :submitting="confirmSubmitting"
      @confirm="handleConfirm"
      @cancel="handleConfirmCancel"
    />

    <!-- 键盘弹出时隐藏底部导航（保持最底层，不随输入框一起被顶起） -->
    <TabBar v-show="keyboardHeight === 0" currentPage="pages/ai-chat/index" :fab="true" :fab-gap="170" />
  </view>
</template>

<script setup>
import { ref, nextTick, computed } from 'vue'
import { onLoad, onUnload, onShow } from '@dcloudio/uni-app'
import { createSession, sendChatStream, getMessages, aiBookkeeping } from '@/api/ai.js'
import { transcribeVoice, getVoiceConfig } from '@/api/voice.js'
import { attachRecorder, detachRecorder, getRecorder } from '@/utils/recorder.js'
import AppIcon from '@/components/AppIcon.vue'
import AmountConfirmPanel from '@/components/AmountConfirmPanel.vue'

const statusBarHeight = ref(20)
// 页面可视高度 + 底部自定义 TabBar 占位高度（避免输入框被 TabBar 遮挡）
const pageHeight = ref(600)
const tabBarSpace = ref(50)
const inputText = ref('')
const messages = ref([])
const loading = ref(false)      // 等待首字节（创建会话 / 建立连接）
const streaming = ref(false)    // 正在流式输出
const sessionId = ref('')
// 键盘当前高度（0 = 收起）：弹出时手动压缩页面高度并隐藏 TabBar
const keyboardHeight = ref(0)
// 滚动锚点：在两个 id 之间来回切换，保证同一条消息持续更新时也能滚动到底部
const scrollAnchor = ref('scroll-anchor-a')
let streamTask = null           // 当前流式请求控制器（用于中断）
let lastScrollAt = 0
// 语义记账的追问草稿：clarify 返回 draftId，用户补金额的下一条消息带上续写
const pendingDraftId = ref(null)
// 本条输入的来源（text=键盘 / voice=话筒），随下一条记账请求上报审计
let lastInputSource = 'text'

// ── 金额确认框：语义记账「预览 → 确认」两步流程的中间态 ──
// 预览命中消费时挂起 pendingConfirm（尚未落库），用户改完金额再确认入账。
const confirmVisible = ref(false)
const confirmItems = ref([])
const confirmWarnings = ref([])
const confirmSource = ref('text')
const confirmSubmitting = ref(false)
// 挂起的预览上下文：确认时复用同一 clientMsgId / draftId / 原文，保证幂等与追问续写
const pendingConfirm = ref(null)

let fullHeight = 600   // 键盘未弹出时的完整视口高度（仅在键盘收起时刷新，防污染）

// 计算页面可用高度与底部安全距离
function calcLayout() {
	const systemInfo = uni.getSystemInfoSync()
	statusBarHeight.value = systemInfo.statusBarHeight || 20
	const safeBottom = systemInfo.safeAreaInsets?.bottom || 0
	// TabBar：悬浮胶囊约 170rpx 内容高度 + 安全区内边距（rpx -> px）
	const tabBarContent = typeof uni.upx2px === 'function' ? uni.upx2px(170) : 85
	tabBarSpace.value = tabBarContent + safeBottom
	// ⚠️ 只在键盘收起时才信任 windowHeight：键盘开着（adjustResize 视口已被系统压矮）
	// 时切后台再回来，onShow 会触发本函数，若此刻刷新 fullHeight，
	// 之后每次开关键盘都会在已被压缩的基准上再减，页面越压越扁
	if (keyboardHeight.value === 0) {
		fullHeight = systemInfo.windowHeight || 600
		pageHeight.value = fullHeight
	}
}

// ── 键盘避让：页面锁定 softinputMode=adjustResize（pages.json），系统把视口压到
// 键盘上沿，无原生平移；这里只需把页面高度同步为「完整视口 - 键盘高」，
// 输入条（flex 底部元素）即贴住键盘；TabBar 隐藏，不再随页面一起被顶起 ──
function onKeyboardChange(res) {
	const kb = (res && res.height) || 0
	keyboardHeight.value = kb
	// 只用干净基准 fullHeight 计算，不读实时 windowHeight（键盘弹出时它已被
	// 系统压矮，再减一次键盘高就是双重补偿——输入条会悬空一个键盘高度）
	pageHeight.value = kb > 0 ? Math.max(320, fullHeight - kb) : fullHeight
	if (kb > 0) scrollToBottom()
}

// ── 语音输入：按住话筒说话 → 转写 → 回填输入框（用户核对/修改后再发送）──
const voiceEnabled = ref(false)
const recording = ref(false)
const transcribing = ref(false)
const recordSeconds = ref(0)
const STT_LOW_CONFIDENCE = 0.4   // 与后端 config.settings STT_LOW_CONFIDENCE 同值
let recordTimer = null
let recordStartAt = 0

const recorder = getRecorder()   // 全局单例，回调经 utils/recorder.js 桥接（只注册一次）

// 后端语音开关：失败/未开启一律隐藏话筒入口，避免「点了才知道不可用」
async function loadVoiceConfig() {
	try {
		const res = await getVoiceConfig()
		voiceEnabled.value = !!(res && res.enabled === true)
	} catch (e) {
		voiceEnabled.value = false
	}
}

function startRecord() {
	if (!voiceEnabled.value || recording.value || transcribing.value) return
	if (loading.value || streaming.value) return
	if (!isLoggedIn.value) {
		uni.showToast({ title: '登录后即可语音输入', icon: 'none' })
		return
	}
	if (!recorder) {
		uni.showToast({ title: '当前环境不支持录音', icon: 'none' })
		return
	}
	recordStartAt = Date.now()
	try {
		recorder.start({
			duration: 60000,
			sampleRate: 16000,
			numberOfChannels: 1,
			// #ifdef H5
			format: 'webm',      // H5 端 MediaRecorder 只认 webm/opus（后端白名单已放行）
			// #endif
			// #ifndef H5
			format: 'mp3',       // App / 小程序用 mp3
			// #endif
			bitRate: 48000
		})
	} catch (e) {
		recording.value = false
		uni.showToast({ title: '当前环境不支持录音', icon: 'none' })
	}
}

function stopRecord() {
	// 触摸事件与 H5 合成的鼠标事件可能双触发：仅录音中才响应
	if (!recording.value) return
	try { recorder.stop() } catch (e) {}
}

async function handleTranscribe(filePath) {
	transcribing.value = true
	uni.showLoading({ title: '识别中...', mask: true })
	try {
		const res = await transcribeVoice(filePath)
		const text = (res && res.text ? res.text : '').trim()
		if (!text) {
			uni.showToast({ title: '没听清，请再说一次', icon: 'none' })
			return
		}
		// 回填输入框而非直接发送：识别结果须过目，避免错记
		inputText.value = inputText.value ? inputText.value + text : text
		lastInputSource = 'voice'
		if (res.confidence != null && res.confidence < STT_LOW_CONFIDENCE) {
			uni.showToast({ title: '识别可能不准确，请核对', icon: 'none' })
		}
	} catch (e) {
		uni.showModal({
			title: '语音识别失败',
			content: (e && e.message) || '请稍后重试',
			confirmText: '改为键盘输入',
			showCancel: false
		})
	} finally {
		uni.hideLoading()
		transcribing.value = false
	}
}

// 录音单例回调桥：页面实例挂接/卸载（重复注册会叠加触发，见 utils/recorder.js）
attachRecorder({
	onStart: () => {
		recording.value = true
		recordSeconds.value = 0
		recordTimer = setInterval(() => {
			recordSeconds.value = Math.floor((Date.now() - recordStartAt) / 1000)
			if (recordSeconds.value >= 60) stopRecord()   // 与 duration=60000 双保险
		}, 1000)
	},
	onStop: (res) => {
		if (recordTimer) { clearInterval(recordTimer); recordTimer = null }
		recording.value = false
		if (!res || !res.tempFilePath) return
		if (Date.now() - recordStartAt < 500) {   // 误触：按一下就松
			uni.showToast({ title: '说话时间太短', icon: 'none' })
			return
		}
		handleTranscribe(res.tempFilePath)
	},
	onError: () => {
		if (recordTimer) { clearInterval(recordTimer); recordTimer = null }
		recording.value = false
		uni.showToast({ title: '无法录音，请检查麦克风权限', icon: 'none' })
	}
})

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
	lastInputSource = 'text'
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
	// 关闭并丢弃未确认的记账预览，避免串到新会话
	confirmVisible.value = false
	pendingConfirm.value = null
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
 * 语义记账第一步：dryRun 预览（05 §6 + 金额确认框契约）。
 *
 * 返回「动作指令」，由 handleSend 决定后续走向：
 *   { type:'quota' }            额度用尽 → 弹窗终止
 *   { type:'error', message }   预览失败（限流等）→ 提示，且不落库
 *   { type:'reply', content }   非消费但服务端有提示文案 → 直接渲染
 *   { type:'confirm', ... }     命中消费 → 弹金额确认框（含 clientMsgId / 原文 / 条目）
 *   null                        非记账（查询/闲聊）或服务异常 → 降级流式对话
 *
 * ⚠️ 预览不落库、不扣 daily_bookkeeping 配额，但会真实跑一次 LLM 解析，
 *    故服务端另有 bookkeeping_preview_rate_limiter 独立限流。
 */
async function previewBookkeeping(text, source) {
	// clientMsgId 在此生成并随预览结果挂起，确认时复用：
	// 同一 key 连点确认会被服务端幂等键拦成 duplicate，不会重复入账。
	const clientMsgId = genClientMsgId()
	try {
		const res = await aiBookkeeping({
			sessionId: sessionId.value,
			message: text,
			clientMsgId,
			draftId: pendingDraftId.value || undefined,
			source: source || 'text',
			dryRun: true
		})
		if (res && res.code === 'QUOTA_EXCEEDED') return { type: 'quota' }
		if (!res || res.error) {
			// 会话失效（被删/过期清理）时重置，让对话流重建新会话
			if (res && res.error === '会话不存在') sessionId.value = ''
			// 预览限流：明确提示并终止（不落库），避免用户误以为已记账
			if (res && res.code === 'RATE_LIMIT') return { type: 'error', message: res.error }
			return null   // 其余（LLM 不可用等）→ 降级对话，与旧行为一致
		}
		if (res.action === 'ignored') {
			pendingDraftId.value = null
			// 找不到要修正/撤销的目标记录等服务端提示，比闲聊回复更有用
			const hintReasons = ['no_recent_record', 'income_unsupported', 'too_ambiguous']
			if (hintReasons.includes(res.reason) && res.echo) return { type: 'reply', content: res.echo }
			return null   // not_expense / query → 降级为对话
		}
		if (res.action === 'preview') {
			const items = (res.preview && res.preview.items) || []
			if (!items.length) return null
			return {
				type: 'confirm',
				clientMsgId,
				// 预览响应的 requestId：确认时回传，服务端据此复用本次解析结果、跳过第二次 AI 解析
				previewId: res.requestId || null,
				text,
				source: source || 'text',
				draftId: pendingDraftId.value || undefined,
				items,
				warnings: res.warnings || []
			}
		}
		// created / duplicate / clarify 不应出现在 dryRun 分支；兜底降级对话
		return null
	} catch (e) {
		// 网络失败/登录过期：交由对话流统一展示错误（其内含 401 弹窗逻辑）
		return null
	}
}

/**
 * 金额确认框「确认记账」：带着用户改后的金额（overrides）真正入账。
 * 与预览复用同一 clientMsgId，落库只发生在这里一次。
 */
async function handleConfirm({ overrides }) {
	const p = pendingConfirm.value
	if (!p) return
	confirmSubmitting.value = true
	try {
		const res = await aiBookkeeping({
			sessionId: sessionId.value,
			message: p.text,
			clientMsgId: p.clientMsgId,
			previewId: p.previewId,     // 复用预览的解析结果，跳过第二次 AI 解析（毫秒级入账）
			draftId: p.draftId,
			source: p.source,
			overrides
		})
		confirmVisible.value = false
		pendingConfirm.value = null

		if (res && res.code === 'QUOTA_EXCEEDED') {
			showQuotaModal()
			return
		}
		if (!res || res.error) {
			if (res && res.error === '会话不存在') sessionId.value = ''
			messages.value.push({ role: 'assistant', content: (res && res.error) || '记账失败，请稍后重试。' })
			scrollToBottom()
			return
		}
		if (res.action === 'created' || res.action === 'duplicate') {
			pendingDraftId.value = null
			messages.value.push({
				role: 'assistant',
				content: res.echo || (res.action === 'created' ? '已记下这笔消费。' : '这条已经记过啦，没有重复记账。')
			})
		} else if (res.action === 'clarify') {
			// 兜底：确认后仍缺金额（确认框已保证有值，此处防御服务端二次解析差异）
			pendingDraftId.value = res.draftId || null
			messages.value.push({ role: 'assistant', content: res.question || '这笔消费的金额是多少？' })
		} else if (res.action === 'ignored') {
			pendingDraftId.value = null
			messages.value.push({ role: 'assistant', content: res.echo || '这不像一笔消费记录，我没有记账。' })
		} else {
			messages.value.push({ role: 'assistant', content: '已完成。' })
		}
		scrollToBottom()
	} catch (e) {
		confirmVisible.value = false
		pendingConfirm.value = null
		messages.value.push({ role: 'assistant', content: '记账失败，请稍后重试。' })
		scrollToBottom()
	} finally {
		confirmSubmitting.value = false
	}
}

/** 取消确认：丢弃本次预览，不落库、不占用配额 */
function handleConfirmCancel() {
	if (confirmSubmitting.value) return
	confirmVisible.value = false
	pendingConfirm.value = null
	uni.showToast({ title: '已取消，本次未记账', icon: 'none' })
}

// 额度用尽统一弹窗：无论文字/语音、记账/对话，命中闸门一律终止并提示
function showQuotaModal() {
	uni.showModal({
		title: '额度已用完',
		content: '额度已使用完毕，请充值后继续使用。',
		confirmText: '去充值',
		cancelText: '知道了',
		success: (res) => {
			if (res.confirm) uni.navigateTo({ url: '/pages/membership/index' })
		}
	})
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

	// ① 语义记账预览：命中消费 → 弹金额确认框（确认前不落库）
	const outcome = await previewBookkeeping(text, lastInputSource)
	lastInputSource = 'text'
	if (outcome && outcome.type === 'quota') {
		// 额度用尽：不做任何回复或处理，撤回刚显示的用户消息
		loading.value = false
		messages.value.pop()
		showQuotaModal()
		return
	}
	if (outcome && outcome.type === 'error') {
		loading.value = false
		messages.value.push({ role: 'assistant', content: outcome.message })
		scrollToBottom()
		return
	}
	if (outcome && outcome.type === 'reply') {
		loading.value = false
		messages.value.push({ role: 'assistant', content: outcome.content })
		scrollToBottom()
		return
	}
	if (outcome && outcome.type === 'confirm') {
		// 命中消费：挂起预览上下文，弹出金额确认框，等用户核对/改金额后再入账
		loading.value = false
		pendingConfirm.value = {
			clientMsgId: outcome.clientMsgId,
			previewId: outcome.previewId,
			text: outcome.text,
			source: outcome.source,
			draftId: outcome.draftId
		}
		confirmItems.value = outcome.items
		confirmWarnings.value = outcome.warnings
		confirmSource.value = outcome.source
		confirmVisible.value = true
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
			} else if (err && err.isQuotaExceeded) {
				// 后端配额闸门 429（QUOTA_EXCEEDED）：不回复不处理，撤回占位气泡并弹窗
				if (last && last.role === 'assistant') messages.value.pop()
				showQuotaModal()
				finishStream()
				return
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
	loadVoiceConfig()
	if (!isLoggedIn.value) {
		// 不主动跳转，由全局拦截器处理
	}
})

onLoad((options) => {
	calcLayout()
	// 键盘高度监听：App / 小程序 / H5（部分版本）支持，不支持时保持原有表现
	if (typeof uni.onKeyboardHeightChange === 'function') {
		uni.onKeyboardHeightChange(onKeyboardChange)
	}
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
		lastInputSource = 'text'
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
	// 注销键盘监听与录音回调桥，防止泄漏到下一次页面实例
	if (typeof uni.offKeyboardHeightChange === 'function') {
		uni.offKeyboardHeightChange(onKeyboardChange)
	}
	detachRecorder()
	if (recordTimer) { clearInterval(recordTimer); recordTimer = null }
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

/* 输入条：纸面 + 顶部结构线；作为录音提示胶囊的定位锚点 */
.input-bar {
	position: relative;
	display: flex;
	align-items: center;
	padding: var(--space-md) var(--space-2xl) var(--space-md);
	background: var(--color-bg);
	border-top: var(--hairline) solid var(--color-border);
	flex-shrink: 0;
}

/* 录音状态胶囊：悬浮在输入条上方，不挤压消息区布局 */
.recording-pill {
	position: absolute;
	top: -72rpx;
	left: 50%;
	transform: translateX(-50%);
	display: flex;
	align-items: center;
	gap: var(--space-sm);
	padding: 14rpx 32rpx;
	background: var(--color-primary);
	border-radius: var(--radius-full);
	box-shadow: var(--shadow-primary);
	z-index: 10;
}

.recording-pill-text {
	color: var(--color-text-inverse);
	font-size: var(--font-sm);
	line-height: 1;
}

/* 录音中的红点呼吸 */
.recording-dot {
	width: 14rpx;
	height: 14rpx;
	border-radius: var(--radius-full);
	background: var(--color-accent);
	animation: recording-pulse 1.2s ease-in-out infinite;
}

@keyframes recording-pulse {
	0%, 100% { opacity: 0.35; }
	50% { opacity: 1; }
}

/* 话筒按钮：与输入框同高的圆形浅盒；录音中图标切语义红（AppIcon 内烘色） */
.mic-btn {
	width: 88rpx;
	height: 88rpx;
	border-radius: var(--radius-full);
	background: var(--color-surface-raised);
	display: flex;
	align-items: center;
	justify-content: center;
	flex-shrink: 0;
	margin-right: var(--space-md);
	-webkit-tap-highlight-color: transparent;
}

.mic-btn:active {
	background: var(--color-surface);
}

.mic-btn--rec {
	background: var(--color-surface);
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
