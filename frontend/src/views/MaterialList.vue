<template>
  <div>
    <div class="page-card">
      <div class="page-title"><el-icon><Box /></el-icon>物料列表</div>
      <!-- 顶部操作栏 -->
      <div class="toolbar">
        <el-button type="primary" @click="onAdd"><el-icon><Plus /></el-icon>新增物料</el-button>
        <el-button @click="onExport"><el-icon><Download /></el-icon>批量导出</el-button>
        <el-input v-model="keyword" placeholder="搜索物料名称" clearable style="width:200px" @keyup.enter="loadData" @clear="loadData" />
        <el-select v-model="parentCategoryId" placeholder="一级分类" clearable style="width:140px" @change="onParentChange">
          <el-option v-for="c in level1" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <el-select v-model="categoryId" placeholder="二级分类" clearable style="width:160px" :disabled="!parentCategoryId" @change="loadData">
          <el-option v-for="c in level2OfSelected" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <el-button @click="loadData">查询</el-button>
        <div class="flex-grow"></div>
        <el-button
          v-if="!manageMode"
          class="tb-btn tb-manage"
          @click="toggleManageMode"
        ><el-icon><Setting /></el-icon>管理</el-button>
        <template v-else>
          <el-button class="tb-btn tb-done" @click="toggleManageMode"><el-icon><Check /></el-icon>完成</el-button>
          <el-button
            class="tb-btn tb-del"
            :disabled="selectedIds.length === 0"
            @click="onBatchDelete"
          ><el-icon><Delete /></el-icon>删除（{{ selectedIds.length }}）</el-button>
        </template>
      </div>
      <!-- 表格 -->
      <el-table
        :data="list"
        v-loading="loading"
        :row-class-name="rowClass"
        border stripe size="default"
        ref="tableRef"
        @selection-change="onSelectionChange"
      >
        <el-table-column label="缩略图" width="70">
          <template #default="{ row }">
            <el-image v-if="row.image" :src="row.image" :preview-src-list="[row.image]" fit="cover" style="width:40px;height:40px;border-radius:6px" />
            <span v-else class="no-img">无</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="物料名称" min-width="130" show-overflow-tooltip />
        <el-table-column label="分类" min-width="90" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="sub">{{ row.parent_category_name }} / </span>{{ row.category_name }}
          </template>
        </el-table-column>
        <el-table-column prop="spec" label="规格" min-width="150" show-overflow-tooltip />
        <el-table-column label="实际库存" width="90">
          <template #default="{ row }"><span class="readonly-field">{{ fmtNum(row.stock_total_num) }}</span></template>
        </el-table-column>
        <el-table-column label="可用库存" width="90">
          <template #default="{ row }"><span class="readonly-field">{{ fmtNum(row.usable_stock) }}</span></template>
        </el-table-column>
        <el-table-column label="加权单价" width="100">
          <template #default="{ row }"><span class="readonly-field">{{ fmtPrice(row.stock_avg_price) }}</span></template>
        </el-table-column>
        <el-table-column label="总成本" width="100">
          <template #default="{ row }"><span class="readonly-field">{{ fmtPrice(row.stock_total_cost) }}</span></template>
        </el-table-column>
        <el-table-column label="告警阈值" width="80">
          <template #default="{ row }">{{ fmtNum(row.warn_num) }}</template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="100" show-overflow-tooltip />
        <el-table-column label="操作" :width="manageMode ? 320 : 220" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <div class="op-cell">
              <el-button link class="op-btn op-detail" size="small" @click="goDetail(row)">详情</el-button>
              <el-button link class="op-btn op-in" size="small" @click="onStockIn(row)">入库</el-button>
              <el-button link class="op-btn op-out" size="small" @click="onStockOut(row)" :disabled="row.stock_total_num <= 0">出库</el-button>
              <el-button
                v-if="manageMode"
                link class="op-btn op-edit" size="small"
                @click="onEdit(row)"
              >编辑</el-button>
              <el-button
                v-if="manageMode"
                link class="op-btn op-del" size="small"
                @click="onDelete(row)"
              >删除</el-button>
            </div>
          </template>
        </el-table-column>
        <el-table-column
          v-if="manageMode"
          type="selection"
          width="50"
          align="center"
          fixed="right"
          class-name="sel-col"
        />
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

    <!-- 弹窗 -->
    <MaterialDialog v-model:visible="dialogVisible" :data="editData" @success="loadData" />
    <StockInDialog v-model:visible="inDialogVisible" :material="editData" @success="loadData" />
    <StockOutTempDialog v-model:visible="outDialogVisible" :material="editData" @success="loadData" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Download, Box, Setting, Check, Delete } from '@element-plus/icons-vue'
import { getMaterialList, getCategoryList, deleteMaterial, deleteMaterialBatch, exportMaterial } from '@/api'
import MaterialDialog from '@/components/MaterialDialog.vue'
import StockInDialog from '@/components/StockInDialog.vue'
import StockOutTempDialog from '@/components/StockOutTempDialog.vue'
import { downloadBlob } from '@/utils/file'
import { fmtNum, fmtPrice } from '@/utils/format'

