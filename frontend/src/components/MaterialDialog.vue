<template>
  <el-dialog v-model="show" :title="isEdit ? '编辑物料' : '新增物料'" width="560px" @close="onClose">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
      <!-- 第1行 一级分类 | 二级分类 -->
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="一级分类" prop="parent_category_id">
            <el-select v-model="form.parent_category_id" placeholder="请选择" @change="onParentChange" style="width:100%">
              <el-option v-for="c in level1" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="二级分类" prop="category_id">
            <el-select v-model="form.category_id" placeholder="请选择" style="width:100%" :disabled="!form.parent_category_id">
              <el-option v-for="c in level2OfSelected" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <!-- 第2行 物料名称 | 物料编码 -->
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="物料名称" prop="name">
            <el-input v-model="form.name" maxlength="120" placeholder="请输入物料名称" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="物料编码" prop="code">
            <el-input
              v-model="form.code"
              maxlength="64"
              :placeholder="nextCodeHint || '如 AR000001，可自定义'"
            />
          </el-form-item>
        </el-col>
      </el-row>
      <!-- 第3行 规格型号 | 告警阈值 -->
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="规格型号" prop="spec">
            <el-input v-model="form.spec" maxlength="200" placeholder="如 0805/10K/1%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="告警阈值" prop="warn_num">
            <el-input-number v-model="form.warn_num" :min="0" :precision="0" :controls="false" style="width:100%" placeholder="库存低于此值告警" />
          </el-form-item>
        </el-col>
      </el-row>
      <!-- 新增模式：第4行 初始数量 | 单位 ；第5行 初始单价 | 币种 -->
      <template v-if="!isEdit">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="初始数量" prop="init_stock">
              <el-input-number v-model="form.init_stock" :min="0" :precision="0" :controls="false" style="width:100%" placeholder="0" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="计量单位" prop="unit">
              <el-input v-model="form.unit" class="input-center" maxlength="20" placeholder="个/PCS/米/卷" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="初始单价" prop="init_cost">
              <el-input-number v-model="form.init_cost" :min="0" :precision="2" :controls="false" style="width:100%" placeholder="0.00" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="币种" prop="price_unit">
              <el-input v-model="form.price_unit" class="input-center" maxlength="10" placeholder="¥ / $ / 元" />
            </el-form-item>
          </el-col>
        </el-row>
      </template>
      <!-- 编辑模式：第4行 单位 | 币种（都能编辑） -->
      <template v-else>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="计量单位" prop="unit">
              <el-input v-model="form.unit" class="input-center" maxlength="20" placeholder="个/PCS/米/卷" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="币种" prop="price_unit">
              <el-input v-model="form.price_unit" class="input-center" maxlength="10" placeholder="¥ / $ / 元" />
            </el-form-item>
          </el-col>
        </el-row>
      </template>
      <!-- 物料图片 -->
      <el-form-item label="物料图片">
        <el-upload
          class="img-uploader"
          :show-file-list="false"
          :http-request="customUpload"
          accept="image/*"
        >
          <img v-if="form.image" :src="form.image" class="preview-img" />
          <div v-else class="upload-placeholder">
            <el-icon><Plus /></el-icon>
            <span>上传图片</span>
          </div>
        </el-upload>
        <el-button v-if="form.image" link type="primary" size="small" @click="form.image = ''" style="margin-left:10px">移除</el-button>
      </el-form-item>
      <!-- 备注 -->
      <el-form-item label="备注">
        <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="500" show-word-limit placeholder="选填" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="show = false">取消</el-button>
      <el-button type="primary" :loading="loading" @click="onSubmit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getCategoryList, saveMaterial, updateMaterial, uploadImage, nextMaterialCode } from '@/api'

const props = defineProps({ visible: Boolean, data: Object })
const emit = defineEmits(['update:visible', 'success'])

const show = computed({ get: () => props.visible, set: v => emit('update:visible', v) })
const isEdit = computed(() => !!props.data?.id)
const formRef = ref()
const loading = ref(false)
const allCats = ref([])
const nextCodeHint = ref('')

