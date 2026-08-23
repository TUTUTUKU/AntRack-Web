<template>
  <el-dialog v-model="show" title="物料入库" width="460px" @close="onClose">
    <div class="mat-info" v-if="material">
      <span class="lbl">物料：</span><strong>{{ material.name }}</strong>
      <span class="sub">当前库存 {{ fmtNum(material.stock_total_num) }} · 加权单价 {{ fmtPrice(material.stock_avg_price) }}</span>
    </div>
    <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" style="margin-top:14px">
      <el-form-item label="入库数量" prop="in_num">
        <el-input-number v-model="form.in_num" :min="1" :precision="0" :step="1" controls-position="right" style="width:100%" />
      </el-form-item>
      <el-form-item label="本次实付总价" prop="pay_total">
        <el-input-number v-model="form.pay_total" :min="0" :precision="2" :step="1" controls-position="right" style="width:100%" />
        <span class="hint">元（含优惠券、满减后的券后实付金额）</span>
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="500" show-word-limit placeholder="选填" />
      </el-form-item>
      <el-form-item label="入库后预览">
        <div class="preview">
          <div>新总库存：<b>{{ fmtNum(preview.newNum) }}</b></div>
          <div>新总成本：<b>{{ fmtPrice(preview.newCost) }}</b> 元</div>
          <div class="hl">新加权单价：<b>{{ fmtPrice(preview.newAvg) }}</b> 元</div>
        </div>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="show = false">取消</el-button>
      <el-button type="primary" :loading="loading" @click="onSubmit">确认入库</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { stockIn } from '@/api'
import { fmtNum, fmtPrice } from '@/utils/format'

const props = defineProps({ visible: Boolean, material: Object })
const emit = defineEmits(['update:visible', 'success'])

const show = computed({
  get: () => props.visible,
  set: v => emit('update:visible', v)
})
const formRef = ref()
const loading = ref(false)
const form = reactive({ in_num: 1, pay_total: 0, remark: '' })
const rules = {
  in_num: [{ required: true, message: '请输入入库数量', trigger: 'blur' }],
  pay_total: [{ required: true, message: '请输入实付总价', trigger: 'blur' }]
}

// 实时预览：前端仅展示计算（最终以后端为准）
const preview = computed(() => {
  const oldNum = props.material?.stock_total_num || 0
  const oldCost = props.material?.stock_total_cost || 0
  const addNum = Number(form.in_num) || 0
  const addCost = Number(form.pay_total) || 0
  const newNum = +(oldNum + addNum).toFixed(6)
  const newCost = +(oldCost + addCost).toFixed(6)
  const newAvg = newNum > 0 ? +(newCost / newNum).toFixed(6) : 0
  return { newNum, newCost, newAvg }
})

watch(() => props.visible, v => { if (v) { form.in_num = 1; form.pay_total = 0; form.remark = '' } })

function onClose() { emit('update:visible', false) }

function onSubmit() {
  formRef.value.validate(async (valid) => {
    if (!valid) return
    if (form.in_num <= 0) { ElMessage.warning('入库数量必须大于0'); return }
    if (form.pay_total < 0) { ElMessage.warning('实付总价不能为负数'); return }
    loading.value = true
    try {
      const res = await stockIn({
        material_id: props.material.id,
        in_num: form.in_num,
        pay_total: form.pay_total,
        remark: form.remark
      })
      ElMessage.success(`入库成功，最新加权单价 ${fmtPrice(res.data.new_avg_price)}`)
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
.hint { color: var(--text-sub); font-size: 12px; }
.preview { background: var(--card-2); border-radius: 8px; padding: 10px 14px; line-height: 2; width: 100%; }
.preview .hl { color: var(--primary); }
</style>
