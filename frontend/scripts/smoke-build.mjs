/**
 * 在真实浏览器里打开生产构建产物，断言它跑得起来。
 *
 * 为什么需要它：`npm run build` 通过只说明能打包，不说明能运行。
 * 部署时 `curl` 到 index.html 的 200 也只说明 HTML 送达了，跟 JS 能不能执行无关。
 * 历史上就是这样漏掉了一次整页白屏（manualChunks 循环引用）。
 *
 * 用法：先 `npm run build`，再 `node scripts/smoke-build.mjs`。
 * Chrome 路径可用 CHROME_BIN 覆盖。
 */
import { spawn, spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'

const PORT = 4399
const URL = `http://127.0.0.1:${PORT}/`
const CANDIDATES = [
  process.env.CHROME_BIN,
  'google-chrome',
  'google-chrome-stable',
  'chromium',
  'chromium-browser',
].filter(Boolean)

function findChrome() {
  for (const bin of CANDIDATES) {
    if (bin.includes('/') && existsSync(bin)) return bin
    if (spawnSync('which', [bin]).status === 0) return bin
  }
  return null
}

const chrome = findChrome()
if (!chrome) {
  console.error(`✗ 找不到 Chrome。装一个，或用 CHROME_BIN 指定路径。试过：${CANDIDATES.join(', ')}`)
  process.exit(1)
}

const preview = spawn('npx', ['vite', 'preview', '--port', String(PORT), '--strictPort'], {
  stdio: 'ignore',
  detached: true,
})

const cleanup = () => {
  try { process.kill(-preview.pid) } catch { /* 已退出 */ }
}
process.on('exit', cleanup)
process.on('SIGINT', () => { cleanup(); process.exit(130) })

async function waitReady(timeoutMs = 30_000) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    try {
      const r = await fetch(URL)
      if (r.ok) return true
    } catch { /* 还没起来 */ }
    await new Promise((r) => setTimeout(r, 500))
  }
  return false
}

function loadPage(url) {
  const r = spawnSync(chrome, [
    '--headless', '--disable-gpu', '--no-sandbox',
    '--virtual-time-budget=15000',
    '--enable-logging=stderr', '--v=0',
    '--dump-dom', url,
  ], { encoding: 'utf8', timeout: 60_000, maxBuffer: 64 * 1024 * 1024 })
  return { dom: r.stdout ?? '', console: r.stderr ?? '' }
}

/** #root 里渲染出了多少个元素（脚本标签不算）。白屏时为 0。 */
function rootElementCount(dom) {
  const start = dom.indexOf('<div id="root">')
  const end = dom.indexOf('</body>')
  if (start < 0 || end <= start) return 0
  const root = dom.slice(start + '<div id="root">'.length, end).replace(/<script[\s\S]*?<\/script>/g, '')
  return (root.match(/<[a-zA-Z]/g) ?? []).length
}

if (!(await waitReady())) {
  console.error(`✗ preview server 未能在 30s 内就绪（:${PORT}）`)
  process.exit(1)
}

let failed = false
// 首页 + 一条深链（深链还顺带验证 SPA fallback 没坏）。
for (const path of ['', 'dashboard']) {
  const url = URL + path
  const { dom, console: log } = loadPage(url)

  const errors = log.split('\n').filter((l) => /Uncaught|TypeError|ReferenceError/.test(l))
  const count = rootElementCount(dom)
  const label = path ? `/${path}` : '/'

  if (errors.length > 0) {
    console.error(`✗ ${label} 控制台有未捕获错误：`)
    for (const e of errors.slice(0, 3)) console.error(`    ${e.trim().slice(0, 160)}`)
    failed = true
  } else if (count < 10) {
    console.error(`✗ ${label} 白屏：#root 只有 ${count} 个元素（React 没挂载？）`)
    failed = true
  } else {
    console.log(`✓ ${label} 渲染正常（${count} 个 DOM 元素），无未捕获错误`)
  }

  // 生产构建里不该出现演示账号提示（SEED_DEMO_DATA=false，这些账号根本不存在）。
  if (dom.includes('demo1234') || dom.includes('演示账号')) {
    console.error(`✗ ${label} 生产产物中出现了演示账号提示`)
    failed = true
  }
}

process.exit(failed ? 1 : 0)
