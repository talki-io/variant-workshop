/**
 * 展示层兜底：把模型偶发的 ```json 代码围栏 / 嵌套 {"body":...} 外壳解开，只保留纯文本文案。
 * 后端 pipeline 已做同样清洗，这里是「用户永不该看到 JSON」的最后一道防线（含历史存量脏数据）。
 * 与 backend/app/pipeline/generate.py::_clean_body 逻辑对齐。
 */
export function cleanVariantBody(raw: string): string {
  if (!raw) return raw
  let b = raw.replace(/```(?:json)?/gi, '').trim()

  // 整段本身是 JSON（[{...}] 或 {...}）且含 body 字段 → 解出内层真正文案
  if ((b[0] === '[' || b[0] === '{') && b.includes('"body"')) {
    try {
      let parsed: unknown = JSON.parse(b)
      if (Array.isArray(parsed)) parsed = parsed[0]
      if (parsed && typeof parsed === 'object' && 'body' in parsed) {
        b = String((parsed as { body: unknown }).body).trim()
      }
    } catch {
      // 退化：正则抓第一个 "body":"..." 的值并解转义
      const m = b.match(/"body"\s*:\s*"((?:[^"\\]|\\.)*)"/)
      if (m) {
        try {
          b = JSON.parse(`"${m[1]}"`)
        } catch {
          b = m[1]
        }
      }
    }
  }

  // 截掉尾部可能残留的围栏
  const idx = b.indexOf('```')
  if (idx > 40) b = b.slice(0, idx)

  b = b.trim()
  if ((b.startsWith('"') && b.endsWith('"')) || (b.startsWith("'") && b.endsWith("'"))) {
    b = b.slice(1, -1)
  }
  return b.trim()
}
