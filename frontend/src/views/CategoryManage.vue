<template>
  <div>
    <div class="page-card">
      <div class="page-title">
        <el-icon><Files /></el-icon>二级分类管理
        <div style="margin-left:auto" class="toolbar-right">
          <el-button type="primary" size="small" @click="onAddLevel1"><el-icon><Plus /></el-icon>新增一级分类</el-button>
          <el-button type="primary" size="small" :disabled="!currentNode || currentNode.level !== 1" @click="onAddLevel2">新增二级分类</el-button>
        </div>
      </div>
      <el-row :gutter="16">
        <el-col :xs="24" :md="10">
          <div class="tree-box">
            <el-input v-model="filterText" placeholder="搜索分类" clearable size="small" style="margin-bottom:10px" />
            <el-tree
              ref="treeRef"
              :data="treeData"
              :props="{ label: 'name', children: 'children' }"
              node-key="id"
              highlight-current
              :expand-on-click-node="false"
              :filter-node-method="filterNode"
              @node-click="onNodeClick"
            >
              <template #default="{ node, data }">
                <span class="tree-node">
                  <span class="node-label">{{ node.label }}</span>
                  <span class="node-ops">
                    <el-button link type="primary" size="small" class="node-btn node-edit" @click.stop="onEdit(data)">编辑</el-button>
                    <el-button link type="danger" size="small" class="node-btn node-del" @click.stop="onDelete(data)">删除</el-button>
                  </span>
                </span>
              </template>
            </el-tree>
          </div>
        </el-col>
        <el-col :xs="24" :md="14">
          <div class="info-box">
            <div v-if="currentNode">
              <h3 class="cur-title">当前选中：{{ currentNode.name }}</h3>
              <div class="info-row"><span class="lbl">层级：</span>{{ currentNode.level === 1 ? '一级分类' : '二级分类' }}</div>
              <div class="info-row"><span class="lbl">排序：</span>{{ currentNode.sort }}</div>
              <div class="info-row"><span class="lbl">子分类数：</span>{{ childCount(currentNode) }}</div>
              <div class="info-row"><span class="lbl">绑定物料数：</span>{{ bindCount(currentNode) }}</div>
            </div>
            <div v-else class="empty">请选择左侧分类查看详情</div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="420px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="所属层级">
          <el-tag>{{ form.level === 1 ? '一级分类' : '二级分类' }}</el-tag>
          <span v-if="form.level === 2 && parentName" class="sub" style="margin-left:10px">父级：{{ parentName }}</span>
        </el-form-item>
        <el-form-item label="分类名称" prop="name">
          <el-input v-model="form.name" maxlength="100" placeholder="请输入分类名称" />
        </el-form-item>
        <el-form-item label="排序权重" prop="sort">
          <el-input-number v-model="form.sort" :min="0" :step="1" controls-position="right" style="width:100%" />
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
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Files } from '@element-plus/icons-vue'
import { getCategoryTree, saveCategory, updateCategory, deleteCategory } from '@/api'

const treeRef = ref()
const treeData = ref([])
const currentNode = ref(null)
const filterText = ref('')
const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref()
const isEdit = ref(false)
const parentName = ref('')

const form = reactive({ id: null, name: '', parent_id: 0, level: 1, sort: 0 })
const rules = { name: [{ required: true, message: '请输入分类名称', trigger: 'blur' }] }

const dialogTitle = computed(() => {
  if (isEdit.value) return '编辑分类'
  return form.level === 1 ? '新增一级分类' : '新增二级分类'
})

function filterNode(value, data) {
  if (!value) return true
  return data.name.includes(value)
}
watch(filterText, v => treeRef.value && treeRef.value.filter(v))

async function loadData() {
  const res = await getCategoryTree()
  treeData.value = res.data
}

function onNodeClick(data) { currentNode.value = data }

function onAddLevel1() {
  isEdit.value = false
  Object.assign(form, { id: null, name: '', parent_id: 0, level: 1, sort: 0 })
  parentName.value = ''
  dialogVisible.value = true
}

