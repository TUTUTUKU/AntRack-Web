<template>
  <div>
    <div class="toolbar">
      <el-select v-model="status" size="small" style="width:140px" @change="loadData">
        <el-option label="待处理" value="pending" />
        <el-option label="已处理" value="accepted" />
        <el-option label="已放弃" value="dismissed" />
      </el-select>
      <el-button type="primary" plain size="small" @click="loadData">
        <el-icon><Refresh /></el-icon>刷新
      </el-button>
      <div class="grow"></div>
      <el-button size="small" :disabled="!selectedPending.length" @click="applyBatch('accepted')">
        批量按最新侧生效（{{ selectedPending.length }}）
      </el-button>
      <el-button size="small" type="danger" plain :disabled="!selectedPending.length" @click="applyBatch('dismissed')">
        批量放弃（{{ selectedPending.length }}）
      </el-button>
      <el-tag size="small" type="danger" effect="dark" v-if="pendingCount > 0">当前待处理 {{ pendingCount }} 条</el-tag>
    </div>

    <div class="conflict-list" v-loading="loading">
      <el-empty v-if="!loading && list.length === 0" description="暂无冲突记录" />

      <div
        v-for="c in list"
        :key="c.id"
        class="conflict-item"
        :class="['status-' + c.status, { sel: selectedSet.has(c.id) }]"
      >
        <div class="ci-head">
          <el-checkbox
            :model-value="selectedSet.has(c.id)"
            :disabled="c.status !== 'pending'"
            @change="(v) => toggleSelect(c.id, v)"
          />
          <div class="ci-title">
            <b>冲突 #{{ c.id }}</b>
            <span class="muted">物料</span>
            <span>ID {{ c.material_id }}</span>
            <span class="muted">阶段码</span>
            <span>{{ c.stage_code }}</span>
          </div>
          <div class="ci-status">
            <el-tag v-if="c.status === 'pending'" size="small" type="warning">待处理</el-tag>
            <el-tag v-else-if="c.status === 'accepted'" size="small" type="success">已确认生效</el-tag>
            <el-tag v-else-if="c.status === 'dismissed'" size="small" type="info">已放弃</el-tag>
          </div>
          <div class="ci-meta">
            <span>{{ c.create_time }}</span>
            <el-button type="primary" link size="small" @click="expanded[c.id] = !expanded[c.id]">
              {{ expanded[c.id] ? '收起' : '展开' }}
            </el-button>
          </div>
        </div>

        <div v-show="expanded[c.id]" class="ci-body">
          <div class="snap-list">
            <div
              v-for="(s, idx) in sorted(c.snapshots || [])"
              :key="idx"
              class="snap-card"
              :class="{ chosen: c.status === 'accepted' && c.chosen_source_index === idx }"
            >
              <div class="snap-head">
                <span class="snap-idx">版本 {{ idx + 1 }}</span>
                <el-tag size="small" :type="s.source === 'app' ? 'primary' : 'success'" effect="light">
                  {{ s.source === 'app' ? 'APP' : 'Web' }}
                </el-tag>
                <span class="snap-op">{{ opName(s.op_type) }}</span>
                <span class="grow"></span>
                <span class="snap-ts">{{ s.fixed_ts || s.local_device_ts }}</span>
              </div>
              <div class="snap-summary">{{ s.summary || JSON.stringify(s.payload || s.diff_fields || {}).slice(0, 240) }}</div>
              <div class="snap-foot">
                <span v-if="s.time_correction_flag === 'forced'" class="flag flag-warn">时间校正：强制</span>
                <span v-else-if="s.time_correction_flag === 'ok'" class="flag flag-ok">时间校正：正常</span>
                <span v-if="s.local_device_ts" class="flag flag-sub">设备原始 {{ s.local_device_ts }}</span>
                <span class="grow"></span>
                <el-button
                  v-if="c.status === 'pending'"
                  size="small"
                  type="primary"
                  @click="resolveOne(c.id, 'accepted', idx)"
                >让此版本生效</el-button>
              </div>
            </div>
          </div>

          <div v-if="c.status === 'pending'" class="ci-actions">
            <el-button
              size="small"
              type="primary"
              @click="resolveOne(c.id, 'accepted', preferredIndex(c))"
            >按偏好生效</el-button>
            <el-button size="small" type="danger" plain @click="resolveOne(c.id, 'dismissed')">放弃冲突</el-button>
          </div>
          <div v-else class="ci-actions done">
            <span>处理人：{{ c.operator || '-' }}</span>
            <span>处理时间：{{ c.update_time }}</span>
          </div>
        </div>
      </div>
    </div>

    <el-pagination
      background layout="total, prev, pager, next, jumper"
      :total="total" :page-size="pageSize" :current-page="page"
      style="margin-top:14px; justify-content:flex-end; display:flex"
      @current-change="p => { page = p; loadData() }"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { listConflicts, resolveConflict, resolveConflictsBatch, getAllUserConfigs } from '@/api'
import * as ws from '@/utils/ws'

const emit = defineEmits(['count-updated'])

const loading = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const status = ref('pending')
const pendingCount = ref(0)
const expanded = reactive({})
const selectedSet = reactive(new Set())
const prefer = ref('latest_side')

const selectedPending = computed(() => [...selectedSet])

function toggleSelect(id, v) {
  if (v) selectedSet.add(id); else selectedSet.delete(id)
}

