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
  const configuredHost = process.env.VUE_APP_SERVER_HOST

  // 127.0.0.1、localhost、0.0.0.0 只对容器或本机有意义；
  // 浏览器从外部访问时如果继续使用它们，会请求到用户自己的电脑，而不是服务器。
  if (
    configuredHost &&
    configuredHost !== '127.0.0.1' &&
    configuredHost !== 'localhost' &&
    configuredHost !== '0.0.0.0'
  ) {
    return configuredHost
  }

  return window.location.hostname
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

  // 生产环境 API 地址是 /prod-api，但媒体文件由 Nginx 在 /media/ 直接托管，
  // 不能继续用 `${baseApi}/media/`，否则会变成 /prod-api/media/ 并请求到 Django。
  const baseApi = getBaseApiUrl()
  if (baseApi && baseApi.startsWith('/')) {
    return `${window.location.origin}/media/`
  }

  // 开发环境或显式配置了完整 API 地址时，媒体仍挂在 API 服务的 /media/ 下。
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
