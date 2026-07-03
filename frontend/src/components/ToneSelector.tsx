import { Select, Avatar, Alert, Space } from 'antd'
import { UserOutlined, InfoCircleOutlined } from '@ant-design/icons'
import type { Tone } from '../types'
import { brand } from '../theme/tokens'

interface Props {
  tones: Tone[]
  value?: string
  onChange: (id: string) => void
  showHint?: boolean
}

export default function ToneSelector({ tones, value, onChange, showHint = true }: Props) {
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{ fontWeight: 600, whiteSpace: 'nowrap' }}>为哪个账号/调性写：</span>
        <Select
          value={value}
          onChange={onChange}
          placeholder="请选择账号 / 调性（必选）"
          style={{ flex: 1, minWidth: 220 }}
          size="large"
          options={tones.map((t) => ({
            value: t.id,
            label: (
              <Space>
                <Avatar size={22} icon={<UserOutlined />} style={{ background: brand.primary }} />
                <span style={{ fontWeight: 600 }}>{t.handle}</span>
                <span style={{ color: brand.textSecondary }}>
                  {t.name} · {t.desc}
                </span>
              </Space>
            ),
          }))}
        />
      </div>
      {showHint && (
        <Alert
          type="info"
          showIcon
          icon={<InfoCircleOutlined />}
          message="不同账号语感指纹独立，生成前必须选，绝不混用"
          style={{ marginTop: 10, background: 'var(--app-soft-primary)', border: 'none', fontSize: 13 }}
        />
      )}
    </div>
  )
}
