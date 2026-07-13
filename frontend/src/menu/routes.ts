import type { MenuItem } from '../types'

/**
 * 代码里真实存在的可路由 path（+ 默认中文名）。菜单管理页的「路径」选择器用它——
 * 菜单只治理已知路由的展示与可见性，不能凭空造出可用页面（新页面仍需写代码）。
 */
export const KNOWN_ROUTES: { path: string; label: string }[] = [
  { path: '/generate', label: '文案生成' },
  { path: '/news', label: '新闻库' },
  { path: '/accounts', label: '账号管理' },
  { path: '/users', label: '用户管理' },
  { path: '/menus', label: '菜单管理' },
  { path: '/models', label: '模型管理' },
  { path: '/dashboard', label: '消耗看板' },
  { path: '/crawl-quota', label: '抓取与配额' },
]

/**
 * 内置默认菜单（与后端 seed_system 的默认项一致）。用途：
 * 1) 首帧兜底——GET /menus 返回前不闪空；2) 接口失败时优雅降级。
 */
export const DEFAULT_MENUS: MenuItem[] = [
  { id: 'mn_generate', path: '/generate', label: '文案生成', icon: 'EditOutlined', order: 1, visibleRoles: ['editor', 'admin'], enabled: true, locked: false },
  { id: 'mn_news', path: '/news', label: '新闻库', icon: 'ReadOutlined', order: 2, visibleRoles: ['editor', 'admin'], enabled: true, locked: false },
  { id: 'mn_accounts', path: '/accounts', label: '账号管理', icon: 'TeamOutlined', order: 3, visibleRoles: ['editor', 'admin'], enabled: true, locked: false },
  { id: 'mn_users', path: '/users', label: '用户管理', icon: 'UsergroupAddOutlined', order: 4, visibleRoles: ['admin'], enabled: true, locked: true },
  { id: 'mn_menus', path: '/menus', label: '菜单管理', icon: 'MenuOutlined', order: 5, visibleRoles: ['admin'], enabled: true, locked: true },
  { id: 'mn_models', path: '/models', label: '模型管理', icon: 'RobotOutlined', order: 6, visibleRoles: ['admin'], enabled: true, locked: false },
  { id: 'mn_dashboard', path: '/dashboard', label: '消耗看板', icon: 'LineChartOutlined', order: 7, visibleRoles: ['admin'], enabled: true, locked: false },
  { id: 'mn_crawl', path: '/crawl-quota', label: '抓取与配额', icon: 'DatabaseOutlined', order: 8, visibleRoles: ['admin'], enabled: true, locked: false },
]
