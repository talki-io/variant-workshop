/**
 * Service 层：页面只依赖这里的 async 函数。
 * 已由 mock 切到真实 FastAPI（经 http.ts / Vite 代理），页面零改动。
 * 假数据已隔离至 dev-only/mocks/，仅供开发期组件走查页使用；生产代码不依赖它。
 */
import { apiFetch } from './http'
import type { NewsItem, Tone, Variant, VariantBatch, GenerationSession, NewsContext, StyleSample, ModelConfig, LlmModel, Provider, DashboardData, CrawlSource, QuotaConfig, UserQuota, LabelState, User, Role, MenuItem } from '../types'

export function getTones(): Promise<Tone[]> {
  return apiFetch<Tone[]>('/tones')
}

// ===== 用户管理（admin）=====
export interface UserInput {
  name: string
  role: Role
  password: string
  active?: boolean
}
export function getUsers(): Promise<User[]> {
  return apiFetch<User[]>('/users')
}
export function createUser(payload: UserInput): Promise<User> {
  return apiFetch<User>('/users', { method: 'POST', body: JSON.stringify(payload) })
}
export function updateUser(id: string, patch: Partial<Pick<User, 'name' | 'role' | 'active'>>): Promise<User> {
  return apiFetch<User>(`/users/${id}`, { method: 'PUT', body: JSON.stringify(patch) })
}
export function resetUserPassword(id: string, password: string): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>(`/users/${id}/password`, { method: 'PUT', body: JSON.stringify({ password }) })
}
export function deleteUser(id: string): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>(`/users/${id}`, { method: 'DELETE' })
}

// ===== 菜单管理（数据驱动导航；GET /menus 任意登录用户，其余 admin）=====
export interface MenuInput {
  path: string
  label: string
  icon: string
  order?: number
  visibleRoles: Role[]
  enabled?: boolean
}
export function getMenus(): Promise<MenuItem[]> {
  return apiFetch<MenuItem[]>('/menus')
}
export function getAllMenus(): Promise<MenuItem[]> {
  return apiFetch<MenuItem[]>('/menus/all')
}
export function createMenu(payload: MenuInput): Promise<MenuItem> {
  return apiFetch<MenuItem>('/menus', { method: 'POST', body: JSON.stringify(payload) })
}
export function updateMenu(id: string, patch: Partial<MenuInput>): Promise<MenuItem> {
  return apiFetch<MenuItem>(`/menus/${id}`, { method: 'PUT', body: JSON.stringify(patch) })
}
export function deleteMenu(id: string): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>(`/menus/${id}`, { method: 'DELETE' })
}

// ===== 账号/调性管理（admin）=====
export type ToneInput = Pick<Tone, 'handle' | 'name' | 'desc'>
export function createTone(payload: ToneInput): Promise<Tone> {
  return apiFetch<Tone>('/tones', { method: 'POST', body: JSON.stringify(payload) })
}
export function updateTone(id: string, patch: Partial<ToneInput>): Promise<Tone> {
  return apiFetch<Tone>(`/tones/${id}`, { method: 'PUT', body: JSON.stringify(patch) })
}
export function deleteTone(id: string): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>(`/tones/${id}`, { method: 'DELETE' })
}

// ===== 模型管理（admin）=====
// 模型库（多厂商 CRUD）
export function getLlmModels(): Promise<LlmModel[]> {
  return apiFetch<LlmModel[]>('/llm-models')
}
export type LlmModelInput = { name: string; provider: Provider; modelId: string; baseUrl?: string | null; apiKey?: string | null }
export function createLlmModel(payload: LlmModelInput): Promise<LlmModel> {
  return apiFetch<LlmModel>('/llm-models', { method: 'POST', body: JSON.stringify(payload) })
}
export function updateLlmModel(id: string, patch: Partial<LlmModelInput> & { enabled?: boolean }): Promise<LlmModel> {
  return apiFetch<LlmModel>(`/llm-models/${id}`, { method: 'PUT', body: JSON.stringify(patch) })
}
export function deleteLlmModel(id: string): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>(`/llm-models/${id}`, { method: 'DELETE' })
}
export function verifyLlmModel(id: string): Promise<{ ok: boolean; model?: string; error?: string }> {
  return apiFetch<{ ok: boolean; model?: string; error?: string }>(`/llm-models/${id}/verify`, { method: 'POST' })
}

