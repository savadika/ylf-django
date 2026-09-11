import router, { resetRouter, notFoundRoute } from './router'
import store from './store'
import { Message } from 'element-ui'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'
import { getToken } from '@/utils/auth'
import getPageTitle from '@/utils/get-page-title'

NProgress.configure({ showSpinner: false })

const whiteList = ['/login']

// 找到第一个可访问的路由路径：根路径 / 登录后重定向到这里，
// 这样没有“首页”权限的角色会落到自己的第一个菜单，而不是 404。
function getFirstAccessiblePath(routes) {
  const visit = (list, base) => {
    for (const route of list || []) {
      if (!route || route.hidden) continue
      const p = route.path || ''
      let full = base
      if (p) {
        full = p.startsWith('/') ? p : `${base}/${p}`.replace(/\/+/g, '/')
      }
      const children = (route.children || []).filter(c => c && !c.hidden)
      if (children.length) {
        const nested = visit(children, full)
        if (nested) return nested
      } else if (route.component || p) {
        return full
      }
    }
    return null
  }
  return visit(routes, '') || '/404'
}

router.beforeEach(async(to, from, next) => {
  NProgress.start()
  document.title = getPageTitle(to.meta.title)

  const hasToken = getToken()
  if (hasToken) {
    if (to.path === '/login') {
      next({ path: '/' })
      NProgress.done()
    } else {
      try {
        // 如果还没有用户信息，先拉取
        if (!store.getters.name) {
          await store.dispatch('user/getInfo')
        }
        // 如果动态路由尚未注入，则注入
        if (!store.state.permission.generated) {
          const accessRoutes = store.state.permission.addRoutes || []
          resetRouter()
          if (typeof router.addRoutes === 'function') {
            // Vue Router 3.x 旧API：一次性批量注入
            router.addRoutes([...accessRoutes, notFoundRoute])
          } else if (typeof router.addRoute === 'function') {
            // 新API：逐个注入
            accessRoutes.forEach(r => router.addRoute(r))
            router.addRoute(notFoundRoute)
          }
          store.commit('permission/SET_GENERATED', true)
          // 确保新路由生效，避免空白页或404
          return next({ ...to, replace: true })
        }

        // 根路径重定向到第一个有权限的路由
        if (to.path === '/') {
          const firstPath = getFirstAccessiblePath(store.state.permission.addRoutes || [])
          next({ path: firstPath, replace: true })
          NProgress.done()
          return
        }

        next()
      } catch (error) {
        await store.dispatch('user/resetToken')
        Message.error(error || 'Has Error')
        next(`/login?redirect=${to.path}`)
        NProgress.done()
      }
    }
  } else {
    if (whiteList.indexOf(to.path) !== -1) {
      next()
    } else {
      next(`/login?redirect=${to.path}`)
      NProgress.done()
    }
  }
})

router.afterEach(() => {
  NProgress.done()
})
