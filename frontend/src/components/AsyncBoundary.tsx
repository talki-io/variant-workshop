import type { ReactNode } from 'react'
import { Button, Result, Spin } from 'antd'

interface Props {
  loading: boolean
  error: Error | null
  onRetry?: () => void
  children: ReactNode
  /** 自定义加载态（如骨架屏）；不传则用居中 Spin */
  loadingNode?: ReactNode
}

/** 包裹数据区，按 loading/error/正常 分别渲染。error 态给「重试」按钮。 */
export default function AsyncBoundary({ loading, error, onRetry, children, loadingNode }: Props) {
  if (loading) {
    return <>{loadingNode ?? <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>}</>
  }
  if (error) {
    return (
      <Result
        status="warning"
        title="加载失败"
        subTitle={error.message || '请求出错，请稍后重试'}
        extra={onRetry ? <Button type="primary" onClick={onRetry}>重试</Button> : undefined}
      />
    )
  }
  return <>{children}</>
}
