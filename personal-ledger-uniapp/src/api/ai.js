import request from './request'
import BASE_URL from './config'

const AI_BASE = '/ai'

// ==================== 会话管理 ====================

/** 创建新会话 */
export const createSession = (title) => request({ url: AI_BASE + '/sessions', method: 'POST', data: { title } })

/** 会话列表（搜索+排序+分页） */
export const listSessions = ({ keyword, sort, order, page, size } = {}) => {
	const params = {}
	if (keyword) params.keyword = keyword
	if (sort) params.sort = sort
	if (order) params.order = order
	if (page) params.page = page
	if (size) params.size = size
	return request({ url: AI_BASE + '/sessions', method: 'GET', data: params })
}

/** 重命名会话 */
export const renameSession = (id, title) => request({ url: AI_BASE + '/sessions/' + id, method: 'PATCH', data: { title } })

/** 删除会话（单条） */
export const deleteSession = (id) => request({ url: AI_BASE + '/sessions/' + id, method: 'DELETE' })

/** 批量删除会话 */
export const batchDeleteSessions = (ids) => request({ url: AI_BASE + '/sessions/batch-delete', method: 'POST', data: { ids } })

/** 获取会话的消息列表 */
export const getMessages = (sessionId) => request({ url: AI_BASE + '/sessions/' + sessionId + '/messages' })

// ==================== 对话 ====================

/** 发送消息（非流式，超时 120 秒）—— 仅作为流式不可用时的兜底 */
export const sendChat = (sessionId, message) => {
	return request({
		url: AI_BASE + '/chat',
		method: 'POST',
		data: { sessionId, message },
		timeout: 120000
	})
}

// ==================== 自然语言记账 ====================

/**
 * 语义记账（05 §6）：服务端解析口语化消息并入账。
 * 响应为裸 JSON（HTTP 200），顶层 action 字段：
 *   created  已入账（echo 可直接渲染）
 *   clarify  信息不全，追问（question + draftId，下一条消息带上续写）
 *   ignored  非消费类消息（reason 区分 not_expense/query 等，调用方应降级走对话）
 *   duplicate 命中幂等，未重复入账（echo）
 * {"error":"中文"} 表示记账服务失败（如 LLM 不可用），调用方降级走对话。
 */
export const aiBookkeeping = ({ sessionId, message, clientMsgId, draftId, dryRun, force } = {}) => {
	const data = { message }
	if (sessionId) data.sessionId = sessionId
	if (clientMsgId) data.clientMsgId = clientMsgId
	if (draftId) data.draftId = draftId
	if (dryRun) data.dryRun = dryRun
	if (force) data.force = force
	return request({
		url: AI_BASE + '/bookkeeping',
		method: 'POST',
		data,
		timeout: 60000
	})
}

// ==================== 流式对话（SSE） ====================

/**
 * 逐行解析 SSE 文本，回调 data: {...} 中的 JSON 对象。
 * 同时兼容 \n\n 与 \n 两种分隔（Java 网关逐行透传后仍为 data: {...}\n\n）。
 */
function createSseParser(onEvent) {
	let buffer = ''
	return (chunk) => {
		if (!chunk) return
		buffer += chunk
		let idx
		while ((idx = buffer.indexOf('\n')) !== -1) {
			const line = buffer.slice(0, idx).trim()
			buffer = buffer.slice(idx + 1)
			if (!line || line.indexOf('data:') !== 0) continue
			const payload = line.slice(5).trim()
			if (!payload || payload === '[DONE]') continue
			try {
				onEvent(JSON.parse(payload))
			} catch (e) {
				// 忽略非 JSON / 截断行
			}
		}
	}
}

/**
 * 分块 UTF-8 解码器：中文常被拆在两个 chunk 之间，必须保留残留字节，
 * 否则会出现乱码方块。
 */
