<template>
  <div class="ab-root">
    <!-- 总开关 + 手动触发 -->
    <div class="card">
      <div class="switch-row">
        <div class="switch-left">
          <el-icon size="18" class="switch-icon"><Timer /></el-icon>
          <div>
            <div class="switch-label">启用自动备份</div>
            <div class="switch-hint">关闭后，定时策略不再触发；手动备份不受影响</div>
          </div>
        </div>
        <el-switch v-model="form.enabled" @change="save" />
      </div>
      <el-divider />
      <div class="manual-row">
        <el-button type="primary" plain :loading="runningNow" @click="onRunNow">
          <el-icon><VideoPlay /></el-icon>立即执行一次备份
        </el-button>
        <el-tag v-if="form.last_run_at" size="small" :type="form.last_run_status === 'success' ? 'success' : 'danger'" effect="light">
          上次：{{ form.last_run_at }} · {{ form.last_run_status === 'success' ? '成功' : '失败' }}
        </el-tag>
      </div>
      <p v-if="form.last_run_msg" class="last-msg">{{ form.last_run_msg }}</p>
    </div>

    <!-- 时间策略 -->
    <div class="card">
      <h4 class="section-title"><el-icon><Clock /></el-icon>备份时间策略</h4>
      <el-radio-group v-model="form.strategy" @change="onStrategyChange" class="strategy-group">
        <el-radio value="interval">间隔周期</el-radio>
        <el-radio value="daily">每日定时</el-radio>
        <el-radio value="weekly">每周定时</el-radio>
        <el-radio value="monthly">每月定时</el-radio>
      </el-radio-group>

      <!-- 间隔周期 -->
      <div v-if="form.strategy === 'interval'" class="strategy-form">
        <span>每</span>
        <el-input-number v-model="form.interval_value" :min="form.interval_unit === 'minutes' ? 10 : 1" :max="9999" size="small" controls-position="right" @change="save" />
        <el-select v-model="form.interval_unit" size="small" style="width:100px" @change="onUnitChange">
          <el-option label="分钟" value="minutes" />
          <el-option label="小时" value="hours" />
        </el-select>
        <span>执行一次（最小间隔 10 分钟）</span>
      </div>

      <!-- 每日定时 -->
      <div v-if="form.strategy === 'daily'" class="strategy-form">
        <span>每天</span>
        <el-input-number v-model="form.daily_hour" :min="0" :max="23" size="small" controls-position="right" @change="save" /> 时
        <el-input-number v-model="form.daily_minute" :min="0" :max="59" size="small" controls-position="right" @change="save" /> 分执行
      </div>

      <!-- 每周定时 -->
      <div v-if="form.strategy === 'weekly'" class="strategy-form">
        <div class="weekday-row">
          <el-checkbox-group v-model="weeklyDaysArr" @change="onWeekDaysChange">
            <el-checkbox v-for="(label, idx) in weekdayLabels" :key="idx" :value="String(idx)">{{ label }}</el-checkbox>
          </el-checkbox-group>
        </div>
        <div class="weekday-time">
          <el-input-number v-model="form.weekly_hour" :min="0" :max="23" size="small" controls-position="right" @change="save" /> 时
          <el-input-number v-model="form.weekly_minute" :min="0" :max="59" size="small" controls-position="right" @change="save" /> 分执行
        </div>
      </div>

      <!-- 每月定时 -->
      <div v-if="form.strategy === 'monthly'" class="strategy-form">
        <span>每月</span>
        <el-input-number v-model="form.monthly_day" :min="1" :max="28" size="small" controls-position="right" @change="save" /> 日
        <el-input-number v-model="form.monthly_hour" :min="0" :max="23" size="small" controls-position="right" @change="save" /> 时
        <el-input-number v-model="form.monthly_minute" :min="0" :max="59" size="small" controls-position="right" @change="save" /> 分执行
        <span class="hint-inline">（日期限 1-28 日）</span>
      </div>
    </div>

    <!-- 保留策略 + 存储路径 + 并发 -->
    <div class="card">
      <h4 class="section-title"><el-icon><Setting /></el-icon>备份配置</h4>

      <div class="cfg-row">
        <span class="cfg-label">保留策略</span>
        <el-radio-group v-model="form.retention_mode" @change="save" size="small">
          <el-radio-button value="count">保留 N 个</el-radio-button>
          <el-radio-button value="days">保留 N 天</el-radio-button>
        </el-radio-group>
        <el-input-number v-if="form.retention_mode === 'count'" v-model="form.retention_count" :min="1" :max="999" size="small" controls-position="right" @change="save" />
        <el-input-number v-else v-model="form.retention_days" :min="1" :max="3650" size="small" controls-position="right" @change="save" />
        <span class="hint-inline">超出自动清理旧备份</span>
      </div>

      <div class="cfg-row">
        <span class="cfg-label">存储路径</span>
        <el-input v-model="form.storage_path" size="small" style="width:260px" @change="save" />
        <span class="hint-inline">服务器本地目录（相对项目根）</span>
      </div>

      <div class="cfg-row">
        <span class="cfg-label">禁止并发</span>
        <el-switch v-model="form.forbid_concurrent" @change="save" />
        <span class="hint-inline">上次备份未完成时，不触发下一次</span>
      </div>
    </div>

    <!-- 提示 -->
    <div class="card hint-card">
      <el-icon color="var(--warning)"><Warning /></el-icon>
      <span>备份属于 IO 密集任务，建议在业务低峰期执行。所有时间均以服务器时区为准，修改配置即时生效，无需重启服务。</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Timer, Clock, Setting, Warning, VideoPlay } from '@element-plus/icons-vue'
