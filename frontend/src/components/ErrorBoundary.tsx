import { Component, type ReactNode } from 'react'
import { Button, Result } from 'antd'

interface Props {
  children: ReactNode
}
interface State {
  error: Error | null
}

/** 渲染期崩溃的兜底：防止某页 render 抛错把整棵子树变白屏。 */
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error) {
    console.error('UI 渲染异常:', error)
  }

  render() {
    if (this.state.error) {
      return (
        <Result
          status="error"
          title="页面出错了"
          subTitle={this.state.error.message || '渲染异常'}
          extra={
            <Button type="primary" onClick={() => window.location.reload()}>
              刷新页面
            </Button>
          }
        />
      )
    }
    return this.props.children
  }
}
