/**
 * 把 axios 抛出的错误转成可展示给用户的一句话。
 *
 * 页面里原先散落着 `error?.response?.data?.message || '请求失败，请稍后重试'`，
 * 五处重复且对网络中断没有专门提示。这里收敛为一处，按可诊断性排序降级：
 * 后端 message → HTTP 状态码 → 网络中断 → 兜底文案。
 *
 * @param {any} error axios 拦截器 reject 出来的错误对象
 * @param {string} [fallback] 全部拿不到时的兜底文案
 * @returns {string}
 */
export function extractErrorMessage(error, fallback = '请求失败，请稍后重试') {
  const fromServer = error?.response?.data?.message
  if (fromServer) return fromServer

  const status = error?.response?.status
  if (status) return `请求失败（HTTP ${status}）`

  if (error?.message === 'Network Error') {
    return '网络连接异常，请检查网络后重试'
  }

  return fallback
}