# 个人记账本 - 前端项目

## 项目简介

基于 Vue 3 + TypeScript + Vite + Element Plus 构建的个人记账本前端应用。

## 技术栈

- Vue 3 (Composition API)
- TypeScript
- Vite
- Element Plus (UI 组件库)
- Vue Router (路由管理)
- Pinia (状态管理)
- Axios (HTTP 客户端)
- Day.js (日期处理)

## 功能模块

### 1. 用户认证
- 用户注册
- 用户登录
- Token 管理

### 2. 分类管理
- 分类列表查询
- 新增分类
- 编辑分类
- 删除分类

### 3. 账单记录
- 分页查询账单
- 按月份/分类筛选
- 新增账单
- 编辑账单
- 删除账单

### 4. 数据统计
- 月度收支汇总
- 分类支出统计
- 分类收入统计

## 项目结构

```
front_end/
├── public/
├── src/
│   ├── api/              # API 接口
│   │   └── index.ts
│   ├── layouts/          # 布局组件
│   │   └── MainLayout.vue
│   ├── router/           # 路由配置
│   │   └── index.ts
│   ├── stores/           # Pinia 状态管理
│   │   └── user.ts
│   ├── types/            # TypeScript 类型定义
│   │   └── index.ts
│   ├── utils/            # 工具函数
│   │   └── request.ts    # Axios 封装
│   ├── views/            # 页面组件
│   │   ├── Login.vue
│   │   ├── Records.vue
│   │   ├── Categories.vue
│   │   └── Statistics.vue
│   ├── App.vue
│   ├── main.ts
│   └── vite-env.d.ts
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

## 快速开始

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

开发服务器将在 `http://localhost:5173` 启动，API 请求会代理到 `http://localhost:8080`。

### 生产构建

```bash
npm run build
```

### 预览构建结果

```bash
npm run preview
```

## 后端接口对接

### API 基础路径

- 开发环境：通过 Vite 代理转发到 `http://localhost:8080`
- 生产环境：根据实际部署配置

### 接口文档

详细接口文档请参考 `接口文档.md` 文件。

### 主要接口

1. 用户模块：`/api/user/*`
2. 分类模块：`/api/categories/*`
3. 账单记录模块：`/api/records/*`
4. 统计模块：`/api/statistics/*`

### 请求/响应格式

所有请求统一使用 JSON 格式，响应格式为：

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

- `code`：业务状态码，200 表示成功
- `message`：响应消息
- `data`：响应数据

## 开发说明

### 代理配置

在 `vite.config.ts` 中已配置 API 代理：

```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8080',
      changeOrigin: true,
      secure: false
    }
  }
}
```

### 环境变量

如需配置其他环境变量，可创建 `.env`、`.env.development`、`.env.production` 文件。

## License

MIT
