import axios from 'axios'
import { MessageBox, Message } from 'element-ui'
import store from '@/store'
import { getToken } from '@/utils/auth'
import { getBaseApiUrl } from '@/utils/config'

let last403MessageAt = 0

// create an axios instance
const service = axios.create({
  baseURL: getBaseApiUrl(), // url = base url + request url
  // withCredentials: true, // send cookies when cross-domain requests
  timeout: 300000 // request timeout: 5 minutes (for slow API calls like LOF data)
})

// request interceptor
service.interceptors.request.use(

  config => {
    // do something before request is sent

    if (store.getters.token) {
      const raw = getToken()
      if (raw) {
        // 按要求：不附加任何前缀（不加 Bearer/Token 等），直接使用原始 token
        config.headers['Authorization'] = raw
      }
    }
    return config
  },
  error => {
    // do something with request error
    console.log(error) // for debug
    return Promise.reject(error)
  }
)

// response interceptor
service.interceptors.response.use(
  /**
   * If you want to get http information such as headers or status
   * Please return  response => response
  */

  /**
   * Determine the request status by custom code
   * Here is just an example
   * You can also judge the status by HTTP Status Code
   */
  response => {
    const res = response.data

    // If response payload contains a custom "code" field, keep legacy behavior
    if (res && typeof res === 'object' && Object.prototype.hasOwnProperty.call(res, 'code') && typeof res.code === 'number') {
      if (res.code !== 200) {
        Message({
          message: res.message || 'Error',
          type: 'error',
          duration: 5 * 1000
        })

        if (res.code === 50008 || res.code === 50012 || res.code === 50014) {
          MessageBox.confirm('You have been logged out, you can cancel to stay on this page, or log in again', 'Confirm logout', {
            confirmButtonText: 'Re-Login',
            cancelButtonText: 'Cancel',
            type: 'warning'
          }).then(() => {
            store.dispatch('user/resetToken').then(() => {
              location.reload()
            })
          })
        } else if (res.code === 401) {
          store.dispatch('user/resetToken').then(() => {
            location.reload()
          })
        }
        return Promise.reject(new Error(res.message || 'Error'))
      }
      return res
    }

    // Otherwise, treat it as a standard REST response (e.g., DRF), return data directly
    return res
  },
  error => {
    const status = error.response && error.response.status
    const serverMessage = error.response && error.response.data && error.response.data.message
    const isLoginRequest = error.config && error.config.url && error.config.url.includes('/gen_token')

    if (status === 403) {
      // 无权限：友好提示并去重，避免一个页面多个请求弹一堆错误
      const now = Date.now()
      if (now - last403MessageAt > 3000) {
        last403MessageAt = now
        Message({ message: '无权限访问该资源', type: 'warning', duration: 3000 })
      }
    } else {
      Message({ message: serverMessage || error.message, type: 'error', duration: 5000 })
    }

    if (status === 401 && !isLoginRequest) {
      store.dispatch('user/resetToken').then(() => {
        location.reload()
      })
    }
    return Promise.reject(error)
  }
)

export default service
