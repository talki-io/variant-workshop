import type { DashboardData, DailyUsage, ModelName } from '../types'

// 生成近 30 天、按模型分组的消耗数据（确定性，非随机）
function buildDaily(): DailyUsage[] {
  const out: DailyUsage[] = []
  const models: { name: ModelName; base: number; amp: number }[] = [
    { name: 'Haiku', base: 220_000, amp: 90_000 },
    { name: 'Sonnet', base: 480_000, amp: 140_000 },
    { name: 'Opus', base: 760_000, amp: 200_000 },
  ]
  for (let i = 0; i < 30; i++) {
    const day = new Date(2025, 3, 28 + i) // 从 04-28 起
    const mm = String(day.getMonth() + 1).padStart(2, '0')
    const dd = String(day.getDate()).padStart(2, '0')
    const date = `${mm}-${dd}`
    for (const m of models) {
      const wave = Math.sin(i / 2.3) * 0.6 + Math.sin(i / 5) * 0.4
      const tokens = Math.round(m.base + m.amp * wave)
      out.push({ date, model: m.name, tokens })
    }
  }
  return out
}

const names = ['张伟', '李娜', '王强', '陈晨', '刘洋', '赵敏', '孙磊', '周舟', '吴迪', '郑凯']
const topTokens = [2.86, 2.15, 1.62, 1.28, 1.05, 0.842, 0.612, 0.498, 0.412, 0.371]

export const dashboard: DashboardData = {
  kpi: {
    todayTokens: 12_456_789,
    todayCost: 2_034.56,
    activeUsers: 236,
    quotaUsedPct: 68.4,
    quotaUsed: '684.2M',
    quotaTotal: '1.0B',
    tokensTrend: -8.32,
    costTrend: 12.67,
    usersTrend: 6.21,
  },
  daily: buildDaily(),
  topUsers: names.map((name, i) => ({
    rank: i + 1,
    name,
    tokens: Math.round(topTokens[i] * 1_000_000),
  })),
  details: [
    { id: 'd1', user: '张伟', time: '2025-05-27 10:32:18', model: 'Sonnet 3.5', inputTokens: 18_742, outputTokens: 6_231, cost: 18.62, scene: '文案生成' },
    { id: 'd2', user: '李娜', time: '2025-05-27 10:28:41', model: 'Haiku 3', inputTokens: 8_921, outputTokens: 3_112, cost: 4.58, scene: '文案生成' },
    { id: 'd3', user: '王强', time: '2025-05-27 10:25:03', model: 'Opus 3', inputTokens: 32_104, outputTokens: 12_987, cost: 52.31, scene: '文案生成' },
    { id: 'd4', user: '陈晨', time: '2025-05-27 10:21:47', model: 'Sonnet 3.5', inputTokens: 11_432, outputTokens: 4_521, cost: 10.93, scene: '新闻摘要' },
    { id: 'd5', user: '刘洋', time: '2025-05-27 10:19:26', model: 'Haiku 3', inputTokens: 6_512, outputTokens: 2_011, cost: 3.21, scene: '标签生成' },
    { id: 'd6', user: '赵敏', time: '2025-05-27 10:15:09', model: 'Sonnet 3.5', inputTokens: 14_209, outputTokens: 5_874, cost: 13.44, scene: '文案生成' },
    { id: 'd7', user: '孙磊', time: '2025-05-27 10:11:52', model: 'Opus 3', inputTokens: 28_930, outputTokens: 10_233, cost: 45.72, scene: '去AI味重写' },
    { id: 'd8', user: '周舟', time: '2025-05-27 10:08:33', model: 'Haiku 3', inputTokens: 5_120, outputTokens: 1_760, cost: 2.68, scene: '合规分类' },
  ],
}
