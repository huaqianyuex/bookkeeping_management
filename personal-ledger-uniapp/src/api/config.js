// =============================================
// 后端 API 地址配置
// =============================================
//
// 【真机/模拟器运行必读】
// 下方地址需要改为你电脑当前的局域网 IP 地址
//
// 查找本机局域网 IP：
//   Windows: cmd → ipconfig → 找到 "IPv4 地址"
//   macOS:   终端 → ifconfig | grep inet
//
// 确认后端已启动（默认端口 8080），且手机与电脑在同一 WiFi 下
// =============================================

let _BASE_URL = ''

function initBaseUrl() {
	if (_BASE_URL) return _BASE_URL

	// #ifdef H5
	_BASE_URL = '/api'
	// #endif

		// #ifndef H5
		// ⬇⬇⬇ 把下面的 IP 改成你电脑的局域网 IP ⬇⬇⬇
		// 2026-10-05：本机 WLAN 网卡 IP（ipconfig 确认；VMware 虚拟网卡 192.168.49.1/17.1 不可用）
		// 电脑换 WiFi 后 IP 会变，报 Unable to resolve host / timeout 时重新 ipconfig 核对
		_BASE_URL = 'http://192.168.101.84:8000/api'
		// #endif

	return _BASE_URL
}

const BASE_URL = initBaseUrl()

export default BASE_URL

/**
 * 【调试用】获取当前 BASE_URL 值，方便排查网络问题
 * 在页面中调用 import { getBaseUrl } from '@/api/config' 即可打印
 */
export const getBaseUrl = () => BASE_URL
