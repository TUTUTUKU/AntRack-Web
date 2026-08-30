<template>
  <div class="settings-root">
    <div class="page-card settings-layout">
      <aside class="settings-menu">
        <div class="menu-title">
          <el-icon><Setting /></el-icon>
          <span>系统设置</span>
          <el-tag size="small" type="primary" effect="light" class="ver-tag">V{{ version }}</el-tag>
        </div>

        <!-- 基础设置 -->
        <div class="menu-l1">
          <div class="l1-title" :class="{ active: activeL1 === 'basic' }" @click="activeL1 = 'basic'">
            <el-icon><Tools /></el-icon>基础设置
          </div>
          <div v-show="activeL1 === 'basic'" class="l2-list">
            <div class="l2-item" :class="{ active: activeL2 === 'account' }" @click="activeL2 = 'account'">
              <el-icon><Lock /></el-icon>修改密码
            </div>
            <div class="l2-item" :class="{ active: activeL2 === 'theme' }" @click="activeL2 = 'theme'">
              <el-icon><Brush /></el-icon>主题切换
            </div>
          </div>
        </div>

        <!-- 高级设置 -->
        <div class="menu-l1">
          <div class="l1-title" :class="{ active: activeL1 === 'data' }" @click="activeL1 = 'data'">
            <el-icon><Coin /></el-icon>高级设置
            <el-badge v-if="pendingConflict > 0" :value="pendingConflict" class="badge-conflict" max="99" />
          </div>
          <div v-show="activeL1 === 'data'" class="l2-list">
            <div class="l2-item" :class="{ active: activeL2 === 'conflict-prefer' }" @click="activeL2 = 'conflict-prefer'">
              <el-icon><Switch /></el-icon>冲突处理偏好
            </div>
            <div class="l2-item" :class="{ active: activeL2 === 'conflict-panel' }" @click="activeL2 = 'conflict-panel'">
              <el-icon><Warning /></el-icon>冲突处理
              <el-tag v-if="pendingConflict > 0" size="small" type="danger" effect="dark" class="l2-badge">{{ pendingConflict }}</el-tag>
            </div>
            <div class="l2-item" :class="{ active: activeL2 === 'oplogs' }" @click="activeL2 = 'oplogs'">
              <el-icon><Tickets /></el-icon>操作日志
            </div>
            <div class="l2-item" :class="{ active: activeL2 === 'backup' }" @click="activeL2 = 'backup'">
              <el-icon><Files /></el-icon>备份与恢复
            </div>
            <div class="l2-item" :class="{ active: activeL2 === 'auto-backup' }" @click="activeL2 = 'auto-backup'">
              <el-icon><Timer /></el-icon>自动备份
            </div>
          </div>
        </div>

        <!-- 系统信息 -->
        <div class="menu-l1">
          <div class="l1-title" :class="{ active: activeL1 === 'system-info' }" @click="activeL1 = 'system-info'; activeL2 = 'revision'">
            <el-icon><Cpu /></el-icon>系统信息
          </div>
        </div>
      </aside>

      <section class="settings-content">
        <!-- 修改密码 -->
        <template v-if="activeL2 === 'account'">
          <h3 class="sub-title"><el-icon><Lock /></el-icon>修改密码</h3>
          <div class="pwd-card">
            <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
              <el-form-item label="原密码" prop="old_password">
                <el-input v-model="form.old_password" type="password" show-password placeholder="请输入原密码" />
              </el-form-item>
              <el-form-item label="新密码" prop="new_password">
                <el-input v-model="form.new_password" type="password" show-password placeholder="至少6位" />
              </el-form-item>
              <el-form-item label="确认新密码" prop="confirm">
                <el-input v-model="form.confirm" type="password" show-password placeholder="再次输入新密码" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="loading" @click="onSubmitPwd">确认修改</el-button>
              </el-form-item>
            </el-form>
          </div>
        </template>

        <!-- 主题切换 -->
        <template v-else-if="activeL2 === 'theme'">
          <h3 class="sub-title"><el-icon><Brush /></el-icon>主题切换</h3>
          <div class="theme-preview-grid">
            <div v-for="t in themeList" :key="t.key" class="theme-card" :class="{ active: t.key === currentTheme }" @click="onPickTheme(t.key)">
              <div class="theme-card-preview" :style="{ background: t.vars['--bg'] }">
                <div class="tp-sidebar" :style="{ background: t.vars['--sidebar-bg'] }">
                  <i class="tp-logo" :style="{ background: t.vars['--primary'] }"></i>
                  <i class="tp-menu-item"></i>
                  <i class="tp-menu-item" :style="{ background: t.vars['--primary'], opacity: 0.85 }"></i>
                  <i class="tp-menu-item"></i>
                </div>
                <div class="tp-main">
                  <div class="tp-topbar" :style="{ background: t.vars['--card'], borderBottom: `1px solid ${t.vars['--border']}` }">
                    <i class="tp-dot" :style="{ background: t.vars['--primary'] }"></i>
                  </div>
                  <div class="tp-body">
                    <div class="tp-card" :style="{ background: t.vars['--card'], border: `1px solid ${t.vars['--border']}` }">
                      <i class="tp-bar" :style="{ background: t.vars['--primary'], width: '40%' }"></i>
                      <i class="tp-bar" :style="{ background: t.vars['--secondary'], width: '70%' }"></i>
                      <i class="tp-bar" :style="{ background: t.vars['--secondary'], width: '55%' }"></i>
                    </div>
                    <div class="tp-card" :style="{ background: t.vars['--card'], border: `1px solid ${t.vars['--border']}` }">
                      <i class="tp-btn" :style="{ background: t.vars['--primary'] }"></i>
                      <i class="tp-btn" :style="{ background: t.vars['--secondary'] }"></i>
                    </div>
                  </div>
                </div>
              </div>
              <div class="theme-card-footer">
                <span class="tc-dot" :style="{ background: t.dot }"></span>
                <span class="tc-name">{{ t.name }}</span>
                <el-icon v-if="t.key === currentTheme" class="tc-check"><CircleCheckFilled /></el-icon>
              </div>
            </div>
          </div>
        </template>

        <!-- 冲突处理偏好 -->
        <template v-else-if="activeL2 === 'conflict-prefer'">
          <h3 class="sub-title"><el-icon><Switch /></el-icon>冲突处理偏好</h3>
          <div class="data-card">
            <p class="hint">离线状态下多端同时编辑产生冲突时，系统会优先选用指定一端的修改作为默认推荐方案。如果选择手动模式，所有冲突项都需要手动确认。</p>
            <el-radio-group v-model="cfg.conflict_prefer" class="pref-group" @change="saveCfg('conflict_prefer')">
              <el-radio label="latest_side" class="pref-item">
                <div class="pref-body">
                  <span class="pref-title">按最新操作时间</span>
                  <span class="pref-desc">自动选取时间戳最新的一端修改作为生效版本</span>
                </div>
                <el-tag size="small" type="success" effect="dark" class="pref-tag">推荐</el-tag>
              </el-radio>
              <el-radio label="prefer_web" class="pref-item">
                <div class="pref-body">
                  <span class="pref-title">优先 Web 端</span>
                  <span class="pref-desc">冲突时默认采用 Web 端的修改结果</span>
                </div>
              </el-radio>
              <el-radio label="prefer_app" class="pref-item">
                <div class="pref-body">
                  <span class="pref-title">优先 APP 端</span>
                  <span class="pref-desc">冲突时默认采用 APP 端的修改结果</span>
                </div>
              </el-radio>
              <el-radio label="manual" class="pref-item">
                <div class="pref-body">
                  <span class="pref-title">全部手动确认</span>
                  <span class="pref-desc">每条冲突都需要人工逐一确认生效版本</span>
                </div>
              </el-radio>
            </el-radio-group>
          </div>
        </template>

        <!-- 冲突处理面板 -->
        <template v-else-if="activeL2 === 'conflict-panel'">
          <h3 class="sub-title"><el-icon><Warning /></el-icon>冲突处理</h3>
          <ConflictPanel @count-updated="n => pendingConflict = n" />
        </template>

        <!-- 操作日志 -->
        <template v-else-if="activeL2 === 'oplogs'">
          <h3 class="sub-title"><el-icon><Tickets /></el-icon>操作日志</h3>
          <OperationLogsPanel />
        </template>

        <!-- 备份与恢复 -->
        <template v-else-if="activeL2 === 'backup'">
          <h3 class="sub-title"><el-icon><Files /></el-icon>备份与恢复</h3>
          <BackupPanel />
        </template>

        <!-- 版本与阶段 -->
        <template v-else-if="activeL2 === 'revision'">
          <h3 class="sub-title"><el-icon><Cpu /></el-icon>系统信息</h3>
          <div class="data-card revision-card">
            <div class="rev-header">
              <span class="rev-name-en">AntRack System</span>
              <span class="rev-name-cn">蚁仓</span>
            </div>
            <div class="rev-row"><span>系统版本</span><b>V{{ version }}</b></div>
            <div class="rev-row"><span>全局阶段校验码</span><b id="gcode-field">{{ revision.global_check_code ?? '-' }}</b></div>
            <div class="rev-row"><span>服务端当前时间</span><b>{{ revision.server_time }}</b></div>
            <el-button type="primary" plain size="small" style="margin-top:12px" @click="loadRevision">
              <el-icon><Refresh /></el-icon> 刷新
            </el-button>
          </div>
          <p class="rev-footer">Developed by TUTUTUKU</p>
        </template>

        <!-- 自动备份 -->
        <template v-else-if="activeL2 === 'auto-backup'">
          <h3 class="sub-title"><el-icon><Timer /></el-icon>自动备份</h3>
          <div class="data-card">
            <p class="hint">每周一白天自动备份。</p>
            <div class="cfg-row">
              <span>启用自动备份</span>
              <el-switch v-model="backupAutoEnable" active-value="1" inactive-value="0" @change="saveCfg('backup_auto_enable')" />
            </div>
            <div class="cfg-row">
              <span>最多保留（份）</span>
              <el-input-number v-model="backupKeepCount" :min="1" :max="50" size="small" controls-position="right" @change="saveCfg('backup_keep_max_count', backupKeepCount)" />
            </div>
            <div class="cfg-row">
              <span>最长保留（天）</span>
              <el-input-number v-model="backupKeepDays" :min="1" :max="365" size="small" controls-position="right" @change="saveCfg('backup_keep_max_days', backupKeepDays)" />
            </div>
          </div>
        </template>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch, nextTick, defineAsyncComponent } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Setting, Lock, Files, Warning, Tickets, Aim, Refresh,
  Brush, Tools, Switch, Coin, Cpu, CircleCheckFilled, Timer
} from '@element-plus/icons-vue'
import {
  changePassword,
  getRevisionInfo,
  getAllUserConfigs,
  setUserConfig,
} from '@/api'
import { themes, getThemeKey, applyTheme } from '@/utils/themes'
import * as ws from '@/utils/ws'

