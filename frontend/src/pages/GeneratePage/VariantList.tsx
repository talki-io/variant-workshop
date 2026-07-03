import { Select, Space, Tag, Skeleton, Empty, Card } from 'antd'
import { CheckCircleOutlined } from '@ant-design/icons'
import VariantCard from '../../components/VariantCard'
import { brand } from '../../theme/tokens'
import type { Variant, VariantBatch } from '../../types'

interface Props {
  batch: VariantBatch | null
  generating: boolean
  onAdopt: (v: Variant) => void
  onEdit: (v: Variant, body: string) => Promise<void>
  onRegenerate: (v: Variant) => Promise<void>
  sort: string
  onSort: (v: string) => void
}

export default function VariantList({ batch, generating, onAdopt, onEdit, onRegenerate, sort, onSort }: Props) {
  if (generating && !batch) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {[0, 1, 2].map((i) => (
          <Card key={i} size="small" style={{ border: `1px solid ${brand.border}` }}>
            <Skeleton active paragraph={{ rows: 3 }} />
          </Card>
        ))}
      </div>
    )
  }

  if (!batch) {
    return (
      <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center' }}>
        <Empty
          description={
            <span style={{ color: brand.textSecondary }}>
              选好账号/调性，在左侧描述你想要的文案，变体会出现在这里
            </span>
          }
        />
      </div>
    )
  }

  if (batch.variants.length === 0) {
    return (
      <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center' }}>
        <Empty
          description={
            <span style={{ color: brand.textSecondary }}>本次没有产出变体，换个角度或调整需求再试试</span>
          }
        />
      </div>
    )
  }

  const sorted = [...batch.variants].sort((a, b) =>
    sort === 'score' ? b.score - a.score : sort === 'ai' ? a.aiScore - b.aiScore : a.rank - b.rank,
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, height: '100%' }}>
      {/* 工具条 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <span style={{ fontWeight: 600 }}>共 {batch.variants.length} 个变体</span>
        <Select
          value={sort}
          onChange={onSort}
          size="small"
          style={{ width: 130 }}
          options={[
            { value: 'score', label: '按综合分' },
            { value: 'ai', label: '按 AI 味' },
            { value: 'rank', label: '按默认排序' },
          ]}
        />
        <div style={{ flex: 1 }} />
        <Tag icon={<CheckCircleOutlined />} color="success" bordered={false} style={{ fontSize: 12 }}>
          两两风格距离 {batch.diversity} · 多样性良好
        </Tag>
      </div>

      {/* 变体卡片列表 */}
      <div style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 12, paddingRight: 4 }}>
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          {sorted.map((v) => (
            <VariantCard key={v.id} variant={v} onAdopt={onAdopt} onEdit={onEdit} onRegenerate={onRegenerate} />
          ))}
        </Space>
      </div>
    </div>
  )
}