function onAddLevel2() {
  if (!currentNode.value || currentNode.value.level !== 1) {
    ElMessage.warning('请先选择一个一级分类'); return
  }
  isEdit.value = false
  Object.assign(form, { id: null, name: '', parent_id: currentNode.value.id, level: 2, sort: 0 })
  parentName.value = currentNode.value.name
  dialogVisible.value = true
}

function onEdit(data) {
  isEdit.value = true
  Object.assign(form, { id: data.id, name: data.name, parent_id: data.parent_id, level: data.level, sort: data.sort })
  const parent = findNode(treeData.value, data.parent_id)
  parentName.value = parent ? parent.name : ''
  dialogVisible.value = true
}

function findNode(nodes, id) {
  for (const n of nodes) {
    if (n.id === id) return n
    if (n.children) {
      const r = findNode(n.children, id)
      if (r) return r
    }
  }
  return null
}

function childCount(node) {
  if (node.level === 1) return (node.children || []).length
  return 0
}

function bindCount(node) {
  return Number(node.material_count ?? 0)
}

function onDelete(data) {
  ElMessageBox.confirm(`确定删除分类「${data.name}」吗？`, '删除确认', { type: 'warning' }).then(async () => {
    await deleteCategory(data.id)
    ElMessage.success('删除成功')
    if (currentNode.value && currentNode.value.id === data.id) currentNode.value = null
    loadData()
  }).catch(() => {})
}

function onSave() {
  formRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      const payload = { name: form.name, parent_id: form.parent_id, level: form.level, sort: form.sort }
      if (isEdit.value) {
        await updateCategory(form.id, payload)
        ElMessage.success('分类修改成功')
      } else {
        await saveCategory(payload)
        ElMessage.success('分类新增成功')
      }
      dialogVisible.value = false
      loadData()
    } catch (e) {} finally { saving.value = false }
  })
}

onMounted(loadData)
</script>

<style scoped>
.toolbar-right { display: flex; gap: 8px; }
.tip { color: var(--text-sub); font-size: 12px; margin-bottom: 12px; }
.tree-box { background: var(--card-2); border-radius: 8px; padding: 12px; min-height: 360px; }
.tree-node { display: flex; align-items: center; justify-content: space-between; width: 100%; padding-right: 8px; }

.node-label {
  color: var(--text-sub) !important;
  transition: color .15s ease;
}
:deep(.el-tree-node > .el-tree-node__content:hover) {
  background: color-mix(in srgb, var(--primary) 8%, transparent) !important;
}
:deep(.el-tree-node > .el-tree-node__content:hover .node-label) {
  color: var(--primary) !important;
}
:deep(.el-tree-node.is-current > .el-tree-node__content) {
  background: color-mix(in srgb, var(--primary) 12%, transparent) !important;
}
:deep(.el-tree-node.is-current > .el-tree-node__content .node-label) {
  color: var(--primary) !important;
}
.node-ops { visibility: hidden; display: flex; gap: 4px; align-items: center; }
.tree-node:hover .node-ops { visibility: visible; }

.node-edit { background: color-mix(in srgb, var(--primary) 22%, transparent) !important; border-color: color-mix(in srgb, var(--primary) 32%, transparent) !important; }
.node-del  { background: color-mix(in srgb, var(--danger) 22%, transparent)  !important; border-color: color-mix(in srgb, var(--danger) 32%, transparent)  !important; }

.info-box { background: var(--card-2); border-radius: 8px; padding: 16px; min-height: 360px; }
.cur-title { margin: 0 0 12px; color: var(--primary); font-size: 16px; }
.info-row { line-height: 2; color: var(--text-main); }
.info-row .lbl { color: var(--text-sub); display: inline-block; width: 90px; }
.empty { color: var(--text-sub); text-align: center; padding-top: 60px; }
.sub { color: var(--text-sub); font-size: 12px; }
@media (max-width: 768px) { .node-ops { visibility: visible; } }
</style>
