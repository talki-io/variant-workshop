import type { ReactNode } from 'react'
import { Card, Tag, Space, Button, Empty, App } from 'antd'
import { ExportOutlined, CopyOutlined, ArrowRightOutlined, CloseOutlined } from '@ant-design/icons'
import HeatBar from '../../components/HeatBar'
import { brand } from '../../theme/tokens'
import type { NewsItem } from '../../types'

interface Props {
  item: NewsItem | null
  onGenerate: (item: NewsItem) => void
  onClose: () => void
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <div style={{ fontSize: 12, color: brand.textSecondary, marginBottom: 6 }}>{label}</div>
      {children}
    </div>
  )
}

export default function NewsDetailPanel({ item, onGenerate, onClose }: Props) {
  const { message } = App.useApp()

  const copy = () => {
    if (!item) return
    const text = [
      item.headline,
      '',
      `来源：${item.source} · ${item.publishedLabel}`,
      `关键事实：${item.keyFacts.join('、')}`,
      `相关标的：${item.tickers.join('、')}`,
      `原文：${item.url}`,
    ].join('\n')
    navigator.clipboard?.writeText(text)
    message.success('已复制内容')
  }

  return (
    <Card
      title="新闻详情"
      extra={item ? <Button type="text" icon={<CloseOutlined />} onClick={onClose} /> : null}
      style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
      styles={{ body: { flex: 1, display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden' } }}
    >
      {!item ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={<span style={{ color: brand.textSecondary }}>选择左侧新闻查看详情</span>}
          style={{ margin: 'auto' }}
        />
      ) : (
        <>
          {/* 可滚动内容区 */}
          <div style={{ flex: 1, overflow: 'auto', padding: 20 }}>
            <Field label="标题">
              <div style={{ fontSize: 15, fontWeight: 600, lineHeight: 1.6 }}>{item.headline}</div>
            </Field>
            <Field label="来源与时间">
              <Space wrap>
                <Tag color="blue" bordered={false}>
                  {item.source}
                </Tag>
                <span style={{ color: brand.textSecondary }}>{item.publishedLabel}</span>
              </Space>
            </Field>
            <Field label="关键事实 (key_facts)">
              <Space size={6} wrap>
                {item.keyFacts.map((f) => (
                  <Tag key={f} bordered={false} style={{ background: '#F3F4F6', margin: 0 }}>
                    {f}
                  </Tag>
                ))}
              </Space>
            </Field>
            <Field label="相关标的 (tickers)">
              <Space size={6} wrap>
                {item.tickers.length ? (
                  item.tickers.map((t) => (
                    <Tag key={t} color="blue" bordered={false}>
                      {t}
                    </Tag>
                  ))
                ) : (
                  <span style={{ color: brand.textSecondary }}>—</span>
                )}
              </Space>
            </Field>
            <Field label="角度提示 (angle_hints)">
              {item.angleHints.length ? (
                <ul style={{ margin: 0, paddingInlineStart: 18, lineHeight: 1.9 }}>
                  {item.angleHints.map((a) => (
                    <li key={a}>{a}</li>
                  ))}
                </ul>
              ) : (
                <span style={{ color: brand.textSecondary }}>—</span>
              )}
            </Field>
            <Field label="新鲜度 (freshness)">
              {item.freshness === 'breaking' ? (
                <Tag color="error" bordered={false}>
                  突发
                </Tag>
              ) : item.freshness === 'recent' ? (
                <Tag color="warning" bordered={false}>
                  近期
                </Tag>
              ) : (
                <Tag bordered={false}>较旧</Tag>
              )}
            </Field>
            <Field label="热度 (heat)">
              <HeatBar heat={item.heat} />
            </Field>
            <Field label="原文链接">
              <a href={item.url} target="_blank" rel="noreferrer" style={{ color: brand.primary, wordBreak: 'break-all' }}>
                {item.url} <ExportOutlined />
              </a>
            </Field>
          </div>

          {/* 固定底部操作 */}
          <div style={{ padding: 16, borderTop: `1px solid ${brand.border}`, display: 'flex', gap: 8 }}>
            <Button icon={<CopyOutlined />} onClick={copy}>
              复制内容
            </Button>
            <Button type="primary" style={{ flex: 1 }} onClick={() => onGenerate(item)}>
              用它生成 <ArrowRightOutlined />
            </Button>
          </div>
        </>
      )}
    </Card>
  )
}
