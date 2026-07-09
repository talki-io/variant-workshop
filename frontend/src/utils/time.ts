import type { Freshness } from '../types'

/**
 * 由绝对发布时间 `publishedAt`（ISO）实时计算相对时间标签 + 新鲜度。
 *
 * 为什么放前端算：相对时间是「相对当前」的量，若在抓取时算好存库（旧的 published_label/freshness），
 * 时间一过就永远定格（几天前的新闻仍显示「2 分钟前」）。真实时间戳 publishedAt 才是唯一可信来源。
 * 阈值与后端 crawl.py::_freshness 对齐：<2h 突发 / <24h 近期 / 其余较旧。
 */
export function newsFreshness(iso: string): { label: string; freshness: Freshness } {
  const t = new Date(iso).getTime()
  if (!iso || Number.isNaN(t)) return { label: '未知时间', freshness: 'old' }
  let mins = (Date.now() - t) / 60000
  if (mins < 0) mins = 0 // 源站时间偶有超前，钳到 0 避免「负数分钟」
  if (mins < 1) return { label: '刚刚', freshness: 'breaking' }
  const hours = mins / 60
  if (hours < 2) return { label: `${Math.floor(mins)} 分钟前`, freshness: 'breaking' }
  if (hours < 24) return { label: `${Math.floor(hours)} 小时前`, freshness: 'recent' }
  return { label: `${Math.floor(hours / 24)} 天前`, freshness: 'old' }
}
