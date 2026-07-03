import { useState, useEffect, type KeyboardEvent } from 'react'
import { Avatar, Button, Card, Tooltip, Input, App } from 'antd'
import { Bubble } from '@ant-design/x'
import {
  RobotOutlined,
  UserOutlined,
  PaperClipOutlined,
  SendOutlined,
  FileTextOutlined,
  FireOutlined,
  ThunderboltOutlined,
  CommentOutlined,
  ScissorOutlined,
  ReloadOutlined,
  CheckOutlined,
} from '@ant-design/icons'
import ToneSelector from '../../components/ToneSelector'
import StyleSampleDrawer from './StyleSampleDrawer'
import { getSamples } from '../../services'
import { brand } from '../../theme/tokens'
import type { Tone } from '../../types'

export interface ChatMessage {
  id: string
  role: 'user' | 'ai'
  content: string
  time?: string // HH:MM
}

interface Props {
  tones: Tone[]
  toneId?: string
  onToneChange: (id: string) => void
  messages: ChatMessage[]
  input: string
  onInput: (v: string) => void
  onSend: (v: string) => void
  generating: boolean
  /** 快捷 chip 点击：带 modifier 触发一次生成 */
  onQuickAction: (label: string) => void
  /** 引用新闻：跳新闻库挑选 */
  onCiteNews: () => void
}

const MAX_LEN = 1000

const QUICK_CHIPS = [
  { key: 'hook', label: '换个钩子', icon: <ThunderboltOutlined /> },
  { key: 'spoken', label: '更口语', icon: <CommentOutlined /> },
  { key: 'short', label: '缩短到IG长度', icon: <ScissorOutlined /> },
  { key: 'regen', label: '重新生成', icon: <ReloadOutlined /> },
]

export default function ChatPanel({
  tones,
  toneId,
  onToneChange,
  messages,
  input,
  onInput,
  onSend,
  generating,
  onQuickAction,
  onCiteNews,
}: Props) {
  const { message } = App.useApp()
  const canSend = !!toneId && !!input.trim() && !generating
  const currentTone = tones.find((t) => t.id === toneId)
  const [sampleOpen, setSampleOpen] = useState(false)
  const [sampleCount, setSampleCount] = useState<number | null>(null)

  // 参考爆款计数：切换账号时刷新，显示在按钮上
  useEffect(() => {
    if (!toneId) {
      setSampleCount(null)
      return
    }
    let cancelled = false
    getSamples(toneId)
      .then((rows) => !cancelled && setSampleCount(rows.length))
      .catch(() => !cancelled && setSampleCount(null))
    return () => {
      cancelled = true
    }
  }, [toneId])

  const submit = () => {
    if (!canSend) return
    onSend(input)
  }

  const handleEnter = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter 发送，Shift+Enter 换行
    if (!e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <Card
      style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
      styles={{ body: { display: 'flex', flexDirection: 'column', height: '100%', padding: 20 } }}
    >
      {/* 调性选择器 */}
      <ToneSelector tones={tones} value={toneId} onChange={onToneChange} />

      {/* 对话流 */}
      <div style={{ flex: 1, overflow: 'auto', margin: '16px 0', paddingRight: 4 }}>
        <Bubble.List
          items={messages.map((m) => {
            const isUser = m.role === 'user'
            return {
              key: m.id,
              content: m.content,
              placement: isUser ? ('end' as const) : ('start' as const),
              avatar: isUser ? (
                <Avatar icon={<UserOutlined />} style={{ background: brand.primary }} />
              ) : (
                <Avatar icon={<RobotOutlined />} style={{ background: 'var(--app-soft-primary)', color: brand.primary }} />
              ),
              variant: 'filled' as const,
              // 用户气泡：蓝底白字（对齐设计图）；AI 气泡：默认浅灰
              styles: isUser ? { content: { background: brand.primary, color: '#fff' } } : undefined,
              footer: m.time ? (
                isUser ? (
                  <span style={{ fontSize: 12, color: brand.textSecondary, display: 'inline-flex', alignItems: 'center' }}>
                    已发送 {m.time}
                    <CheckOutlined style={{ fontSize: 11, color: brand.primary, marginLeft: 4 }} />
                    <CheckOutlined style={{ fontSize: 11, color: brand.primary, marginLeft: -5 }} />
                  </span>
                ) : (
                  <span style={{ fontSize: 12, color: brand.textSecondary }}>{m.time}</span>
                )
              ) : undefined,
            }
          })}
        />
        {generating && (
          <Bubble
            placement="start"
            loading
            avatar={<Avatar icon={<RobotOutlined />} style={{ background: 'var(--app-soft-primary)', color: brand.primary }} />}
            content=""
          />
        )}
      </div>

      {/* 快捷 chips：小巧 pill，带 modifier 触发一次生成 */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {QUICK_CHIPS.map((c) => (
          <Button
            key={c.key}
            size="small"
            icon={c.icon}
            disabled={generating}
            onClick={() => onQuickAction(c.label)}
            style={{ borderRadius: 999 }}
          >
            {c.label}
          </Button>
        ))}
      </div>

      {/* 输入框（对齐设计图：工具栏 → 输入区 → 底部计数 + 发送） */}
      <div
        style={{
          marginTop: 12,
          border: `1px solid ${brand.border}`,
          borderRadius: 12,
          padding: 12,
          background: '#fff',
        }}
      >
        {/* 工具栏 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 8 }}>
          <Tooltip title="附件上传（即将开放）">
            <Button
              type="text"
              size="small"
              icon={<PaperClipOutlined />}
              style={{ color: brand.textSecondary }}
              onClick={() => message.info('附件上传功能即将开放')}
            />
          </Tooltip>
          <Tooltip title="引用新闻：去新闻库挑一条作为素材">
            <Button size="small" icon={<FileTextOutlined />} onClick={onCiteNews}>
              引用新闻
            </Button>
          </Tooltip>
          <Tooltip title="参考爆款：管理该账号的往期爆款样本，生成会模仿其语感">
            <Button
              size="small"
              icon={<FireOutlined />}
              disabled={!toneId}
              onClick={() => setSampleOpen(true)}
            >
              参考爆款{sampleCount != null ? ` (${sampleCount})` : ''}
            </Button>
          </Tooltip>
        </div>

        {/* 输入区 */}
        <Input.TextArea
          value={input}
          onChange={(e) => onInput(e.target.value)}
          onPressEnter={handleEnter}
          disabled={!toneId}
          maxLength={MAX_LEN}
          autoSize={{ minRows: 3, maxRows: 8 }}
          variant="borderless"
          placeholder={toneId ? '输入你的需求，越具体越好…' : '请先在上方选择账号/调性'}
          style={{ padding: 0, resize: 'none' }}
        />

        {/* 底部：计数 + 发送 */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 8 }}>
          <span style={{ fontSize: 12, color: brand.textSecondary }}>
            {input.length}/{MAX_LEN}
          </span>
          <Button type="primary" icon={<SendOutlined />} loading={generating} disabled={!canSend} onClick={submit}>
            发送
          </Button>
        </div>
      </div>

      {/* 参考爆款管理抽屉 */}
      <StyleSampleDrawer
        open={sampleOpen}
        onClose={() => setSampleOpen(false)}
        tone={currentTone}
        onChange={setSampleCount}
      />
    </Card>
  )
}
