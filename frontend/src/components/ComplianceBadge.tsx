import { CheckCircleFilled, ExclamationCircleFilled, StopFilled } from '@ant-design/icons'
import { brand } from '../theme/tokens'
import type { ComplianceStatus } from '../types'

interface Props {
  status: ComplianceStatus
  softFlagCount?: number
}

export default function ComplianceBadge({ status, softFlagCount = 0 }: Props) {
  if (status === 'pass') {
    return (
      <span style={{ color: brand.success, fontWeight: 600, fontSize: 13 }}>
        <CheckCircleFilled /> 合规 ✓
      </span>
    )
  }
  if (status === 'soft') {
    return (
      <span style={{ color: brand.warning, fontWeight: 600, fontSize: 13 }}>
        <ExclamationCircleFilled /> 软提示 · {softFlagCount} 句待判断
      </span>
    )
  }
  return (
    <span style={{ color: brand.error, fontWeight: 600, fontSize: 13 }}>
      <StopFilled /> 禁词命中 · 已改写
    </span>
  )
}
