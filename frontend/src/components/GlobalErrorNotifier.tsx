import { useEffect } from 'react'
import { App } from 'antd'

/**
 * 未捕获 Promise 拒绝的全局兜底 toast。
 * 页面若已用 useAsyncData/try-catch 处理，则不会走到这里；
 * 这里只兜住漏网的 rejection，避免「静默失败」。
 */
export default function GlobalErrorNotifier() {
  const { message } = App.useApp()
  useEffect(() => {
    const onRejection = (e: PromiseRejectionEvent) => {
      const reason = e.reason as { message?: string } | undefined
      message.error(reason?.message || '发生未知错误，请稍后重试')
    }
    window.addEventListener('unhandledrejection', onRejection)
    return () => window.removeEventListener('unhandledrejection', onRejection)
  }, [message])
  return null
}
