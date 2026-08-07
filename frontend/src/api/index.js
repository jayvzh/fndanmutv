import axios from 'axios'

const TOKEN_KEY = 'danmutv_token'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res.data,
  (error) => {
    const status = error?.response?.status
    if (status === 401 || status === 403) {
      localStorage.removeItem(TOKEN_KEY)
      window.dispatchEvent(new CustomEvent('auth:unauthorized'))
    }
    return Promise.reject(error)
  }
)

// axios config 中可能出现的字段；用于区分“裸 params 对象”和“axios config 对象”
const AXIOS_CONFIG_KEYS = new Set([
  'params', 'headers', 'timeout', 'responseType', 'signal', 'cancelToken',
  'withCredentials', 'auth', 'baseURL', 'data', 'transformRequest',
  'transformResponse', 'paramsSerializer', 'onUploadProgress',
  'onDownloadProgress', 'validateStatus', 'maxContentLength', 'maxBodyLength',
])

// 兼容两种调用：
//   api.get(url, { key: value })          -> query 参数
//   api.get(url, { params: {...} })      -> axios 原生 config
function toAxiosConfig(arg) {
  if (arg === undefined || arg === null) return undefined
  if (typeof arg !== 'object') return { params: arg }
  const hasConfigKey = Object.keys(arg).some((k) => AXIOS_CONFIG_KEYS.has(k))
  return hasConfigKey ? arg : { params: arg }
}

export default {
  get: (url, params) => api.get(url, toAxiosConfig(params)),
  post: (url, data) => api.post(url, data),
}

export { api as axiosInstance }
