<template>
  <div class="login-wrap">
    <div class="login-card">
      <div class="login-header">
        <img class="logo-icon" src="/logo.png" alt="logo" />
        <h1 class="title">蚁仓</h1>
        <p class="sub">Ant Rack System V1.0</p>
      </div>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="onLogin">
        <el-form-item label="账号" prop="username">
          <el-input v-model="form.username" placeholder="请输入登录账号" :prefix-icon="User" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入登录密码" :prefix-icon="Lock" @keyup.enter="onLogin" />
        </el-form-item>
        <el-button type="primary" class="login-btn" :loading="loading" @click="onLogin">登 录</el-button>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { login } from '@/api'

const router = useRouter()
const formRef = ref()
const loading = ref(false)
const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

function onLogin() {
  formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      const res = await login(form)
      localStorage.setItem('token', res.data.token)
      localStorage.setItem('username', res.data.username)
      ElMessage.success('登录成功')
      // V1.2：登录成功启动 WS，接收冲突/恢复事件
      try { window.__antrack_ws && window.__antrack_ws.connect() } catch (e) {}
      router.push('/dashboard')
    } catch (e) {
      // 错误已在拦截器提示
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.login-wrap {
  height: 100vh; width: 100vw;
  display: flex; align-items: center; justify-content: center;
  background:
    radial-gradient(circle at 30% 20%, color-mix(in srgb, var(--sidebar-bg) 70%, transparent) 0%, var(--bg) 60%),
    var(--bg);
}
.login-card {
  width: 380px; max-width: 92vw;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 36px 32px 28px;
  box-shadow: 0 16px 48px -12px color-mix(in srgb, var(--sidebar-bg) 45%, transparent);
}
.login-header { text-align: center; margin-bottom: 28px; }
.logo-icon { width: 44px; height: 44px; object-fit: contain; }
.title { margin: 10px 0 4px; font-size: 20px; color: var(--text-main); }
.sub { margin: 0; color: var(--text-sub); font-size: 12px; }
.login-btn { width: 100%; height: 40px; font-size: 15px; margin-top: 4px; }
</style>
