import type { CrawlSource, QuotaConfig, UserQuota } from '../types'

export const sources: CrawlSource[] = [
  { id: 's1', name: '行业资讯 RSS', type: 'RSS', url: 'https://example.com/rss/industry.xml', frequency: '每 15 分钟', lastCrawl: '2025-05-10 10:28', health: 'ok', enabled: true },
  { id: 's2', name: '竞品官网搜索 API', type: '搜索API', url: 'https://api.example.com/search', frequency: '每 30 分钟', lastCrawl: '2025-05-10 10:12', health: 'ok', enabled: true },
  { id: 's3', name: '新闻站点 Playwright', type: 'Playwright', url: 'https://news.example.com/', frequency: '每 60 分钟', lastCrawl: '2025-05-10 09:45', health: 'error', enabled: true },
  { id: 's4', name: '博客聚合 RSS', type: 'RSS', url: 'https://blog.example.com/feed.xml', frequency: '每 2 小时', lastCrawl: '2025-05-10 08:30', health: 'ok', enabled: true },
  { id: 's5', name: '论坛热点搜索 API', type: '搜索API', url: 'https://api.example.com/forum/search', frequency: '每 60 分钟', lastCrawl: '2025-05-10 09:50', health: 'ok', enabled: false },
  { id: 's6', name: '社区内容抓取 Playwright', type: 'Playwright', url: 'https://community.example.com/', frequency: '每 4 小时', lastCrawl: '2025-05-10 07:20', health: 'error', enabled: true },
]

export const quotaConfig: QuotaConfig = {
  perUserDaily: 20_000,
  overThresholdPct: 80,
  circuitBreaker: true,
  breakerCondition: '错误率 ≥ 20% 且持续 5 分钟',
  globalDaily: 1_000_000,
  globalUsed: 342_500,
  globalUsedPct: 34.25,
}

export const userQuotas: UserQuota[] = [
  { name: '林小北（你）', used: 8_200, total: 20_000, isSelf: true },
  { name: '张三', used: 12_600, total: 20_000 },
  { name: '李四', used: 18_100, total: 20_000 },
  { name: '王五', used: 5_400, total: 20_000 },
  { name: '赵六', used: 2_300, total: 20_000 },
]
