import { useMemo, useState } from 'react'
import { Card, Input, Select, Button, Tag, Dropdown, Empty, Tooltip } from 'antd'
import { SearchOutlined, StarFilled, StarOutlined, MoreOutlined, DownOutlined } from '@ant-design/icons'
import type { GenerationSession, Tone } from '../../types'
import { brand } from '../../theme/tokens'

interface Props {
  sessions: GenerationSession[]
  tones: Tone[]
  activeSessionId?: string
  loading?: boolean
  canLoadMore?: boolean
  onRestore: (s: GenerationSession) => void
  onToggleFavorite: (s: GenerationSession) => void
  onDelete: (s: GenerationSession) => void
  onLoadMore: () => void
}

/** created_at ("YYYY-MM-DD HH:MM:SS") → 今天/昨天/前天 HH:MM 或 MM-DD HH:MM */
function relTime(s: string): string {
  const d = new Date(s.replace(' ', 'T'))
  if (isNaN(d.getTime())) return s
  const startOf = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime()
  const days = Math.round((startOf(new Date()) - startOf(d)) / 86_400_000)
  const p = (n: number) => String(n).padStart(2, '0')
  const hm = `${p(d.getHours())}:${p(d.getMinutes())}`
  if (days === 0) return `今天 ${hm}`
  if (days === 1) return `昨天 ${hm}`
  if (days === 2) return `前天 ${hm}`
  return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${hm}`
}

export default function HistoryPanel({
  sessions,
  tones,
  activeSessionId,
  loading,
  canLoadMore,
  onRestore,
  onToggleFavorite,
  onDelete,
  onLoadMore,
}: Props) {
  const [keyword, setKeyword] = useState('')
  const [sort, setSort] = useState<'time' | 'fav'>('time')

  const handleOf = (toneId: string) => tones.find((t) => t.id === toneId)?.handle ?? toneId

  const list = useMemo(() => {
    let l = sessions
    if (keyword) l = l.filter((s) => s.prompt.toLowerCase().includes(keyword.toLowerCase()))
    l = [...l].sort((a, b) =>
      sort === 'fav'
        ? Number(b.favorite) - Number(a.favorite) || b.createdAt.localeCompare(a.createdAt)
        : b.createdAt.localeCompare(a.createdAt),
    )
    return l
  }, [sessions, keyword, sort])

  return (
    <Card
      title="历史记录"
      style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
      styles={{ body: { display: 'flex', flexDirection: 'column', height: '100%', padding: 16, overflow: 'hidden' } }}
    >
      {/* 搜索 + 排序 */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <Input
          prefix={<SearchOutlined style={{ color: brand.textSecondary }} />}
          placeholder="搜索历史任务…"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          allowClear
        />
        <Select
          value={sort}
          onChange={setSort}
          style={{ width: 108, flex: 'none' }}
          options={[
            { value: 'time', label: '按时间' },
            { value: 'fav', label: '按收藏' },
          ]}
        />
      </div>

      {/* 会话卡片列表 */}
      <div style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 10, paddingRight: 2 }}>
        {list.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            style={{ marginTop: 48 }}
            description={
              <span style={{ color: brand.textSecondary }}>
                {sessions.length === 0 ? (loading ? '加载中…' : '暂无历史生成') : '没有匹配的历史任务'}
              </span>
            }
          />
        ) : (
          list.map((s) => {
            const active = s.id === activeSessionId
            const sub = active ? 'rgba(255,255,255,0.82)' : brand.textSecondary
            return (
              <div
                key={s.id}
                onClick={() => onRestore(s)}
                style={{
                  cursor: 'pointer',
                  borderRadius: 10,
                  padding: '12px 14px',
                  background: active ? brand.primary : '#fff',
                  border: `1px solid ${active ? brand.primary : brand.border}`,
                  boxShadow: active ? '0 4px 12px rgba(37,99,235,0.25)' : 'none',
                  transition: 'all .15s',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                  <div
                    style={{
                      flex: 1,
                      minWidth: 0,
                      fontSize: 14,
                      fontWeight: 600,
                      lineHeight: 1.45,
                      color: active ? '#fff' : brand.textBase,
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                    }}
                  >
                    {s.prompt}
                  </div>
                  <Tooltip title={s.favorite ? '取消收藏' : '收藏'}>
                    {s.favorite ? (
                      <StarFilled
                        onClick={(e) => { e.stopPropagation(); onToggleFavorite(s) }}
                        style={{ color: '#F59E0B', fontSize: 15, flex: 'none' }}
                      />
                    ) : (
                      <StarOutlined
                        onClick={(e) => { e.stopPropagation(); onToggleFavorite(s) }}
                        style={{ color: active ? 'rgba(255,255,255,0.9)' : brand.textSecondary, fontSize: 15, flex: 'none' }}
                      />
                    )}
                  </Tooltip>
                  <Dropdown
                    trigger={['click']}
                    menu={{
                      items: [{ key: 'del', label: '删除', danger: true }],
                      onClick: ({ key, domEvent }) => { domEvent.stopPropagation(); if (key === 'del') onDelete(s) },
                    }}
                  >
                    <MoreOutlined
                      onClick={(e) => e.stopPropagation()}
                      style={{ color: active ? 'rgba(255,255,255,0.9)' : brand.textSecondary, fontSize: 15, flex: 'none' }}
                    />
                  </Dropdown>
                </div>
                <div style={{ fontSize: 12, color: sub, marginTop: 6 }}>{handleOf(s.toneId)}</div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 8 }}>
                  <span style={{ fontSize: 12, color: sub }}>{relTime(s.createdAt)}</span>
                  {/* 统一用 backgroundColor（非简写），避免与 antd color prop 的 backgroundColor 跨渲染混用触发告警 */}
                  <Tag
                    bordered={false}
                    style={{
                      margin: 0,
                      backgroundColor: active ? 'rgba(255,255,255,0.22)' : '#ECFDF3',
                      color: active ? '#fff' : brand.success,
                    }}
                  >
                    已生成
                  </Tag>
                </div>
              </div>
            )
          })
        )}
      </div>

      {canLoadMore && (
        <Button type="text" block onClick={onLoadMore} style={{ marginTop: 8, color: brand.textSecondary }}>
          查看更多历史 <DownOutlined />
        </Button>
      )}
    </Card>
  )
}
