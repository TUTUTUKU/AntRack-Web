<template>
  <div>
    <div class="page-card">
      <div class="page-title"><el-icon><Tickets /></el-icon>库存流水记录</div>
      <div class="toolbar">
        <el-select v-model="logType" placeholder="流水类型" clearable style="width:140px" @change="loadData">
          <el-option label="入库" value="in" />
          <el-option label="临时出库" value="out_temp" />
          <el-option label="项目出库" value="out_project" />
          <el-option label="锁定" value="lock" />
          <el-option label="解锁" value="unlock" />
        </el-select>
        <el-select v-model="materialId" filterable clearable placeholder="指定物料" style="width:200px" @change="loadData">
          <el-option v-for="m in materialOptions" :key="m.id" :label="m.name" :value="m.id" />
        </el-select>
        <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width:260px" @change="loadData" />
        <el-button @click="loadData">查询</el-button>
        <el-button @click="onExport"><el-icon><Download /></el-icon>导出流水</el-button>
        <div class="flex-grow"></div>
        <el-button
          v-if="!manageMode"
          class="tb-btn tb-manage"
          @click="openAuthDialog"
        ><el-icon><Setting /></el-icon>管理</el-button>
        <template v-else>
          <el-button class="tb-btn tb-done" @click="exitManageMode"><el-icon><Check /></el-icon>完成</el-button>
          <el-button
            class="tb-btn tb-del"
            :disabled="selectedIds.length === 0"
            @click="onBatchDelete"
          ><el-icon><Delete /></el-icon>批量删除（{{ selectedIds.length }}）</el-button>
        </template>
      </div>
      <el-table
        :data="list"
        v-loading="loading"
        border
        stripe
        ref="tableRef"
        @selection-change="onSelectionChange"
      >
        <el-table-column type="selection" width="50" align="center" fixed="right" class-name="sel-col" v-if="manageMode" />
        <el-table-column label="业务时间" width="170">
          <template #default="{ row }">
            <div class="ts-cell">
              <div class="ts-main">{{ row.server_commit_ts || row.create_time }}</div>
              <div v-if="row.local_device_ts" class="ts-sub" title="设备原始本地时间，仅供参考">
                设备时间 {{ row.local_device_ts }}
              </div>
              <div v-if="row.time_correction_flag === 'forced'" class="ts-flag ts-flag-forced">时间校正：强制</div>
              <div v-else-if="row.time_correction_flag === 'ok'" class="ts-flag ts-flag-ok">时间校正：正常</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="来源" width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.source === 'app' ? 'primary' : 'success'" effect="light">
              {{ row.source === 'app' ? 'APP' : 'Web' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <template v-if="row.invalid || row.revoke_status === 'revoked'">
              <el-tag size="small" type="info" effect="plain">已撤销</el-tag>
            </template>
            <template v-else>
              <el-tag size="small" type="success" effect="plain">有效</el-tag>
            </template>
          </template>
        </el-table-column>
        <el-table-column prop="material_name" label="物料名称" min-width="140" show-overflow-tooltip />
        <el-table-column label="流水类型" width="100">
          <template #default="{ row }"><el-tag :type="tagType(row.log_type)" size="small">{{ row.log_type_name }}</el-tag></template>
        </el-table-column>
        <el-table-column label="数量" width="90">
          <template #default="{ row }">{{ fmtNum(row.num) }}</template>
        </el-table-column>
        <el-table-column label="成本" width="100">
          <template #default="{ row }">{{ fmtPrice(row.cost) }}</template>
        </el-table-column>
        <el-table-column label="操作后均价" width="110">
          <template #default="{ row }">{{ fmtPrice(row.avg_price) }}</template>
        </el-table-column>
        <el-table-column prop="project_name" label="关联项目" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.project_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="140" show-overflow-tooltip />
        <el-table-column
          label="操作"
          :width="manageMode ? 220 : 170"
          fixed="right"
          class-name="op-col"
        >
          <template #default="{ row }">
            <div class="op-cell">
              <el-button
                v-if="row.can_undo && row.revoke_status === 'ok' && !row.invalid"
                type="warning"
                size="small"
                class="op-undo"
                @click="onUndo(row)"
              >
                <el-icon><RefreshLeft /></el-icon>撤销
              </el-button>
              <el-button size="small" class="op-view" @click="peek(row)">详情</el-button>
              <el-button
                v-if="manageMode"
                type="danger"
                size="small"
                class="op-del"
                @click="onDelete(row)"
              >删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        background layout="total, sizes, prev, pager, next, jumper"
        :total="total" :page-size="pageSize" :current-page="page"
        :page-sizes="[20, 50, 100]"
        style="margin-top:14px; justify-content:flex-end; display:flex"
        @current-change="p => { page = p; loadData() }"
        @size-change="s => { pageSize = s; page = 1; loadData() }"
      />
    </div>

    <!-- 管理模式身份验证 -->
    <el-dialog
      v-model="authVisible"
      title="进入管理模式 · 身份验证"
      width="420px"
      :close-on-click-modal="false"
    >
      <el-form ref="authFormRef" :model="authForm" :rules="authRules" label-width="80px">
        <el-form-item label="账号" prop="username">
          <el-input v-model="authForm.username" placeholder="请输入登录账号" :disabled="!!authForm.username" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="authForm.password"
            type="password"
            show-password
            placeholder="请输入当前账号的登录密码"
            @keyup.enter="onAuthSubmit"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="authVisible = false">取消</el-button>
        <el-button type="primary" :loading="authLoading" @click="onAuthSubmit">确认并进入管理模式</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Tickets, Setting, Check, Delete, RefreshLeft } from '@element-plus/icons-vue'
import {
  getStockLogList,
  getAllMaterials,
  exportStockLog,
  deleteStockLog,
  deleteStockLogBatch,
  undoStockLog,
  login,
} from '@/api'
import { downloadBlob } from '@/utils/file'
import { fmtNum, fmtPrice } from '@/utils/format'

const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const logType = ref('')
const materialId = ref(null)
const dateRange = ref([])
const materialOptions = ref([])
const tableRef = ref(null)

// 管理模式
const manageMode = ref(false)
const selectedRows = ref([])
const selectedIds = computed(() => selectedRows.value.map(r => r.id))

// 身份验证弹窗
const authVisible = ref(false)
const authLoading = ref(false)
const authFormRef = ref(null)
const authForm = reactive({
  username: localStorage.getItem('username') || 'admin',
  password: '',
})
const authRules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

function tagType(t) { return { in: 'success', out_temp: 'warning', out_project: 'danger', lock: 'info', unlock: 'info' }[t] || '' }

async function loadData() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (logType.value) params.log_type = logType.value
    if (materialId.value) params.material_id = materialId.value
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_time = dateRange.value[0]
      params.end_time = dateRange.value[1]
    }
    const res = await getStockLogList(params)
    list.value = res.data.list
    total.value = res.data.total
    // 数据刷新后清除选中
    selectedRows.value = []
    if (tableRef.value) tableRef.value.clearSelection()
  } finally { loading.value = false }
}