function opName(t) {
  return {
    stock_in: '入库',
    stock_out_temp: '临时出库',
    stock_out_project: '项目出库',
    material_update: '物料编辑',
    material_create: '物料创建',
    bom_lock: 'BOM 锁定',
    bom_unlock: 'BOM 解锁',
    project_create: '项目创建',
  }[t] || t
}

function sorted(snaps) {
  // 按校正后业务时间倒序展示
  return [...(snaps || [])].sort((a, b) => (b.fixed_ts || '').localeCompare(a.fixed_ts || ''))
}

function preferredIndex(c) {
  if (prefer.value === 'prefer_app') {
    const i = (c.snapshots || []).findIndex(s => s.source === 'app')
    if (i >= 0) return i
  }
  if (prefer.value === 'prefer_web') {
    const i = (c.snapshots || []).findIndex(s => s.source === 'web')
    if (i >= 0) return i
  }
  // latest_side：已按 fixed_ts 倒序，取第 0 个
  return 0
}

async function loadData() {
  loading.value = true
  try {
    const r = await listConflicts({
      status: status.value,
      page: page.value,
      page_size: pageSize,
    })
    list.value = r.data.list
    total.value = r.data.total
    pendingCount.value = Number(r.data.pending_count || 0)
    emit('count-updated', pendingCount.value)
    ws.setPendingCount(pendingCount.value)
    // 自动展开待处理
    list.value.forEach(c => {
      if (c.status === 'pending' && expanded[c.id] === undefined) expanded[c.id] = true
    })
  } finally { loading.value = false }
}

async function resolveOne(id, action, idx = null) {
  try {
    await resolveConflict(id, {
      status: action,
      chosen_snapshot_index: action === 'accepted' ? idx : null,
    })
    ElMessage.success(action === 'accepted' ? '已确认生效' : '已放弃冲突')
    loadData()
  } catch (e) {}
}

async function applyBatch(action) {
  if (!selectedPending.value.length) return
  try {
    await ElMessageBox.confirm(
      `确定对选中的 ${selectedPending.value.length} 条冲突执行「${action === 'accepted' ? '按最新侧生效' : '放弃'}」吗？`,
      '批量处理确认',
      { type: 'warning', confirmButtonText: '确认', cancelButtonText: '取消' }
    )
  } catch (e) { return }
  const chosen_indexes = {}
  if (action === 'accepted') {
    list.value.forEach(c => {
      if (selectedSet.has(c.id)) chosen_indexes[String(c.id)] = preferredIndex(c)
    })
  }
  try {
    await resolveConflictsBatch({
      ids: selectedPending.value,
      status: action,
      chosen_indexes,
    })
    ElMessage.success('批量处理完成')
    selectedSet.clear()
    loadData()
  } catch (e) {}
}

onMounted(async () => {
  try {
    const r = await getAllUserConfigs()
    prefer.value = (r.data || {}).conflict_prefer || 'latest_side'
  } catch (e) {}
  loadData()
  ws.on((evt, data) => {
    if (evt === 'conflict:created' || evt === 'conflict:resolved' || evt === 'conflict:resolved:batch') {
      loadData()
    }
  })
})
</script>

<style scoped>
.toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; flex-wrap: wrap; }
.grow { flex: 1; }

.conflict-item {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 10px;
}
.conflict-item.status-pending { border-left: 4px solid var(--warning); }
.conflict-item.status-accepted { border-left: 4px solid var(--success); }
.conflict-item.status-dismissed { border-left: 4px solid var(--border); opacity: 0.85; }
.conflict-item.sel { border-color: var(--primary); box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary) 20%, transparent); }

.ci-head {
  display: grid;
  grid-template-columns: auto 1fr auto auto;
  align-items: center;
  gap: 12px;
}
.ci-title { display: flex; align-items: center; gap: 6px; color: var(--text-main); flex-wrap: wrap; }
.ci-title b { font-size: 14px; }
.ci-title .muted { color: var(--text-sub); font-size: 12px; margin-left: 8px; }
.ci-meta { display: flex; align-items: center; gap: 10px; color: var(--text-sub); font-size: 12px; }

.ci-body { margin-top: 10px; padding-top: 10px; border-top: 1px dashed var(--border); }
.snap-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 10px; }
.snap-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  background: var(--card-2);
  position: relative;
}
.snap-card.chosen { border-color: var(--success); background: color-mix(in srgb, var(--success) 8%, var(--card-2)); }
.snap-head { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text-sub); margin-bottom: 6px; }
.snap-idx { font-weight: 700; color: var(--text-main); }
.snap-op { color: var(--primary); font-weight: 600; }
.snap-ts { color: var(--text-sub); }
.snap-summary { color: var(--text-main); font-size: 13px; line-height: 1.6; min-height: 2.2em; margin-bottom: 8px; }
.snap-foot { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; font-size: 11px; }
.flag { padding: 2px 6px; border-radius: 3px; }
.flag-ok { background: color-mix(in srgb, var(--success) 14%, transparent); color: var(--success); }
.flag-warn { background: color-mix(in srgb, var(--warning) 18%, transparent); color: var(--warning); font-weight: 600; }
.flag-sub { background: color-mix(in srgb, var(--secondary) 18%, transparent); color: var(--text-sub); }

.ci-actions {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.ci-actions.done { color: var(--text-sub); font-size: 12px; justify-content: flex-end; gap: 18px; }
</style>
