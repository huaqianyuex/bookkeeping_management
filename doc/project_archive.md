# 个人记账本 — 项目存档

## 项目信息

| 项目 | 内容 |
|------|------|
| 项目名称 | 个人记账本 (Account Book) |
| 技术栈 | Vue 3 + TypeScript + Vite + Element Plus (前端) / Spring Boot + MyBatis-Plus + JWT (后端) |
| 前端端口 | 5173 (Vite dev) |
| 后端端口 | 8080 (Spring Boot) |
| 数据库 | MySQL `bookkeeping_book` (用户: root / 密码: 123456) |
| 项目路径 | `E:\一些毕设探索\记账管理系统` |
| 存档日期 | 2026-05-17 |

## 目录结构

```
记账管理系统/
├── front_end/           # Vue 3 前端项目
│   ├── src/
│   │   ├── api/         # API 接口封装
│   │   ├── layouts/     # 布局组件 (MainLayout.vue)
│   │   ├── router/      # 路由配置
│   │   ├── stores/      # Pinia 状态管理
│   │   ├── types/       # TS 类型定义
│   │   ├── utils/       # Axios 请求封装
│   │   ├── views/       # 页面组件
│   │   │   ├── Login.vue
│   │   │   ├── Records.vue
│   │   │   ├── Categories.vue
│   │   │   └── Statistics.vue
│   │   ├── App.vue
│   │   └── main.ts
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   └── README.md
├── backend/
│   └── test_backend/    # Spring Boot 后端项目
├── database_backup_20260517.sql   # 数据库备份
├── 接口文档.md
└── doc/
    └── project_archive.md
```

## 当前工作状态

### 已完成 (100%)

#### 1. 后端 (Spring Boot)
- 用户模块: 注册 / 登录 / 获取信息 / 修改密码
- 分类模块: CRUD (按类型筛选)
- 账单模块: CRUD + 分页 + 月份/分类筛选
- 统计模块: 月度汇总 + 分类统计
- JWT 拦截器 + 全局异常处理 + 统一响应格式

#### 2. 前端基础架构
- Vue 3 + Vite + TypeScript + Element Plus
- 路由配置 (登录守卫)
- Pinia 用户状态管理 (token + 用户信息)
- Axios 封装 + 请求拦截器 (自动注入 Bearer token)
- Vite proxy 代理 `/api` → `localhost:8080`

#### 3. 前端页面 — 桌面端
- 登录页 (深色渐变 + 毛玻璃卡片 + 标签切换)
- 主布局 (侧边栏 + 顶栏 + 用户菜单)
- 账单页 (表格 + 分页 + 月份/分类筛选 + 统计行 + 新增/编辑弹窗)
- 分类页 (双栏布局 + 增删改弹窗)
- 统计页 (月度统计卡片 + 分类进度条)

#### 4. 前端页面 — 移动端 (本次优化)
- 统计行垂直堆叠 (`xs:24`) 修复三列过窄
- 移动端卡片样式优化 (14px 圆角, 16px padding, 提升阴影)
- 底部 Tab 栏高度加大 (64px) + 活动指示线
- Dialog 底部弹出样式 (slide-up 动画, 全宽, 圆角顶边)
- 表单元素高度 48px, 按钮全宽, 圆角 12px
- Select 下拉选项加大 (44px)
- 分类页触控区域加大 (44px 按钮, 16px padding)
- 间距全面加大 (页面 gap 18-20px, padding 16px)
- 消息弹窗/确认框圆角适配

#### 5. 已修复的问题
- 登录 token 类型匹配修复 (后端直接返回字符串 token)
- 请求拦截器过滤 `"undefined"` / `"null"` 字符串
- Vite host 配置 `0.0.0.0` 支持局域网手机访问

### 待验证

- [ ] 移动端实际设备 (手机) 上的 touch 交互体验
- [ ] Dialog 底部弹出在不同机型上的表现
- [ ] 统计页数据为空时的容错显示
- [ ] 长时间使用后的 token 过期处理
- [ ] 后端 `application.yml` 密码明文 (123456) 需要生产环境替换

### 后续建议

1. **APP 封装** — 使用 PWA (Service Worker + manifest.json) 实现"添加到主屏幕"，或用 Capacitor 封装为原生壳
2. **生产安全** — 后端密码加密 (jasypt / 环境变量), HTTPS 部署
3. **功能扩展** — 月度预算、账单标签、数据导出 (Excel/PDF)、多账户
4. **性能优化** — 路由懒加载、Element Plus 按需引入、图片懒加载
5. **测试** — 补全后端单元测试 + 前端 E2E 测试

## 启动方式

### 启动后端
```bash
cd backend/test_backend
mvn spring-boot:run
```

### 启动前端
```bash
cd front_end
npm install   # 首次
npm run dev   # http://localhost:5173
```

### 移动端访问
确保手机与电脑在同一 WiFi，电脑防火墙允许 5173 端口。
访问 `http://<电脑IP>:5173`

## 数据库恢复
```bash
mysql -u root -p123456 < database_backup_20260517.sql
```
