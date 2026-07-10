/**
 * 检查生产构建产物里 chunk 之间有没有循环引用。
 *
 * 为什么需要它：`manualChunks` 把同一生态的包分到不同 chunk 时，很容易造成
 * 跨 chunk 循环引用。运行时表现是 antd 在 React 初始化完成前读 React.version，
 * 报 "Cannot read properties of undefined (reading 'version')" 并整页白屏。
 * `tsc --noEmit` 和 `vite build` 都不会报错——开发模式根本不走分包。
 *
 * 用法：先 `npm run build`，再 `node scripts/check-bundle.mjs`。
 */
import { readFileSync, readdirSync, existsSync } from 'node:fs'
import { join } from 'node:path'

const ASSETS = 'dist/assets'

if (!existsSync(ASSETS)) {
  console.error(`✗ 找不到 ${ASSETS}/，先跑 npm run build`)
  process.exit(1)
}

/** Rollup 把所有静态 import 放在文件最开头，连续排列。动态 import() 不算，它不影响初始化顺序。 */
function staticImports(file) {
  const src = readFileSync(file, 'utf8')
  const head = src.match(/^((?:import[^;]*?;)+)/)
  if (!head) return []
  return [...head[1].matchAll(/from"\.\/([^"]+)"/g)].map((m) => m[1])
}

const files = readdirSync(ASSETS).filter((f) => f.endsWith('.js'))
if (files.length === 0) {
  console.error(`✗ ${ASSETS}/ 里没有 .js 产物`)
  process.exit(1)
}

const graph = new Map(files.map((f) => [f, staticImports(join(ASSETS, f))]))

// 有向图找环：白灰黑三色 DFS，记录第一条环路径。
const WHITE = 0, GRAY = 1, BLACK = 2
const color = new Map(files.map((f) => [f, WHITE]))
const cycles = []

function visit(node, stack) {
  color.set(node, GRAY)
  for (const next of graph.get(node) ?? []) {
    if (!graph.has(next)) continue
    if (color.get(next) === GRAY) {
      cycles.push([...stack.slice(stack.indexOf(next)), next])
    } else if (color.get(next) === WHITE) {
      visit(next, [...stack, next])
    }
  }
  color.set(node, BLACK)
}

for (const f of files) if (color.get(f) === WHITE) visit(f, [f])

if (cycles.length > 0) {
  console.error(`✗ 检出 ${cycles.length} 处 chunk 循环引用：\n`)
  for (const c of cycles) console.error(`  ${c.join('\n    → ')}\n`)
  console.error('修 vite.config.ts 的 manualChunks —— 同一生态的包要分到同一个 chunk。')
  console.error('按包名精确匹配，别用 id.includes() 子串匹配。')
  process.exit(1)
}

console.log(`✓ ${files.length} 个 chunk，无循环引用`)
