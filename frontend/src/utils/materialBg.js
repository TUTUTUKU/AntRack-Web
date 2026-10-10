// 物料背景图缓存工具
// 后端上传会覆盖同名文件 material-bg.png，浏览器会缓存旧图。
// 通过 localStorage 记录上传时间戳，所有引用处拼接 ?t=ts 强制刷新。

const BG_STORAGE_KEY = 'antrack_material_bg_ts'
const BG_URL = '/static/material-bg.png'

// 获取当前背景图时间戳（不存在则初始化）
export function getBgTs() {
  let v = localStorage.getItem(BG_STORAGE_KEY)
  if (!v) {
    v = String(Date.now())
    localStorage.setItem(BG_STORAGE_KEY, v)
  }
  return Number(v)
}

// 更新背景图时间戳（上传/恢复默认后调用）
export function updateBgTs(ts) {
  const t = ts || Date.now()
  localStorage.setItem(BG_STORAGE_KEY, String(t))
  return t
}

// 获取带缓存破坏参数的背景图 URL
export function getMaterialBgUrl() {
  const ts = getBgTs()
  return ts ? `${BG_URL}?t=${ts}` : BG_URL
}
