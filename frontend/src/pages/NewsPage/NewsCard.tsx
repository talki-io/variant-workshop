import { Card, Tag, Button, Space } from 'antd'
import { LikeOutlined, DislikeOutlined, ArrowRightOutlined } from '@ant-design/icons'
import HeatBar from '../../components/HeatBar'
import { brand } from '../../theme/tokens'
import type { NewsItem, LabelState } from '../../types'

const freshColor: Record<NewsItem['freshness'], string> = {
  breaking: brand.error,
  recent: brand.warning,
  old: '#9CA3AF',
}

interface Props {
  item: NewsItem
  selected?: boolean
  onSelect: (item: NewsItem) => void
  onLabel: (id: string, label: LabelState) => void
  onGenerate: (item: NewsItem) => void
}

export default function NewsCard({ item, selected, onSelect, onLabel, onGenerate }: Props) {
  // 阻止操作按钮点击冒泡到卡片选中
  const stop = (fn: () => void) => (e: React.MouseEvent) => {
    e.stopPropagation()
    fn()
  }

  return (
    <Card
      size="small"
      hoverable
      onClick={() => onSelect(item)}
      style={{
        borderInlineStart: `4px solid ${freshColor[item.freshness]}`,
        boxShadow: selected ? `0 0 0 2px ${brand.primary}` : undefined,
        cursor: 'pointer',
      }}
      styles={{ body: { padding: 16 } }}
    >
      <div style={{ display: 'flex', gap: 16 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
            {item.freshness === 'breaking' && (
              <Tag color="error" bordered={false} style={{ marginTop: 2 }}>
                突发
              </Tag>
            )}
            <span style={{ fontSize: 15, fontWeight: 600, color: brand.textBase, lineHeight: 1.5 }}>
              {item.headline}
            </span>
          </div>
          <Space size={8} style={{ marginTop: 8, color: brand.textSecondary, fontSize: 12 }}>
            <Tag color="blue" bordered={false}>
              {item.source}
            </Tag>
            <span>{item.publishedLabel}</span>
          </Space>
          <div style={{ marginTop: 10 }}>
            <Space size={6} wrap>
              {item.keyFacts.map((f) => (
                <Tag key={f} bordered={false} style={{ background: '#F3F4F6', margin: 0 }}>
                  {f}
                </Tag>
              ))}
            </Space>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 12, minWidth: 240 }}>
          <HeatBar heat={item.heat} />
          <Space size={4}>
            <Button
              size="small"
              type={item.label === 'relevant' ? 'primary' : 'default'}
              icon={<LikeOutlined />}
              onClick={stop(() => onLabel(item.id, 'relevant'))}
            >
              相关
            </Button>
            <Button
              size="small"
              danger={item.label === 'irrelevant'}
              icon={<DislikeOutlined />}
              onClick={stop(() => onLabel(item.id, 'irrelevant'))}
            >
              不相关
            </Button>
            <span style={{ fontSize: 12, color: brand.textSecondary }}>打标可选</span>
            <Button size="small" type="link" onClick={stop(() => onGenerate(item))}>
              用它生成 <ArrowRightOutlined />
            </Button>
          </Space>
        </div>
      </div>
    </Card>
  )
}
