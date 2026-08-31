<template>
  <div v-loading="loading">
    <!-- 顶部项目信息 -->
    <div class="page-card" v-if="project">
      <div class="page-title">
        <el-icon><Folder /></el-icon>{{ project.name }}
        <el-button link @click="$router.back()" style="margin-left:auto"><el-icon><Back /></el-icon>返回</el-button>
      </div>
      <div class="info-grid">
        <div class="info-row"><span class="lbl">状态：</span>
          <el-tag :type="statusTagType(project.status)" size="small">{{ statusText(project.status) }}</el-tag>
        </div>
        <div class="info-row"><span class="lbl">创建时间：</span>{{ project.create_time }}</div>
        <div class="info-row"><span class="lbl">简介：</span>{{ project.intro || '-' }}</div>
        <div class="info-row"><span class="lbl">资料链接：</span>
          <a v-if="project.link" :href="project.link" target="_blank">{{ project.link }}</a>
          <span v-else>-</span>
        </div>
      </div>
      <div class="action-bar">
        <span class="lbl">状态切换：</span>
        <el-select :model-value="project.status" style="width:130px" :disabled="project.status === 'finish'" @change="onStatusChange">
          <el-option label="准备阶段" value="prepare" :disabled="project.status === 'finish'" />
          <el-option label="制作阶段" value="making" :disabled="project.status === 'finish'" />
          <el-option label="完工结算" value="finish" />
        </el-select>
        <div class="grow"></div>
        <el-upload
          :show-file-list="false"
          :before-upload="(f) => onImportBom(f)"
          accept=".xlsx,.xls"
        >
          <el-button v-if="project && project.status !== 'finish'" size="small"><el-icon><Upload /></el-icon>导入BOM</el-button>
        </el-upload>
        <el-button size="small" @click="onExportBom"><el-icon><Download /></el-icon>导出BOM</el-button>
        <el-button v-if="project && project.status !== 'finish'" type="primary" size="small" @click="onAddBom"><el-icon><Plus /></el-icon>新增BOM</el-button>
      </div>
    </div>

    <!-- 中部BOM表格 -->
    <div class="page-card">
      <div class="page-title">
        <el-icon><List /></el-icon>BOM清单
      </div>
      <el-table :data="bomList" border stripe size="default" empty-text="暂无BOM明细">
        <el-table-column label="物料名称" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="mat-cell">
              <el-image v-if="row.material_image" :src="row.material_image" fit="cover" class="mat-img" />
              <div class="mat-info">
                <strong>{{ row.material_name }}</strong>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="规格 / 分类" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <div>{{ row.material_spec || '—' }}</div>
            <div class="sub">{{ row.parent_category_name }}{{ row.parent_category_name?' / ':'' }}{{ row.category_name }}</div>
          </template>
        </el-table-column>
        <el-table-column label="预估用量" width="110" align="center">
          <template #default="{ row }"><strong>{{ fmtNum(row.plan_num) }}</strong></template>
        </el-table-column>
        <el-table-column label="状态" min-width="300">
          <template #default="{ row }">
            <div class="status-cell">
              <el-tag size="small" type="info" effect="plain">预占 {{ fmtNum(row.lock_num) }}</el-tag>
              <el-tag size="small" type="primary" effect="plain">已用 {{ fmtNum(row.used_num) }}</el-tag>
              <el-tag size="small" type="success" effect="plain">可用 {{ fmtNum(row.usable_stock) }}</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right" class-name="op-col" align="center">
          <template #default="{ row }">
            <div class="op-cell">
              <el-button link class="op-btn op-edit" size="small" @click="onEditBom(row)" :disabled="isFinished">编辑</el-button>
              <el-button link class="op-btn op-consume" size="small" @click="onConsume(row)" :disabled="project?.status !== 'making' || row.lock_num <= row.used_num">消耗</el-button>
              <el-button link class="op-btn op-del" size="small" @click="onDeleteBom(row)" :disabled="isFinished">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 底部Tab：项目操作流水 -->
    <div class="page-card">
      <el-tabs v-model="logTab">
        <el-tab-pane label="项目操作流水" name="log">
          <el-table :data="logs" border size="small" :max-height="420" empty-text="暂无流水">
            <el-table-column prop="create_time" label="时间" width="160" />
            <el-table-column label="类型" width="100">
              <template #default="{ row }"><el-tag :type="logTagType(row.log_type)" size="small">{{ row.log_type_name }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="material_name" label="物料" min-width="140" show-overflow-tooltip />
            <el-table-column label="数量" width="90">
              <template #default="{ row }">{{ fmtNum(row.num) }}</template>
            </el-table-column>
            <el-table-column label="成本" width="100">
              <template #default="{ row }">{{ fmtPrice(row.cost) }}</template>
            </el-table-column>
            <el-table-column label="操作后均价" width="110">
              <template #default="{ row }">{{ fmtPrice(row.avg_price) }}</template>
            </el-table-column>
            <el-table-column prop="remark" label="备注" min-width="140" show-overflow-tooltip />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 新增/编辑BOM弹窗 -->
    <el-dialog v-model="bomDialogVisible" :title="bomEditMode ? '编辑BOM明细' : '新增BOM明细'" width="460px">
      <el-form ref="bomFormRef" :model="bomForm" :rules="bomRules" label-width="90px">
        <el-form-item label="选择物料" prop="material_id">
          <el-select v-model="bomForm.material_id" filterable placeholder="搜索选择物料" style="width:100%" :disabled="bomEditMode">
            <el-option v-for="m in materialOptions" :key="m.id" :label="`${m.name}（可用${fmtNum(m.usable_stock)}）`" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="预估用量" prop="plan_num">
          <el-input-number v-model="bomForm.plan_num" :min="0" :precision="0" :step="1" controls-position="right" style="width:100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="bomDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="bomSaving" @click="onSaveBom">{{ bomEditMode ? '保存' : '添加' }}</el-button>
      </template>
    </el-dialog>

    <!-- 消耗确认弹窗已移除：点击消耗直接二次确认→一次性消耗全部剩余预占用 -->
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Download, Folder, List, Back, Upload } from '@element-plus/icons-vue'
import {
  getProjectDetail, switchProjectStatus, finishSettle,
  getAllMaterials, saveBom, updateBomPlan, deleteBom, bomConsume,
  getStockLogList, exportProject, importProjectBom
} from '@/api'
import { downloadBlob } from '@/utils/file'
import { fmtNum, fmtPrice } from '@/utils/format'

