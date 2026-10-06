/**
 * 录音管理器单例桥接 — 配套 AI 页「按住说话」（docs/语音记账实施指南.md §4.4）。
 *
 * ⚠️ uni.getRecorderManager() 是全局单例：onStart/onStop/onError 直接在每次页面
 * 实例创建时注册会**叠加**（页面经 reLaunch 反复重建，旧回调仍挂在单例上），
 * 表现为第二次录音触发两次转写。因此回调只在此处注册一次，页面通过
 * attach/detach 挂接当前实例的处理器（同一时刻仅一个页面用录音）。
 */

let recorder = null
let bridge = null   // 当前页面的 { onStart, onStop, onError }

function ensure() {
	if (recorder || typeof uni.getRecorderManager !== 'function') return
	recorder = uni.getRecorderManager()
	recorder.onStart(() => { if (bridge && bridge.onStart) bridge.onStart() })
	recorder.onStop((res) => { if (bridge && bridge.onStop) bridge.onStop(res) })
	recorder.onError(() => { if (bridge && bridge.onError) bridge.onError() })
}

/** 页面挂接录音回调；返回 null 表示当前环境不支持录音 */
export function attachRecorder(handlers) {
	ensure()
	bridge = handlers
	return recorder
}

/** 页面卸载时摘除回调，避免操作已销毁的页面状态 */
export function detachRecorder() {
	bridge = null
}

/** 获取录音管理器；不支持录音的环境返回 null */
export function getRecorder() {
	ensure()
	return recorder
}
