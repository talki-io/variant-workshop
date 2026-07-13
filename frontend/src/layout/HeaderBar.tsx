import { useEffect, useState } from 'react'
import { Layout, Input, Badge, Avatar, Breadcrumb, Space, Popover, Dropdown, Empty, Tag, App, Button, Tooltip } from 'antd'
import {
  BellOutlined,
  SearchOutlined,
  UserOutlined,
  ThunderboltOutlined,
  DownOutlined,
  IdcardOutlined,
  SettingOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  SunOutlined,
  MoonOutlined,
} from '@ant-design/icons'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useMenu } from '../menu/MenuContext'
import { useThemeMode } from '../theme/ThemeContext'
import { getQuota } from '../services'
import { brand } from '../theme/tokens'

const { Header } = Layout

// 菜单表未覆盖的非导航路由（如开发期组件走查页）在此兜底标题
const EXTRA_TITLES: Record<string, string> = {
  '/components': '组件规范',
}

export default function HeaderBar({
  collapsed = false,
  onToggleCollapse,
}: {
  collapsed?: boolean
  onToggleCollapse?: () => void
}) {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { user } = useAuth()
  const { menus } = useMenu()
  const { mode, toggle } = useThemeMode()
  const { message } = App.useApp()
  // 面包屑标题由菜单数据派生，与侧栏保持一致
  const title = menus.find((m) => m.path === pathname)?.label ?? EXTRA_TITLES[pathname] ?? '文案生成'

  const [search, setSearch] = useState('')
  // 今日 token 用量：admin 才有 /api/quota 权限（users[0]=当前用户真实今日用量）
  const [todayTokens, setTodayTokens] = useState<number | null>(null)
  useEffect(() => {
    if (user?.role !== 'admin') {
      setTodayTokens(null)
      return
    }
    getQuota()
      .then((q) => setTodayTokens(q.users[0]?.used ?? 0))
      .catch(() => setTodayTokens(null))
  }, [user?.role])

  const submitSearch = () => {
    const q = search.trim()
    if (!q) return
    navigate('/news', { state: { q } })
    setSearch('')
  }

  const fmtTokens = (n: number) => (n >= 1000 ? `${(n / 1000).toFixed(1)}k` : `${n}`)

  return (
    <Header
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        height: 64,
        borderBottom: `1px solid ${brand.border}`,
        position: 'sticky',
        top: 0,
        zIndex: 10,
      }}
    >
      <Space size={12}>
        <Button
          type="text"
          aria-label={collapsed ? '展开侧栏' : '收起侧栏'}
          icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          onClick={onToggleCollapse}
          style={{ fontSize: 16, color: brand.textSecondary }}
        />
        <Breadcrumb
          items={[{ title: '首页' }, { title: <span style={{ color: brand.primary }}>{title}</span> }]}
          style={{ fontSize: 15 }}
        />
      </Space>

      <Space size={16}>
        <Input
          prefix={<SearchOutlined style={{ color: brand.textSecondary }} />}
          placeholder="搜索新闻标题或关键词…"
          variant="filled"
          style={{ width: 300, borderRadius: 999 }}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onPressEnter={submitSearch}
          allowClear
        />
        <Tooltip title={mode === 'dark' ? '切换到亮色' : '切换到暗色'}>
          <Button
            type="text"
            aria-label="切换主题"
            icon={mode === 'dark' ? <SunOutlined /> : <MoonOutlined />}
            onClick={toggle}
            style={{ fontSize: 17, color: brand.textSecondary }}
          />
        </Tooltip>
        <Popover
          trigger="click"
          placement="bottomRight"
          content={
            <div style={{ width: 240 }}>
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无新通知" />
            </div>
          }
        >
          <Badge dot={false}>
            <BellOutlined style={{ fontSize: 18, color: brand.textSecondary, cursor: 'pointer' }} />
          </Badge>
        </Popover>
        {todayTokens !== null && (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              height: 32,
              padding: '0 12px',
              borderRadius: 999,
              background: 'var(--app-soft-primary)',
              color: brand.primary,
              fontWeight: 500,
              fontSize: 13,
              whiteSpace: 'nowrap',
              flex: 'none',
            }}
          >
            <ThunderboltOutlined />
            今日 {fmtTokens(todayTokens)} tokens
          </span>
        )}
        <Dropdown
          trigger={['click']}
          placement="bottomRight"
          menu={{
            items: [
              {
                key: 'profile',
                icon: <IdcardOutlined />,
                label: '个人资料',
                onClick: () => message.info('个人资料 · 即将开放'),
              },
              {
                key: 'prefs',
                icon: <SettingOutlined />,
                label: '偏好设置',
                onClick: () => message.info('偏好设置 · 即将开放'),
              },
            ],
          }}
          dropdownRender={(menu) => (
            <div
              style={{
                background: 'var(--app-bg-container)',
                borderRadius: 8,
                boxShadow: 'var(--app-shadow-hover)',
                overflow: 'hidden',
                minWidth: 208,
              }}
            >
              {/* 用户资料卡头（退出登录在左下角侧栏，这里只放设置类操作） */}
              <div style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 10, borderBottom: `1px solid ${brand.border}` }}>
                <Avatar size={36} icon={<UserOutlined />} style={{ background: brand.primary }} />
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>{user?.name ?? '未登录'}</div>
                  <div style={{ fontSize: 12, color: brand.textSecondary }}>
                    {user ? `${user.role === 'admin' ? '管理员' : '素材员'} · 内部账号` : ''}
                  </div>
                </div>
              </div>
              {menu}
            </div>
          )}
        >
          <Space size={6} style={{ cursor: 'pointer' }}>
            <Avatar size={32} icon={<UserOutlined />} style={{ background: brand.primary }} />
            <span style={{ fontSize: 13 }}>{user?.name ?? '未登录'}</span>
            {user && (
              <Tag color={user.role === 'admin' ? 'blue' : 'default'} style={{ margin: 0, fontSize: 11 }}>
                {user.role === 'admin' ? '管理员' : '素材员'}
              </Tag>
            )}
            <DownOutlined style={{ fontSize: 10, color: brand.textSecondary }} />
          </Space>
        </Dropdown>
      </Space>
    </Header>
  )
}