const route = useRoute()
const loading = ref(false)
const project = ref(null)
const bomList = ref([])
const logs = ref([])
const logTab = ref('log')
const materialOptions = ref([])

const isFinished = computed(() => project.value?.status === 'finish')

// 新增/编辑BOM
const bomDialogVisible = ref(false)
const bomEditMode = ref(false)  // false=新增, true=编辑
const bomEditRowId = ref(null)
const bomSaving = ref(false)
const bomFormRef = ref()
const bomForm = reactive({ material_id: null, plan_num: 0 })
const bomRules = {
  material_id: [{ required: true, message: '请选择物料', trigger: 'change' }],
  plan_num: [{ required: true, message: '请输入预估用量', trigger: 'blur' }]
}

// 消耗：直接一次性扣减"剩余预占用 = 锁定 - 已用"全部数量
const consumeSaving = ref(false)

function statusText(s) { return { prepare: '准备阶段', making: '制作阶段', finish: '已归档' }[s] || s }
function statusTagType(s) { return { prepare: 'info', making: 'warning', finish: 'success' }[s] || '' }
function logTagType(t) { return { in: 'success', out_temp: 'warning', out_project: 'danger', lock: 'info', unlock: 'info' }[t] || '' }

async function loadData() {
  loading.value = true
  try {
    const id = route.params.id
    const res = await getProjectDetail(id)
    project.value = res.data.project
    bomList.value = res.data.bom_list
    const logRes = await getStockLogList({ project_id: id, page: 1, page_size: 200 })
    logs.value = logRes.data.list
  } finally { loading.value = false }
}

async function loadMaterials() {
  const res = await getAllMaterials()
  materialOptions.value = res.data
}

function onStatusChange(val) {
  if (val === 'finish') {
    onFinishSettle()
    return
  }
  ElMessageBox.confirm(`确定将项目切换为「${statusText(val)}」吗？`, '状态切换', { type: 'warning' }).then(async () => {
    await switchProjectStatus(project.value.id, { status: val })
    ElMessage.success('状态切换成功')
    loadData()
  }).catch(() => loadData())
}

function onFinishSettle() {
  ElMessageBox.confirm(
    '确定执行完工结算吗？\n结算后将把所有BOM行剩余预占用强制消耗（扣减真实库存），项目状态归档，不可撤销。',
    '完工结算确认', { type: 'warning', confirmButtonText: '确认结算' }
  ).then(async () => {
    const res = await finishSettle(project.value.id)
    const d = res.data
    let msg = `项目完工结算成功，总消耗成本 ${fmtPrice(d.total_cost)} 元`
    if (d.settle_list && d.settle_list.length) {
      const out = d.settle_list.map(s => `${s.material_name}:消耗${fmtNum(s.used_num)}${s.auto_consumed_num > 0 ? `(含自动${fmtNum(s.auto_consumed_num)})` : ''}`).join('；')
      if (out) msg += `\n物料明细：${out}`
    }
    ElMessageBox.alert(msg, '结算结果', { type: 'success' })
    loadData()
  }).catch(() => loadData())
}

function onAddBom() {
  loadMaterials()
  bomEditMode.value = false
  bomEditRowId.value = null
  Object.assign(bomForm, { material_id: null, plan_num: 0 })
  bomDialogVisible.value = true
}

function onEditBom(row) {
  loadMaterials()
  bomEditMode.value = true
  bomEditRowId.value = row.id
  Object.assign(bomForm, { material_id: row.material_id, plan_num: row.plan_num })
  bomDialogVisible.value = true
}

