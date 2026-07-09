import { Layout, Menu, Avatar, Dropdown, Tag, Tooltip } from 'antd'
import {
  EditOutlined,
  ReadOutlined,
  LineChartOutlined,
  DatabaseOutlined,
  LogoutOutlined,
  UserOutlined,
  DownOutlined,
  AppstoreOutlined,
  TeamOutlined,
  RobotOutlined,
} from '@ant-design/icons'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { brand } from '../theme/tokens'

const { Sider } = Layout

export default function AppSider({ collapsed = false }: { collapsed?: boolean }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const items = [
    { key: '/generate', icon: <EditOutlined />, label: '文案生成' },
    { key: '/news', icon: <ReadOutlined />, label: '新闻库' },
    ...(user?.role === 'admin'
      ? [
          { key: '/accounts', icon: <TeamOutlined />, label: '账号管理' },
          { key: '/models', icon: <RobotOutlined />, label: '模型管理' },
          { key: '/dashboard', icon: <LineChartOutlined />, label: '消耗看板' },
          { key: '/crawl-quota', icon: <DatabaseOutlined />, label: '抓取与配额' },
        ]
      : []),
    { key: '/components', icon: <AppstoreOutlined />, label: '组件规范' },
  ]

  return (
    <Sider
      width={220}
      collapsedWidth={72}
      collapsed={collapsed}
      trigger={null}
      theme="light"
      style={{
        borderRight: `1px solid ${brand.border}`,
        display: 'flex',
        flexDirection: 'column',
        position: 'sticky',
        top: 0,
        height: '100vh',
      }}
    >
      {/* 内容层撑满高度：antd 会把子元素包进 .ant-layout-sider-children，
          需在此再套一层 flex 纵列，Menu flex:1 才能把用户区顶到最底部 */}
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        {/* Logo：收起时显示缩写 */}
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
            padding: collapsed ? 0 : '0 24px',
            fontSize: collapsed ? 18 : 22,
            fontWeight: 700,
            color: brand.primary,
            letterSpacing: collapsed ? 0 : 1,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
          }}
        >
          {collapsed ? '工坊' : '变体工坊'}
        </div>

        <Menu
          mode="inline"
          inlineCollapsed={collapsed}
          selectedKeys={[location.pathname]}
          items={items}
          style={{ borderInlineEnd: 'none', flex: 1, paddingTop: 8 }}
          onClick={({ key }) => navigate(key)}
        />

        {/* 底部用户区 */}
        <div style={{ borderTop: `1px solid ${brand.border}`, padding: collapsed ? '12px 0' : '12px 16px' }}>
          <Dropdown
            menu={{
              items: [
                {
                  key: 'logout',
                  icon: <LogoutOutlined />,
                  label: '退出登录',
                  danger: true,
                  onClick: () => {
                    logout()
                    navigate('/login')
                  },
                },
              ],
            }}
            trigger={['click']}
            placement="topRight"
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: collapsed ? 'center' : 'flex-start',
                gap: 10,
                cursor: 'pointer',
                padding: '6px 8px',
                borderRadius: 8,
              }}
            >
              <Avatar size={36} icon={<UserOutlined />} style={{ background: brand.primary, flex: 'none' }} />
              {!collapsed && (
                <>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>{user?.name ?? '未登录'}</div>
                    <Tag
                      color={user?.role === 'admin' ? 'blue' : 'default'}
                      style={{ marginTop: 2, fontSize: 11, lineHeight: '16px' }}
                    >
                      {user?.role === 'admin' ? '管理员' : '素材员'}
                    </Tag>
                  </div>
                  <Tooltip title="账户菜单">
                    <DownOutlined style={{ color: brand.textSecondary, fontSize: 10 }} />
                  </Tooltip>
                </>
              )}
            </div>
          </Dropdown>
        </div>
      </div>
    </Sider>
  )
}
