<template>
  <el-dialog v-model="show" title="临时出库" width="460px" @close="onClose">
    <div class="mat-info" v-if="material">
      <span class="lbl">物料：</span><strong>{{ material.name }}</strong>
      <span class="sub">实际库存 {{ fmtNum(material.stock_total_num) }} · 加权单价 {{ fmtPrice(material.stock_avg_price) }}（出库不变）</span>
    </div>
    <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" style="margin-top:14px">
      <el-form-item label="出库数量" prop="out_num">
        <el-input-number v-model="form.out_num" :min="1" :max="maxOut" :precision="0" :step="1" controls-position="right" style="width:100%" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="500" show-word-limit placeholder="选填" />
      </el-form-item>
      <el-form-item label="出库预览">
        <div class="preview">
          <div>本次扣减成本：<b>{{ fmtPrice(cutCost) }}</b> 元</div>
          <div>剩余库存：<b>{{ fmtNum(remainNum) }}</b></div>
          <div class="hl">出库后加权单价：<b>{{ fmtPrice(material?.stock_avg_price) }}</b>（保持不变）</div>
        </div>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="show = false">取消</el-button>
      <el-button type="warning" :loading="loading" @click="onSubmit">确认出库</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { stockOutTemp } from '@/api'
import { fmtNum, fmtPrice } from '@/utils/format'

const props = defineProps({ visible: Boolean, material: Object })
const emit = defineEmits(['update:visible', 'success'])

const show = computed({
  get: () => props.visible,
  set: v => emit('update:visible', v)
})
const formRef = ref()
const loading = ref(false)
const form = reactive({ out_num: 1, remark: '' })
const maxOut = computed(() => props.material?.stock_total_num || 0)
const rules = {
  out_num: [{ required: true, message: '请输入出库数量', trigger: 'blur' }]
}

const cutCost = computed(() => {
  const n = Number(form.out_num) || 0
  const avg = props.material?.stock_avg_price || 0
  return +(n * avg).toFixed(6)
})
const remainNum = computed(() => +(((props.material?.stock_total_num || 0) - (Number(form.out_num) || 0)).toFixed(6)))

watch(() => props.visible, v => { if (v) { form.out_num = 1; form.remark = '' } })

function onClose() { emit('update:visible', false) }

function onSubmit() {
  formRef.value.validate(async (valid) => {
    if (!valid) return
    if (form.out_num <= 0) { ElMessage.warning('出库数量必须大于0'); return }
    if (form.out_num > props.material.stock_total_num) {
      ElMessage.warning(`出库数量不能超过实际库存 ${fmtNum(props.material.stock_total_num)}`); return
    }
    loading.value = true
    try {
      await stockOutTemp({ material_id: props.material.id, out_num: form.out_num, remark: form.remark })
      ElMessage.success('临时出库成功')
      emit('success')
      show.value = false
    } catch (e) {} finally { loading.value = false }
  })
}
</script>

<style scoped>
.mat-info { padding: 10px 14px; background: var(--card-2); border-radius: 8px; }
.mat-info .lbl { color: var(--text-sub); }
.mat-info .sub { display: block; color: var(--text-sub); font-size: 12px; margin-top: 4px; }
.preview { background: var(--card-2); border-radius: 8px; padding: 10px 14px; line-height: 2; width: 100%; }
.preview .hl { color: var(--warning); }
</style>
