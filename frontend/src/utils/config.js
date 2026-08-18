/**
 * 统一配置工具
 * 所有域名、端口、API 地址的配置都从这里获取
 * 配置来源优先级：
 * 1. 环境变量 (通过 docker-compose 注入)
 * 2. .env 文件中的默认值
 * 3. 运行时动态获取 (如 window.location.hostname)
 */

// 获取服务器协议
export const getServerProtocol = () => {
  return process.env.VUE_APP_SERVER_PROTOCOL || 'http'
}

// 获取服务器主机地址
export const getServerHost = () => {
  return process.env.VUE_APP_SERVER_HOST || window.location.hostname
}

// 获取后端端口
export const getBackendPort = () => {
  return process.env.VUE_APP_BACKEND_PORT || '8002'
}

// 获取后端 API 基础地址
export const getBaseApiUrl = () => {
  // 如果有完整的 VUE_APP_BASE_API 配置，直接使用
  if (process.env.VUE_APP_BASE_API && !process.env.VUE_APP_BASE_API.includes('undefined')) {
    return process.env.VUE_APP_BASE_API
  }
  
  // 否则根据环境变量动态生成
  const protocol = getServerProtocol()
  const host = getServerHost()
  const port = getBackendPort()
  
  return `${protocol}://${host}:${port}`
}

// 获取图片资源基础地址
export const getBaseImgUrl = () => {
  // 如果有完整的 VUE_APP_BASE_IMG_URL 配置，直接使用
  if (process.env.VUE_APP_BASE_IMG_URL && !process.env.VUE_APP_BASE_IMG_URL.includes('undefined')) {
    return process.env.VUE_APP_BASE_IMG_URL
  }
  
  // 否则根据 API 地址生成
  const baseApi = getBaseApiUrl()
  return `${baseApi}/media/`
}

// 处理图片 URL，将相对路径转换为完整 URL
export const resolveImageUrl = (url) => {
  if (!url) return ''
  
  // 如果已经是完整 URL，直接返回
  if (url.startsWith('http') || url.startsWith('https') || url.startsWith('blob:')) {
    return url
  }
  
  const baseUrl = getBaseImgUrl()
  const cleanPath = url.startsWith('/') ? url.slice(1) : url
  return `${baseUrl}${cleanPath}`
}

// 导出配置对象，方便调试
export const getConfig = () => ({
  serverProtocol: getServerProtocol(),
  serverHost: getServerHost(),
  backendPort: getBackendPort(),
  baseApiUrl: getBaseApiUrl(),
  baseImgUrl: getBaseImgUrl()
})

export default {
  getServerProtocol,
  getServerHost,
  getBackendPort,
  getBaseApiUrl,
  getBaseImgUrl,
  resolveImageUrl,
  getConfig
}
