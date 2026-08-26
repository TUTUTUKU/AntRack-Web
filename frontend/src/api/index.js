import request from './request'

// ========== 鉴权 ==========
export const login = (data) => request.post('/api/auth/login', data)
export const getUserInfo = () => request.get('/api/auth/info')
export const changePassword = (data) => request.post('/api/auth/change-password', data)

// ========== 仪表盘 ==========
export const getDashboardStats = () => request.get('/api/dashboard/stats')

// ========== 分类 ==========
export const getCategoryTree = () => request.get('/api/category/tree')
export const getCategoryList = () => request.get('/api/category/list')
export const saveCategory = (data) => request.post('/api/category/save', data)
export const updateCategory = (id, data) => request.put(`/api/category/update/${id}`, data)
export const deleteCategory = (id) => request.delete(`/api/category/delete/${id}`)

// ========== 物料 ==========
export const getMaterialList = (params) => request.get('/api/material/list', { params })
export const getAllMaterials = () => request.get('/api/material/all')
export const getMaterialDetail = (id) => request.get(`/api/material/detail/${id}`)
export const nextMaterialCode = () => request.get('/api/material/next-code')
export const saveMaterial = (data) => request.post('/api/material/save', data)
export const updateMaterial = (id, data) => request.put(`/api/material/update/${id}`, data)
export const deleteMaterial = (id) => request.delete(`/api/material/delete/${id}`)
export const deleteMaterialBatch = (ids) => request.post('/api/material/delete-batch', { ids })
export const uploadImage = (formData) => request.post('/api/material/upload-image', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
// 接口1：入库
export const stockIn = (data) => request.post('/api/material/stock-in', data)
// 接口2：临时出库
export const stockOutTemp = (data) => request.post('/api/material/stock-out-temp', data)

// ========== 项目 ==========
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
// 接口3：锁定/解锁
export const bomLock = (data) => request.post('/api/project/bom-lock', data)
// 制作阶段消耗
export const bomConsume = (bomId, data) => request.post(`/api/project/bom-consume/${bomId}`, data)
// 接口4：完工结算
export const finishSettle = (projectId) => request.post('/api/project/finish-settle', null, { params: { project_id: projectId } })

// ========== 库存流水 ==========
export const getStockLogList = (params) => request.get('/api/stock-log/list', { params })
export const getRecentLogs = (limit) => request.get('/api/stock-log/recent', { params: { limit } })
export const deleteStockLog = (id) => request.delete(`/api/stock-log/delete/${id}`)
export const deleteStockLogBatch = (ids) => request.post('/api/stock-log/delete-batch', { ids })

// ========== 导出 ==========
export const exportMaterial = () => request.get('/api/export/material', { responseType: 'blob' })
export const exportStockLog = (params) => request.get('/api/export/stock-log', { params, responseType: 'blob' })
export const exportProject = (id) => request.get(`/api/export/project/${id}`, { responseType: 'blob' })
export const exportProjectList = () => request.get('/api/export/project-list', { responseType: 'blob' })

// ========== 数据备份与恢复 ==========
// 一键下载备份（.antrack = zip，仅含业务表，不含用户）
export const exportBackup = () => request.get('/api/backup/export', { responseType: 'blob' })
// 上传 .antrack 备份并恢复业务数据（管理员专用）
export const restoreBackup = (formData, onUploadProgress) =>
  request.post('/api/backup/restore', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress,
    timeout: 0  // 大文件上传不超时
  })
