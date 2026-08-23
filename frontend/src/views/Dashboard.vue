<template>
  <div>
    <!-- 顶部4统计卡片 -->
    <el-row :gutter="14">
      <el-col :xs="12" :sm="6" v-for="card in statCards" :key="card.key">
        <div class="stat-card clickable" :style="{ borderTopColor: card.color }" @click="onStatCardClick(card)">
          <div class="stat-label">{{ card.label }}</div>
          <div class="stat-value" :style="{ color: card.color }">{{ card.value }}</div>
          <div class="stat-unit">{{ card.unit }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- 中部双卡片 -->
    <el-row :gutter="14" style="margin-top:14px">
      <el-col :xs="24" :md="12">
        <div class="page-card">
          <div class="page-title"><el-icon><Warning /></el-icon>低库存告警</div>
          <el-table
            :data="stats.warn_list || []"
            size="small"
            :max-height="320"
            empty-text="暂无低库存物料"
            @row-click="onWarnRowClick"
            :row-class-name="() => 'clickable-row'"
          >
            <el-table-column prop="name" label="物料名称" min-width="120" />
            <el-table-column label="实际库存" width="100">
              <template #default="{ row }">{{ fmtNum(row.stock_total_num) }}</template>
            </el-table-column>
            <el-table-column label="告警阈值" width="100">
              <template #default="{ row }">{{ fmtNum(row.warn_num) }}</template>
            </el-table-column>
            <el-table-column label="可用库存" width="100">
              <template #default="{ row }">{{ fmtNum(row.usable_stock) }}</template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>
      <el-col :xs="24" :md="12">
        <div class="page-card">
          <div class="page-title"><el-icon><Tickets /></el-icon>最近10条库存流水</div>
          <el-table
            :data="recentLogs"
            size="small"
            :max-height="320"
            empty-text="暂无流水记录"
            @row-click="onLogRowClick"
            :row-class-name="() => 'clickable-row'"
          >
            <el-table-column prop="create_time" label="时间" width="150" />
            <el-table-column label="类型" width="90">
              <template #default="{ row }">
                <el-tag :type="logTagType(row.log_type)" size="small">{{ row.log_type_name }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="material_name" label="物料" min-width="120" show-overflow-tooltip />
            <el-table-column label="数量" width="80">
              <template #default="{ row }">{{ fmtNum(row.num) }}</template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>
    </el-row>

    <!-- 底部项目状态统计 -->
    <div class="page-card" style="margin-top:14px">
      <div class="page-title"><el-icon><Folder /></el-icon>项目状态统计</div>
      <el-row :gutter="14">
        <el-col :xs="24" :sm="8" v-for="ps in projectStatusList" :key="ps.key">
          <div class="ps-card clickable" :style="{ borderColor: ps.color }" @click="onProjectStatusClick(ps)">
            <div class="ps-label">{{ ps.label }}</div>
            <div class="ps-value" :style="{ color: ps.color }">{{ ps.value }}</div>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getDashboardStats, getRecentLogs } from '@/api'
import { fmtNum } from '@/utils/format'

const router = useRouter()
const stats = ref({})
const recentLogs = ref([])

const statCards = computed(() => [
  { key: 'material', label: '物料总品类数', value: stats.value.material_count ?? 0, unit: '种', color: '#22b8dd', route: '/material' },
  { key: 'project', label: '全部项目数', value: stats.value.project_count ?? 0, unit: '个', color: '#28c868', route: '/project' },
  { key: 'making', label: '进行中项目', value: stats.value.making_count ?? 0, unit: '个', color: '#ff9500', route: { path: '/project', query: { status: 'making' } } },
  { key: 'cost', label: '库存总金额', value: (stats.value.total_cost ?? 0).toFixed(2), unit: '元', color: '#f84242', route: '/material' }
])

const projectStatusList = computed(() => {
  const ps = stats.value.project_status || {}
  return [
    { key: 'prepare', label: '准备阶段', value: ps.prepare ?? 0, color: '#22b8dd', status: 'prepare' },
    { key: 'making', label: '制作阶段', value: ps.making ?? 0, color: '#ff9500', status: 'making' },
    { key: 'finish', label: '已归档', value: ps.finish ?? 0, color: '#28c868', status: 'finish' }
  ]
})

function logTagType(t) {
  return { in: 'success', out_temp: 'warning', out_project: 'danger', lock: 'info', unlock: 'info' }[t] || ''
}

function onStatCardClick(card) {
  if (card.route) router.push(card.route)
}

function onWarnRowClick(row) {
  if (row.id) router.push(`/material/detail/${row.id}`)
}

function onLogRowClick(row) {
  if (row.material_id) router.push(`/material/detail/${row.material_id}`)
}

function onProjectStatusClick(ps) {
  router.push({ path: '/project', query: { status: ps.status } })
}

async function load() {
  const [s, r] = await Promise.all([getDashboardStats(), getRecentLogs(10)])
  stats.value = s.data
  recentLogs.value = r.data
}
onMounted(load)
</script>

<style scoped>
.stat-card {
  background: var(--card); border: 1px solid var(--border);
  border-top: 3px solid var(--primary); border-radius: 10px;
  padding: 16px 18px; margin-bottom: 14px;
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}
.stat-label { color: var(--text-sub); font-size: 13px; }
.stat-value { font-size: 28px; font-weight: 700; margin-top: 6px; }
.stat-unit { color: var(--text-sub); font-size: 12px; margin-top: 2px; }

.ps-card {
  background: var(--card-2); border: 1px solid var(--border);
  border-left: 4px solid var(--primary); border-radius: 8px;
  padding: 18px; text-align: center; margin-bottom: 14px;
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}
.ps-label { color: var(--text-sub); font-size: 13px; }
.ps-value { font-size: 30px; font-weight: 700; margin-top: 6px; }

.clickable { cursor: pointer; }
.clickable:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12);
}

:deep(.clickable-row) { cursor: pointer; }
:deep(.clickable-row:hover > td) {
  background-color: color-mix(in srgb, var(--primary) 8%, transparent) !important;
}
</style>
