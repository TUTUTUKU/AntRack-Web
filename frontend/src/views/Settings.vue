<template>
  <div>
    <div class="page-card">
      <div class="page-title"><el-icon><Setting /></el-icon>系统设置</div>
      <el-row :gutter="20">
        <!-- 左：修改密码（上）+ 数据备份与恢复（下） -->
        <el-col :xs="24" :md="12">
          <h3 class="sub-title"><el-icon><Lock /></el-icon>修改管理员密码</h3>
          <div class="pwd-card">
            <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
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
                <el-button type="primary" :loading="loading" @click="onSubmit">确认修改</el-button>
              </el-form-item>
            </el-form>
          </div>

          <h3 class="sub-title backup-section-title"><el-icon><Files /></el-icon>数据备份与恢复</h3>
          <div class="backup-stack">
            <div class="backup-card">
              <div class="backup-icon bg-download">
                <el-icon><Download /></el-icon>
              </div>
              <div class="backup-content">
                <div class="backup-title">一键备份下载</div>
                <div class="backup-desc">导出全部业务数据（物料 / 分类 / 项目 / BOM / 库存流水 + 物料图片），不含账号密码与激活码</div>
              </div>
              <el-button
                type="primary"
                :loading="exporting"
                @click="onExportBackup"
              >
                <el-icon v-if="!exporting"><Download /></el-icon>
                {{ exporting ? '备份中…' : '下载备份' }}
              </el-button>
            </div>

            <div class="backup-card">
              <div class="backup-icon bg-upload">
                <el-icon><Upload /></el-icon>
              </div>
              <div class="backup-content">
                <div class="backup-title">上传备份恢复</div>
                <div class="backup-desc">
                  选择 .antrack 备份文件恢复
                  <span v-if="restoring" class="restore-progress">上传 {{ restoreProgress }}%</span>
                </div>
              </div>
              <el-upload
                class="backup-upload"
                :show-file-list="false"
                :before-upload="handleBackupUpload"
                accept=".antrack,.zip"
                :disabled="restoring"
              >
                <el-button
                  type="primary"
                  :loading="restoring"
                  :disabled="exporting"
                >
                  <el-icon v-if="!restoring"><Upload /></el-icon>
                  {{ restoring ? '恢复中…' : '选择文件恢复' }}
                </el-button>
              </el-upload>
            </div>
          </div>

          <div class="backup-warn">
            <el-icon><WarningFilled /></el-icon>
            <span>恢复会清空当前业务数据（物料 / 分类 / 项目 / BOM / 库存流水）并还原为备份中的数据；账号密码、激活码不受影响。建议恢复前先点一次「下载备份」留存当前状态。</span>
          </div>
        </el-col>

        <!-- 右：主题卡片预览 -->
        <el-col :xs="24" :md="12">
          <h3 class="sub-title"><el-icon><Brush /></el-icon>主题切换</h3>
          <div class="theme-preview-grid">
            <div
              v-for="t in themeList"
              :key="t.key"
              class="theme-card"
              :class="{ active: t.key === currentTheme }"
              @click="onPickTheme(t.key)"
            >
              <div class="theme-card-preview" :style="{ background: t.vars['--bg'] }">
                <!-- 左侧侧边栏预览 -->
                <div class="tp-sidebar" :style="{ background: t.vars['--sidebar-bg'] }">
                  <i class="tp-logo" :style="{ background: t.vars['--primary'] }"></i>
                  <i class="tp-menu-item"></i>
                  <i class="tp-menu-item" :style="{ background: t.vars['--primary'], opacity: 0.85 }"></i>
                  <i class="tp-menu-item"></i>
                </div>
                <!-- 右侧内容区预览 -->
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
        </el-col>
      </el-row>
    </div>

    <div class="page-card info-card">
      <h3 class="sub-title">系统信息</h3>
      <div class="info-row">蚁仓库存管理系统（Ant Rack System）</div>
      <div class="info-row">版本 V1.1.1</div>
      <div class="info-row">TK02-ANS by TUTUTUKU</div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Setting, Brush, Lock, CircleCheckFilled,
  Download, Upload, Files, WarningFilled
} from '@element-plus/icons-vue'
import { changePassword, exportBackup, restoreBackup } from '@/api'
import { themes, getThemeKey, applyTheme } from '@/utils/themes'
import { downloadBlob } from '@/utils/file'