const ConflictPanel = defineAsyncComponent(() => import('@/components/ConflictPanel.vue'))
const OperationLogsPanel = defineAsyncComponent(() => import('@/components/OperationLogsPanel.vue'))
const BackupPanel = defineAsyncComponent(() => import('@/components/BackupPanel.vue'))

const router = useRouter()
const username = localStorage.getItem('username') || 'admin'

const formRef = ref()
const loading = ref(false)
const form = reactive({ old_password: '', new_password: '', confirm: '' })
const validateConfirm = (rule, value, cb) => {
  if (value !== form.new_password) cb(new Error('两次输入的新密码不一致'))
  else cb()
}
const rules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [{ required: true, min: 6, message: '新密码至少6位', trigger: 'blur' }],
  confirm: [{ required: true, validator: validateConfirm, trigger: 'blur' }],
}
async function onSubmitPwd() {
  formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      await changePassword({ old_password: form.old_password, new_password: form.new_password })
      ElMessage.success('密码修改成功，请重新登录')
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      setTimeout(() => router.push('/login'), 800)
    } catch (e) {} finally { loading.value = false }
  })
}

// 菜单状态
const activeL1 = ref('basic')
const activeL2 = ref('account')
watch(activeL1, (v) => {
  if (v === 'basic') activeL2.value = 'account'
  if (v === 'data') activeL2.value = 'conflict-prefer'
  if (v === 'system-info') activeL2.value = 'revision'
})

