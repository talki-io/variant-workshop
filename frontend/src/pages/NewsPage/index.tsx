import { useEffect, useMemo, useRef, useState, type UIEvent } from 'react'
import { Card, Input, Select, DatePicker, Switch, Space, Empty, Spin, App } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import NewsCard from './NewsCard'
import NewsDetailPanel from './NewsDetailPanel'
import { getNews, labelNews } from '../../services'
import type { NewsItem, LabelState } from '../../types'
import { brand } from '../../theme/tokens'

const { RangePicker } = DatePicker
const PAGE = 20 // 每页条数
const SCROLL_THRESHOLD = 240 // 距底部多少 px 触发加载更多

const fmt = (d: unknown): string | undefined =>
  d && typeof (d as { format?: unknown }).format === 'function'
    ? (d as { format: (f: string) => string }).format('YYYY-MM-DD')
    : undefined

export default function NewsPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { message } = App.useApp()

  // —— 筛选条件（变化即重置分页、走接口）——
  const [keyword, setKeyword] = useState((location.state as { q?: string } | null)?.q ?? '')
  const [debouncedKw, setDebouncedKw] = useState(keyword)
  const [sources, setSources] = useState<string[]>([])
  const [sortBy, setSortBy] = useState<'heat' | 'time'>('time')
  const [dateRange, setDateRange] = useState<[unknown, unknown] | null>(null)
  const [onlyUnlabeled, setOnlyUnlabeled] = useState(false)

  // —— 分页数据 ——
  const [items, setItems] = useState<NewsItem[]>([])
  const [total, setTotal] = useState(0)
  const [sourceOptions, setSourceOptions] = useState<string[]>([])
  const [loading, setLoading] = useState(true) // 首屏/换条件加载
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [activeId, setActiveId] = useState<string | null>(null)
  const [reloadTick, setReloadTick] = useState(0) // 手动重试触发器

  const loadingMoreRef = useRef(false) // 防抖：滚动连发时只发一次
  const scrollRef = useRef<HTMLDivElement>(null)

  const dateFrom = fmt(dateRange?.[0])
  const dateTo = fmt(dateRange?.[1])

  // 搜索输入防抖 → debouncedKw
  useEffect(() => {
    const t = setTimeout(() => setDebouncedKw(keyword), 400)
    return () => clearTimeout(t)
  }, [keyword])

  // 顶部搜索跳转带入关键词（组件已挂载时同步）
  const stateQ = (location.state as { q?: string } | null)?.q
  useEffect(() => {
    if (stateQ !== undefined) setKeyword(stateQ)
  }, [stateQ, location.key])

  const query = useMemo(
    () => ({ q: debouncedKw, sources, sort: sortBy, onlyUnlabeled, dateFrom, dateTo }),
    [debouncedKw, sources, sortBy, onlyUnlabeled, dateFrom, dateTo],
  )

  // 条件变化 → 重置分页，拉第一页
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    getNews({ ...query, limit: PAGE, offset: 0 })
      .then((res) => {
        if (cancelled) return
        setItems(res.items)
        setTotal(res.total)
        setSourceOptions(res.sources)
        if (scrollRef.current) scrollRef.current.scrollTop = 0
      })
      .catch((e) => !cancelled && setError(e instanceof Error ? e : new Error('加载失败')))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [query, reloadTick])

  // 加载更多（下一页，追加）
  const loadMore = () => {
    if (loadingMoreRef.current || loading || items.length >= total) return
    loadingMoreRef.current = true
    setLoadingMore(true)
    getNews({ ...query, limit: PAGE, offset: items.length })
      .then((res) => {
        setItems((prev) => {
          // 按 id 去重后追加（防止分页边界重复）
          const seen = new Set(prev.map((n) => n.id))
          return [...prev, ...res.items.filter((n) => !seen.has(n.id))]
        })
        setTotal(res.total)
      })
      .catch((e) => message.error(e instanceof Error ? e.message : '加载更多失败'))
      .finally(() => {
        loadingMoreRef.current = false
        setLoadingMore(false)
      })
  }

  const onScroll = (e: UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget
    if (el.scrollHeight - el.scrollTop - el.clientHeight < SCROLL_THRESHOLD) loadMore()
  }

  // 选中：默认第一条；当前选中被筛掉时改选第一条
  useEffect(() => {
    if (items.length === 0) {
      if (activeId !== null) setActiveId(null)
      return
    }
    if (!activeId || !items.some((n) => n.id === activeId)) setActiveId(items[0].id)
  }, [items, activeId])

  const active = useMemo(() => items.find((n) => n.id === activeId) ?? null, [items, activeId])

  // 打标落库：乐观更新 + 失败回滚（点已有标签=取消→none）
  const handleLabel = (id: string, label: LabelState) => {
    const current = items.find((n) => n.id === id)
    if (!current) return
    const next: LabelState = current.label === label ? 'none' : label
    setItems((prev) => prev.map((n) => (n.id === id ? { ...n, label: next } : n)))
    labelNews(id, next).catch((e) => {
      setItems((prev) => prev.map((n) => (n.id === id ? { ...n, label: current.label } : n)))
      message.error(e instanceof Error ? e.message : '打标失败，已回滚')
    })
  }

  const handleGenerate = (item: NewsItem) =>
    navigate('/generate', {
      state: {
        newsHeadline: item.headline,
        newsContext: {
          headline: item.headline,
          keyFacts: item.keyFacts,
          tickers: item.tickers,
          angleHints: item.angleHints,
        },
      },
    })

  const hasMore = items.length < total
  const sourceSelectOptions = useMemo(
    () => sourceOptions.map((s) => ({ label: s, value: s })),
    [sourceOptions],
  )

  return (
    <div style={{ display: 'flex', gap: 16, height: 'calc(100vh - 64px - 48px)' }}>
      {/* 左：筛选栏 + 新闻列表 */}
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 16 }}>
        <Card size="small" styles={{ body: { padding: 16 } }}>
          <Space size={16} wrap>
            <Input
              prefix={<SearchOutlined style={{ color: brand.textSecondary }} />}
              placeholder="搜索新闻标题或关键词…"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              style={{ width: 240 }}
              allowClear
            />
            <Space size={8}>
              <span style={{ color: brand.textSecondary }}>来源</span>
              <Select
                mode="multiple"
                placeholder="全部来源"
                value={sources}
                onChange={setSources}
                options={sourceSelectOptions}
                style={{ minWidth: 200 }}
                maxTagCount="responsive"
              />
            </Space>
            <Space size={8}>
              <span style={{ color: brand.textSecondary }}>时间</span>
              <RangePicker value={dateRange as never} onChange={(v) => setDateRange(v as [unknown, unknown] | null)} />
            </Space>
            <Select
              value={sortBy}
              onChange={(v) => setSortBy(v)}
              style={{ width: 120 }}
              options={[
                { value: 'time', label: '时间排序' },
                { value: 'heat', label: '热度排序' },
              ]}
            />
            <Space size={8}>
              <Switch checked={onlyUnlabeled} onChange={setOnlyUnlabeled} />
              <span>仅看未打标</span>
            </Space>
            <span style={{ color: brand.textSecondary, fontSize: 13 }}>共 {total} 条</span>
          </Space>
        </Card>

        <div ref={scrollRef} onScroll={onScroll} style={{ flex: 1, overflow: 'auto', paddingRight: 4 }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: 80 }}>
              <Spin />
            </div>
          ) : error ? (
            <Empty
              style={{ padding: 60 }}
              description={
                <span style={{ color: brand.textSecondary }}>
                  {error.message}
                  <a style={{ marginLeft: 8 }} onClick={() => setReloadTick((t) => t + 1)}>
                    重试
                  </a>
                </span>
              }
            />
          ) : items.length === 0 ? (
            <Empty
              style={{ padding: 60 }}
              description={<span style={{ color: brand.textSecondary }}>没有符合条件的新闻</span>}
            />
          ) : (
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              {items.map((n) => (
                <NewsCard
                  key={n.id}
                  item={n}
                  selected={n.id === activeId}
                  onSelect={(item) => setActiveId(item.id)}
                  onLabel={handleLabel}
                  onGenerate={handleGenerate}
                />
              ))}
              {/* 底部加载态 / 到底提示 */}
              <div style={{ textAlign: 'center', padding: '12px 0', color: brand.textSecondary, fontSize: 13 }}>
                {loadingMore ? (
                  <Spin size="small" />
                ) : hasMore ? (
                  <a onClick={loadMore}>加载更多</a>
                ) : (
                  '— 没有更多了 —'
                )}
              </div>
            </Space>
          )}
        </div>
      </div>

      {/* 右：新闻详情常驻面板 */}
      <div style={{ flex: '0 0 380px', height: '100%' }}>
        <NewsDetailPanel item={active} onGenerate={handleGenerate} onClose={() => setActiveId(null)} />
      </div>
    </div>
  )
}
