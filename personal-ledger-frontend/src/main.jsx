import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { applyPalette } from './theme/palette'

// 在首次渲染前把色板写入 :root —— design-tokens.css 不再持有颜色字面量，
// 晚于这一步渲染会导致颜色变量缺失、首帧回退为浏览器默认色。
applyPalette()

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