// 主题
const themeList = themes
const currentTheme = ref(getThemeKey())
function onPickTheme(key) {
  applyTheme(key)
  currentTheme.value = key
  // 持久化到服务端：下次登录 APP/Web 自动生效
  setUserConfig('theme_key', key).catch(() => {})
  ElMessage.success(`已切换主题：${themeList.find(t => t.key === key)?.name || key}`)
}

// 配置
const cfg = reactive({
  conflict_prefer: 'latest_side',
  backup_auto_enable: '1',
  backup_keep_max_count: '10',
  backup_keep_max_days: '60',
  theme_key: 'tech-dark',
})
const backupAutoEnable = ref('1')
const backupKeepCount = ref(10)
const backupKeepDays = ref(60)

async function saveCfg(key, value) {
  try {
    const v = value !== undefined ? value : cfg[key]
    await setUserConfig(key, String(v))
    cfg[key] = String(v)
    if (key === 'backup_auto_enable') backupAutoEnable.value = String(v)
    if (key === 'backup_keep_max_count') backupKeepCount.value = Number(v)
    if (key === 'backup_keep_max_days') backupKeepDays.value = Number(v)
    ElMessage.success('已保存（客户端登录/刷新时自动拉取最新）')
  } catch (e) {}
}

// 版本
const version = ref('1.2.0')
const revision = reactive({ global_check_code: 0, server_time: '', version: '' })
async function loadRevision() {
  try {
    const res = await getRevisionInfo()
    version.value = res.data.version
    revision.global_check_code = res.data.global_check_code
    revision.server_time = res.data.server_time
  } catch (e) {}
}