function onSaveBom() {
  bomFormRef.value.validate(async (valid) => {
    if (!valid) return
    bomSaving.value = true
    try {
      if (bomEditMode.value) {
        // 编辑模式：更新预估用量（会同步更新lock_num）
        await updateBomPlan(bomEditRowId.value, { plan_num: bomForm.plan_num })
        ElMessage.success('BOM明细编辑成功')
      } else {
        await saveBom({ project_id: project.value.id, material_id: bomForm.material_id, plan_num: bomForm.plan_num })
        ElMessage.success('BOM明细新增成功')
      }
      bomDialogVisible.value = false
      loadData()
    } catch (e) {} finally { bomSaving.value = false }
  })
}

function onDeleteBom(row) {
  ElMessageBox.confirm(`确定移除BOM明细「${row.material_name}」吗？`, '删除确认', { type: 'warning' }).then(async () => {
    await deleteBom(row.id)
    ElMessage.success('BOM明细删除成功')
    loadData()
  }).catch(() => {})
}

function onConsume(row) {
  const remain = +(row.lock_num - row.used_num).toFixed(6)
  if (remain <= 0) { ElMessage.warning('没有可消耗的数量'); return }
  const stock = +(row.stock_total_num ?? 0).toFixed(6)
  if (stock < remain) {
    ElMessage.warning(`库存不足，取消消耗：需要 ${fmtNum(remain)}，当前实际库存仅 ${fmtNum(stock)}`)
    return
  }
  ElMessageBox.confirm(
    `确定消耗物料「${row.material_name}」吗？\n\n将一次性消耗全部剩余预占用：${fmtNum(remain)} 个（预估用量 ${fmtNum(row.plan_num)}，已消耗 ${fmtNum(row.used_num)}，实际库存 ${fmtNum(stock)}）`,
    '确认消耗', { type: 'warning', confirmButtonText: '确认消耗' }
  ).then(async () => {
    consumeSaving.value = true
    try {
      await bomConsume(row.id, { consume_num: remain })
      ElMessage.success(`消耗成功：${fmtNum(remain)} 个`)
      loadData()
    } catch (e) {} finally { consumeSaving.value = false }
  }).catch(() => {})
}

async function onExportBom() {
  try {
    const res = await exportProject(project.value.id)
    downloadBlob(res.data, res.headers['content-disposition'])
    ElMessage.success('BOM导出成功')
  } catch (e) {}
}

async function onImportBom(file) {
  const ok = await ElMessageBox.confirm(
    `确定向项目「${project.value.name}」导入 BOM 吗？\nExcel 需包含「物料ID」和「预估用量」列，可先点「导出BOM」获取模板。`,
    '导入BOM确认',
    { type: 'warning', confirmButtonText: '确认导入', cancelButtonText: '取消' }
  ).then(() => true).catch(() => false)
  if (!ok) return false
  const formData = new FormData()
  formData.append('file', file)
  try {
    const r = await importProjectBom(project.value.id, formData)
    ElMessage.success(r.msg || '导入成功')
    loadData()
  } catch (e) {}
  return false
}

onMounted(loadData)
</script>

<style scoped>
.info-grid { display: flex; flex-wrap: wrap; gap: 10px 30px; }
.info-row { color: var(--text-main); }
.info-row .lbl { color: var(--text-sub); }
.action-bar { margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--border); display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.action-bar .lbl { color: var(--text-sub); }
.grow { flex: 1 1 auto; }
.sub { color: var(--text-sub); font-size: 12px; }
.mat-cell { display: flex; align-items: center; gap: 10px; }
.mat-img {
  width: 42px; height: 42px; border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--card-2);
  flex-shrink: 0;
}

.status-cell { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }

/* 操作列按钮居中（之前是 justify-flex-end → 改 center，配合列 align=center） */
.op-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  flex-wrap: nowrap;
}
.op-btn { padding: 2px 8px !important; min-width: 48px; }
.op-edit {
  background: color-mix(in srgb, var(--primary) 18%, transparent) !important;
  border-color: color-mix(in srgb, var(--primary) 28%, transparent) !important;
  color: var(--primary) !important;
}
.op-consume {
  background: color-mix(in srgb, var(--success) 18%, transparent) !important;
  border-color: color-mix(in srgb, var(--success) 28%, transparent) !important;
  color: var(--success) !important;
}
.op-del {
  background: color-mix(in srgb, var(--danger) 18%, transparent) !important;
  border-color: color-mix(in srgb, var(--danger) 28%, transparent) !important;
  color: var(--danger) !important;
}

/* 操作列（fixed=right）不透明底色，防止滚动透字 */
:deep(.el-table .op-col),
:deep(.el-table__row:hover .op-col),
:deep(.el-table__row.el-table__row--striped .op-col),
:deep(.el-table__row.el-table__row--striped:hover .op-col) {
  background: var(--card, #242830) !important;
}
</style>
