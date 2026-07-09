import { useEffect, useState } from 'react'
import { App } from 'antd'
import { useLocation, useNavigate } from 'react-router-dom'
import ChatPanel, { type ChatMessage } from './ChatPanel'
import VariantList from './VariantList'
import HistoryPanel from './HistoryPanel'
import {
  getTones, generateVariants, confirmVariant, logEvent, editVariant, regenerateVariant,
  getSessions, toggleSessionFavorite, deleteSession,
} from '../../services'
import type { Tone, Variant, VariantBatch, GenerationSession, NewsContext } from '../../types'

const PAGE = 10 // 历史每页条数

let msgSeq = 0
const nextId = () => `m${++msgSeq}`
const hhmm = () => {
  const d = new Date()
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(d.getHours())}:${p(d.getMinutes())}`
}

export default function GeneratePage() {
  const { message, modal } = App.useApp()
  const location = useLocation()
  const navigate = useNavigate()
  const locState = location.state as { newsHeadline?: string; newsContext?: NewsContext } | null
  const prefillNews = locState?.newsHeadline
  const citedContext = locState?.newsContext

  const [tones, setTones] = useState<Tone[]>([])
  const [toneId, setToneId] = useState<string>()
  // 引用新闻的事实底稿：随发送一起送后端 grounding。仅反映「本次显式引用」，
  // 恢复历史会话不设它——那类会话的「重新生成」由后端读 session.news_context 保持贴事实。
  const [citedNews, setCitedNews] = useState<NewsContext | undefined>()
  const [styleRefs, setStyleRefs] = useState<string[]>([]) // 本次临时仿写范本
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [generating, setGenerating] = useState(false)
  const [batch, setBatch] = useState<VariantBatch | null>(null)
  const [sort, setSort] = useState('score')
  const [lastPrompt, setLastPrompt] = useState('') // 供「重新生成」「快捷 chips」复用
  const [sessions, setSessions] = useState<GenerationSession[]>([]) // 历史生成会话（收藏优先/最新在前）
  const [sessionsLoading, setSessionsLoading] = useState(true)
  const [limit, setLimit] = useState(PAGE) // 历史加载条数（「查看更多」递增）

  // 恢复某次生成会话到工作台（切模块/刷新/选历史时）
  const restoreSession = (s: GenerationSession, toneList: Tone[]) => {
    setToneId(toneList.some((t) => t.id === s.toneId) ? s.toneId : toneList[0]?.id)
    setBatch({ toneId: s.toneId, diversity: s.diversity, variants: s.variants, sessionId: s.id })
    setLastPrompt(s.prompt)
    setStyleRefs(s.styleRefs ?? []) // 恢复该会话的临时仿写范本
    const src = s.sourceHeadline ? `（引用新闻：${s.sourceHeadline}）` : ''
    const t = s.createdAt.slice(11, 16) || undefined // "YYYY-MM-DD HH:MM:SS" → HH:MM
    setMessages([
      { id: nextId(), role: 'user', content: s.prompt, time: t },
      { id: nextId(), role: 'ai', content: `已恢复该次生成的 ${s.variants.length} 条变体${src}，可继续编辑/采用。`, time: t },
    ])
  }

  // 首屏：加载调性 + 历史会话；有历史则恢复最近一次，实现刷新/切模块不丢内容
  useEffect(() => {
    let cancelled = false
    Promise.all([getTones(), getSessions(PAGE).catch(() => [] as GenerationSession[])])
      .then(([t, sess]) => {
        if (cancelled) return
        setTones(t)
        setSessions(sess)
        if (sess.length) restoreSession(sess[0], t)
        else setToneId(t[0]?.id)
      })
      .catch((e) => message.error(`加载失败：${e instanceof Error ? e.message : '请刷新重试'}`))
      .finally(() => {
        if (!cancelled) setSessionsLoading(false)
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [message])

  // 从新闻库「用它生成」跳转带入：填充 prompt 模板 + 记录事实底稿（供发送时 grounding）
  useEffect(() => {
    if (prefillNews) setInput(`基于「${prefillNews}」这条，写 5 条短文案，钩子要强、能引发 FOMO。`)
    if (citedContext) setCitedNews(citedContext)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prefillNews])

  const handleSend = async (text: string) => {
    const content = text.trim()
    if (!content) return
    if (!toneId) {
      message.warning('请先选择账号/调性')
      return
    }
    const tone = tones.find((t) => t.id === toneId)
    setMessages((prev) => [...prev, { id: nextId(), role: 'user', content, time: hhmm() }])
    setInput('')
    setLastPrompt(content)
    setGenerating(true)
    setBatch(null)
    try {
      // 引用新闻时把标题 + 事实底稿一起送后端 grounding；否则走通用生成
      const result = await generateVariants(
        toneId,
        content,
        citedNews?.headline || prefillNews || undefined,
        citedNews,
        styleRefs.length ? styleRefs : undefined,
      )
      setBatch(result)
      // 生成已落库为会话，刷新历史列表（含刚产出的这次）
      getSessions(limit).then(setSessions).catch(() => {})
      // 埋点：记录一次生成（含来源），fire-and-forget，失败不影响 UX
      logEvent({ eventType: citedNews ? 'generate_from_news' : 'generate', toneId }).catch(() => {})
      const grounded = citedNews
        ? `（已结合引用新闻的 ${citedNews.keyFacts.length} 项关键事实${citedNews.tickers.length ? ` 与标的 ${citedNews.tickers.join('、')}` : ''}）`
        : ''
      setMessages((prev) => [
        ...prev,
        {
          id: nextId(),
          role: 'ai',
          content: `收到！已基于该需求为 ${tone?.handle} 生成 ${result.variants.length} 条短文案变体${grounded}，均已完成合规扫描与打分。`,
          time: hhmm(),
        },
      ])
    } catch (e) {
      message.error(`生成失败：${e instanceof Error ? e.message : '请稍后重试'}`)
      setMessages((prev) => [
        ...prev,
        { id: nextId(), role: 'ai', content: '⚠️ 生成失败了，请检查网络或稍后重试。', time: hhmm() },
      ])
    } finally {
      setGenerating(false)
    }
  }

  const handleAdopt = (v: Variant) => {
    if (v.compliance === 'blocked') {
      message.error('该变体禁词命中，已改写，请复核后再采用')
      return
    }
    // 记强正信号（采用）；fire-and-forget，失败不影响本地状态
    confirmVariant(v.id).catch(() => {})
    // 本地把该变体标记为已确认，卡片上的「未确认」随之消失
    setBatch((b) => (b ? { ...b, variants: b.variants.map((x) => (x.id === v.id ? { ...x, confirmed: true } : x)) } : b))
    message.success(`已采用变体 #${v.rank}`)
  }

  // 替换 batch 中的某条变体（编辑/重新生成后回填）
  const replaceVariant = (updated: Variant) =>
    setBatch((b) => (b ? { ...b, variants: b.variants.map((x) => (x.id === updated.id ? updated : x)) } : b))

  // 编辑正文：服务端重跑合规后回填。抛错交给 VariantCard 提示。
  const handleEdit = async (v: Variant, body: string) => {
    const updated = await editVariant(v.id, body)
    replaceVariant(updated)
    if (updated.compliance === 'blocked') message.warning('编辑后命中禁词，已标红，请再复核')
    else message.success('已保存并通过合规校验')
  }

  // 重新生成该条：复用最近一次需求描述作为 prompt。
  const handleRegenerate = async (v: Variant) => {
    const prompt = lastPrompt || '按该变体的维度换一个新表达重写'
    const updated = await regenerateVariant(v.id, prompt)
    replaceVariant(updated)
    message.success(`变体 #${v.rank} 已重新生成`)
  }

  // 快捷 chips：带 modifier 直接触发一次新生成（无历史需求时退化为填入输入框）
  const handleQuickAction = (label: string) => {
    if (generating) return
    if (lastPrompt) handleSend(`${lastPrompt}（要求：${label}）`)
    else setInput((prev) => (prev ? `${prev} ${label}` : label))
  }

  // 引用新闻：跳新闻库，用「用它生成」回带（回带逻辑已在 NewsPage）
  const handleCiteNews = () => navigate('/news')

  // 历史：收藏（乐观更新 + 失败回滚）
  const handleToggleFavorite = (s: GenerationSession) => {
    const next = !s.favorite
    setSessions((prev) => prev.map((x) => (x.id === s.id ? { ...x, favorite: next } : x)))
    toggleSessionFavorite(s.id, next)
      .then(() => getSessions(limit).then(setSessions)) // 重排（收藏优先）
      .catch((e) => {
        setSessions((prev) => prev.map((x) => (x.id === s.id ? { ...x, favorite: s.favorite } : x)))
        message.error(e instanceof Error ? e.message : '操作失败')
      })
  }

  // 历史：删除（确认 → 删库 → 移除；若删的是当前会话则清空工作台）
  const handleDeleteSession = (s: GenerationSession) => {
    modal.confirm({
      title: '删除这条历史生成？',
      content: s.prompt,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await deleteSession(s.id)
          setSessions((prev) => prev.filter((x) => x.id !== s.id))
          if (batch?.sessionId === s.id) {
            setBatch(null)
            setMessages([])
            setLastPrompt('')
          }
          message.success('已删除')
        } catch (e) {
          message.error(e instanceof Error ? e.message : '删除失败')
        }
      },
    })
  }

  // 历史：查看更多（递增 limit 重新拉取）
  const handleLoadMore = () => {
    const next = limit + PAGE
    setLimit(next)
    getSessions(next).then(setSessions).catch(() => {})
  }

  return (
    <div style={{ display: 'flex', gap: 16, height: 'calc(100vh - 64px - 48px)' }}>
      <div style={{ flex: '0 0 360px', height: '100%' }}>
        <HistoryPanel
          sessions={sessions}
          tones={tones}
          activeSessionId={batch?.sessionId}
          loading={sessionsLoading}
          canLoadMore={sessions.length >= limit}
          onRestore={(s) => restoreSession(s, tones)}
          onToggleFavorite={handleToggleFavorite}
          onDelete={handleDeleteSession}
          onLoadMore={handleLoadMore}
        />
      </div>
      <div style={{ flex: '0 0 34%', minWidth: 340, height: '100%' }}>
        <ChatPanel
          tones={tones}
          toneId={toneId}
          onToneChange={setToneId}
          messages={messages}
          input={input}
          onInput={setInput}
          onSend={handleSend}
          generating={generating}
          onQuickAction={handleQuickAction}
          onCiteNews={handleCiteNews}
          styleRefs={styleRefs}
          onStyleRefsChange={setStyleRefs}
        />
      </div>
      <div style={{ flex: 1, minWidth: 380, height: '100%', overflow: 'hidden' }}>
        <VariantList
          batch={batch}
          generating={generating}
          onAdopt={handleAdopt}
          onEdit={handleEdit}
          onRegenerate={handleRegenerate}
          sort={sort}
          onSort={setSort}
        />
      </div>
    </div>
  )
}
