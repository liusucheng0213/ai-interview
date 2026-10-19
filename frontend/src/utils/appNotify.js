import { ElMessage } from 'element-plus'

const messageBase = {
  center: true,
  duration: 2600,
}

export function notifySuccess(message, title = '操作成功') {
  ElMessage({
    ...messageBase,
    type: 'success',
    message: title ? `${title}：${message}` : message,
  })
}

export function notifyError(message, title = '操作失败') {
  ElMessage({
    ...messageBase,
    type: 'error',
    message: title ? `${title}：${message}` : message,
  })
}

export function notifyWarning(message, title = '提示') {
  ElMessage({
    ...messageBase,
    type: 'warning',
    message: title ? `${title}：${message}` : message,
  })
}

export function notifyInfo(message, title = '说明') {
  ElMessage({
    ...messageBase,
    type: 'info',
    message: title ? `${title}：${message}` : message,
  })
}