function createUtf8Decoder() {
	if (typeof TextDecoder !== 'undefined') {
		try {
			const decoder = new TextDecoder('utf-8')
			return (buf) => decoder.decode(new Uint8Array(buf), { stream: true })
		} catch (e) {
			// 部分环境 TextDecoder 构造受限，走下面的手写实现
		}
	}
	let pending = []
	return (buf) => {
		const bytes = pending.concat(Array.from(new Uint8Array(buf)))
		pending = []
		let out = ''
		let i = 0
		while (i < bytes.length) {
			const b = bytes[i]
			let len = 1
			if (b >= 0xf0) len = 4
			else if (b >= 0xe0) len = 3
			else if (b >= 0xc0) len = 2
			if (i + len > bytes.length) {
				pending = bytes.slice(i) // 半截字符留到下一个 chunk
				break
			}
			let hex = ''
			for (let k = 0; k < len; k++) {
				hex += '%' + ('0' + bytes[i + k].toString(16)).slice(-2)
			}
			try {
				out += decodeURIComponent(hex)
			} catch (e) {
				out += '?'
			}
			i += len
		}
		return out
	}
}

/**
 * 流式对话（SSE）
 * 服务端事件格式：data: {"type":"content"|"done"|"error", ...}
 *
 * H5 端：fetch + ReadableStream
 * 小程序 / App 端：uni.request({ enableChunked: true }) + onChunkReceived
 *
 * @param {string} sessionId
 * @param {string} message
 * @param {{onDelta:Function, onDone:Function, onError:Function}} handlers
 * @returns {{abort:Function}} 调用 abort() 可中断生成
 */
export const sendChatStream = (sessionId, message, handlers = {}) => {
	const onDelta = handlers.onDelta || (() => {})
	const onDone = handlers.onDone || (() => {})
	const onError = handlers.onError || (() => {})

	const token = uni.getStorageSync('token')
	const url = BASE_URL + AI_BASE + '/chat/stream'
	const header = {
		'Content-Type': 'application/json',
		'Authorization': token ? `Bearer ${token}` : ''
	}
	const body = { sessionId, message }

	let finished = false
	let gotChunk = false
	const finish = () => {
		if (finished) return
		finished = true
		onDone()
	}
	const fail = (err) => {
		if (finished) return
		finished = true
		onError(err instanceof Error ? err : new Error((err && err.errMsg) || (err && err.message) || '对话失败'))
	}
	const handle401 = () => fail(new Error('未登录或登录已过期'))

	const parse = createSseParser((data) => {
		if (data.type === 'content') {
			gotChunk = true
			onDelta(data.content || '')
		} else if (data.type === 'error') {
			onError(new Error(data.error || '对话失败'))
		} else if (data.type === 'done') {
			gotChunk = true
			finish()
		}
	})

	const controller = { abort: () => { finished = true } }

	// #ifdef H5
	const ac = typeof AbortController !== 'undefined' ? new AbortController() : null
	controller.abort = () => {
		finished = true
		if (ac) ac.abort()
	}
	fetch(url, {
		method: 'POST',
		headers: header,
		body: JSON.stringify(body),
		signal: ac ? ac.signal : undefined
	}).then(async (res) => {
		if (res.status === 401) {
			handle401()
			return
		}
		if (!res.ok) {
			fail(new Error('请求失败（' + res.status + '）'))
			return
		}
		const reader = res.body.getReader()
		const decoder = new TextDecoder('utf-8')
		while (true) {
			const { done, value } = await reader.read()
			if (done) break
			if (finished) {
				try { await reader.cancel() } catch (e) {}
				break
			}
			parse(decoder.decode(value, { stream: true }))
		}
		finish()
	}).catch((e) => {
		if (e && e.name === 'AbortError') return
		fail(e)
	})
	return controller
	// #endif

	// #ifndef H5
	const task = uni.request({
		url,
		method: 'POST',
		data: body,
		header,
		timeout: 180000,
		enableChunked: true,
		success: (res) => {
			if (res.statusCode === 401) {
				handle401()
				return
			}
			if (res.statusCode >= 500) {
				fail(new Error('服务器错误，请稍后重试'))
				return
			}
			// 平台不支持分块时，success 会带全量数据，这里兜底解析一次
			if (!gotChunk && res.data) {
				parse(typeof res.data === 'string' ? res.data : JSON.stringify(res.data))
			}
			finish()
		},
		fail: (err) => fail(err)
	})

	if (task && typeof task.onChunkReceived === 'function') {
		const decode = createUtf8Decoder()
		task.onChunkReceived((res) => {
			if (finished) return
			parse(decode(res.data))
		})
	}

	controller.abort = () => {
		finished = true
		try { if (task && task.abort) task.abort() } catch (e) {}
	}
	return controller
	// #endif
}
