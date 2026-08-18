# ExportButton 通用导出组件

一个通用的数据导出组件，支持Excel和CSV格式导出，可以在任何列表页面中使用。

## 功能特性

- 🚀 支持Excel和CSV两种格式导出
- 📊 自动处理搜索条件和分页参数
- 🎨 可自定义按钮样式和文本
- 📱 响应式设计，支持移动端
- 🔧 灵活的配置选项
- 📝 完整的事件回调

## 基本用法

```vue
<template>
  <export-button
    :api-function="getDataList"
    :search-params="searchParams"
    :export-options="exportOptions"
    @export-success="onExportSuccess"
    @export-error="onExportError"
  />
</template>

<script>
import ExportButton from '@/components/ExportButton'
import { getDataList } from '@/api/data'

export default {
  components: {
    ExportButton
  },
  data() {
    return {
      searchParams: {
        name: '',
        status: ''
      },
      exportOptions: {
        filename: '数据列表',
        headers: {
          id: 'ID',
          name: '名称',
          status: '状态',
          created_at: '创建时间'
        },
        sheetName: '数据表'
      }
    }
  },
  methods: {
    onExportSuccess(data) {
      console.log('导出成功:', data)
    },
    onExportError(error) {
      console.error('导出失败:', error)
    }
  }
}
</script>
```

## Props 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| apiFunction | Function | 是 | - | API调用函数 |
| searchParams | Object | 否 | {} | 搜索参数对象 |
| exportOptions | Object | 是 | - | 导出配置选项 |
| buttonType | String | 否 | 'success' | 按钮类型 |
| buttonSize | String | 否 | 'medium' | 按钮大小 |
| buttonText | String | 否 | '导出' | 按钮文本 |
| marginLeft | String | 否 | '10px' | 左边距 |
| disabled | Boolean | 否 | false | 是否禁用 |

## exportOptions 配置

```javascript
{
  filename: '文件名称',        // 导出文件名（不含扩展名）
  headers: {                  // 列头映射
    field_key: '显示名称',
    id: 'ID',
    name: '名称'
  },
  sheetName: '工作表名称'      // Excel工作表名称（可选）
}
```

## 事件

| 事件名 | 参数 | 说明 |
|--------|------|------|
| export-start | format | 开始导出时触发 |
| export-success | { format, result } | 导出成功时触发 |
| export-error | { format, error } | 导出失败时触发 |
| export-end | format | 导出结束时触发 |

## API函数要求

API函数应该接受一个参数对象，并返回包含数据的响应：

```javascript
// API函数示例
export function getDataList(params) {
  return request({
    url: '/api/data',
    method: 'get',
    params
  })
}

// 响应格式（支持多种格式）
{
  results: [...],     // 数据数组
  total: 100         // 总数（可选）
}
// 或
{
  data: [...]        // 数据数组
}
// 或直接返回数组
[...]
```

## 高级用法

### 自定义按钮样式

```vue
<export-button
  :api-function="getDataList"
  :search-params="searchParams"
  :export-options="exportOptions"
  button-type="primary"
  button-size="small"
  button-text="下载数据"
  margin-left="20px"
/>
```

### 动态搜索参数

```vue
<template>
  <div>
    <!-- 搜索表单 -->
    <el-form :model="searchForm">
      <el-form-item label="名称">
        <el-input v-model="searchForm.name" />
      </el-form-item>
    </el-form>
    
    <!-- 导出按钮 -->
    <export-button
      :api-function="getDataList"
      :search-params="getSearchParams()"
      :export-options="exportOptions"
    />
  </div>
</template>

<script>
export default {
  data() {
    return {
      searchForm: {
        name: '',
        status: ''
      }
    }
  },
  methods: {
    getSearchParams() {
      // 过滤空值
      const params = {}
      Object.keys(this.searchForm).forEach(key => {
        if (this.searchForm[key] !== '' && this.searchForm[key] !== null) {
          params[key] = this.searchForm[key]
        }
      })
      return params
    }
  }
}
</script>
```

### 处理特殊字段

```javascript
// 在exportOptions中定义headers时，可以处理特殊字段
exportOptions: {
  filename: '用户列表',
  headers: {
    id: 'ID',
    username: '用户名',
    email: '邮箱',
    status: '状态',        // 会自动转换 true/false 为 是/否
    created_at: '创建时间', // 会自动格式化日期
    profile: '个人信息'     // 对象会转换为JSON字符串
  },
  sheetName: '用户数据'
}
```

## 注意事项

1. 确保已安装 `xlsx` 依赖：`npm install xlsx`
2. API函数应该支持分页参数（page, page_size）
3. 导出时会自动设置 `page_size: 10000` 来获取所有数据
4. 文件名会自动添加时间戳避免重复
5. CSV文件会自动添加BOM以支持中文显示

## 完整示例

参考 `src/views/department/index.vue` 中的使用方式。