import { getAutoBackupConfig, updateAutoBackupConfig, runAutoBackupNow } from '@/api'

const loading = ref(false)
const runningNow = ref(false)
const form = ref({
  enabled: true,
  strategy: 'weekly',
  interval_value: 60,
  interval_unit: 'minutes',
  daily_hour: 2,
  daily_minute: 0,
  weekly_days: '0',
  weekly_hour: 2,
  weekly_minute: 0,
  monthly_day: 1,
  monthly_hour: 2,
  monthly_minute: 0,
  cron_expr: '',
  retention_mode: 'count',
  retention_count: 10,
  retention_days: 60,
  storage_path: 'data/backups',
  forbid_concurrent: true,
  last_run_at: '',
  last_run_status: '',
  last_run_msg: '',
})

const weekdayLabels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const weeklyDaysArr = ref([])

async function loadConfig() {
  loading.value = true
  try {
    const r = await getAutoBackupConfig()
    Object.assign(form.value, r.data)
    weeklyDaysArr.value = (form.value.weekly_days || '').split(',').filter(d => d.trim())
  } finally { loading.value = false }
}

function onStrategyChange() { save() }
function onUnitChange() {
  if (form.value.interval_unit === 'minutes' && form.value.interval_value < 10) {
    form.value.interval_value = 10
  }
  save()
}
function onWeekDaysChange(val) {
  form.value.weekly_days = val.join(',')
  save()
}

let saveTimer = null
function save() {
  clearTimeout(saveTimer)
  saveTimer = setTimeout(async () => {
    try {
      const r = await updateAutoBackupConfig(form.value)
      if (r.data) Object.assign(form.value, r.data)
      ElMessage.success('配置已保存，即时生效')
    } catch (e) {
      ElMessage.error('保存失败')
    }
  }, 300)
}

async function onRunNow() {
  runningNow.value = true
  try {
    const r = await runAutoBackupNow()
    ElMessage.success(r.msg || '备份执行成功')
    loadConfig()
  } catch (e) {
    ElMessage.error('备份执行失败')
  } finally { runningNow.value = false }
}

onMounted(() => loadConfig())
</script>

<style scoped>
.ab-root { display: flex; flex-direction: column; gap: 14px; }
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 18px;
}
.section-title {
  font-weight: 700; font-size: 14px; margin: 0 0 12px;
  display: flex; align-items: center; gap: 6px;
}
.switch-row {
  display: flex; align-items: center; justify-content: space-between;
}
.switch-left { display: flex; align-items: center; gap: 10px; }
.switch-icon { color: var(--primary); }
.switch-label { font-weight: 700; font-size: 14px; }
.switch-hint { font-size: 12px; color: var(--text-sub); }
.manual-row { display: flex; align-items: center; gap: 10px; }
.last-msg { font-size: 12px; color: var(--text-sub); margin: 8px 0 0; padding: 6px 10px; border-radius: 6px; background: color-mix(in srgb, var(--primary) 6%, transparent); }

.strategy-group { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.strategy-form {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  padding: 12px 14px; border-radius: 8px;
  background: color-mix(in srgb, var(--primary) 5%, transparent);
  border: 1px solid color-mix(in srgb, var(--primary) 12%, transparent);
  font-size: 13px;
}
.weekday-row { margin-bottom: 8px; }
.hint-inline { font-size: 12px; color: var(--text-sub); }

.cfg-row {
  display: flex; align-items: center; gap: 10px; margin-bottom: 12px; flex-wrap: wrap;
}
.cfg-label { font-size: 13px; font-weight: 600; min-width: 80px; }

.hint-card {
  display: flex; align-items: center; gap: 8px;
  font-size: 12px; color: var(--text-sub); line-height: 1.6;
  background: color-mix(in srgb, var(--warning) 6%, transparent);
  border-color: color-mix(in srgb, var(--warning) 16%, transparent);
}

:deep(.el-divider--horizontal) { margin: 12px 0; }
:deep(.el-input-number--small) { width: 110px; }
</style>
