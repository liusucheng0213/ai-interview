import axios from 'axios'
import router from '@/router'
import { notifyError } from '@/utils/appNotify'
// 业务错误（4xx/5xx）由各请求的 catch 统一用 appNotify 展示，避免与拦截器重复弹窗

// 与后端 DEEPSEEK_TIMEOUT 默认 120 秒对齐，覆盖面试流式与报告生成
const REQUEST_TIMEOUT_MS = 120000

const service = axios.create({
  baseURL: '/api',  // 🌟 使用相对路径，配合 vite 代理
  timeout: REQUEST_TIMEOUT_MS,
  // 跨域请求携带 cookie（如果后端需要）
  withCredentials: true
})

// 请求拦截器：自动携带Token
service.interceptors.request.use(
  (config) => {
    // 从localStorage获取Token
    const token = localStorage.getItem('token')
    if (token) {
      // 🌟 后端约定的Token头（可根据后端要求修改，如直接用token: xxx）
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    console.error('请求出错：', error)
    return Promise.reject(error)
  }
)

// 响应拦截器：统一处理 Token 失效/401
service.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    const data = error.response?.data
    if (data && typeof data === 'object' && !(data instanceof Blob)) {
      const serverMsg = data.message || data.detail
      if (typeof serverMsg === 'string' && serverMsg.trim()) {
        error.message = serverMsg
      }
    }
    // 🌟 Token 过期/无效/未携带，统一跳登录
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token') // 清除无效 Token
      localStorage.removeItem('ai-interview-user') // 清除用户名
      notifyError('登录已过期，请重新登录', '登录失效')
      router.push('/login') // 跳登录页
    }
    return Promise.reject(error)
  }
)

// 🌟 添加从 Token 获取用户名的辅助函数
export const getUsernameFromToken = () => {
  return localStorage.getItem('ai-interview-user')
}

export const getToken = () => {
  return localStorage.getItem('token')
}

export default service