// 待处理冲突计数
const pendingConflict = ref(0)
async function loadPendingCount() {
  const { listConflicts } = await import('@/api')
  try {
    const r = await listConflicts({ status: 'pending', page: 1, page_size: 1 })
    pendingConflict.value = Number(r.data?.pending_count || 0)
    ws.setPendingCount(pendingConflict.value)
  } catch (e) {}
}

onMounted(async () => {
  // 拉版本 & 冲突数 & 配置
  await loadRevision()
  await loadPendingCount()
  try {
    const res = await getAllUserConfigs()
    const m = res.data || {}
    Object.keys(cfg).forEach(k => { if (m[k] !== undefined) cfg[k] = m[k] })
    backupAutoEnable.value = cfg.backup_auto_enable
    backupKeepCount.value = Number(cfg.backup_keep_max_count)
    backupKeepDays.value = Number(cfg.backup_keep_max_days)
    if (cfg.theme_key && cfg.theme_key !== currentTheme.value) {
      // 服务端配置覆盖本地
      applyTheme(cfg.theme_key)
      currentTheme.value = cfg.theme_key
    }
  } catch (e) {}
  // WS 事件：冲突计数 + 配置变更
  ws.on((evt, data) => {
    if (evt === 'conflict:created') loadPendingCount()
    if (evt === 'conflict:resolved') loadPendingCount()
    if (evt === 'config:changed') {
      getAllUserConfigs().then(r => {
        const m = r.data || {}
        Object.keys(cfg).forEach(k => { if (m[k] !== undefined) cfg[k] = m[k] })
      }).catch(() => {})
    }
    if (evt === 'data:restored') loadRevision()
  })
})
</script>

<style scoped>
.settings-root { }

.settings-layout {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 20px;
}
@media (max-width: 900px) {
  .settings-layout { grid-template-columns: 1fr; }
}

/* 左菜单 */
.settings-menu {
  background: var(--card-2);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 10px;
  height: fit-content;
  position: sticky;
  top: 16px;
}
.menu-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  color: var(--text-main);
  padding: 4px 8px 14px;
  margin-bottom: 8px;
  border-bottom: 1px solid var(--border);
}
.ver-tag { margin-left: auto; }
.menu-l1 { margin-bottom: 10px; }
.l1-title {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 10px;
  font-weight: 600;
  font-size: 13px;
  color: var(--text-main);
  border-radius: 6px;
  cursor: pointer;
  user-select: none;
  position: relative;
}
.l1-title:hover { background: color-mix(in srgb, var(--primary) 6%, transparent); }
.l1-title.active {
  background: color-mix(in srgb, var(--primary) 14%, transparent);
  color: var(--primary);
}
.l2-list { padding: 2px 4px 2px 18px; }
.l2-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  font-size: 13px;
  color: var(--text-sub);
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 2px;
  position: relative;
}
.l2-item:hover { background: color-mix(in srgb, var(--primary) 6%, transparent); color: var(--text-main); }
.l2-item.active {
  background: color-mix(in srgb, var(--primary) 18%, transparent);
  color: var(--primary);
  font-weight: 600;
}
.l2-badge { margin-left: auto; }
.badge-conflict { margin-left: auto; }

/* 右内容 */
.settings-content { min-width: 0; }
.sub-title {
  margin: 0 0 14px;
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 8px;
}
.pwd-card, .data-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 20px 22px;
}
.hint {
  color: var(--text-sub);
  line-height: 1.7;
  font-size: 12px;
  margin: 0 0 14px;
  padding: 10px 12px;
  border-radius: 8px;
  background: color-mix(in srgb, var(--primary) 6%, transparent);
  border: 1px solid color-mix(in srgb, var(--primary) 16%, transparent);
}
.radio-vertical { display: flex; flex-direction: column; gap: 12px; width: fit-content; margin: 0 auto; align-items: flex-start; }
.radio-vertical :deep(.el-radio) { margin-right: 0; }

