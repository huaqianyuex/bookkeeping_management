import request from './request'

const AI_BASE = '/ai'

/**
 * 创建新会话
 * POST /api/ai/sessions
 */
export const createSession = (title) => request({ url: AI_BASE + '/sessions', method: 'POST', data: { title } })

/**
 * 获取会话列表
 * GET /api/ai/sessions
 */
export const getSessions = () => request({ url: AI_BASE + '/sessions' })

/**
 * 获取会话的消息列表
 * GET /api/ai/sessions/{id}/messages
 */
export const getMessages = (sessionId) => request({ url: AI_BASE + '/' + sessionId + '/messages' })

/**
 * 发送消息（非流式，超时 120 秒）
 * POST /api/ai/chat
 *
 * uni-app 对 SSE 流式支持有限，使用非流式接口获取完整回复
 * AI 对话可能需要较长时间（调用 LLM），因此设置更长超时
 */
export const sendChat = (sessionId, message) => {
	return request({
		url: AI_BASE + '/chat',
		method: 'POST',
		data: { sessionId, message },
		timeout: 120000 // AI 对话可能需要 30-120 秒
	})
}
