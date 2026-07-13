import { useState, useEffect, type KeyboardEvent } from 'react'
import { Avatar, Button, Card, Tooltip, Input, App, Tag, Alert } from 'antd'
import { Bubble } from '@ant-design/x'
import { useNavigate } from 'react-router-dom'
import {
  RobotOutlined,
  UserOutlined,
  PaperClipOutlined,
  SendOutlined,
  FileTextOutlined,
  FireOutlined,
  SnippetsOutlined,
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
  /** 本次临时仿写范本（贴一段爆款让 AI 仿写，走 few-shot，不入样本库） */
  styleRefs: string[]
  onStyleRefsChange: (refs: string[]) => void
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
  styleRefs,
  onStyleRefsChange,
}: Props) {
  const { message } = App.useApp()
  const navigate = useNavigate()
  const noTones = tones.length === 0
  const canSend = !!toneId && !!input.trim() && !generating
  const currentTone = tones.find((t) => t.id === toneId)
  const [sampleOpen, setSampleOpen] = useState(false)
  const [sampleCount, setSampleCount] = useState<number | null>(null)
  const [refMode, setRefMode] = useState(false) // 仿写范本录入模式：就地在输入框输入
  const [pulse, setPulse] = useState(false) // 点按钮时的启动动画

  const toggleRefMode = () => {
    setRefMode((m) => !m)
    setPulse(true) // 触发一次启动脉冲动画
  }
  // 把当前输入框内容收作一条仿写范本（refMode 下 Enter / 完成录入触发）
  const addRefFromInput = () => {
    const t = input.trim()
    if (!t) return
    if (styleRefs.length >= 3) { message.warning('最多 3 段仿写范本'); return }
    onStyleRefsChange([...styleRefs, t])
    onInput('')
  }
  const removeRef = (i: number) => onStyleRefsChange(styleRefs.filter((_, idx) => idx !== i))

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
    if (e.shiftKey) return // Shift+Enter 换行
    e.preventDefault()
    if (refMode) addRefFromInput() // 录范本模式：Enter 添加一段
    else submit() // 普通模式：Enter 发送
  }

  return (
    <Card
      style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
      styles={{ body: { display: 'flex', flexDirection: 'column', height: '100%', padding: 20 } }}
    >
      {/* 调性选择器；无账号时引导去账号管理创建（账号按用户隔离，新用户初始为空） */}
      {noTones ? (
        <Alert
          type="info"
          showIcon
          message="还没有账号"
          description="文案生成需要先有一个「账号语感」。账号与参考爆款样本按用户隔离，请先创建你自己的账号。"
          action={
            <Button size="small" type="primary" onClick={() => navigate('/accounts')}>
              去创建账号
            </Button>
          }
        />
      ) : (
        <ToneSelector tones={tones} value={toneId} onChange={onToneChange} />
      )}

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

      {/* 输入框（工具栏 → [仿写范本条] → 输入区 → 底部）。refMode 高亮 + 点按钮脉冲动画 */}
      <div
        className={pulse ? 'vw-ref-pulse' : undefined}
        onAnimationEnd={() => setPulse(false)}
        style={{
          marginTop: 12,
          border: `1px solid ${refMode ? brand.primary : brand.border}`,
          borderRadius: 12,
          padding: 12,
          background: '#fff',
          transition: 'border-color .2s',
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
          <Tooltip title="仿写范本：点亮后直接在下方输入框贴文案、Enter 添加，本次照它的风格仿写（临时·不入样本库）">
            <Button
              size="small"
              icon={<SnippetsOutlined />}
              type={refMode ? 'primary' : 'default'}
              onClick={toggleRefMode}
            >
              仿写范本{styleRefs.length ? ` (${styleRefs.length})` : ''}
            </Button>
          </Tooltip>
        </div>

        {/* 仿写范本条：录入提示 + 已加范本 chips（refMode 或已有范本时显示） */}
        {(refMode || styleRefs.length > 0) && (
          <div style={{ marginBottom: 8 }}>
            {refMode && (
              <div style={{ fontSize: 12, color: brand.primary, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
                <SnippetsOutlined /> 仿写范本录入中：在下方贴文案、Enter 添加（最多 3 段），点上方「仿写范本」或「完成录入」退出
              </div>
            )}
            {styleRefs.length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {styleRefs.map((r, i) => (
                  <Tag key={i} closable onClose={() => removeRef(i)} color="blue" bordered={false} style={{ maxWidth: 280, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    仿写{i + 1}：{r.length > 18 ? `${r.slice(0, 18)}…` : r}
                  </Tag>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 输入区 */}
        <Input.TextArea
          value={input}
          onChange={(e) => onInput(e.target.value)}
          onPressEnter={handleEnter}
          disabled={!toneId}
          maxLength={refMode ? 2000 : MAX_LEN}
          autoSize={{ minRows: 3, maxRows: 8 }}
          variant="borderless"
          placeholder={
            !toneId ? '请先在上方选择账号/调性'
              : refMode ? '粘贴要仿写的爆款文案，Enter 添加为范本…'
                : '输入你的需求，越具体越好…'
          }
          style={{ padding: 0, resize: 'none' }}
        />

        {/* 底部：计数 + 发送/完成录入 */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 8 }}>
          <span style={{ fontSize: 12, color: brand.textSecondary }}>
            {refMode ? `仿写范本 ${styleRefs.length}/3 段` : `${input.length}/${MAX_LEN}`}
          </span>
          {refMode ? (
            <Button icon={<CheckOutlined />} onClick={() => { setRefMode(false); setPulse(true) }}>
              完成录入
            </Button>
          ) : (
            <Button type="primary" icon={<SendOutlined />} loading={generating} disabled={!canSend} onClick={submit}>
              发送
            </Button>
          )}
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
