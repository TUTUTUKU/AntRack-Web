<template>
  <div class="layout">
    <!-- 侧边栏 -->
    <aside class="sidebar" :class="{ collapsed: isMobile }" v-show="!isMobile || drawerOpen">
      <div class="logo">
        <img class="logo-icon" src="/logo.png" alt="logo" />
        <span class="logo-text" v-show="!isMobile">蚁仓</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="isMobile"
        @select="onMenuSelect"
        class="side-menu"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataLine /></el-icon>
          <template #title>首页</template>
        </el-menu-item>
        <el-sub-menu index="material-group">
          <template #title>
            <el-icon><Box /></el-icon>
            <span>物料管理</span>
          </template>
          <el-menu-item index="/material">物料列表</el-menu-item>
          <el-menu-item index="/category">分类管理</el-menu-item>
        </el-sub-menu>
        <el-menu-item index="/project">
          <el-icon><Folder /></el-icon>
          <template #title>项目管理</template>
        </el-menu-item>
        <el-menu-item index="/stock-log">
          <el-icon><Tickets /></el-icon>
          <template #title>库存流水记录</template>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <template #title>系统设置</template>
        </el-menu-item>
      </el-menu>
    </aside>

    <!-- 移动端遮罩 -->
    <div class="mask" v-show="isMobile && drawerOpen" @click="drawerOpen = false"></div>

    <div class="main">
      <!-- 顶部状态栏 -->
      <header class="topbar">
        <div class="topbar-left">
          <el-icon v-if="isMobile" class="burger" @click="drawerOpen = true"><Expand /></el-icon>
          <el-icon v-else class="burger" @click="drawerOpen = !drawerOpen; toggleDesktopCollapse()"><Fold /></el-icon>
          <span class="page-name">{{ currentTitle }}</span>
        </div>
        <div class="topbar-right">
          <el-dropdown trigger="click" @command="onThemeCommand" popper-class="theme-dropdown">
            <el-button class="theme-btn" circle size="small" title="切换主题配色">
              <el-icon><Brush /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled style="opacity:0.6;cursor:default;font-size:11px;color:var(--text-sub);border-bottom:1px solid var(--border);margin-bottom:4px;padding:6px 12px;">选择主题配色</el-dropdown-item>
                <el-dropdown-item
                  v-for="t in themeList"
                  :key="t.key"
                  :command="t.key"
                  :class="{ 'theme-active': t.key === currentTheme }"
                >
                  <span class="theme-dot" :style="{ background: t.dot }"></span>
                  <span class="theme-name">{{ t.name }}</span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-dropdown @command="onUserCommand">
            <span class="user-info">
              <el-icon><User /></el-icon>
              <span class="username">{{ username }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="settings">系统设置</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- 主内容区 -->
      <main class="content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { themes, getThemeKey, applyTheme } from '@/utils/themes'

const route = useRoute()
const router = useRouter()
const isMobile = ref(window.innerWidth <= 768)
const drawerOpen = ref(false)
const desktopCollapsed = ref(false)
const username = ref(localStorage.getItem('username') || 'admin')
const themeList = themes
const currentTheme = ref(getThemeKey())

const activeMenu = computed(() => route.path)
const currentTitle = computed(() => route.meta.title || '蚁仓 Ant Rack System')

function checkMobile() {
  isMobile.value = window.innerWidth <= 768
  if (!isMobile.value) drawerOpen.value = false
}
onMounted(() => window.addEventListener('resize', checkMobile))
onUnmounted(() => window.removeEventListener('resize', checkMobile))

function toggleDesktopCollapse() {
  if (isMobile.value) return
  // 桌面端折叠占位（V1.0 仅保持展开，保留入口）
}

function onMenuSelect(index) {
  router.push(index)
  if (isMobile.value) drawerOpen.value = false
}

function onUserCommand(cmd) {
  if (cmd === 'settings') {
    router.push('/settings')
  } else if (cmd === 'logout') {
    ElMessageBox.confirm('确定要退出登录吗？', '提示', { type: 'warning' }).then(() => {
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      router.push('/login')
    }).catch(() => {})
  }
}

function onThemeCommand(key) {
  applyTheme(key)
  currentTheme.value = key
}

watch(() => route.path, () => { drawerOpen.value = false })
</script>

<style scoped>
.layout { display: flex; height: 100vh; overflow: hidden; }

/* 侧边栏：实色（禁止毛玻璃） · 使用专属 sidebar-bg */
.sidebar {
  width: 220px;
  background: var(--sidebar-bg);
  color: #ffffff;
  border-right: 1px solid rgba(0,0,0,0.08);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  transition: width 0.2s;
}
.sidebar.collapsed { width: 64px; }
.logo {
  height: 56px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 18px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  color: #ffffff;
  font-weight: 700;
  font-size: 16px;
}
.logo-icon { width: 22px; height: 22px; object-fit: contain; filter: drop-shadow(0 1px 2px rgba(0,0,0,0.3)); }
.side-menu { border-right: none; background: transparent; flex: 1; }
:deep(.el-menu) { background: transparent !important; }
:deep(.el-menu-item), :deep(.el-sub-menu__title) {
  color: rgba(255,255,255,0.68) !important;
}
:deep(.el-menu-item:hover), :deep(.el-sub-menu__title:hover) {
  background: rgba(255,255,255,0.08) !important;
  color: #ffffff !important;
}
:deep(.el-menu-item.is-active) {
  color: #ffffff !important;
  background: var(--primary) !important;
}
:deep(.el-sub-menu .el-menu-item) {
  background: color-mix(in srgb, var(--sidebar-bg) 92%, #000) !important;
}

.main { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; }

/* 顶栏：毛玻璃半透明 + 背景融合 */
.topbar {
  height: 56px;
  background: var(--topbar-alpha);
  backdrop-filter: blur(20px) saturate(1.5);
  -webkit-backdrop-filter: blur(20px) saturate(1.5);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 18px;
  flex-shrink: 0;
  position: relative;
  z-index: 2;
}
.topbar-left { display: flex; align-items: center; gap: 12px; }
.burger { font-size: 20px; cursor: pointer; color: var(--text-main); }
.page-name { font-size: 16px; font-weight: 600; color: var(--text-main); }
.topbar-right { display: flex; align-items: center; gap: 14px; }
.theme-btn {
  background: color-mix(in srgb, var(--primary) 8%, var(--card-2)) !important;
  border: 1px solid var(--border) !important;
  color: var(--primary) !important;
  transition: all .2s ease;
}
.theme-btn:hover {
  background: color-mix(in srgb, var(--primary) 18%, var(--card-2)) !important;
  transform: translateY(-1px);
}
:deep(.theme-dot) { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; vertical-align: middle; flex-shrink: 0; border: 1px solid #000; box-sizing: border-box; }
:deep(.theme-name) { flex: 1; }
:deep(.el-dropdown-menu__item.theme-active) {
  color: var(--primary) !important;
  font-weight: 600;
  background: color-mix(in srgb, var(--primary) 10%, transparent) !important;
}
.user-info { display: flex; align-items: center; gap: 6px; color: var(--text-main); cursor: pointer; }
.username { font-size: 14px; }

.content { flex: 1; overflow-y: auto; padding: 16px; }

.mask {
  position: fixed; inset: 0; background: rgba(0,0,0,0.45); z-index: 99;
  backdrop-filter: blur(2px);
}

@media (max-width: 768px) {
  .sidebar {
    position: fixed; left: 0; top: 0; bottom: 0; z-index: 100; width: 220px;
  }
  .content { padding: 10px; }
}
</style>
