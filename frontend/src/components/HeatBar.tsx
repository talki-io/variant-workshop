import { brand } from '../theme/tokens'

/** 新闻热度条：按热度分段着色 */
export default function HeatBar({ heat }: { heat: number }) {
  const color = heat >= 80 ? brand.error : heat >= 60 ? brand.warning : heat >= 45 ? '#EAB308' : brand.success
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 160 }}>
      <span style={{ fontSize: 12, color: brand.textSecondary, whiteSpace: 'nowrap' }}>
        热度 <b style={{ color: brand.textBase }}>{heat}</b>/100
      </span>
      <div style={{ flex: 1, height: 6, background: '#EEF2F6', borderRadius: 999 }}>
        <div
          style={{
            width: `${heat}%`,
            height: '100%',
            background: color,
            borderRadius: 999,
            transition: 'width .3s',
          }}
        />
      </div>
    </div>
  )
}
