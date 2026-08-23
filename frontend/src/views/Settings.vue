<template>
  <div>
    <div class="page-card">
      <div class="page-title"><el-icon><Setting /></el-icon>系统设置</div>
      <el-row :gutter="20">
        <!-- 左：修改密码 -->
        <el-col :xs="24" :md="10">
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
        </el-col>

        <!-- 右：主题卡片预览 -->
        <el-col :xs="24" :md="14">
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
      <div class="info-row">TK01-ANS by TUTUTUKU</div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Setting, Brush, Lock, CircleCheckFilled } from '@element-plus/icons-vue'
import { changePassword } from '@/api'
import { themes, getThemeKey, applyTheme } from '@/utils/themes'

const router = useRouter()
const username = ref(localStorage.getItem('username') || 'admin')
const formRef = ref()
const loading = ref(false)
const form = reactive({ old_password: '', new_password: '', confirm: '' })
const themeList = themes
const currentTheme = ref(getThemeKey())

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

.info-row { line-height: 2; color: var(--text-main); }
.info-row .lbl { color: var(--text-sub); display: inline-block; width: 110px; }
.info-card .sub-title { text-align: center; color: var(--text-sub); }
.info-card .info-row { text-align: center; color: var(--text-sub); }
</style>
