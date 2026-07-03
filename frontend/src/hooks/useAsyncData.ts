import { useCallback, useEffect, useRef, useState } from 'react'

interface AsyncState<T> {
  data: T | null
  loading: boolean
  error: Error | null
}

/**
 * 统一的「拉数据」hook：自动 try/catch/loading，暴露 reload 供重试。
 * services 现在打真实网络，任何调用都可能 reject——用它把每个数据页从
 * 「rejection 未处理 → 白屏/无限 spinner」收敛成 loading/error/data 三态。
 *
 * setData 支持函数式更新，页面内的本地乐观改动（打标、开关）直接用它。
 */
export function useAsyncData<T>(fn: () => Promise<T>) {
  const [state, setState] = useState<AsyncState<T>>({ data: null, loading: true, error: null })
  const fnRef = useRef(fn)
  fnRef.current = fn

  const reload = useCallback(() => {
    setState((s) => ({ ...s, loading: true, error: null }))
    fnRef
      .current()
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((e) => setState({ data: null, loading: false, error: e instanceof Error ? e : new Error(String(e)) }))
  }, [])

  useEffect(() => {
    reload()
  }, [reload])

  const setData = useCallback((updater: T | ((prev: T | null) => T | null)) => {
    setState((s) => ({
      ...s,
      data: typeof updater === 'function' ? (updater as (prev: T | null) => T | null)(s.data) : updater,
    }))
  }, [])

  return { ...state, reload, setData }
}
