// WebSocket 客户端：冲突/阶段/恢复/配置事件

import { ElMessage } from 'element-plus'

const listeners = new Set()   // 全局事件监听 (evt, data) => void

let ws = null
let reconnectTimer = null
let closeByUser = false
let pendingCount = 0         // 待处理冲突数（缓存）

function _wsUrl() {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const host = window.location.host
  const token = localStorage.getItem('token') || ''
  return `${proto}://${host}/ws?token=${encodeURIComponent(token)}`
}

function notify(evt, data) {
  for (const fn of listeners) {
    try { fn(evt, data) } catch (e) { /* ignore */ }
  }
}

function bindDefaultHints() {
  on((evt, data) => {
    if (evt === 'conflict:created') {
      const count = (data?.conflict_ids || []).length
      pendingCount += count
      ElMessage({
        type: 'warning',
        duration: 0,
        showClose: true,
        message: `检测到 ${count} 条待处理冲突，请前往「系统设置 → 数据相关 → 冲突处理」处理。`,
      })
    } else if (evt === 'conflict:resolved') {
      pendingCount = Math.max(0, pendingCount - 1)
    } else if (evt === 'data:restored') {
      ElMessage({
        type: 'info',
        duration: 5000,
        showClose: true,
        message: '服务端数据已恢复，即将刷新页面获取最新数据…',
      })
      setTimeout(() => window.location.reload(), 1200)
    } else if (evt === 'config:changed') {
      // 通知 settings 面板主动刷新
    } else if (evt === 'stage:changed') {
      // 阶段变化：列表页可按需刷新
    }
  })
}
bindDefaultHints()

export function connect() {
  if (ws) return
  closeByUser = false
  try {
    ws = new WebSocket(_wsUrl())
  } catch (e) {
    ws = null
    scheduleReconnect()
    return
  }
  ws.onopen = () => { /* hello 由服务端主动推送 */ }
  ws.onmessage = (ev) => {
    try {
      const payload = JSON.parse(ev.data)
      notify(payload.event, payload.data)
    } catch (e) { /* ignore */ }
  }
  ws.onerror = () => { /* close 里处理重连 */ }
  ws.onclose = () => {
    ws = null
    if (!closeByUser) scheduleReconnect()
  }
}

export function disconnect() {
  closeByUser = true
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (ws) {
    try { ws.close() } catch (e) {}
    ws = null
  }
}

function scheduleReconnect() {
  if (closeByUser || reconnectTimer) return
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null
    connect()
  }, 4000)
}

export function on(fn) {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

export function getPendingCount() {
  return pendingCount
}

export function setPendingCount(n) {
  pendingCount = Math.max(0, Number(n) || 0)
  notify('pending:changed', { count: pendingCount })
}
