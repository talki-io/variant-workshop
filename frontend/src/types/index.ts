// ===== 角色 / 用户 =====
export type Role = 'editor' | 'admin' // 素材员 / 管理员

export interface User {
  id: string
  name: string
  role: Role
  avatar?: string
}

// ===== 语感调性（账号指纹） =====
export interface Tone {
  id: string
  handle: string // @akun_demo
  name: string // 犀利散户体
  desc: string // 短句 · 大量俚语
}

// ===== 模型管理 =====
export type Provider = 'anthropic' | 'openai'

// 模型库：管理员维护的可用模型（多厂商）
export interface LlmModel {
  id: string
  name: string
  provider: Provider
  modelId: string // 厂商裸模型串
  baseUrl: string | null
  hasKey: boolean // 是否已配密钥（不回显明文）
  enabled: boolean
  createdAt: string
}

// 场景绑定：generate/clean/compliance → 选模型库某模型 + 参数
export interface ModelConfig {
  scene: string // generate | clean | compliance
  label: string // 中文场景名
  modelId: string // → LlmModel.id
  maxTokens: number
  temperature: number | null
  enabled: boolean
  updatedAt: string
}

// ===== 变体 =====
export type ComplianceStatus = 'pass' | 'soft' | 'blocked'
// pass=合规✓  soft=软提示·待判断  blocked=禁词命中·已改写

export interface VariantDimensions {
  hook: string // 钩子类型：悬念/对比/数字/反常识/恐惧
  structure: string // 叙事结构：故事/观点/列表/对比
  emotion: string // 情绪驱动：FOMO/贪婪/希望/怀疑/恐惧
  platform: string // 平台：IG/...
  cta: string // CTA 强度：强/中/弱
}

export interface Variant {
  id: string
  rank: number
  score: number // 综合分 0-100
  dimensions: VariantDimensions
  body: string // 印尼语文案正文
  softFlagSentence?: string // 命中软提示的句子（正文中需高亮）
  compliance: ComplianceStatus
  softFlagCount?: number // soft 时待判断句数
  aiScore: number // AI 味 0-100（越低越好）
  styleDistance: number // 风格距离（越小越贴合）
  confirmed: boolean
}

export interface VariantBatch {
  toneId: string
  diversity: number // 两两风格距离
  variants: Variant[]
  sessionId?: string // 所属生成会话（真实生成时返回）
}

// 引用新闻时的「事实底稿」：把新闻结构化素材喂给模型 grounding（而非仅标题）
export interface NewsContext {
  headline: string
  keyFacts: string[]
  tickers: string[]
  angleHints: string[]
}

// 生成会话（持久化到 DB，供切模块/刷新后恢复 + 历史列表）
export interface GenerationSession {
  id: string
  toneId: string
  prompt: string
  sourceHeadline?: string
  newsContext?: NewsContext // 引用新闻时的事实底稿（供恢复后重新生成仍贴事实）
  styleRefs?: string[] // 本次临时仿写范本（供恢复后重新生成仍参照）
  diversity: number
  createdAt: string
  favorite: boolean
  variants: Variant[]
}

// ===== 账号风格样本（往期爆款，few-shot 锚）=====
export interface StyleSample {
  id: string
  toneId: string
  body: string // 爆款正文
  source?: string // 备注/来源标签
  enabled: boolean
  createdAt: string
}

// ===== 新闻 =====
export type Freshness = 'breaking' | 'recent' | 'old' // 突发 / 近期 / 较旧
export type LabelState = 'none' | 'relevant' | 'irrelevant'

export interface NewsItem {
  id: string
  headline: string
  source: string // 财经源A/B/C
  publishedAt: string // ISO
  publishedLabel: string // "2 分钟前"
  freshness: Freshness
  heat: number // 0-100
  keyFacts: string[] // chips
  tickers: string[]
  angleHints: string[]
  url: string
  label: LabelState
}

// ===== 消耗看板 =====
export type ModelName = 'Haiku' | 'Sonnet' | 'Opus'

export interface DailyUsage {
  date: string
  model: ModelName
  tokens: number
}

export interface TopUser {
  rank: number
  name: string
  tokens: number
}

export interface UsageDetail {
  id: string
  user: string
  time: string
  model: string
  inputTokens: number
  outputTokens: number
  cost: number
  scene: string // 文案生成/新闻摘要/标签生成
}

export interface DashboardData {
  kpi: {
    todayTokens: number
    todayCost: number
    activeUsers: number
    quotaUsedPct: number
    quotaUsed: string
    quotaTotal: string
    tokensTrend: number // 同比 %
    costTrend: number
    usersTrend: number
  }
  daily: DailyUsage[]
  topUsers: TopUser[]
  details: UsageDetail[]
}

// ===== 抓取源 / 配额 =====
export type SourceType = 'RSS' | 'HTML' | '搜索API' | 'Playwright'
export type SourceHealth = 'ok' | 'error'

export interface CrawlSource {
  id: string
  name: string
  type: SourceType
  url: string
  frequency: string
  lastCrawl: string
  health: SourceHealth
  enabled: boolean
}

export interface QuotaConfig {
  perUserDaily: number
  overThresholdPct: number
  circuitBreaker: boolean
  breakerCondition: string
  globalDaily: number
  globalUsed: number
  globalUsedPct: number
}

export interface UserQuota {
  name: string
  used: number
  total: number
  isSelf?: boolean
}