const AUTO_CODE_RE = /^AR\d{6}$/
const form = reactive({
  name: '', code: '', parent_category_id: null, category_id: null,
  spec: '', unit: '个', price_unit: '¥', image: '', warn_num: 0, remark: '',
  init_stock: 0, init_cost: 0
})
const rules = {
  name: [{ required: true, message: '请输入物料名称', trigger: 'blur' }],
  parent_category_id: [{ required: true, message: '请选择一级分类', trigger: 'change' }],
  category_id: [{ required: true, message: '请选择二级分类', trigger: 'change' }]
}

const level1 = computed(() => allCats.value.filter(c => c.level === 1))
const level2OfSelected = computed(() => allCats.value.filter(c => c.level === 2 && c.parent_id === form.parent_category_id))

function onParentChange() { form.category_id = null }

async function loadCats() {
  const res = await getCategoryList()
  allCats.value = res.data
}

// 输入框清空时：placeholder 直接写编号（不写"留空将自动生成"前缀）
async function updateHintIfEmpty() {
  const cur = form.code.trim()
  if (cur) {
    nextCodeHint.value = ''
    return
  }
  try {
    const res = await nextMaterialCode()
    nextCodeHint.value = res.data.code || ''
  } catch (e) { nextCodeHint.value = '' }
}

watch(() => form.code, () => {
  if (!show.value) return
  if (form.code.trim() === '') updateHintIfEmpty()
  else nextCodeHint.value = ''
})

watch(() => props.visible, async v => {
  if (v) {
    await loadCats()
    nextCodeHint.value = ''
    if (props.data?.id) {
      form.name = props.data.name
      form.code = props.data.code || ''
      form.category_id = props.data.category_id
      form.spec = props.data.spec
      // 兼容字段名：优先后端 price_unit；如果误传了 currency 也能用
      form.unit = props.data.unit || '个'
      form.price_unit = props.data.price_unit || props.data.currency || '¥'
      form.image = props.data.image
      form.warn_num = props.data.warn_num
      form.remark = props.data.remark
      const cat = allCats.value.find(c => c.id === props.data.category_id)
      form.parent_category_id = cat ? cat.parent_id : null
      // 编辑模式：原有编码为空 / 自定义（非 ARxxxxxx）→ placeholder 显示下一个自动编号（直接编号）
      const existing = (props.data.code || '').trim()
      if (!existing || !AUTO_CODE_RE.test(existing)) {
        await updateHintIfEmpty()
      }
    } else {
      // 新增模式：预填下一个自动编码，用户可改；不清空就用这个
      Object.assign(form, {
        name: '', code: '', parent_category_id: null, category_id: null,
        spec: '', unit: '个', price_unit: '¥', image: '', warn_num: 0, remark: '',
        init_stock: 0, init_cost: 0
      })
      try {
        const res = await nextMaterialCode()
        form.code = res.data.code || ''
      } catch (e) {}
      if (!form.code) await updateHintIfEmpty()
    }
  }
})

async function customUpload({ file }) {
  const fd = new FormData()
  fd.append('file', file)
  try {
    const res = await uploadImage(fd)
    form.image = res.data.path
    ElMessage.success('图片上传成功')
  } catch (e) {}
}

function onClose() { emit('update:visible', false) }

function onSubmit() {
  formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      const basePayload = {
        name: form.name, category_id: form.category_id, code: form.code,
        spec: form.spec, unit: form.unit, price_unit: form.price_unit,
        image: form.image, warn_num: form.warn_num, remark: form.remark
      }
      if (isEdit.value) {
        await updateMaterial(props.data.id, basePayload)
        ElMessage.success('物料修改成功')
      } else {
        const payload = { ...basePayload, init_stock: form.init_stock, init_cost: form.init_cost }
        await saveMaterial(payload)
        ElMessage.success('物料新增成功')
      }
      emit('success')
      show.value = false
    } catch (e) {} finally { loading.value = false }
  })
}
</script>

<style scoped>
.img-uploader :deep(.el-upload) {
  border: 1px dashed var(--border); border-radius: 8px;
  width: 100px; height: 100px; display: flex; align-items: center; justify-content: center;
  overflow: hidden; background: var(--card-2);
}
.preview-img { width: 100%; height: 100%; object-fit: cover; }
.upload-placeholder { color: var(--text-sub); display: flex; flex-direction: column; align-items: center; gap: 4px; font-size: 12px; }
.input-center :deep(.el-input__wrapper .el-input__inner) {
  text-align: center;
}
</style>
