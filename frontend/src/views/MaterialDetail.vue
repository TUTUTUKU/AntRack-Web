<template>
  <div v-loading="loading">
    <div class="page-card">
      <div class="page-title">
        <el-icon><Box /></el-icon>物料详情
        <el-button link @click="$router.back()" style="margin-left:auto"><el-icon><Back /></el-icon>返回</el-button>
      </div>
      <div class="detail-top" v-if="data">
        <div class="img-box">
          <el-image v-if="data.image" :src="data.image" :preview-src-list="[data.image]" fit="cover" class="big-img" />
          <div v-else class="no-img"><el-icon><Picture /></el-icon></div>
        </div>
        <div class="info-box">
          <h2 class="mat-name">{{ data.name }}</h2>
          <div class="info-row"><span class="lbl">分类：</span>{{ data.parent_category_name }} / {{ data.category_name }}</div>
          <div class="info-row"><span class="lbl">规格：</span>{{ data.spec || '-' }}</div>
          <div class="info-row"><span class="lbl">备注：</span>{{ data.remark || '-' }}</div>
          <div class="info-row"><span class="lbl">告警阈值：</span>{{ fmtNum(data.warn_num) }}</div>
          <div class="stock-box">
            <div class="stock-item"><span class="lbl">实际库存</span><b>{{ fmtNum(data.stock_total_num) }}</b></div>
            <div class="stock-item"><span class="lbl">可用库存</span><b class="primary">{{ fmtNum(data.usable_stock) }}</b></div>
            <div class="stock-item"><span class="lbl">锁定量</span><b class="warning">{{ fmtNum(data.lock_num) }}</b></div>
            <div class="stock-item"><span class="lbl">加权单价</span><b>{{ fmtPrice(data.stock_avg_price) }}</b></div>
            <div class="stock-item"><span class="lbl">总成本</span><b class="danger">{{ fmtPrice(data.stock_total_cost) }}</b></div>
          </div>
        </div>
      </div>
      <div class="action-bar" v-if="data">
        <el-button type="success" @click="onStockIn"><el-icon><Bottom /></el-icon>入库</el-button>
        <el-button type="warning" @click="onStockOut" :disabled="data.stock_total_num <= 0"><el-icon><Top /></el-icon>临时出库</el-button>
        <el-button type="primary" @click="onEdit"><el-icon><Edit /></el-icon>编辑物料</el-button>
        <el-button type="danger" @click="onDelete"><el-icon><Delete /></el-icon>删除物料</el-button>
      </div>
    </div>

    <div class="page-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="物料流水记录" name="log">
          <el-table :data="logs" border size="small" :max-height="420" empty-text="暂无流水">
            <el-table-column prop="create_time" label="时间" width="160" />
            <el-table-column label="类型" width="100">
              <template #default="{ row }"><el-tag :type="logTagType(row.log_type)" size="small">{{ row.log_type_name }}</el-tag></template>
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
            <el-table-column prop="project_name" label="关联项目" min-width="120" show-overflow-tooltip />
            <el-table-column prop="remark" label="备注" min-width="120" show-overflow-tooltip />
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="关联BOM项目" name="bom">
          <el-table :data="bomProjects" border size="small" :max-height="420" empty-text="未被任何项目BOM引用">
            <el-table-column prop="project_name" label="项目名称" min-width="140" />
            <el-table-column prop="status" label="项目状态" width="100">
              <template #default="{ row }">{{ statusText(row.status) }}</template>
            </el-table-column>
            <el-table-column label="预估用量" width="100">
              <template #default="{ row }">{{ fmtNum(row.plan_num) }}</template>
            </el-table-column>
            <el-table-column label="锁定数量" width="100">
              <template #default="{ row }">{{ fmtNum(row.lock_num) }}</template>
            </el-table-column>
            <el-table-column label="已消耗" width="100">
              <template #default="{ row }">{{ fmtNum(row.used_num) }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>

    <MaterialDialog v-model:visible="dialogVisible" :data="data" @success="loadData" />
    <StockInDialog v-model:visible="inDialogVisible" :material="data" @success="loadData" />
    <StockOutTempDialog v-model:visible="outDialogVisible" :material="data" @success="loadData" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMaterialDetail, getStockLogList, deleteMaterial } from '@/api'
import MaterialDialog from '@/components/MaterialDialog.vue'
import StockInDialog from '@/components/StockInDialog.vue'
import StockOutTempDialog from '@/components/StockOutTempDialog.vue'
import { fmtNum, fmtPrice } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const data = ref(null)
const logs = ref([])
const bomProjects = ref([])
const activeTab = ref('log')

const dialogVisible = ref(false)
const inDialogVisible = ref(false)
const outDialogVisible = ref(false)

function logTagType(t) {
  return { in: 'success', out_temp: 'warning', out_project: 'danger', lock: 'info', unlock: 'info' }[t] || ''
}
function statusText(s) { return { prepare: '准备阶段', making: '制作阶段', finish: '已归档' }[s] || s }

async function loadData() {
  loading.value = true
  try {
    const id = route.params.id
    const res = await getMaterialDetail(id)
    data.value = res.data
    const logRes = await getStockLogList({ material_id: id, page: 1, page_size: 100 })
    logs.value = logRes.data.list
    // 关联BOM项目：从流水里提取 project_id 去重（简化展示）
    const map = new Map()
    logRes.data.list.forEach(l => {
      if (l.project_id && !map.has(l.project_id)) {
        map.set(l.project_id, { project_name: l.project_name, status: '', plan_num: '', lock_num: '', used_num: '' })
      }
    })
    bomProjects.value = Array.from(map.values())
  } finally { loading.value = false }
}

function onStockIn() { inDialogVisible.value = true }
function onStockOut() { outDialogVisible.value = true }
function onEdit() { dialogVisible.value = true }
function onDelete() {
  ElMessageBox.confirm(`确定删除物料「${data.value.name}」吗？`, '删除确认', { type: 'warning' }).then(async () => {
    await deleteMaterial(data.value.id)
    ElMessage.success('删除成功')
    router.push('/material')
  }).catch(() => {})
}

onMounted(loadData)
</script>

<style scoped>
.detail-top { display: flex; gap: 24px; flex-wrap: wrap; }
.img-box { flex-shrink: 0; }
.big-img { width: 220px; height: 220px; border-radius: 10px; border: 1px solid var(--border); }
.no-img { width: 220px; height: 220px; border-radius: 10px; border: 1px dashed var(--border); display: flex; align-items: center; justify-content: center; color: var(--text-sub); font-size: 40px; background: var(--card-2); }
.info-box { flex: 1; min-width: 280px; }
.mat-name { margin: 0 0 12px; font-size: 20px; color: var(--text-main); }
.info-row { line-height: 2; color: var(--text-main); }
.info-row .lbl { color: var(--text-sub); display: inline-block; width: 80px; }
.stock-box { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 14px; }
.stock-item { background: var(--card-2); border-radius: 8px; padding: 10px 16px; min-width: 110px; }
.stock-item .lbl { display: block; color: var(--text-sub); font-size: 12px; }
.stock-item b { font-size: 18px; color: var(--text-main); }
.stock-item b.primary { color: var(--primary); }
.stock-item b.warning { color: var(--warning); }
.stock-item b.danger { color: var(--danger); }
.action-bar { margin-top: 18px; padding-top: 16px; border-top: 1px solid var(--border); display: flex; gap: 10px; flex-wrap: wrap; }
@media (max-width: 768px) { .big-img, .no-img { width: 140px; height: 140px; } }
</style>