/* 冲突处理偏好 · 卡片式选项 */
.pref-group {
  display: flex; flex-direction: column; gap: 10px;
  width: 100%; max-width: 520px; margin: 0 auto;
}
.pref-group :deep(.el-radio) {
  margin: 0; height: auto; width: 100%;
  display: flex; align-items: center; gap: 12px;
  background: var(--card-2, var(--card));
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
  cursor: pointer;
  transition: border-color .15s ease, background .15s ease;
  box-sizing: border-box;
}
.pref-group :deep(.el-radio:hover) {
  border-color: color-mix(in srgb, var(--primary) 40%, var(--border)) !important;
  background: color-mix(in srgb, var(--primary) 5%, var(--card-2, var(--card))) !important;
}
.pref-group :deep(.el-radio.is-checked) {
  border-color: var(--primary) !important;
  background: color-mix(in srgb, var(--primary) 8%, var(--card-2, var(--card))) !important;
}
.pref-group :deep(.el-radio__input) {
  flex-shrink: 0;
}
.pref-group :deep(.el-radio__label) {
  padding: 0; flex: 1; display: flex; align-items: center; justify-content: space-between; gap: 8px;
}
.pref-body { display: flex; flex-direction: column; gap: 3px; }
.pref-title { font-size: 14px; font-weight: 600; color: var(--text-main); line-height: 1.4; }
.pref-desc { font-size: 12px; color: var(--text-sub); line-height: 1.5; }
.pref-tag { flex-shrink: 0; }
.cfg-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px dashed var(--border);
  color: var(--text-main);
}
.cfg-row:last-child { border-bottom: none; }
.revision-card .rev-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px dashed var(--border);
  color: var(--text-sub);
}
.revision-card .rev-row:last-child { border-bottom: none; }
.revision-card .rev-row b { color: var(--text-main); font-weight: 600; }
.rev-header { display: flex; align-items: baseline; gap: 8px; justify-content: center; padding-bottom: 12px; margin-bottom: 4px; border-bottom: 1px solid var(--border); }
.rev-name-en { font-size: 18px; font-weight: 700; color: var(--primary); letter-spacing: 0.5px; }
.rev-name-cn { font-size: 15px; font-weight: 600; color: var(--text-sub); }
.rev-footer { text-align: center; margin-top: 16px; font-size: 12px; color: var(--text-sub); }

/* 主题预览网格 */
.theme-preview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
@media (max-width: 992px) { .theme-preview-grid { grid-template-columns: 1fr; } }
.theme-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
  transition: all .2s ease;
  display: flex;
  flex-direction: column;
}
.theme-card:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.08); border-color: var(--primary); }
.theme-card.active { border-color: var(--primary); box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary) 25%, transparent); }
.theme-card-preview { height: 150px; display: flex; overflow: hidden; border-bottom: 1px solid var(--border); }
.tp-sidebar { width: 34px; flex-shrink: 0; padding: 10px 6px; display: flex; flex-direction: column; gap: 6px; }
.tp-logo { width: 14px; height: 14px; border-radius: 4px; margin-bottom: 6px; border: 1px solid rgba(0,0,0,0.15); }
.tp-menu-item { width: 100%; height: 6px; background: rgba(255,255,255,0.18); border-radius: 2px; }
.tp-main { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.tp-topbar { height: 22px; display: flex; align-items: center; padding: 0 8px; flex-shrink: 0; }
.tp-dot { width: 10px; height: 10px; border-radius: 50%; border: 1px solid rgba(0,0,0,0.15); }
.tp-body { flex: 1; padding: 8px; display: flex; flex-direction: column; gap: 6px; }
.tp-card { flex: 1; border-radius: 4px; padding: 6px; display: flex; flex-direction: column; gap: 4px; justify-content: center; }
.tp-card:last-child { flex-direction: row; align-items: center; gap: 6px; }
.tp-bar { height: 5px; border-radius: 2px; }
.tp-btn { width: 26px; height: 10px; border-radius: 3px; border: 1px solid rgba(0,0,0,0.08); }
.theme-card-footer { padding: 10px 12px; display: flex; align-items: center; gap: 8px; }
.tc-dot { width: 10px; height: 10px; border-radius: 50%; border: 1px solid #000; flex-shrink: 0; box-sizing: border-box; }
.tc-name { flex: 1; font-size: 13px; font-weight: 600; color: var(--text-main); }
.tc-check { color: var(--primary); font-size: 16px; }
</style>