const router = useRouter()
const username = ref(localStorage.getItem('username') || 'admin')
const formRef = ref()
const loading = ref(false)
const form = reactive({ old_password: '', new_password: '', confirm: '' })
const themeList = themes
const currentTheme = ref(getThemeKey())

// 备份/恢复状态
const exporting = ref(false)
const restoring = ref(false)
const restoreProgress = ref(0)

function padZero(n) { return String(n).padStart(2, '0') }
function onPickTheme(key) {
  applyTheme(key)
  currentTheme.value = key
  ElMessage.success(`已切换主题：${themeList.find(t => t.key === key)?.name || key}`)
}

const validateConfirm = (rule, value, cb) => {
  if (value !== form.new_password) cb(new Error('两次输入的新密码不一致'))
  else cb()
}
const rules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [{ required: true, min: 6, message: '新密码至少6位', trigger: 'blur' }],
  confirm: [{ required: true, validator: validateConfirm, trigger: 'blur' }]
}

function onSubmit() {
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

// ========== 一键备份下载 ==========
async function onExportBackup() {
  exporting.value = true
  try {
    const res = await exportBackup()
    downloadBlob(res.data, res.headers['content-disposition'])
    ElMessage.success('备份下载成功')
  } catch (e) {
    // 错误已由 request 拦截器弹窗
  } finally {
    exporting.value = false
  }
}

// ========== 上传备份恢复 ==========
async function handleBackupUpload(file) {
  // 1. 扩展名校验
  const name = (file.name || '').toLowerCase()
  if (!name.endsWith('.antrack') && !name.endsWith('.zip')) {
    ElMessage.error('请上传 .antrack 备份文件')
    return false
  }

  // 2. 二次确认（破坏性操作）
  try {
    await ElMessageBox.confirm(
      '恢复将清空当前所有业务数据（物料 / 分类 / 项目 / BOM / 库存流水）并替换为备份内容。\n账号密码、激活码不受影响。\n\n是否继续？',
      '确认恢复数据',
      {
        type: 'warning',
        confirmButtonText: '确认恢复',
        cancelButtonText: '取消',
        confirmButtonClass: 'el-button--danger'
      }
    )
  } catch (e) {
    return false  // 用户取消
  }

  // 3. 上传 + 恢复
  restoring.value = true
  restoreProgress.value = 0
  try {
    const formData = new FormData()
    formData.append('file', file)
    const res = await restoreBackup(formData, (e) => {
      if (e.total) {
        restoreProgress.value = Math.round((e.loaded / e.total) * 100)
      }
    })
    const stats = res.data?.stats || {}
    ElMessage.success(
      `恢复成功：物料 ${stats.materials || 0} 条 · 分类 ${stats.categories || 0} 条 · 项目 ${stats.projects || 0} 个 · BOM ${stats.project_boms || 0} 条 · 流水 ${stats.stock_logs || 0} 条 · 图片 ${stats.images || 0} 张`
    )
    // 刷新整个应用，确保所有页面拿到最新数据
    setTimeout(() => window.location.reload(), 1200)
  } catch (e) {
    // 错误已由 request 拦截器弹窗
  } finally {
    restoring.value = false
    restoreProgress.value = 0
  }
  // 返回 false 阻止 el-upload 默认上传（我们用自定义 API）
  return false
}
</script>

<style scoped>
.sub-title { margin: 0 0 16px; font-size: 15px; color: var(--text-main); display: flex; align-items: center; justify-content: center; gap: 8px; text-align: center; }

/* 修改密码卡片 */
.pwd-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 22px;
}

