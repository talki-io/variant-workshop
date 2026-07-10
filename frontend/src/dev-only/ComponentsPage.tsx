import { Card, Col, Row, Typography, Divider, Table } from 'antd'
import VariantCard from '../components/VariantCard'
import ToneSelector from '../components/ToneSelector'
import { variantBatch } from './mocks/variants'
import { tones } from './mocks/tones'
import { brand } from '../theme/tokens'

const { Title, Paragraph } = Typography

const tokenRows = [
  { k: '主色', v: brand.primary },
  { k: '成功', v: brand.success },
  { k: '警告', v: brand.warning },
  { k: '危险', v: brand.error },
  { k: '中性文字', v: brand.textBase },
  { k: '次级文字', v: brand.textSecondary },
  { k: '边框 / 分割', v: brand.border },
  { k: '背景', v: brand.bgLayout },
  { k: '卡片背景', v: brand.bgContainer },
]

export default function ComponentsPage() {
  const [pass, soft, blocked] = [
    variantBatch.variants[0],
    variantBatch.variants[1],
    variantBatch.variants[4],
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div>
        <Title level={3} style={{ margin: 0 }}>关键组件规范</Title>
        <Paragraph type="secondary" style={{ marginTop: 4 }}>
          用于展示单条生成变体的综合评分、维度评估与操作能力，支持合规/提示/违规三种状态。
        </Paragraph>
      </div>

      <Card title="VariantCard（变体卡片）· 三态">
        <Row gutter={16}>
          <Col span={8}>
            <div style={{ marginBottom: 8, fontWeight: 600 }}>A. 合规（绿色）</div>
            <VariantCard variant={pass} />
          </Col>
          <Col span={8}>
            <div style={{ marginBottom: 8, fontWeight: 600 }}>B. 软提示（琥珀色）</div>
            <VariantCard variant={soft} />
          </Col>
          <Col span={8}>
            <div style={{ marginBottom: 8, fontWeight: 600 }}>C. 禁词命中（红色）</div>
            <VariantCard variant={blocked} />
          </Col>
        </Row>
      </Card>

      <Row gutter={16}>
        <Col span={14}>
          <Card title="ToneSelector（语感选择器）">
            <ToneSelector tones={tones} value={tones[0].id} onChange={() => {}} />
          </Card>
        </Col>
        <Col span={10}>
          <Card title="设计标记（Design Tokens）">
            <Table
              rowKey="k"
              pagination={false}
              size="small"
              showHeader={false}
              columns={[
                { dataIndex: 'k', width: 100 },
                {
                  dataIndex: 'v',
                  render: (v: string) => (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ width: 16, height: 16, borderRadius: 4, background: v, border: `1px solid ${brand.border}` }} />
                      <code>{v}</code>
                    </span>
                  ),
                },
              ]}
              dataSource={tokenRows}
            />
            <Divider style={{ margin: '12px 0' }} />
            <Paragraph type="secondary" style={{ fontSize: 13, margin: 0 }}>
              圆角：卡片 12px · 按钮 8px · 标签 999px<br />
              阴影：卡片 0 1px 4px rgba(16,24,40,0.05)
            </Paragraph>
          </Card>
        </Col>
      </Row>
    </div>
  )
}