// 场景绑定
export function getModels(): Promise<ModelConfig[]> {
  return apiFetch<ModelConfig[]>('/models')
}
export type ModelPatch = { modelId?: string; maxTokens?: number; temperature?: number | null; enabled?: boolean }
export function updateModel(scene: string, patch: ModelPatch): Promise<ModelConfig> {
  return apiFetch<ModelConfig>(`/models/${scene}`, { method: 'PUT', body: JSON.stringify(patch) })
}

// ===== 账号风格样本（往期爆款，few-shot 锚）=====
/** 列出某账号的爆款样本（最新在前）。 */
export function getSamples(toneId: string): Promise<StyleSample[]> {
  return apiFetch<StyleSample[]>(`/tones/${toneId}/samples`)
}

/** 为某账号新增一条爆款样本。 */
export function addSample(toneId: string, body: string, source?: string): Promise<StyleSample> {
  return apiFetch<StyleSample>(`/tones/${toneId}/samples`, {
    method: 'POST',
    body: JSON.stringify({ body, source }),
  })
}

/** 删除一条爆款样本。 */
export function deleteSample(id: string): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>(`/samples/${id}`, { method: 'DELETE' })
}

/** 生成变体。newsContext = 引用新闻时的事实底稿（喂给模型 grounding，不传则走通用生成）。 */
export function generateVariants(
  toneId: string,
  prompt: string,
  sourceHeadline?: string,
  newsContext?: NewsContext,
  styleRefs?: string[],
): Promise<VariantBatch> {
  return apiFetch<VariantBatch>('/variants', {
    method: 'POST',
    body: JSON.stringify({ toneId, prompt, sourceHeadline, newsContext, styleRefs }),
  })
}

/** 当前用户最近的生成会话（含变体；收藏优先、其后最新在前）。用于工作台恢复 + 历史列表。 */
export function getSessions(limit = 10): Promise<GenerationSession[]> {
  return apiFetch<GenerationSession[]>(`/variants/sessions?limit=${limit}`)
}

