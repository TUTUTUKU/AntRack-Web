<template>
  <div class="backup-root">
    <!-- 顶部：操作区 -->
    <div class="card">
      <p class="hint">
        点击「备份当前数据」生成 .ans 备份文件并加入下方备份列表；点击「上传恢复备份」可上传本地 .ans 文件直接恢复到该备份状态（当前数据将被覆盖）。备份列表中的每条记录均可下载或恢复，恢复后所有客户端会自动刷新数据。
      </p>
      <div class="actions">
        <el-button type="primary" :loading="creating" @click="onCreate">
          <el-icon><Download /></el-icon>备份当前数据
        </el-button>
        <el-upload
          ref="uploadRef"
          :show-file-list="false"
          :before-upload="beforeUpload"
          :http-request="handleUploadRestore"
          accept=".ans,.zip"
        >
          <el-button type="warning" :loading="restoringUpload">
            <el-icon><Upload /></el-icon>上传恢复备份
          </el-button>
        </el-upload>
      </div>
    </div>

    <!-- 下方：备份列表 -->
    <div class="card">
      <div class="snap-head">
        <div class="snap-title"><el-icon><Files /></el-icon>备份列表</div>
        <div class="filters">
          <el-select v-model="triggerType" size="small" placeholder="备份方式" style="width:110px" @change="onFilterChange">
            <el-option label="全部" value="" />
            <el-option label="手动" value="manual" />
            <el-option label="自动" value="auto" />
          </el-select>
          <el-select v-model="sourceType" size="small" placeholder="来源" style="width:110px" @change="onFilterChange">
            <el-option label="全部" value="" />
            <el-option label="Web 端" value="web" />
            <el-option label="App 端" value="app" />
          </el-select>
          <el-button size="small" @click="reload">
            <el-icon><Refresh /></el-icon>刷新
          </el-button>
        </div>
      </div>

      <el-table :data="list" v-loading="loading" border stripe size="small">
        <el-table-column label="编号" width="110" align="center">
          <template #default="{ row }"><b>{{ row.name || `#${row.id}` }}</b></template>
        </el-table-column>
        <el-table-column label="来源" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="(row.name || '').startsWith('APP')" size="small" type="primary" effect="light">APP</el-tag>
            <el-tag v-else size="small" type="success" effect="light">WEB</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="备份方式" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="isAutoTrigger(row.trigger)" size="small" type="info" effect="light">自动</el-tag>
            <el-tag v-else size="small" type="success" effect="light">手动</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="系统版本" width="120" align="center">
          <template #default="{ row }"><b>V{{ row.version }}</b></template>
        </el-table-column>
        <el-table-column label="文件大小" width="110" align="center">
          <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column label="生成时间" prop="create_time" width="170" align="center" />
        <el-table-column label="备注" prop="note" min-width="140" show-overflow-tooltip />
        <el-table-column label="操作" width="240" fixed="right" align="center" class-name="bk-op-col">
          <template #default="{ row }">
            <div class="bk-op-cell">
              <el-button size="small" class="bk-dl" @click="onDownload(row)">下载</el-button>
              <el-popconfirm title="确定从该备份恢复吗？当前数据将被覆盖（不可撤销）。" @confirm="onRestoreFrom(row)">
                <template #reference>
                  <el-button size="small" class="bk-restore">恢复</el-button>
                </template>
              </el-popconfirm>
              <el-popconfirm title="确定删除该备份吗？文件将从服务端永久删除。" @confirm="onDelete(row)">
                <template #reference>
                  <el-button size="small" class="bk-del">删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        background
        layout="total, sizes, prev, pager, next, jumper"
        :total="total"
        :page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :current-page="page"
        style="margin-top:12px; justify-content:flex-end; display:flex"
        @current-change="p => { page = p; reload() }"
        @size-change="s => { pageSize = s; page = 1; reload() }"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Upload, Files, Refresh } from '@element-plus/icons-vue'
import {
  listBackupSnapshots,
  createBackupSnapshot,
  deleteBackupSnapshot,
  downloadBackupSnapshot,
  restoreFromSnapshot,
  restoreBackup,
} from '@/api'
import { downloadBlob } from '@/utils/file'

const loading = ref(false)
const creating = ref(false)
const restoringUpload = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const triggerType = ref('')
const sourceType = ref('')

function isAutoTrigger(t) {
  return ['auto', 'weekly', 'after_proofread'].includes(t)
}

async function reload() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (triggerType.value) params.trigger_type = triggerType.value
    if (sourceType.value) params.source = sourceType.value
    const r = await listBackupSnapshots(params)
    list.value = r.data.list || []
    total.value = Number(r.data.total || 0)
  } finally { loading.value = false }
}

