import { useEffect, useMemo, useState } from 'react'
import { Card, Input, Select, DatePicker, Switch, Space, Empty, App } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import NewsCard from './NewsCard'
import NewsDetailPanel from './NewsDetailPanel'
import AsyncBoundary from '../../components/AsyncBoundary'
import { useAsyncData } from '../../hooks/useAsyncData'
import { getNews, labelNews } from '../../services'
import type { NewsItem, LabelState } from '../../types'
import { brand } from '../../theme/tokens'

const { RangePicker } = DatePicker

export default function NewsPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { message } = App.useApp()
  const { data, loading, error, reload, setData } = useAsyncData(getNews)
  const list = useMemo(() => data ?? [], [data])
  // 顶部搜索框跳转带入的关键词（HeaderBar → navigate('/news', {state:{q}})）
  const [keyword, setKeyword] = useState((location.state as { q?: string } | null)?.q ?? '')
  const [sources, setSources] = useState<string[]>([])
  const [sortBy, setSortBy] = useState<'heat' | 'time'>('heat')
  const [dateRange, setDateRange] = useState<[unknown, unknown] | null>(null)
  const [onlyUnlabeled, setOnlyUnlabeled] = useState(false)
  const [activeId, setActiveId] = useState<string | null>(null)

  // 已在 /news 时再次从顶部搜索跳转（组件不重挂），同步关键词
  const stateQ = (location.state as { q?: string } | null)?.q
  useEffect(() => {
    if (stateQ) setKeyword(stateQ)
  }, [stateQ, location.key])

  const sourceOptions = useMemo(
    () => Array.from(new Set(list.map((n) => n.source))).map((s) => ({ label: s, value: s })),
    [list],
  )

  const filtered = useMemo(
    () =>
      list
        .filter((n) => {
          if (keyword && !n.headline.toLowerCase().includes(keyword.toLowerCase())) return false
          if (sources.length && !sources.includes(n.source)) return false
          if (onlyUnlabeled && n.label !== 'none') return false
          if (dateRange && dateRange[0] && dateRange[1]) {
            const t = new Date(n.publishedAt).getTime()
            const start = (dateRange[0] as { valueOf(): number }).valueOf()
            const end = (dateRange[1] as { valueOf(): number }).valueOf() + 86_400_000 // 含当天
            if (t < start || t > end) return false
          }
          return true
        })
        .sort((a, b) => (sortBy === 'heat' ? b.heat - a.heat : b.publishedAt.localeCompare(a.publishedAt))),
    [list, keyword, sources, onlyUnlabeled, dateRange, sortBy],
  )

  // 默认选中筛选结果第一条；当前选中被筛掉时自动改选第一条
  useEffect(() => {
    if (filtered.length === 0) {
      if (activeId !== null) setActiveId(null)
      return
    }
    if (!activeId || !filtered.some((n) => n.id === activeId)) setActiveId(filtered[0].id)
  }, [filtered, activeId])

  // 详情面板始终反映最新数据（打标后同步），按 id 从 list 派生
  const active = useMemo(() => list.find((n) => n.id === activeId) ?? null, [list, activeId])

  // 打标落库：乐观更新 UI，失败回滚并提示（点已有标签 = 取消 → none）
  const handleLabel = (id: string, label: LabelState) => {
    const current = list.find((n) => n.id === id)
    if (!current) return
    const next: LabelState = current.label === label ? 'none' : label
    setData((prev) => (prev ?? []).map((n) => (n.id === id ? { ...n, label: next } : n)))
    labelNews(id, next).catch((e) => {
      setData((prev) => (prev ?? []).map((n) => (n.id === id ? { ...n, label: current.label } : n)))
      message.error(e instanceof Error ? e.message : '打标失败，已回滚')
    })
  }

  // 引用新闻：带走标题（供 prompt 展示）+ 完整事实底稿（供模型 grounding），不再只传标题
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
                options={sourceOptions}
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
                { value: 'heat', label: '热度排序' },
                { value: 'time', label: '时间排序' },
              ]}
            />
            <Space size={8}>
              <Switch checked={onlyUnlabeled} onChange={setOnlyUnlabeled} />
              <span>仅看未打标</span>
            </Space>
          </Space>
        </Card>

        <div style={{ flex: 1, overflow: 'auto', paddingRight: 4 }}>
          <AsyncBoundary loading={loading} error={error} onRetry={reload}>
            {filtered.length === 0 ? (
              <Empty
                style={{ padding: 60 }}
                description={
                  <span style={{ color: brand.textSecondary }}>
                    {list.length === 0 ? '暂无已采集新闻' : '没有符合筛选条件的新闻'}
                  </span>
                }
              />
            ) : (
              <Space direction="vertical" size={12} style={{ width: '100%' }}>
                {filtered.map((n) => (
                  <NewsCard
                    key={n.id}
                    item={n}
                    selected={n.id === activeId}
                    onSelect={(item) => setActiveId(item.id)}
                    onLabel={handleLabel}
                    onGenerate={handleGenerate}
                  />
                ))}
              </Space>
            )}
          </AsyncBoundary>
        </div>
      </div>

      {/* 右：新闻详情常驻面板 */}
      <div style={{ flex: '0 0 380px', height: '100%' }}>
        <NewsDetailPanel item={active} onGenerate={handleGenerate} onClose={() => setActiveId(null)} />
      </div>
    </div>
  )
}
