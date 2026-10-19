<template>
  <div id="app">
    <router-view></router-view>
  </div>
</template>

<script setup>
// App.vue 现在只是根组件
</script>

<style>
/* ==================== 全局 CSS 变量 ==================== */
:root {
  --color-primary: #1e40af;
  --color-primary-dark: #1e3a8a;
  --color-primary-light: #3b82f6;
  --color-primary-pale: #dbeafe;
  --color-success: #059669;
  --color-warning: #d97706;
  --color-danger: #dc2626;
  --color-text-primary: #000000ff;
  --color-text-secondary: #000000ff;
  --color-text-muted: #000000ff;
  --el-text-color-primary: #000000;
  --el-text-color-regular: #000000;
  --el-text-color-secondary: #000000;
  --el-text-color-placeholder: #334155;
  --color-border: #cbd5e1;
  --color-bg: #f1f5f9;
  --color-surface: #ffffff;
  --sidebar-start: #1e3a5f;
  --sidebar-mid: #1e40af;
  --sidebar-end: #1e4976;
  --sidebar-text: rgba(255,255,255,0.95);
  --sidebar-muted: rgba(255,255,255,0.6);
  --sidebar-hover: rgba(255,255,255,0.18);
  --sidebar-active: rgba(255,255,255,0.25);
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 20px;
  --radius-xl: 24px;
  --shadow-sm: 0 1px 3px rgba(15, 23, 42, 0.08);
  --shadow-md: 0 4px 16px rgba(15, 23, 42, 0.12);
  --shadow-lg: 0 12px 32px rgba(15, 23, 42, 0.16);
  --shadow-xl: 0 20px 48px rgba(15, 23, 42, 0.2);
  --transition: 0.25s ease;
  --page-max-width: 1280px;
  --section-gap: 24px;
  --gradient-primary: linear-gradient(135deg, var(--color-primary-light), var(--color-primary) 55%, var(--color-primary-dark));
  --gradient-success: linear-gradient(135deg, #34d399, #10b981 55%, #059669);
  --gradient-warning: linear-gradient(135deg, #fbbf24, #f59e0b 55%, #d97706);
  --gradient-bg: linear-gradient(135deg, #f8fafc 0%, #eef2ff 50%, #dbeafe 100%);
  --gradient-card: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
  --gradient-dialog: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
}

/* 内容区最大宽度与栅格（子页面可选用） */
.page-container {
  max-width: var(--page-max-width);
  margin: 0 auto;
  width: 100%;
}

.surface-card {
  background: var(--gradient-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-md);
  transition: box-shadow var(--transition), border-color var(--transition), transform var(--transition);
}

.surface-card:hover {
  box-shadow: var(--shadow-lg);
  border-color: rgba(37, 99, 235, 0.25);
  transform: translateY(-2px);
}

*, *::before, *::after { box-sizing: border-box; }

body {
  margin: 0;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC',
    'Microsoft YaHei', 'Helvetica Neue', sans-serif;
  background: var(--gradient-bg);
  background-attachment: fixed;
  color: var(--color-text-primary);
  -webkit-font-smoothing: antialiased;
}

@media (prefers-color-scheme: dark) {
  :root {
    --color-text-primary: #000000;
    --color-text-secondary: #000000;
    --color-text-muted: #000000;
    --el-text-color-primary: #000000;
    --el-text-color-regular: #000000;
    --el-text-color-secondary: #000000;
    --el-text-color-placeholder: #334155;
    --color-border: #334155;
    --color-bg: #0f172a;
    --color-surface: rgba(30, 41, 59, 0.92);
    --color-primary-pale: rgba(37, 99, 235, 0.15);
  }
  body {
    background: linear-gradient(165deg, #0f172a 0%, #1e293b 45%, #172554 100%);
    color: var(--color-text-primary);
  }
}

#app { min-height: 100vh; }

/* 全局滚动条 */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #c7d2e0; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

/* Element Plus 全局微调 */
.el-button--primary {
  background: var(--gradient-primary);
  border-color: transparent;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.el-button--primary:hover {
  background: var(--gradient-primary);
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(37, 99, 235, 0.28);
}

/* 通用悬浮提示弹窗 */
.el-message-box {
  width: min(480px, calc(100vw - 32px));
  border-radius: var(--radius-xl);
  border: 1px solid rgba(37, 99, 235, 0.3);
  box-shadow: var(--shadow-xl);
  background: var(--gradient-dialog);
  overflow: hidden;
  animation: float-in 0.3s ease-out;
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 9999;
}

@keyframes float-in {
  from {
    opacity: 0;
    transform: translate(-50%, -50%) scale(0.95) translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1) translateY(0);
  }
}

/* 弹窗头部 */
.el-message-box__header, .el-dialog__header {
  padding: 20px 24px 12px;
  background: linear-gradient(135deg, var(--color-primary-pale), #ffffff);
  border-bottom: 1px solid var(--color-border);
}

/* 弹窗标题 */
.el-message-box__title, .el-dialog__title {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text-primary);
}

/* 弹窗内容 */
.el-message-box__content, .el-dialog__body {
  padding: 16px 24px 12px;
}

/* 弹窗消息 */
.el-message-box__message {
  font-size: 16px;
  line-height: 1.7;
  color: var(--color-text-secondary);
}

/* 弹窗底部 */
.el-message-box__btns, .el-dialog__footer {
  padding: 16px 24px 20px;
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  border-top: 1px solid var(--color-border);
  background: #f8fafc;
}

/* 行内二次确认气泡 */
.el-popover.kb-inline-confirm-popover {
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border);
  background: var(--gradient-card);
  animation: float-in 0.2s ease-out;
}

/* 卡片样式优化 */
.el-card {
  border-radius: var(--radius-lg);
  border-color: var(--color-border);
  box-shadow: var(--shadow-md);
  transition: box-shadow var(--transition), transform var(--transition);
  background: var(--gradient-card);
}

.el-card:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-2px);
}

/* 全局 Message：悬浮卡片感 */
.el-message {
  border-radius: var(--radius-lg);
  padding: 16px 20px;
  min-width: 300px;
  box-shadow: var(--shadow-lg);
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: var(--gradient-card);
  animation: slide-in 0.3s ease-out;
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
}

@keyframes slide-in {
  from {
    opacity: 0;
    transform: translateX(100%) translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0) translateY(0);
  }
}