function onFilterChange() {
  page.value = 1
  reload()
}

async function onCreate() {
  creating.value = true
  try {
    await createBackupSnapshot('manual', 'Web 手动生成')
    ElMessage.success('备份生成成功')
    reload()
  } catch (e) {} finally { creating.value = false }
}

async function onDownload(row) {
  try {
    const r = await downloadBackupSnapshot(row.id)
    downloadBlob(r.data, r.headers['content-disposition'] || `attachment; filename="${row.name || 'snapshot_' + row.id}.ans"`)
  } catch (e) {}
}

async function onDelete(row) {
  try {
    await deleteBackupSnapshot(row.id)
    ElMessage.success('已删除')
    reload()
  } catch (e) {}
}

async function onRestoreFrom(row) {
  try {
    const r = await restoreFromSnapshot(row.id)
    ElMessage.success((r.msg || '恢复成功') + '，请稍等片刻，系统正在重新拉取最新数据')
    setTimeout(() => window.location.reload(), 1500)
  } catch (e) {}
}

function formatSize(n) {
  const v = Number(n) || 0
  if (v < 1024) return v + ' B'
  if (v < 1024 * 1024) return (v / 1024).toFixed(1) + ' KB'
  return (v / 1024 / 1024).toFixed(2) + ' MB'
}

// 上传恢复
function beforeUpload(file) {
  const ok = /\.(ans|zip)$/i.test(file.name || '')
  if (!ok) ElMessage.warning('仅支持 .ans 或 .zip 文件')
  return ok
}

async function handleUploadRestore(opts) {
  const file = opts.file
  try {
    await ElMessageBox.confirm(
      `即将上传文件「${file.name}」并恢复备份，当前数据将被覆盖，确认继续吗？`,
      '上传恢复确认',
      { type: 'warning', confirmButtonText: '确认恢复', cancelButtonText: '取消' }
    )
  } catch (e) {
    opts.onAbort && opts.onAbort()
    return
  }
  restoringUpload.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    const r = await restoreBackup(fd, () => {})
    ElMessage.success((r.msg || '恢复成功') + '，即将刷新页面')
    setTimeout(() => window.location.reload(), 1500)
    opts.onSuccess && opts.onSuccess()
  } catch (e) {
    opts.onError && opts.onError(e)
  } finally {
    restoringUpload.value = false
  }
}

onMounted(() => reload())
</script>

<style scoped>
.backup-root { display: flex; flex-direction: column; gap: 16px; }
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px 18px;
}
.hint {
  color: var(--text-sub); font-size: 12px; line-height: 1.7; margin: 0 0 12px;
  padding: 8px 10px; border-radius: 8px;
  background: color-mix(in srgb, var(--primary) 6%, transparent);
  border: 1px solid color-mix(in srgb, var(--primary) 14%, transparent);
}
.actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }

.snap-head {
  display: flex; align-items: center; gap: 10px; margin-bottom: 12px;
}
.snap-title {
  font-weight: 700; color: var(--text-main); font-size: 14px;
  display: flex; align-items: center; gap: 6px;
}
.filters { margin-left: auto; display: flex; gap: 8px; }

/* 操作按钮：实心风格 */
.bk-op-cell { display: flex; align-items: center; justify-content: center; gap: 4px; flex-wrap: nowrap; }
.bk-dl {
  background: color-mix(in srgb, var(--primary) 14%, transparent) !important;
  border-color: color-mix(in srgb, var(--primary) 22%, transparent) !important;
  color: var(--primary) !important;
}
.bk-restore {
  background: color-mix(in srgb, var(--warning) 18%, transparent) !important;
  border-color: color-mix(in srgb, var(--warning) 28%, transparent) !important;
  color: var(--warning) !important;
}
.bk-del {
  background: color-mix(in srgb, var(--danger) 16%, transparent) !important;
  border-color: color-mix(in srgb, var(--danger) 26%, transparent) !important;
  color: var(--danger) !important;
}

/* 固定列底色不随行变化 */
:deep(.el-table .bk-op-col),
:deep(.el-table__row:hover .bk-op-col),
:deep(.el-table__row.el-table__row--striped .bk-op-col),
:deep(.el-table__row.el-table__row--striped:hover .bk-op-col) {
  background: var(--card) !important;
}
:deep(.el-table__fixed-right-patch) {
  background: var(--card-2, var(--card)) !important;
}
:deep(.el-table) {
  --el-table-bg-color: var(--card);
  --el-table-tr-bg-color: var(--card);
  --el-table-row-hover-bg-color: color-mix(in srgb, var(--primary) 6%, transparent);
}
</style>
