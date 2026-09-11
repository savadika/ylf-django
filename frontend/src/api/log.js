import request from '@/utils/request'

/**
 * 获取日志管理列表
 * @param {Object} params - 查询参数
 * @param {number} params.page - 页码
 * @param {number} params.page_size - 每页数量
 * @param {number} [params.id] - ID
 * @param {string|number} [params.user] - 操作用户
 * @param {string} [params.ip] - 访问IP
 * @param {string} [params.method] - 请求方式
 * @param {string} [params.path] - 请求路径
 * @param {string} [params.params] - 请求参数
 * @param {number} [params.status] - 响应状态码
 * @param {number} [params.cost_time] - 耗时(ms)
 * @param {string} [params.create_time] - 创建时间
 * @param {string} [params.log_type] - 日志类型
 * @param {string} [params.error_msg] - 错误信息
 * @param {string} [params.traceback] - 堆栈详情
 * @returns {Promise} 返回日志管理列表数据
 */
export function getLogList(params) {
  return request({
    url: '/log',
    method: 'get',
    params
  })
}

/**
 * 获取日志管理详情
 * @param {number|string} id - 日志管理ID
 * @returns {Promise} 返回日志管理详情数据
 */
export function getLogDetail(id) {
  return request({
    url: `/log/${id}`,
    method: 'get'
  })
}

// 默认导出所有API函数
export default {
  getLogList,
  getLogDetail
}
