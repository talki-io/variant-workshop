import { brand } from '../theme/tokens'

/** 新闻热度条：按热度分段着色 */
export default function HeatBar({ heat }: { heat: number }) {
  const color = heat >= 80 ? brand.error : heat >= 60 ? brand.warning : heat >= 45 ? '#EAB308' : brand.success
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, width: 184 }}>
      <span style={{ fontSize: 12, color: brand.textSecondary, whiteSpace: 'nowrap', flex: 'none' }}>
        热度 <b style={{ color: brand.textBase }}>{heat}</b>/100
      </span>
      <div style={{ flex: 1, minWidth: 0, height: 6, background: 'var(--app-track)', borderRadius: 999, overflow: 'hidden' }}>
        <div
          style={{
            width: `${Math.min(Math.max(heat, 0), 100)}%`,
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
