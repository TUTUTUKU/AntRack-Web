// -*- coding: utf-8 -*-
/**
 * 数字格式化工具
 *  - 数量类（库存、可用、锁定、阈值、出入库数）：精确到个位
 *  - 价格/成本类（单价、总成本、金额）：精确到 0.01 元
 */

// 数量 → 整数字符串（null/undefined 安全）
export function fmtNum(v) {
  const n = Number(v)
  if (!isFinite(n)) return '0'
  return String(Math.round(n))
}

// 价格 → 两位小数字符串
export function fmtPrice(v) {
  const n = Number(v)
  if (!isFinite(n)) return '0.00'
  return n.toFixed(2)
}
