# Frontend 目录说明

## 核心作用
前端交互层，负责页面展示、用户操作、接口调用、实时流式问答展示和报告可视化。

## 包含模块
- `src/`：前端源码。
- `public/`：静态资源。
- `scripts/`：构建辅助脚本。
- `package.json`：Node 依赖与运行脚本。
- `vite.config.js`：构建与代理配置。

## 核心文件功能
- `src/main.js`：前端应用入口。
- `src/router/index.js`：页面路由管理。
- `src/views/interview/Chat.vue`：面试主交互页面。

## 调用关系
页面通过 `axios` 调用后端 `/api/*` 接口，响应数据直接驱动组件状态和图表/报告渲染。

