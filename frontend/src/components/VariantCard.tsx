import { useState } from 'react'
import { Card, Tag, Button, Space, Tooltip, App, Input } from 'antd'
import {
  CopyOutlined,
  EditOutlined,
  ReloadOutlined,
  SendOutlined,
  SafetyCertificateFilled,
  CheckOutlined,
  CloseOutlined,
} from '@ant-design/icons'
import type { Variant } from '../types'
import { brand } from '../theme/tokens'
import { cleanVariantBody } from '../utils/text'
import ScoreRing from './ScoreRing'
import ComplianceBadge from './ComplianceBadge'

interface Props {
  variant: Variant
  onAdopt?: (v: Variant) => void
  /** 保存编辑后的正文（内部会重跑合规）。返回 Promise 以驱动 loading。 */
  onEdit?: (v: Variant, body: string) => Promise<void>
  /** 重新生成该变体。返回 Promise 以驱动 loading。 */
  onRegenerate?: (v: Variant) => Promise<void>
}

const rankBg: Record<number, string> = {
  1: '#FEF3C7',
  2: '#F3F4F6',
  3: '#FED7AA',
}

/** 正文渲染：把软提示句用黄色波浪下划线高亮 */
function renderBody(body: string, flag?: string) {
  if (!flag || !body.includes(flag)) return body
  const [before, after] = body.split(flag)
  return (
    <>
      {before}
      <span className="soft-flag-underline">{flag}</span>
      {after}
    </>
  )
}

export default function VariantCard({ variant: v, onAdopt, onEdit, onRegenerate }: Props) {
  const { message } = App.useApp()
  // 展示层兜底：解开可能的 JSON/围栏外壳，display/edit/copy 统一用干净正文
  const body = cleanVariantBody(v.body)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(body)
  const [saving, setSaving] = useState(false)
  const [regenerating, setRegenerating] = useState(false)

  const startEdit = () => {
    setDraft(body)
    setEditing(true)
  }

  const saveEdit = async () => {
    const next = draft.trim()
    if (!next) {
      message.warning('正文不能为空')
      return
    }
    if (next === body) {
      setEditing(false)
      return
    }
    setSaving(true)
    try {
      await onEdit?.(v, next)
      setEditing(false)
    } catch (e) {
      message.error(e instanceof Error ? e.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const regenerate = async () => {
    setRegenerating(true)
    try {
      await onRegenerate?.(v)
    } catch (e) {
      message.error(e instanceof Error ? e.message : '重新生成失败')
    } finally {
      setRegenerating(false)
    }
  }

  const dims = [
    `钩子:${v.dimensions.hook}`,
    `结构:${v.dimensions.structure}`,
    `情绪:${v.dimensions.emotion}`,
    v.dimensions.platform,
    `CTA:${v.dimensions.cta}`,
  ]

  return (
    <Card
      size="small"
      style={{ border: `1px solid ${brand.border}`, boxShadow: '0 1px 4px rgba(16,24,40,0.05)' }}
      styles={{ body: { padding: 16 } }}
    >
      {/* 顶部：排名 + 维度标签 + 未确认 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <span
          style={{
            background: rankBg[v.rank] ?? '#F3F4F6',
            color: brand.textBase,
            fontWeight: 700,
            fontSize: 12,
            padding: '2px 8px',
            borderRadius: 6,
          }}
        >
          #{v.rank}
        </span>
        <Space size={4} wrap style={{ flex: 1 }}>
          {dims.map((d) => (
            <Tag key={d} color="blue" bordered={false} style={{ margin: 0, fontSize: 12 }}>
              {d}
            </Tag>
          ))}
        </Space>
        {!v.confirmed && (
          <Tag bordered={false} style={{ margin: 0, color: brand.textSecondary, background: '#F3F4F6' }}>
            未确认
          </Tag>
        )}
      </div>

      {/* 主体：评分环 + 正文 */}
      <div style={{ display: 'flex', gap: 16 }}>
        <ScoreRing score={v.score} />
        <div style={{ flex: 1 }}>
          {editing ? (
            <Input.TextArea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              autoSize={{ minRows: 2, maxRows: 8 }}
              disabled={saving}
              style={{ marginBottom: 8 }}
            />
          ) : (
            <div style={{ fontSize: 14, lineHeight: 1.6, color: brand.textBase, marginBottom: 8, whiteSpace: 'pre-wrap' }}>
              {renderBody(body, v.softFlagSentence)}
            </div>
          )}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
            <ComplianceBadge status={v.compliance} softFlagCount={v.softFlagCount} />
            <span style={{ fontSize: 12, color: brand.textSecondary }}>
              AI味 {v.aiScore}/100 · 风格距离 {v.styleDistance}
              <Tooltip title="风格贴合度（越小越像人）">
                <SafetyCertificateFilled style={{ color: brand.success, marginLeft: 6 }} />
              </Tooltip>
            </span>
          </div>
        </div>
      </div>

      {/* 操作行 */}
      <div style={{ borderTop: `1px solid ${brand.border}`, marginTop: 12, paddingTop: 12 }}>
        {editing ? (
          <Space>
            <Button type="primary" icon={<CheckOutlined />} loading={saving} onClick={saveEdit}>
              保存
            </Button>
            <Button icon={<CloseOutlined />} disabled={saving} onClick={() => setEditing(false)}>
              取消
            </Button>
            <span style={{ fontSize: 12, color: brand.textSecondary }}>保存后将重新做合规校验</span>
          </Space>
        ) : (
          <Space>
            <Button type="primary" icon={<SendOutlined />} onClick={() => onAdopt?.(v)}>
              采用
            </Button>
            <Button icon={<CopyOutlined />} onClick={() => { navigator.clipboard?.writeText(body); message.success('已复制') }}>
              复制
            </Button>
            <Button icon={<EditOutlined />} disabled={regenerating} onClick={startEdit}>
              编辑
            </Button>
            <Button icon={<ReloadOutlined />} loading={regenerating} onClick={regenerate}>
              重新生成
            </Button>
          </Space>
        )}
      </div>
    </Card>
  )
}