/** 收藏 / 取消收藏某生成会话（仅本人）。 */
export function toggleSessionFavorite(id: string, favorite: boolean): Promise<GenerationSession> {
  return apiFetch<GenerationSession>(`/variants/sessions/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ favorite }),
  })
}

/** 删除某生成会话及其变体（仅本人）。 */
export function deleteSession(id: string): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>(`/variants/sessions/${id}`, { method: 'DELETE' })
}

/** 编辑变体正文并重跑合规（服务端）。返回更新后的变体。 */
export function editVariant(id: string, body: string): Promise<Variant> {
  return apiFetch<Variant>(`/variants/${id}`, { method: 'PATCH', body: JSON.stringify({ body }) })
}

/** 按该变体维度重新生成正文（原地替换）。返回更新后的变体。 */
export function regenerateVariant(id: string, prompt: string): Promise<Variant> {
  return apiFetch<Variant>(`/variants/${id}/regenerate`, { method: 'POST', body: JSON.stringify({ prompt }) })
}

export interface NewsQuery {
  q?: string
  sources?: string[]
  sort?: 'heat' | 'time'
  onlyUnlabeled?: boolean
  dateFrom?: string // YYYY-MM-DD
  dateTo?: string // YYYY-MM-DD
  limit?: number
  offset?: number
}

export interface NewsPage {
  items: NewsItem[]
  total: number
  sources: string[] // 全表来源，供筛选下拉（与分页无关）
}

/** 新闻库分页 + 服务端检索/筛选/排序。供下滑加载。 */
export function getNews(params: NewsQuery = {}): Promise<NewsPage> {
  const sp = new URLSearchParams()
  if (params.q?.trim()) sp.set('q', params.q.trim())
  ;(params.sources ?? []).forEach((s) => sp.append('source', s))
  if (params.sort) sp.set('sort', params.sort)
  if (params.onlyUnlabeled) sp.set('onlyUnlabeled', 'true')
  if (params.dateFrom) sp.set('dateFrom', params.dateFrom)
  if (params.dateTo) sp.set('dateTo', params.dateTo)
  sp.set('limit', String(params.limit ?? 20))
  sp.set('offset', String(params.offset ?? 0))
  return apiFetch<NewsPage>(`/news?${sp.toString()}`)
}

/** 新闻打标落库（相关/不相关/取消）。返回更新后的新闻。editor/admin 均可。 */
export function labelNews(id: string, label: LabelState): Promise<NewsItem> {
  return apiFetch<NewsItem>(`/news/${id}/label`, {
    method: 'PUT',
    body: JSON.stringify({ label }),
  })
}

export function getDashboard(): Promise<DashboardData> {
  return apiFetch<DashboardData>('/dashboard')
}

export function getSources(): Promise<CrawlSource[]> {
  return apiFetch<CrawlSource[]>('/sources')
}

export type SourceCreate = Pick<CrawlSource, 'name' | 'type' | 'url' | 'frequency'>
export type SourcePatch = Partial<Pick<CrawlSource, 'name' | 'type' | 'url' | 'frequency' | 'enabled'>>

/** 新增抓取源（admin）。 */
export function createSource(payload: SourceCreate): Promise<CrawlSource> {
  return apiFetch<CrawlSource>('/sources', { method: 'POST', body: JSON.stringify(payload) })
}

/** 部分更新抓取源（名称/类型/URL/频率/启用开关）（admin）。 */
export function updateSource(id: string, patch: SourcePatch): Promise<CrawlSource> {
  return apiFetch<CrawlSource>(`/sources/${id}`, { method: 'PUT', body: JSON.stringify(patch) })
}

/** 删除抓取源（admin）。 */
export function deleteSource(id: string): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>(`/sources/${id}`, { method: 'DELETE' })
}

export function getQuota(): Promise<{ config: QuotaConfig; users: UserQuota[] }> {
  return apiFetch<{ config: QuotaConfig; users: UserQuota[] }>('/quota')
}

/** 保存配额/限流配置（admin）。globalUsed/globalUsedPct 为派生量，不作为入参。 */
export type QuotaConfigInput = Omit<QuotaConfig, 'globalUsed' | 'globalUsedPct'>
export function updateQuota(config: QuotaConfigInput): Promise<{ config: QuotaConfig; users: UserQuota[] }> {
  return apiFetch<{ config: QuotaConfig; users: UserQuota[] }>('/quota', {
    method: 'PUT',
    body: JSON.stringify(config),
  })
}

// ===== M7 反馈埋点 =====
export interface TelemetryPayload {
  eventType: string
  variantId?: string
  newsId?: string
  toneId?: string
  position?: number
  editedSentences?: string[]
  meta?: Record<string, unknown>
}

/** 隐式行为信号上报。调用处一律 fire-and-forget（.catch 吞掉），绝不阻断 UX。 */
export function logEvent(payload: TelemetryPayload): Promise<{ ok: boolean; eventId: string }> {
  return apiFetch<{ ok: boolean; eventId: string }>('/telemetry', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

/** 采用某变体（强正信号）。 */
export function confirmVariant(variantId: string): Promise<{ ok: boolean; eventId: string }> {
  return apiFetch<{ ok: boolean; eventId: string }>(`/variants/${variantId}/confirm`, { method: 'POST' })
}

// ===== M1 采集触发 =====
export interface CrawlResult {
  ok: boolean
  fetched: number
  inserted: number
  skipped: number
  filteredIrrelevant: number
  message: string
}

/** 立即抓取某 RSS 源。 */
export function crawlSource(id: string): Promise<CrawlResult> {
  return apiFetch<CrawlResult>(`/sources/${id}/crawl`, { method: 'POST' })
}