const router = useRouter()
const tableRef = ref(null)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const keyword = ref('')
const categoryId = ref(null)
const parentCategoryId = ref(null)
const allCats = ref([])

const dialogVisible = ref(false)
const inDialogVisible = ref(false)
const outDialogVisible = ref(false)
const editData = ref(null)

// 管理模式 + 选中
const manageMode = ref(false)
const selectedRows = ref([])
const selectedIds = computed(() => selectedRows.value.map(r => r.id))

const level1 = computed(() => allCats.value.filter(c => c.level === 1))
const level2OfSelected = computed(() => allCats.value.filter(c => c.level === 2 && c.parent_id === parentCategoryId.value))

function onParentChange() { categoryId.value = null; loadData() }

function rowClass({ row }) {
  if (row.warn_num > 0 && row.stock_total_num <= row.warn_num) return 'row-warn'
  return ''
}

async function loadData() {
  loading.value = true
  try {
    const res = await getMaterialList({
      page: page.value, page_size: pageSize.value,
      keyword: keyword.value,
      category_id: categoryId.value || undefined,
      parent_category_id: parentCategoryId.value || undefined
    })
    list.value = res.data.list
    total.value = res.data.total
    // 数据刷新后清除选中
    selectedRows.value = []
    if (tableRef.value) tableRef.value.clearSelection()
  } finally { loading.value = false }
}

async function loadCats() {
  const res = await getCategoryList()
  allCats.value = res.data
}

function onAdd() { editData.value = null; dialogVisible.value = true }
function onEdit(row) { editData.value = row; dialogVisible.value = true }
function onStockIn(row) { editData.value = row; inDialogVisible.value = true }
function onStockOut(row) { editData.value = row; outDialogVisible.value = true }
function goDetail(row) { router.push(`/material/detail/${row.id}`) }

function toggleManageMode() {
  manageMode.value = !manageMode.value
  // 退出管理时清除选中
  if (!manageMode.value) {
    selectedRows.value = []
    if (tableRef.value) tableRef.value.clearSelection()
  }
}

function onSelectionChange(rows) {
  selectedRows.value = rows
}

function onDelete(row) {
  ElMessageBox.confirm(`确定删除物料「${row.name}」吗？`, '删除确认', { type: 'warning' }).then(async () => {
    await deleteMaterial(row.id)
    ElMessage.success('删除成功')
    loadData()
  }).catch(() => {})
}

function onBatchDelete() {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先选择要删除的物料')
    return
  }
  ElMessageBox.confirm(
    `确定删除已选中的 ${selectedIds.value.length} 条物料吗？`,
    '删除确认',
    { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' }
  ).then(async () => {
    try {
      const res = await deleteMaterialBatch(selectedIds.value)
      ElMessage.success(res.msg || '批量删除成功')
      loadData()
    } catch (e) {}
  }).catch(() => {})
}

async function onExport() {
  try {
    const res = await exportMaterial()
    downloadBlob(res.data, res.headers['content-disposition'])
    ElMessage.success('导出成功')
  } catch (e) {}
}

onMounted(() => { loadCats(); loadData() })
</script>

<style scoped>
.no-img { color: var(--text-sub); font-size: 12px; }
.sub { color: var(--text-sub); }

:deep(.toolbar .el-button + .el-button) { margin-left: 0; }

.op-cell {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 2px;
  flex-wrap: nowrap;
}

.op-detail {
  background: color-mix(in srgb, var(--text-sub) 18%, transparent) !important;
  border-color: color-mix(in srgb, var(--text-sub) 25%, transparent) !important;
  color: var(--text-sub) !important;
}
.op-in {
  background: color-mix(in srgb, var(--success) 18%, transparent) !important;
  border-color: color-mix(in srgb, var(--success) 28%, transparent) !important;
  color: var(--success) !important;
}
.op-out {
  background: color-mix(in srgb, var(--warning) 18%, transparent) !important;
  border-color: color-mix(in srgb, var(--warning) 28%, transparent) !important;
  color: var(--warning) !important;
}
.op-edit {
  background: color-mix(in srgb, var(--primary) 18%, transparent) !important;
  border-color: color-mix(in srgb, var(--primary) 28%, transparent) !important;
  color: var(--primary) !important;
}
.op-del {
  background: color-mix(in srgb, var(--danger) 18%, transparent) !important;
  border-color: color-mix(in srgb, var(--danger) 28%, transparent) !important;
  color: var(--danger) !important;
}

:deep(.el-table .op-col),
:deep(.el-table .sel-col),
:deep(.el-table__row:hover .op-col),
:deep(.el-table__row:hover .sel-col),
:deep(.el-table__row.el-table__row--striped .op-col),
:deep(.el-table__row.el-table__row--striped .sel-col),
:deep(.el-table__row.el-table__row--striped:hover .op-col),
:deep(.el-table__row.el-table__row--striped:hover .sel-col) {
  background: var(--card, #242830) !important;
}
:deep(.el-table__fixed-right-patch) {
  background: var(--card-2, #2c313a) !important;
}
:deep(.el-table) {
  --el-table-bg-color: var(--card, #242830);
  --el-table-tr-bg-color: var(--card, #242830);
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
</style>