.el-message--success { 
  border-color: rgba(5, 150, 105, 0.4);
  background: linear-gradient(135deg, #f0fdf4, #ffffff);
}

.el-message--warning { 
  border-color: rgba(245, 158, 11, 0.4);
  background: linear-gradient(135deg, #fffbeb, #ffffff);
}

.el-message--error { 
  border-color: rgba(239, 68, 68, 0.4);
  background: linear-gradient(135deg, #fef2f2, #ffffff);
}

/* 通知样式优化 */
.el-notification {
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border);
  background: var(--gradient-card);
  animation: slide-in 0.3s ease-out;
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
}

.el-notification__title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.el-notification__content {
  font-size: 14px;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

/* 按钮样式优化 */
.el-button {
  border-radius: var(--radius-md);
  transition: all 0.3s ease;
}

.el-button--primary {
  background: var(--gradient-primary);
  border-color: transparent;
  color: #fff;
}

.el-button--primary:hover {
  background: var(--gradient-primary);
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(37, 99, 235, 0.35);
}

.el-button--success {
  background: var(--gradient-success);
  border-color: transparent;
  color: #fff;
}

.el-button--success:hover {
  background: var(--gradient-success);
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(16, 185, 129, 0.35);
}

.el-table {
  --el-table-border-color: var(--color-border);
  --el-table-header-bg-color: var(--color-primary-pale);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}
</style>
