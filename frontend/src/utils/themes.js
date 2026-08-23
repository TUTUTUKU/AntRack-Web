// ============================================================
// 全局固定功能色（所有主题共用，不跟随主题切换）
// 成功 / 警告 / 危险 / 信息提示
// ============================================================
export const FIXED = {
  '--success': '#28c868',
  '--warning': '#ff9500',
  '--danger':  '#f84242',
  '--info':    '#3B82F6',
}

// ============================================================
// 6 套主题（默认 = 黑玄色基底 + 科技蓝强调）
// 每套 10 个色彩用途：
//   --bg / --card / --sidebar-bg  背景三层（基底控制）
//   --text-main / --text-sub / --text-placeholder  文字三级
//   --primary / --primary-hover  主强调色（色彩主题控制）
//   --secondary  次要按钮
//   --border  分割线
// ============================================================
const DEFAULT_ACCENT = '#22b8dd'
const DEFAULT_ACCENT_HOVER = '#1a9bc0'

export const themes = [
  // 01 黑玄色｜黑夜基底
  {
    key: 'base-dark',
    name: '深曜暗夜',
    order: 1,
    base: 'dark',
    color: 'none',
    dark: true,
    dot: '#111317',
    vars: {
      '--sidebar-bg': '#111317',
      '--bg': '#15171b',
      '--card': '#1e2126',
      '--text-main': '#f3f4f6',
      '--text-sub': '#9ca3af',
      '--text-placeholder': '#6b7280',
      '--secondary': '#25282e',
      '--border': '#2a2d34',
      '--primary': DEFAULT_ACCENT,
      '--primary-hover': DEFAULT_ACCENT_HOVER
    },
  },
  // 02 白昼｜白色基底
  {
    key: 'base-light',
    name: '素白昼光',
    order: 2,
    base: 'light',
    color: 'none',
    dark: false,
    dot: '#ffffff',
    vars: {
      '--sidebar-bg': '#242c37',
      '--bg': '#ffffff',
      '--card': '#f6f8fb',
      '--text-main': '#171c26',
      '--text-sub': '#606b7e',
      '--text-placeholder': '#919cb0',
      '--secondary': '#e8ecf2',
      '--border': '#d2d9e3',
      '--primary': '#3B82F6',
      '--primary-hover': '#2563eb'
    },
  },
  // 03 科技蓝｜完整色彩主题
  {
    key: 'tech-blue',
    name: '科技深蓝',
    order: 3,
    base: 'light',
    color: 'tech-blue',
    dark: false,
    dot: '#00c8ff',
    vars: {
      '--sidebar-bg': '#0b1220',
      '--bg': '#0f172a',
      '--card': '#1e293b',
      '--text-main': '#f1f5f9',
      '--text-sub': '#94a3b8',
      '--text-placeholder': '#64748b',
      '--secondary': '#334155',
      '--border': '#1e3a5f',
      '--primary': '#00c8ff',
      '--primary-hover': '#00a6d6'
    },
  },
  // 04 森林绿｜完整色彩主题
  {
    key: 'forest-green',
    name: '绿意盎然',
    order: 4,
    base: 'light',
    color: 'forest-green',
    dark: false,
    dot: '#22c58b',
    vars: {
      '--sidebar-bg': '#1e4a35',
      '--bg': '#f8fcf9',
      '--card': '#ffffff',
      '--text-main': '#1f362b',
      '--text-sub': '#577566',
      '--text-placeholder': '#88a394',
      '--secondary': '#d4eede',
      '--border': '#b8dcc8',
      '--primary': '#22c58b',
      '--primary-hover': '#16a375'
    },
  },
  // 05 低对比度｜完整色彩主题
  {
    key: 'low-contrast',
    name: '低对比度',
    order: 5,
    base: 'light',
    color: 'low-contrast',
    dark: false,
    dot: '#6c8699',
    vars: {
      '--sidebar-bg': '#596269',
      '--bg': '#f2f3f4',
      '--card': '#ffffff',
      '--text-main': '#4a5258',
      '--text-sub': '#7c848b',
      '--text-placeholder': '#a1a8ad',
      '--secondary': '#e4e6e8',
      '--border': '#d0d4d7',
      '--primary': '#6c8699',
      '--primary-hover': '#587082'
    },
  },
  // 06 赛博朋克紫｜完整色彩主题
  {
    key: 'cyber-purple',
    name: '赛博朋克',
    order: 6,
    base: 'light',
    color: 'cyber-purple',
    dark: false,
    dot: '#a855f7',
    vars: {
      '--sidebar-bg': '#120420',
      '--bg': '#170827',
      '--card': '#231038',
      '--text-main': '#f0e8ff',
      '--text-sub': '#b89cd6',
      '--text-placeholder': '#7a5e99',
      '--secondary': '#3b1f5c',
      '--border': '#ff2ea8',
      '--primary': '#00f0ff',
      '--primary-hover': '#00c8d6'
    },
  },
]

