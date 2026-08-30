<template>
  <div class="backup-root">
    <!-- 顶部：手动操作 -->
    <div class="card split-card">
      <div class="col">
        <h4 class="col-title"><el-icon><Download /></el-icon>手动备份</h4>
        <p class="hint">生成快照文件（.antrack）并保存在服务端 data/backups 目录；也可直接下载到本地。</p>
        <div class="actions">
          <el-button type="primary" :loading="creating" @click="onCreate">
            <el-icon><Plus /></el-icon>生成快照
          </el-button>
          <el-button type="success" plain :loading="downloading" @click="onExport">
            <el-icon><Download /></el-icon>下载当前备份
          </el-button>
        </div>
      </div>
      <div class="col-divider" />
      <div class="col">
        <h4 class="col-title"><el-icon><Upload /></el-icon>恢复备份</h4>
        <p class="hint">支持两种来源：从服务端历史快照（下方列表）恢复，或上传本地 .antrack 文件恢复。跨版本字段自动兼容。</p>
        <div class="actions">
          <el-upload
            ref="uploadRef"
            :show-file-list="false"
            :before-upload="beforeUpload"
            :http-request="handleUploadRestore"
            accept=".antrack,.zip"
          >
            <el-button type="warning" :loading="restoringUpload">
              <el-icon><Upload /></el-icon>上传 .antrack 恢复
            </el-button>
          </el-upload>
          <el-tag size="small" type="info" effect="light">恢复后，所有客户端会自动刷新数据</el-tag>
        </div>
      </div>
    </div>

    <!-- 下方：快照列表 -->
    <div class="card">
      <div class="snap-head">
        <div class="snap-title"><el-icon><Files /></el-icon>备份快照列表</div>
        <div class="filters">
          <el-select v-model="trigger" size="small" placeholder="触发类型" clearable style="width:130px" @change="reload">
            <el-option label="手动" value="manual" />
            <el-option label="自动" value="auto" />
            <el-option label="APP" value="app" />
          </el-select>
          <el-button size="small" @click="reload">
            <el-icon><Refresh /></el-icon>刷新
          </el-button>
        </div>
      </div>

      <el-table :data="list" v-loading="loading" border stripe size="small">
        <el-table-column label="ID" prop="id" width="70" align="center" />
        <el-table-column label="类型" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.trigger === 'auto'" size="small" type="info" effect="light">自动</el-tag>
            <el-tag v-else-if="row.trigger === 'app'" size="small" type="primary" effect="light">APP</el-tag>
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
        <el-table-column label="过期时间" width="170" align="center">
          <template #default="{ row }">{{ row.expiry_time || '—' }}</template>
        </el-table-column>
        <el-table-column label="备注" prop="note" min-width="180" show-overflow-tooltip />
        <el-table-column label="操作" width="260" fixed="right" align="center" class-name="bk-op-col">
          <template #default="{ row }">
            <div class="bk-op-cell">
              <el-button size="small" class="bk-dl" @click="onDownload(row)">下载</el-button>
              <el-popconfirm title="确定从该快照恢复吗？当前数据将被覆盖（不可撤销）。" @confirm="onRestoreFrom(row)">
                <template #reference>
                  <el-button size="small" class="bk-restore">恢复</el-button>
                </template>
              </el-popconfirm>
              <el-popconfirm title="确定删除该快照吗？文件将从服务端永久删除。" @confirm="onDelete(row)">
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
        layout="total, prev, pager, next, jumper"
        :total="total"
        :page-size="pageSize"
        :current-page="page"
        style="margin-top:12px; justify-content:flex-end; display:flex"
        @current-change="p => { page = p; reload() }"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Download, Upload, Files, Refresh } from '@element-plus/icons-vue'
import {
  listBackupSnapshots,
  createBackupSnapshot,
  deleteBackupSnapshot,
  downloadBackupSnapshot,
  restoreFromSnapshot,
  exportBackup,
  restoreBackup,
} from '@/api'
import { downloadBlob } from '@/utils/file'

const loading = ref(false)
const creating = ref(false)
const downloading = ref(false)
const restoringUpload = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const trigger = ref('')

async function reload() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize }
    if (trigger.value) params.trigger = trigger.value
    const r = await listBackupSnapshots(params)
    list.value = r.data.list || []
    total.value = Number(r.data.total || 0)
  } finally { loading.value = false }
}

async function onCreate() {
  creating.value = true
  try {
    await createBackupSnapshot('manual', 'Web 手动生成')
    ElMessage.success('快照生成成功')
    reload()
  } catch (e) {} finally { creating.value = false }
}

async function onExport() {
  downloading.value = true
  try {
    const res = await exportBackup()
    downloadBlob(res.data, res.headers['content-disposition'])
    ElMessage.success('已触发下载')
    reload()
  } catch (e) {} finally { downloading.value = false }
}

async function onDownload(row) {
  try {
    const r = await downloadBackupSnapshot(row.id)
    downloadBlob(r.data, r.headers['content-disposition'] || `attachment; filename="snapshot_${row.id}.antrack"`)
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
    // 恢复后可能 token/权限环境变化，给用户提示 + 延迟刷新
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
  const ok = /\.(antrack|zip)$/i.test(file.name || '')
  if (!ok) ElMessage.warning('仅支持 .antrack 或 .zip 文件')
  return ok
}

async function handleUploadRestore(opts) {
  const file = opts.file
  try {
    await ElMessageBox.confirm(
      `即将从文件「${file.name}」恢复备份，当前数据将被覆盖，确认继续吗？`,
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
    const r = await restoreBackup(fd, (e) => {
    })
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
.split-card {
  display: grid;
  grid-template-columns: 1fr 1px 1fr;
  gap: 16px;
}
@media (max-width: 900px) {
  .split-card { grid-template-columns: 1fr; }
  .col-divider { display: none; }
}
.col-divider { background: var(--border); }
.col-title {
  margin: 0 0 6px; font-size: 14px; font-weight: 700; color: var(--text-main);
  display: flex; align-items: center; gap: 6px;
}
.hint {
  color: var(--text-sub); font-size: 12px; line-height: 1.7; margin: 0 0 10px;
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

/* 操作按钮：实心风格，不透明 */
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

/* 固定列底色不随行变化，防止滚动穿透 */
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
