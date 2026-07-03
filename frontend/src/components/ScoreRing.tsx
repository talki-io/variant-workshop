import { Progress } from 'antd'
import { brand } from '../theme/tokens'

/** 综合分环形进度：按分值着色（高分绿、中分主色、低分灰） */
export default function ScoreRing({ score, size = 56 }: { score: number; size?: number }) {
  const color = score >= 85 ? brand.success : score >= 75 ? brand.primary : '#9CA3AF'
  return (
    <Progress
      type="circle"
      percent={score}
      size={size}
      strokeColor={color}
      strokeWidth={8}
      format={() => (
        <span style={{ fontSize: size / 3.2, fontWeight: 600, color: brand.textBase }}>
          {score}
        </span>
      )}
    />
  )
}
