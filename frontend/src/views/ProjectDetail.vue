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
        <el-button type="primary" @click="onExport"><el-icon><Download /></el-icon>导出项目+BOM</el-button>
      </div>
    </div>

    <!-- 中部BOM表格 -->
    <div class="page-card">
      <div class="page-title">
        <el-icon><List /></el-icon>BOM清单
        <div style="margin-left:auto;display:flex;gap:8px;align-items:center">
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
      <el-table :data="bomList" border stripe size="default" empty-text="暂无BOM明细">
        <el-table-column label="物料名称" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.material_name }}</template>
        </el-table-column>
        <el-table-column label="规格" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.material_spec || '-' }}</span>
            <div class="sub">{{ row.parent_category_name }} / {{ row.category_name }}</div>
          </template>
        </el-table-column>
        <el-table-column label="预估用量" width="120">
          <template #default="{ row }">
            <el-input-number v-if="project && project.status !== 'finish'" v-model="row.plan_num" :min="0" :precision="0" :step="1" size="small" controls-position="right" style="width:100%" @change="v => onPlanChange(row, v)" />
            <span v-else>{{ fmtNum(row.plan_num) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" min-width="180">
          <template #default="{ row }">
            <div class="status-cell">
              <el-tag size="small" type="info" effect="plain">预占 {{ fmtNum(row.lock_num) }}</el-tag>
              <el-tag size="small" type="primary" effect="plain">已用 {{ fmtNum(row.used_num) }}</el-tag>
              <el-tag size="small" type="success" effect="plain">可用 {{ fmtNum(row.usable_stock) }}</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right" class-name="op-col">
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

    <!-- 消耗确认弹窗 -->
    <el-dialog v-model="consumeDialogVisible" title="确认物料消耗" width="420px">
      <div class="mat-info" v-if="consumeRow">
        <strong>{{ consumeRow.material_name }}</strong>
        <span class="sub">锁定 {{ fmtNum(consumeRow.lock_num) }} · 已消耗 {{ fmtNum(consumeRow.used_num) }} · 可消耗 {{ fmtNum(consumeRemain) }}</span>
      </div>
      <el-form label-width="100px" style="margin-top:14px">
        <el-form-item label="本次消耗数量">
          <el-input-number v-model="consumeNum" :min="1" :max="consumeRemain" :precision="0" :step="1" controls-position="right" style="width:100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="consumeRemark" type="textarea" :rows="2" maxlength="500" show-word-limit placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="consumeDialogVisible = false">取消</el-button>
        <el-button type="success" :loading="consumeSaving" @click="onSubmitConsume">确认消耗</el-button>
      </template>
    </el-dialog>
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

// 消耗
const consumeDialogVisible = ref(false)
const consumeRow = ref(null)
const consumeNum = ref(0)
const consumeRemark = ref('')
const consumeSaving = ref(false)
const consumeRemain = computed(() => {
  if (!consumeRow.value) return 0
  return +(consumeRow.value.lock_num - consumeRow.value.used_num).toFixed(6)
})

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
    '确定执行完工结算吗？',
    '完工结算确认', { type: 'warning', confirmButtonText: '确认结算' }
  ).then(async () => {
    const res = await finishSettle(project.value.id)
    const d = res.data
    let msg = `项目完工结算成功，总消耗成本 ${fmtPrice(d.total_cost)} 元`
    if (d.settle_list && d.settle_list.length) {
      const out = d.settle_list.filter(s => s.used_num > 0).map(s => `${s.material_name}:出库${fmtNum(s.used_num)}`).join('；')
      const unlock = d.settle_list.filter(s => s.unlock_num > 0).map(s => `${s.material_name}:解锁${fmtNum(s.unlock_num)}`).join('；')
      if (out) msg += `\n出库：${out}`
      if (unlock) msg += `\n解锁：${unlock}`
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

async function onPlanChange(row, v) {
  try {
    await updateBomPlan(row.id, { plan_num: v })
    ElMessage.success('预估用量已更新')
  } catch (e) { loadData() }
}

function onDeleteBom(row) {
  ElMessageBox.confirm(`确定移除BOM明细「${row.material_name}」吗？`, '删除确认', { type: 'warning' }).then(async () => {
    await deleteBom(row.id)
    ElMessage.success('BOM明细删除成功')
    loadData()
  }).catch(() => {})
}

function onConsume(row) {
  consumeRow.value = row
  consumeNum.value = consumeRemain.value > 0 ? 1 : 0
  consumeRemark.value = ''
  consumeDialogVisible.value = true
}

async function onSubmitConsume() {
  if (consumeNum.value <= 0) { ElMessage.warning('消耗数量必须大于0'); return }
  if (consumeNum.value > consumeRemain.value) { ElMessage.warning(`消耗数量不能超过可消耗量 ${fmtNum(consumeRemain.value)}`); return }
  consumeSaving.value = true
  try {
    await bomConsume(consumeRow.value.id, { consume_num: consumeNum.value, remark: consumeRemark.value })
    ElMessage.success('消耗确认成功')
    consumeDialogVisible.value = false
    loadData()
  } catch (e) {} finally { consumeSaving.value = false }
}

async function onExport() {
  try {
    const res = await exportProject(project.value.id)
    downloadBlob(res.data, res.headers['content-disposition'])
    ElMessage.success('导出成功')
  } catch (e) {}
}

// BOM导入导出（仅BOM表，非项目整体）
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
.sub { color: var(--text-sub); font-size: 12px; }
.mat-info { padding: 10px 14px; background: var(--card-2); border-radius: 8px; }
.mat-info .sub { display: block; margin-top: 4px; }

.status-cell { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }

/* 操作栏按钮样式 */
.op-cell {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  flex-wrap: nowrap;
}
.op-btn { padding: 2px 8px !important; }
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
