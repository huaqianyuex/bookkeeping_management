/**
 * JWT 本地解析工具 — 仅用于读取 exp 提前清理过期 token，不校验签名。
 * 签名校验始终由后端完成；这里解析失败一律按"已过期"处理，
 * 让清理逻辑走同一出口，由后端 401 / 重新登录兜底。
 */

// base64url 字母表与标准 base64 的差异仅在 -_ 与 +/，JWT 不携带标准字符
const B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'

/** base64url 解码为字节数组；含非法字符返回 null。不依赖 atob，H5/App/小程序均可运行 */
function base64UrlDecode(input) {
	const str = String(input).replace(/-/g, '+').replace(/_/g, '/').replace(/=+$/, '')
	let acc = 0
	let bits = 0
	const bytes = []
	for (let i = 0; i < str.length; i++) {
		const val = B64.indexOf(str[i])
		if (val === -1) return null
		acc = (acc << 6) | val
		bits += 6
		if (bits >= 8) {
			bits -= 8
			bytes.push((acc >> bits) & 0xff)
		}
	}
	return bytes
}

/** 字节序列 → UTF-8 字符串，用 percent-encoding 兜底无 TextDecoder 的运行时 */
function bytesToUtf8(bytes) {
	const percented = bytes.map(b => '%' + ('00' + b.toString(16)).slice(-2)).join('')
	try {
		return decodeURIComponent(percented)
	} catch (e) {
		return null
	}
}

/**
 * 解析 JWT payload；格式非法返回 null
 * @param {string} token
 */
export function getTokenPayload(token) {
	if (!token || typeof token !== 'string') return null
	const parts = token.split('.')
	if (parts.length !== 3) return null
	const bytes = base64UrlDecode(parts[1])
	if (!bytes || !bytes.length) return null
	const json = bytesToUtf8(bytes)
	if (!json) return null
	try {
		const payload = JSON.parse(json)
		return payload && typeof payload === 'object' ? payload : null
	} catch (e) {
		return null
	}
}

/**
 * token 是否已过期（本地时钟判断）。
 * 解析不出 exp 也返回 true：无效 token 留着只会等 401，提前清理行为一致。
 * @param {string} token
 * @param {number} leewaySeconds 容忍的时钟偏差秒数，避免临界过期被服务端判活
 */
export function isTokenExpired(token, leewaySeconds = 30) {
	const payload = getTokenPayload(token)
	if (!payload || typeof payload.exp !== 'number') return true
	return Date.now() / 1000 >= payload.exp - leewaySeconds
}
