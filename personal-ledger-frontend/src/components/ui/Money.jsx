import { Typography } from 'antd'

const { Text } = Typography

/**
 * 千分位 + 两位小数的金额文本（不含货币符号与正负号）
 */
export function formatMoney(value) {
  const n = Number(value) || 0
  return Math.abs(n).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

/**
 * Money - 全站统一的金额展示：¥ 符号 + 千分位 + tabular-nums + 收支语义色
 *
 * @param {number|string} value - 金额数值
 * @param {'income'|'expense'|'plain'|'balance'} [type='plain'] - 语义类型；
 *   income 绿 / expense 红 / balance 按数值正负着色 / plain 中性色
 * @param {boolean} [signed=false] - 是否渲染 +/- 号（expense 为 -，income 为 +）
 * @param {number|string} [categoryType] - 便捷入口：账单的类型字段（0=支出 1=收入），
 *   传入时自动映射为 expense / income
 */
export default function Money({
  value,
  type = 'plain',
  signed = false,
  categoryType,
  style,
  ...rest
}) {
  const resolved = categoryType !== undefined
    ? (Number(categoryType) === 0 ? 'expense' : 'income')
    : type
  const n = Number(value) || 0

  const colorMap = {
    income: 'var(--color-income)',
    expense: 'var(--color-expense)',
    balance: n >= 0 ? 'var(--color-text)' : 'var(--color-expense)',
    plain: 'var(--color-text)',
  }

  const sign = signed ? (resolved === 'expense' ? '-' : resolved === 'income' ? '+' : '') : ''
  const text = `${sign}¥${formatMoney(n)}`

  return (
    <Text className="money" strong style={{ color: colorMap[resolved], ...style }} {...rest}>
      {text}
    </Text>
  )
}
