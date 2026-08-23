<template>
  <div>
    <div class="page-card">
      <div class="page-title"><el-icon><Folder /></el-icon>项目列表</div>
      <div class="toolbar">
        <el-button type="primary" @click="onAdd"><el-icon><Plus /></el-icon>新建项目</el-button>
        <el-button @click="onExport"><el-icon><Download /></el-icon>批量导出</el-button>
        <el-input v-model="keyword" placeholder="搜索项目名称" clearable style="width:200px" @keyup.enter="loadData" @clear="loadData" />
        <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width:140px" @change="loadData">
          <el-option label="准备阶段" value="prepare" />
          <el-option label="制作阶段" value="making" />
          <el-option label="已归档" value="finish" />
        </el-select>
        <el-button @click="loadData">查询</el-button>
      </div>
      <el-table :data="list" v-loading="loading" border stripe>
        <el-table-column prop="name" label="项目名称" min-width="160" show-overflow-tooltip />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="create_time" label="创建时间" width="170" />
        <el-table-column prop="intro" label="项目简介" min-width="180" show-overflow-tooltip />
        <el-table-column label="操作" width="280" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <div class="op-cell">
              <el-button link class="op-btn op-detail" size="small" @click="goDetail(row)">进入详情</el-button>
              <el-button link class="op-btn op-export" size="small" @click="onExportOne(row)">导出BOM</el-button>
              <el-button link class="op-btn op-edit" size="small" @click="onEdit(row)">编辑</el-button>
              <el-button link class="op-btn op-del" size="small" @click="onDelete(row)">删除</el-button>
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

    <!-- 新建/编辑项目弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editData ? '编辑项目' : '新建项目'" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="项目名称" prop="name">
          <el-input v-model="form.name" maxlength="120" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="项目简介">
          <el-input v-model="form.intro" type="textarea" :rows="3" maxlength="500" show-word-limit placeholder="选填" />
        </el-form-item>
        <el-form-item label="资料链接">
          <el-input v-model="form.link" maxlength="255" placeholder="选填，如 GitHub / 文档链接" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Download, Folder } from '@element-plus/icons-vue'
import { getProjectList, saveProject, updateProject, deleteProject, exportProject, exportProjectList } from '@/api'
import { downloadBlob } from '@/utils/file'

const router = useRouter()
const route = useRoute()
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const keyword = ref('')
const statusFilter = ref('')

const VALID_STATUS = ['prepare', 'making', 'finish']

onMounted(() => {
  const qs = route.query.status
  if (typeof qs === 'string' && VALID_STATUS.includes(qs)) {
    statusFilter.value = qs
  }
  loadData()
})

watch(statusFilter, (v) => {
  router.replace({ query: { ...route.query, status: v || undefined } })
})
const dialogVisible = ref(false)
const editData = ref(null)
const saving = ref(false)
const formRef = ref()
const form = reactive({ name: '', intro: '', link: '' })
const rules = { name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }] }

function statusText(s) { return { prepare: '准备阶段', making: '制作阶段', finish: '已归档' }[s] || s }
function statusTagType(s) { return { prepare: 'info', making: 'warning', finish: 'success' }[s] || '' }

async function loadData() {
  loading.value = true
  try {
    const res = await getProjectList({ page: page.value, page_size: pageSize.value, keyword: keyword.value, status: statusFilter.value })
    list.value = res.data.list
    total.value = res.data.total
  } finally { loading.value = false }
}

function onAdd() { editData.value = null; Object.assign(form, { name: '', intro: '', link: '' }); dialogVisible.value = true }
function onEdit(row) { editData.value = row; Object.assign(form, { name: row.name, intro: row.intro, link: row.link }); dialogVisible.value = true }

function onSave() {
  formRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      if (editData.value) {
        await updateProject(editData.value.id, form)
        ElMessage.success('项目修改成功')
      } else {
        await saveProject(form)
        ElMessage.success('项目创建成功')
      }
      dialogVisible.value = false
      loadData()
    } catch (e) {} finally { saving.value = false }
  })
}

function goDetail(row) { router.push(`/project/detail/${row.id}`) }

function onDelete(row) {
  ElMessageBox.confirm(`确定删除项目「${row.name}」吗？`, '删除确认', { type: 'warning' }).then(async () => {
    await deleteProject(row.id)
    ElMessage.success('删除成功')
    loadData()
  }).catch(() => {})
}

async function onExport() {
  try {
    const res = await exportProjectList()
    downloadBlob(res.data, res.headers['content-disposition'])
    ElMessage.success('导出成功')
  } catch (e) {}
}
async function onExportOne(row) {
  try {
    const res = await exportProject(row.id)
    downloadBlob(res.data, res.headers['content-disposition'])
    ElMessage.success('导出成功')
  } catch (e) {}
}
</script>

<style scoped>
.op-cell {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 2px;
  flex-wrap: nowrap;
}

.op-detail  { background: color-mix(in srgb, var(--text-sub) 18%, transparent) !important; border-color: color-mix(in srgb, var(--text-sub) 25%, transparent) !important; }
.op-export  { background: color-mix(in srgb, var(--text-sub) 22%, transparent) !important; border-color: color-mix(in srgb, var(--text-sub) 32%, transparent) !important; }
.op-edit    { background: color-mix(in srgb, var(--primary) 18%, transparent)  !important; border-color: color-mix(in srgb, var(--primary) 28%, transparent) !important; }
.op-del     { background: color-mix(in srgb, var(--danger) 22%, transparent)   !important; border-color: color-mix(in srgb, var(--danger) 32%, transparent)  !important; }

:deep(.el-table .op-col) {
  background: var(--card, #242830) !important;
}
:deep(.el-table__row:hover .op-col) {
  background: var(--card-2, #2c313a) !important;
}
:deep(.el-table__row.el-table__row--striped .op-col) {
  background: var(--card-2, #2c313a) !important;
}
:deep(.el-table__row.el-table__row--striped:hover .op-col) {
  background: color-mix(in srgb, var(--primary) 10%, transparent) !important;
}
</style>