async function onExport() {
  try {
    const params = {}
    if (logType.value) params.log_type = logType.value
    if (materialId.value) params.material_id = materialId.value
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_time = dateRange.value[0]
      params.end_time = dateRange.value[1]
    }
    const res = await exportStockLog(params)
    downloadBlob(res.data, res.headers['content-disposition'])
    ElMessage.success('导出成功')
  } catch (e) {}
}

function onSelectionChange(rows) {
  selectedRows.value = rows
}

function onDelete(row) {
  ElMessageBox.confirm(
    `确定删除该条流水记录吗？\n时间：${row.create_time}\n物料：${row.material_name}\n类型：${row.log_type_name}`,
    '删除确认', { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' }
  ).then(async () => {
    await deleteStockLog(row.id)
    ElMessage.success('删除成功')
    loadData()
  }).catch(() => {})
}

function peek(row) {
  ElMessageBox.alert(
    `时间：${row.create_time}\n物料：${row.material_name}\n类型：${row.log_type_name}\n数量：${fmtNum(row.num)}\n成本：${fmtPrice(row.cost)}\n操作后均价：${fmtPrice(row.avg_price)}\n关联项目：${row.project_name || '-'}\n备注：${row.remark || '-'}`,
    `流水 #${row.id} 详情`,
    { confirmButtonText: '关闭', customStyle: { whiteSpace: 'pre-line' } }
  )
}

// 管理模式：先校验密码，再开启
function openAuthDialog() {
  authForm.username = localStorage.getItem('username') || 'admin'
  authForm.password = ''
  authVisible.value = true
  nextTick(() => {
    if (authFormRef.value) authFormRef.value.clearValidate()
  })
}

async function onAuthSubmit() {
  if (!authFormRef.value) return
  const valid = await authFormRef.value.validate().catch(() => false)
  if (!valid) return
  authLoading.value = true
  try {
    // 调用登录接口做账号密码二次校验（不替换现有 token，仅验证）
    await login({ username: authForm.username, password: authForm.password })
    manageMode.value = true
    authVisible.value = false
    ElMessage.success('身份验证通过，已进入管理模式，可批量选择并删除流水')
  } catch (e) {
    // 错误已由拦截器提示
  } finally {
    authLoading.value = false
  }
}

function exitManageMode() {
  manageMode.value = false
  selectedRows.value = []
  if (tableRef.value) tableRef.value.clearSelection()
}

function onBatchDelete() {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先勾选要删除的流水记录')
    return
  }
  ElMessageBox.confirm(
    `确定批量删除已选中的 ${selectedIds.value.length} 条流水记录吗？\n该操作不可逆，请谨慎操作。`,
    '批量删除确认',
    { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' }
  ).then(async () => {
    try {
      const res = await deleteStockLogBatch(selectedIds.value)
      ElMessage.success(res.msg || '批量删除成功')
      loadData()
    } catch (e) {}
  }).catch(() => {})
}

// V1.2：5 分钟内可撤销
async function onUndo(row) {
  try {
    await ElMessageBox.confirm(
      `确定撤销该条流水吗？\n时间：${row.server_commit_ts || row.create_time}\n物料：${row.material_name}\n类型：${row.log_type_name}\n撤销后会生成反向补偿流水并标记原流水失效。`,
      '撤销确认',
      { type: 'warning', confirmButtonText: '确认撤销', cancelButtonText: '取消' }
    )
  } catch (e) {
    return
  }
  try {
    await undoStockLog(row.id)
    ElMessage.success('撤销成功，已生成反向补偿流水')
    loadData()
  } catch (e) {}
}

onMounted(async () => {
  const res = await getAllMaterials()
  materialOptions.value = res.data
  loadData()
})
</script>

<style scoped>
.op-cell {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 2px;
  flex-wrap: nowrap;
}
.op-del  {
  background: color-mix(in srgb, var(--danger) 16%, transparent) !important;
  border-color: color-mix(in srgb, var(--danger) 26%, transparent) !important;
  color: var(--danger) !important;
}
.op-view {
  background: color-mix(in srgb, var(--primary) 14%, transparent) !important;
  border-color: color-mix(in srgb, var(--primary) 22%, transparent) !important;
  color: var(--primary) !important;
}

/* 操作列固定 · 底色不随行变化（与 MaterialList 一致，防止滚动穿透） */
:deep(.el-table .op-col),
:deep(.el-table .sel-col),
:deep(.el-table__row:hover .op-col),
:deep(.el-table__row:hover .sel-col),
:deep(.el-table__row.el-table__row--striped .op-col),
:deep(.el-table__row.el-table__row--striped .sel-col),
:deep(.el-table__row.el-table__row--striped:hover .op-col),
:deep(.el-table__row.el-table__row--striped:hover .sel-col) {
  background: var(--card) !important;
}
:deep(.el-table__fixed-right-patch) {
  background: var(--card-2) !important;
}
:deep(.el-table) {
  --el-table-bg-color: var(--card);
  --el-table-tr-bg-color: var(--card);
  --el-table-row-hover-bg-color: color-mix(in srgb, var(--primary) 6%, transparent);
}

.tb-manage {
  background: color-mix(in srgb, var(--primary) 24%, transparent) !important;
  border-color: color-mix(in srgb, var(--primary) 36%, transparent) !important;
  color: var(--primary) !important;
}
.tb-done {
  background: color-mix(in srgb, var(--success) 24%, transparent) !important;
  border-color: color-mix(in srgb, var(--success) 36%, transparent) !important;
  color: var(--success) !important;
}
.tb-del {
  background: color-mix(in srgb, var(--danger) 28%, transparent) !important;
  border-color: color-mix(in srgb, var(--danger) 40%, transparent) !important;
  color: var(--danger) !important;
}
.op-undo {
  background: color-mix(in srgb, var(--warning) 24%, transparent) !important;
  border-color: color-mix(in srgb, var(--warning) 36%, transparent) !important;
  color: var(--warning) !important;
}
.ts-cell { display: flex; flex-direction: column; gap: 2px; }
.ts-main { font-weight: 600; color: var(--text-main); font-size: 13px; }
.ts-sub { font-size: 11px; color: var(--text-sub); }
.ts-flag { font-size: 11px; display: inline-block; padding: 0 6px; border-radius: 3px; align-self: flex-start; }
.ts-flag-ok { background: color-mix(in srgb, var(--success) 15%, transparent); color: var(--success); }
.ts-flag-forced { background: color-mix(in srgb, var(--warning) 20%, transparent); color: var(--warning); font-weight: 600; }
</style>