/* ============ 主题卡片网格 ============ */
.theme-preview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
@media (max-width: 992px) {
  .theme-preview-grid { grid-template-columns: 1fr; }
}

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
.theme-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0,0,0,0.08);
  border-color: var(--primary);
}
.theme-card.active {
  border-color: var(--primary);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary) 25%, transparent);
}

/* 卡片预览区：模拟真实布局结构 */
.theme-card-preview {
  height: 150px;
  display: flex;
  overflow: hidden;
  border-bottom: 1px solid var(--border);
}
.tp-sidebar {
  width: 34px;
  flex-shrink: 0;
  padding: 10px 6px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.tp-logo {
  width: 14px;
  height: 14px;
  border-radius: 4px;
  margin-bottom: 6px;
  border: 1px solid rgba(0,0,0,0.15);
}
.tp-menu-item {
  width: 100%;
  height: 6px;
  background: rgba(255,255,255,0.18);
  border-radius: 2px;
}
.tp-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.tp-topbar {
  height: 22px;
  display: flex;
  align-items: center;
  padding: 0 8px;
  flex-shrink: 0;
}
.tp-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 1px solid rgba(0,0,0,0.15);
}
.tp-body {
  flex: 1;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.tp-card {
  flex: 1;
  border-radius: 4px;
  padding: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  justify-content: center;
}
.tp-card:last-child {
  flex-direction: row;
  align-items: center;
  gap: 6px;
}
.tp-bar {
  height: 5px;
  border-radius: 2px;
}
.tp-btn {
  width: 26px;
  height: 10px;
  border-radius: 3px;
  border: 1px solid rgba(0,0,0,0.08);
}

/* 卡片底部：名字 + 圆点 + 选中勾 */
.theme-card-footer {
  padding: 10px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.tc-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 1px solid #000;
  flex-shrink: 0;
  box-sizing: border-box;
}
.tc-name {
  flex: 1;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}
.tc-check {
  color: var(--primary);
  font-size: 16px;
}

/* ============ 备份/恢复卡片 ============ */
.backup-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.backup-section-title {
  margin-top: 24px;
}
.backup-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 18px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-sizing: border-box;
}
.backup-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
}
.backup-icon.bg-download {
  background: color-mix(in srgb, var(--primary) 15%, transparent);
  color: var(--primary);
}
.backup-icon.bg-upload {
  background: color-mix(in srgb, var(--primary) 15%, transparent);
  color: var(--primary);
}
.backup-content {
  flex: 1;
  min-width: 0;
}
.backup-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 4px;
}
.backup-desc {
  font-size: 12px;
  color: var(--text-sub);
  line-height: 1.5;
}
.restore-progress {
  display: inline-block;
  margin-left: 6px;
  color: var(--primary);
  font-weight: 600;
}
.backup-upload {
  flex-shrink: 0;
}
/* 让 el-upload 内的按钮跟其他按钮对齐 */
.backup-upload :deep(.el-upload) {
  display: inline-block;
}

.backup-warn {
  margin-top: 14px;
  padding: 10px 14px;
  background: color-mix(in srgb, var(--primary) 8%, transparent);
  border: 1px solid color-mix(in srgb, var(--primary) 25%, transparent);
  border-radius: 8px;
  font-size: 12px;
  color: var(--text-sub);
  line-height: 1.6;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.backup-warn .el-icon {
  flex-shrink: 0;
  margin-top: 1px;
  color: var(--primary);
}

@media (max-width: 768px) {
  .backup-card {
    flex-direction: column;
    align-items: flex-start;
    text-align: left;
  }
  .backup-card .el-button {
    align-self: stretch;
  }
}

.info-row { line-height: 2; color: var(--text-main); }
.info-row .lbl { color: var(--text-sub); display: inline-block; width: 110px; }
.info-card .sub-title { text-align: center; color: var(--text-sub); }
.info-card .info-row { text-align: center; color: var(--text-sub); }
</style>
