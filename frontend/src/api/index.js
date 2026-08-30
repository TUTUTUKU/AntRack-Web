import request from './request'

// 鉴权
export const login = (data) => request.post('/api/auth/login', data)
export const getUserInfo = () => request.get('/api/auth/info')
export const changePassword = (data) => request.post('/api/auth/change-password', data)

// 仪表盘
export const getDashboardStats = () => request.get('/api/dashboard/stats')

// 分类
export const getCategoryTree = () => request.get('/api/category/tree')
export const getCategoryList = () => request.get('/api/category/list')
export const saveCategory = (data) => request.post('/api/category/save', data)
export const updateCategory = (id, data) => request.put(`/api/category/update/${id}`, data)
export const deleteCategory = (id) => request.delete(`/api/category/delete/${id}`)

// 物料
export const getMaterialList = (params) => request.get('/api/material/list', { params })
export const getAllMaterials = () => request.get('/api/material/all')
export const getMaterialDetail = (id) => request.get(`/api/material/detail/${id}`)
export const nextMaterialCode = () => request.get('/api/material/next-code')
export const saveMaterial = (data) => request.post('/api/material/save', data)
export const updateMaterial = (id, data) => request.put(`/api/material/update/${id}`, data)
export const deleteMaterial = (id) => request.delete(`/api/material/delete/${id}`)
export const deleteMaterialBatch = (ids) => request.post('/api/material/delete-batch', { ids })
export const uploadImage = (formData) => request.post('/api/material/upload-image', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
// 入库
export const stockIn = (data) => request.post('/api/material/stock-in', data)
// 临时出库
export const stockOutTemp = (data) => request.post('/api/material/stock-out-temp', data)

// 项目
export const getProjectList = (params) => request.get('/api/project/list', { params })
export const getProjectDetail = (id) => request.get(`/api/project/detail/${id}`)
export const saveProject = (data) => request.post('/api/project/save', data)
export const updateProject = (id, data) => request.put(`/api/project/update/${id}`, data)
export const switchProjectStatus = (id, data) => request.put(`/api/project/status/${id}`, data)
export const deleteProject = (id) => request.delete(`/api/project/delete/${id}`)
// BOM
export const saveBom = (data) => request.post('/api/project/bom/save', data)
export const updateBomPlan = (bomId, data) => request.put(`/api/project/bom/update-plan/${bomId}`, data)
export const deleteBom = (bomId) => request.delete(`/api/project/bom/delete/${bomId}`)
// 锁定/解锁
export const bomLock = (data) => request.post('/api/project/bom-lock', data)
// 制作阶段消耗
export const bomConsume = (bomId, data) => request.post(`/api/project/bom-consume/${bomId}`, data)
// 完工结算
export const finishSettle = (projectId) => request.post(`/api/project/finish-settle`, null, { params: { project_id: projectId } })

// 库存流水
export const getStockLogList = (params) => request.get('/api/stock-log/list', { params })
export const getRecentLogs = (limit) => request.get('/api/stock-log/recent', { params: { limit } })
export const deleteStockLog = (id) => request.delete(`/api/stock-log/delete/${id}`)
export const deleteStockLogBatch = (ids) => request.post('/api/stock-log/delete-batch', { ids })
// V1.2：5 分钟内可撤销
export const undoStockLog = (id) => request.post(`/api/stock-log/undo/${id}`)

// 导出
export const exportMaterial = () => request.get('/api/export/material', { responseType: 'blob' })
export const exportStockLog = (params) => request.get('/api/export/stock-log', { params, responseType: 'blob' })
export const exportProject = (id) => request.get(`/api/export/project/${id}`, { responseType: 'blob' })
export const exportProjectList = () => request.get('/api/export/project-list', { responseType: 'blob' })

// 数据备份与恢复
export const exportBackup = () => request.get('/api/backup/export', { responseType: 'blob' })
export const restoreBackup = (formData, onUploadProgress) =>
  request.post('/api/backup/restore', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress,
    timeout: 0
  })
// V1.2：快照管理
export const listBackupSnapshots = (params) => request.get('/api/backup/list', { params })
export const latestBackupMeta = () => request.get('/api/backup/latest-meta')
export const createBackupSnapshot = (trigger = 'manual', note = '') =>
  request.post('/api/backup/create', null, { params: { trigger, note } })
export const downloadBackupSnapshot = (id) =>
  request.get(`/api/backup/download/${id}`, { responseType: 'blob' })
export const deleteBackupSnapshot = (id) => request.delete(`/api/backup/delete/${id}`)
export const restoreFromSnapshot = (id) => request.post(`/api/backup/restore-from-snapshot/${id}`)

// 自动备份配置
export const getAutoBackupConfig = () => request.get('/api/auto-backup/config')
export const updateAutoBackupConfig = (data) => request.put('/api/auto-backup/config', data)
export const runAutoBackupNow = () => request.post('/api/auto-backup/run-now')

// V1.2 版本与阶段
export const getRevisionInfo = () => request.get('/api/revision/info')

// V1.2 冲突处理
export const listConflicts = (params) => request.get('/api/conflicts/list', { params })
export const resolveConflict = (id, data) => request.post(`/api/conflicts/resolve/${id}`, data)
export const resolveConflictsBatch = (data) => request.post('/api/conflicts/resolve-batch', data)

// V1.2 操作日志
export const listOperationLogs = (params) => request.get('/api/operation-logs/list', { params })

// V1.2 用户配置
export const getAllUserConfigs = () => request.get('/api/user-configs/all')
export const listUserConfigs = () => request.get('/api/user-configs/list')
export const setUserConfig = (keyOrMap, maybeValue) => {
  if (typeof keyOrMap === 'string') {
    return request.post('/api/user-configs/set', { key: keyOrMap, value: String(maybeValue ?? '') })
  }
  return request.post('/api/user-configs/set', keyOrMap || {})
}
export const batchSetUserConfigs = (items) => request.post('/api/user-configs/batch', { items })

// 健康检查（前端断网判断）
export const healthCheck = () => request.get('/api/health', { timeout: 5000 })
