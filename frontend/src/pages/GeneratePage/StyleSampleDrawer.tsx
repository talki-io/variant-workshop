import { useEffect, useState } from 'react'
import { Drawer, Input, Button, List, Tag, Empty, Spin, App, Popconfirm, Alert } from 'antd'
import { DeleteOutlined, PlusOutlined, FireOutlined } from '@ant-design/icons'
import { getSamples, addSample, deleteSample } from '../../services'
import type { StyleSample, Tone } from '../../types'
import { brand } from '../../theme/tokens'

interface Props {
  open: boolean
  onClose: () => void
  tone?: Tone
  /** 样本增删后回调父组件（刷新计数） */
  onChange?: (count: number) => void
}

/** 参考爆款管理：查看/新增/删除某账号的往期爆款样本，作为生成的 few-shot 风格锚。 */
export default function StyleSampleDrawer({ open, onClose, tone, onChange }: Props) {
  const { message } = App.useApp()
  const [list, setList] = useState<StyleSample[]>([])
  const [loading, setLoading] = useState(false)
  const [body, setBody] = useState('')
  const [source, setSource] = useState('')
  const [saving, setSaving] = useState(false)

  const load = (toneId: string) => {
    setLoading(true)
    getSamples(toneId)
      .then((rows) => {
        setList(rows)
        onChange?.(rows.length)
      })
      .catch((e) => message.error(e instanceof Error ? e.message : '加载样本失败'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    if (open && tone) load(tone.id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, tone?.id])

  const add = async () => {
    const text = body.trim()
    if (!text || !tone) return
    setSaving(true)
    try {
      const created = await addSample(tone.id, text, source.trim() || undefined)
      const next = [created, ...list]
      setList(next)
      onChange?.(next.length)
      setBody('')
      setSource('')
      message.success('已添加爆款样本，下次生成即会参考')
    } catch (e) {
      message.error(e instanceof Error ? e.message : '添加失败')
    } finally {
      setSaving(false)
    }
  }

  const remove = async (s: StyleSample) => {
    try {
      await deleteSample(s.id)
      const next = list.filter((x) => x.id !== s.id)
      setList(next)
      onChange?.(next.length)
      message.success('已删除')
    } catch (e) {
      message.error(e instanceof Error ? e.message : '删除失败')
    }
  }

  return (
    <Drawer
      title={
        <span>
          <FireOutlined style={{ color: brand.warning, marginRight: 8 }} />
          参考爆款 · {tone?.name ?? ''}
        </span>
      }
      open={open}
      onClose={onClose}
      width={480}
    >
      <Alert
        type="info"
        showIcon
        message="贴入该账号的往期爆款文案，系统会把它们作为「语感范本」参考着写（模仿人称/开场/给干货/软 CTA 的写法，不照抄）。样本越贴近真实风格，产出越像人话。"
        style={{ marginBottom: 16, background: 'var(--app-soft-primary)', border: 'none' }}
      />

      {/* 新增区 */}
      <div style={{ marginBottom: 20 }}>
        {/* 计数放到输入框内右下角：relative 容器 + 预留 paddingBottom 防文字压字 */}
        <div style={{ position: 'relative' }}>
          <Input.TextArea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="粘贴一条往期爆款文案…"
            autoSize={{ minRows: 4, maxRows: 10 }}
            maxLength={2000}
            style={{ paddingBottom: 24 }}
          />
          <span
            style={{
              position: 'absolute',
              right: 12,
              bottom: 8,
              fontSize: 12,
              color: brand.textSecondary,
              pointerEvents: 'none',
              background: 'var(--app-bg-container)',
              paddingLeft: 6,
              borderRadius: 4,
            }}
          >
            {body.length}/2000
          </span>
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
          <Input
            value={source}
            onChange={(e) => setSource(e.target.value)}
            placeholder="备注（可选，如：均线干货/晒收益）"
            style={{ flex: 1 }}
            maxLength={40}
          />
          <Button type="primary" icon={<PlusOutlined />} loading={saving} disabled={!body.trim() || !tone} onClick={add}>
            添加
          </Button>
        </div>
      </div>

      {/* 列表区 */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin />
        </div>
      ) : list.length === 0 ? (
        <Empty description="该账号还没有参考爆款，添加后生成会更像它的风格" />
      ) : (
        <List
          dataSource={list}
          header={<span style={{ color: brand.textSecondary, fontSize: 13 }}>共 {list.length} 条参考爆款</span>}
          renderItem={(s) => (
            <List.Item
              actions={[
                <Popconfirm
                  key="del"
                  title="删除这条爆款样本？"
                  okText="删除"
                  okType="danger"
                  cancelText="取消"
                  onConfirm={() => remove(s)}
                >
                  <Button size="small" type="text" danger icon={<DeleteOutlined />} />
                </Popconfirm>,
              ]}
            >
              <div style={{ minWidth: 0 }}>
                {s.source && (
                  <Tag color="orange" bordered={false} style={{ marginBottom: 4 }}>
                    {s.source}
                  </Tag>
                )}
                <div style={{ fontSize: 13, color: brand.textBase, lineHeight: 1.6 }}>{s.body}</div>
              </div>
            </List.Item>
          )}
        />
      )}
    </Drawer>
  )
}
