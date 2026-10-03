import dayjs from 'dayjs'

/**
 * "2026-10-03T13:26:15" → "2026-10-03 13:26"
 * 非法或空值原样返回 '-'，供表格与详情展示使用
 */
export function formatDateTime(text) {
  if (!text) return '-'
  const d = dayjs(text)
  return d.isValid() ? d.format('YYYY-MM-DD HH:mm') : String(text)
}
