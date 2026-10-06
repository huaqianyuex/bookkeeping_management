import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { applyPalette } from './theme/palette'
import { applyTokens } from './theme/tokens'

// 在首次渲染前把色板与标量令牌写入 :root —— design-tokens.css 不再持有真值，
// 晚于这一步渲染会导致颜色/尺寸变量缺失、首帧回退为浏览器默认值。
// 两个调用都是同步的，因此不会产生可观测的样式闪烁。
applyPalette()
applyTokens()

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