const STORAGE_KEY = 'antrack-theme'
const BASE_KEY = 'antrack-base-theme'
const COLOR_KEY = 'antrack-color-theme'
const DEFAULT_KEY = 'base-dark'

export function getThemeKey() {
  const k = localStorage.getItem(STORAGE_KEY)
  if (k && themes.find(t => t.key === k)) return k
  return DEFAULT_KEY
}

// 根据主题自动推导辅助变量（按钮文字色、遮罩、card-2、毛玻璃透明色）
function deriveVars(theme) {
  const v = theme.vars
  const dark = theme.dark
  const card2 = shade(v['--card'], dark ? 5 : -4)
  const btnText = '#ffffff'
  const secText = dark ? '#ffffff' : v['--text-main']
  return {
    '--card-2': card2,
    '--btn-text': btnText,
    '--btn-text-secondary': secText,
    '--btn-text-disabled': dark ? 'rgba(255,255,255,0.35)' : 'rgba(0,0,0,0.35)',
    '--btn-overlay': dark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)',
    '--btn-overlay-border': dark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)',
    '--overlay-subtle': dark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.03)',
    // 顶栏/弹窗毛玻璃透明度，深色/浅色都用对应卡片色的 alpha
    '--topbar-alpha': hexToRgba(v['--card'], dark ? 0.72 : 0.78),
    '--dialog-alpha': hexToRgba(v['--card'], dark ? 0.82 : 0.86),
    '--dropdown-alpha': hexToRgba(v['--card'], dark ? 0.88 : 0.90),
  }
}

function hexToRgba(hex, a) {
  const { r, g, b } = parseHex(hex)
  return `rgba(${r},${g},${b},${a})`
}
function parseHex(hex) {
  let h = hex.replace('#', '')
  if (h.length === 3) h = h.split('').map(c => c + c).join('')
  const num = parseInt(h, 16)
  return { r: (num >> 16) & 255, g: (num >> 8) & 255, b: num & 255 }
}
function rgbStrToHex(rgb) {
  const m = rgb.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/)
  if (!m) return rgb
  return '#' + [1, 2, 3].map(i => parseInt(m[i]).toString(16).padStart(2, '0')).join('')
}
function shade(hexOrRgb, percent) {
  const c = parseHex(hexOrRgb.startsWith('rgb') ? rgbStrToHex(hexOrRgb) : hexOrRgb)
  const mix = (channel) => {
    if (percent >= 0) return Math.round(channel + (255 - channel) * percent / 100)
    return Math.round(channel * (100 + percent) / 100)
  }
  return `rgb(${mix(c.r)}, ${mix(c.g)}, ${mix(c.b)})`
}

export function applyTheme(key) {
  const theme = themes.find(t => t.key === key)
  if (!theme) return
  const root = document.documentElement
  Object.entries(theme.vars).forEach(([k, val]) => root.style.setProperty(k, val))
  Object.entries(deriveVars(theme)).forEach(([k, val]) => root.style.setProperty(k, val))
  Object.entries(FIXED).forEach(([k, val]) => root.style.setProperty(k, val))
  if (theme.dark) document.body.classList.add('is-dark')
  else document.body.classList.remove('is-dark')
  localStorage.setItem(STORAGE_KEY, theme.key)
  localStorage.setItem(BASE_KEY, theme.base)
  localStorage.setItem(COLOR_KEY, theme.color)
}

export function initTheme() {
  const root = document.documentElement
  Object.entries(FIXED).forEach(([k, val]) => root.style.setProperty(k, val))
  applyTheme(getThemeKey())
}
