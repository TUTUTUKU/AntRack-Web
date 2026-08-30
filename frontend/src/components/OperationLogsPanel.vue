<template>
  <div class="oplogs-root">
    <div class="toolbar">
      <el-select v-model="filters.action" placeholder="操作类型" clearable size="small" style="width:140px">
        <el-option v-for="it in actionOptions" :key="it.v" :label="it.n" :value="it.v" />
      </el-select>
      <el-select v-model="filters.source" placeholder="来源端" clearable size="small" style="width:120px">
        <el-option label="Web" value="web" />
        <el-option label="APP" value="app" />
      </el-select>
      <el-input v-model="filters.material_id" placeholder="物料ID" clearable size="small" style="width:130px" />
      <el-input v-model="filters.project_id" placeholder="项目ID" clearable size="small" style="width:130px" />
      <el-date-picker
        v-model="filters.range"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        size="small"
        style="width:260px"
      />
      <el-button type="primary" plain size="small" @click="reload">
        <el-icon><Refresh /></el-icon>查询
      </el-button>
      <el-button size="small" @click="resetFilters">重置</el-button>
      <div class="grow"></div>
      <span class="total-tip">共 {{ total }} 条（服务端保留 1 年）</span>
    </div>

    <el-table :data="list" v-loading="loading" border stripe size="small" style="width:100%">
      <el-table-column label="业务时间" width="170" prop="effective_time" sortable />
      <el-table-column label="来源" width="72" align="center">
        <template #default="{ row }">
          <el-tag size="small" :type="row.source === 'app' ? 'primary' : 'success'" effect="light">
            {{ row.source === 'app' ? 'APP' : 'Web' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作类型" width="130">
        <template #default="{ row }">
          <el-tag size="small" :type="tagType(row.action)">{{ actionName(row.action) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作人" prop="username" width="120" show-overflow-tooltip />
      <el-table-column label="设备" prop="device_id" width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.device_id || '-' }}</template>
      </el-table-column>
      <el-table-column label="物料ID" width="80" align="center">
        <template #default="{ row }">{{ row.material_id ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="项目ID" width="80" align="center">
        <template #default="{ row }">{{ row.project_id ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="关联流水ID" width="100" align="center">
        <template #default="{ row }">{{ row.related_log_id ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="详情" min-width="220" show-overflow-tooltip>
        <template #default="{ row }">
          <span class="detail-text">{{ detailText(row.detail) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80" align="center">
        <template #default="{ row }">
          <template v-if="row.revoke_status === 'revoked'">
            <el-tag size="small" type="info" effect="plain">已撤销</el-tag>
          </template>
          <template v-else>
            <el-tag size="small" type="success" effect="plain">有效</el-tag>
          </template>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      background
      layout="total, prev, pager, next, jumper"
      :total="total"
      :page-size="pageSize"
      :current-page="page"
      style="margin-top:12px; justify-content:flex-end; display:flex"
      @current-change="p => { page = p; reload() }"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { listOperationLogs } from '@/api'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20

const filters = reactive({
  action: '',
  source: '',
  material_id: '',
  project_id: '',
  range: [],
})

const actionOptions = [
  { v: 'stock_in', n: '入库' },
  { v: 'stock_out_temp', n: '临时出库' },
  { v: 'stock_out_project', n: '项目出库' },
  { v: 'material_create', n: '物料创建' },
  { v: 'material_update', n: '物料编辑' },
  { v: 'material_delete', n: '物料删除' },
  { v: 'project_create', n: '项目创建' },
  { v: 'bom_lock', n: 'BOM 锁定' },
  { v: 'bom_unlock', n: 'BOM 解锁' },
  { v: 'backup_restore', n: '备份恢复' },
  { v: 'undo', n: '撤销回滚' },
  { v: 'config_change', n: '配置变更' },
]

function actionName(t) {
  const hit = actionOptions.find(x => x.v === t)
  return hit ? hit.n : (t || '-')
}
function tagType(t) {
  return {
    stock_in: 'success',
    stock_out_temp: 'warning',
    stock_out_project: 'danger',
    material_create: 'primary',
    material_update: '',
    material_delete: 'danger',
    project_create: 'primary',
    bom_lock: 'warning',
    bom_unlock: 'warning',
    backup_restore: 'info',
    undo: 'info',
    config_change: '',
  }[t] || ''
}
function detailText(d) {
  try {
    if (!d || typeof d !== 'object') return String(d || '')
    if (d.summary) return d.summary
    return JSON.stringify(d)
  } catch (e) { return '' }
}

async function reload() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize }
    if (filters.action) params.action = filters.action
    if (filters.source) params.source = filters.source
    if (filters.material_id) params.material_id = Number(filters.material_id) || 0
    if (filters.project_id) params.project_id = Number(filters.project_id) || 0
    if (filters.range && filters.range.length === 2) {
      params.start_time = filters.range[0]
      params.end_time = filters.range[1]
    }
    const r = await listOperationLogs(params)
    list.value = r.data.list || []
    total.value = Number(r.data.total || 0)
  } finally { loading.value = false }
}

function resetFilters() {
  filters.action = ''
  filters.source = ''
  filters.material_id = ''
  filters.project_id = ''
  filters.range = []
  page.value = 1
  reload()
}

onMounted(() => reload())
</script>

<style scoped>
.oplogs-root { }
.toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; flex-wrap: wrap; }
.grow { flex: 1; }
.total-tip { color: var(--text-sub); font-size: 12px; }
.detail-text { font-size: 12px; color: var(--text-main); line-height: 1.6; }
</style>
