import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

const service = axios.create({
  baseURL: '/',
  timeout: 30000
})

// 请求拦截器
service.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = 'Bearer ' + token
    }
    // 前端断网快速判断（无任何缓存/离线队列——Web端仅实时联网）
    if (typeof navigator !== 'undefined' && navigator.onLine === false) {
      // 直接中止：避免长超时
      const err = new Error('NETWORK_OFFLINE')
      err.__offline = true
      return Promise.reject(err)
    }
    return config
  },
  error => Promise.reject(error)
)

// 响应拦截：统一处理 code、登录过期、断网
service.interceptors.response.use(
  response => {
    const res = response.data
    // 文件流（导出 Excel / 备份）
    if (response.config.responseType === 'blob' || res instanceof Blob) {
      return response
    }
    if (res.code === 0) {
      return res
    }
    // 业务错误
    ElMessage.error(res.msg || '操作失败')
    return Promise.reject(new Error(res.msg || '操作失败'))
  },
  error => {
    // V1.2：Web 端只做实时联网，断网直接提示；不做任何缓存与离线队列
    const isOffline =
      error?.__offline === true ||
      error?.code === 'ERR_NETWORK' ||
      (typeof error?.message === 'string' && (
        error.message.includes('NETWORK_OFFLINE') ||
        error.message.includes('Network Error') ||
        /timeout\s*of\s*\d+\s*ms\s*exceeded/i.test(error.message)
      )) ||
      !error?.response
    if (isOffline) {
      ElMessage({
        type: 'error',
        duration: 4000,
        showClose: true,
        message: '当前网络异常，Web 端仅支持实时联网使用，请检查网络连接后再操作。',
      })
      return Promise.reject(error)
    }
    const status = error.response && error.response.status
    if (status === 401) {
      ElMessage.error('登录已过期，请重新登录')
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      router.push('/login')
    } else {
      ElMessage.error(error.response?.data?.detail || error.response?.data?.msg || error.message || '网络错误')
    }
    return Promise.reject(error)
  }
)

export default service
