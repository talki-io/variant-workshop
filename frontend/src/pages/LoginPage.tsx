import { useState } from 'react'
import { App, Button, Form, Input } from 'antd'
import { LockOutlined, UserOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { brand } from '../theme/tokens'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const { message } = App.useApp()
  const [loading, setLoading] = useState(false)

  const onFinish = async (values: { username?: string; password?: string }) => {
    setLoading(true)
    try {
      await login(values.username ?? '', values.password ?? '')
      navigate('/generate')
    } catch (e) {
      message.error(e instanceof Error ? e.message : '登录失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', height: '100vh' }}>
      {/* 左：品牌区 */}
      <div
        style={{
          flex: '0 0 55%',
          background: `linear-gradient(135deg, ${brand.gradientFrom} 0%, ${brand.gradientTo} 100%)`,
          color: '#fff',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '0 96px',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* 几何数据线装饰 */}
        <svg
          width="100%"
          height="320"
          viewBox="0 0 800 320"
          style={{ position: 'absolute', bottom: 40, left: 0, opacity: 0.35 }}
        >
          <path d="M0 240 Q 200 120 400 200 T 800 140" stroke="#fff" strokeWidth="2" fill="none" />
          <path d="M0 280 Q 220 180 420 240 T 800 200" stroke="#93C5FD" strokeWidth="1.5" fill="none" />
          {[120, 260, 400, 540, 680].map((x, i) => (
            <circle key={i} cx={x} cy={200 - i * 8} r="4" fill="#fff" />
          ))}
        </svg>
        <h1 style={{ fontSize: 48, fontWeight: 800, margin: 0, letterSpacing: 2 }}>变体工坊</h1>
        <p style={{ fontSize: 18, marginTop: 20, opacity: 0.92 }}>
          让「想角度·写多版」从小时级压到分钟级
        </p>
      </div>

      {/* 右：表单区 */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#F5F7FA',
        }}
      >
        <div
          style={{
            width: 400,
            background: '#fff',
            borderRadius: 16,
            padding: '40px 40px 32px',
            boxShadow: '0 8px 30px rgba(16,24,40,0.06)',
          }}
        >
          <h2 style={{ textAlign: 'center', fontSize: 28, fontWeight: 700, margin: 0 }}>登录</h2>
          <p style={{ textAlign: 'center', color: brand.textSecondary, marginTop: 8, marginBottom: 28 }}>
            欢迎回来，请登录继续使用变体工坊
          </p>
          <Form onFinish={onFinish} size="large">
            <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
              <Input prefix={<UserOutlined />} placeholder="用户名 / 邮箱 / 工号" />
            </Form.Item>
            <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
              <Input.Password prefix={<LockOutlined />} placeholder="密码" />
            </Form.Item>
            <Form.Item>
              <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
                <a
                  style={{ color: brand.primary }}
                  onClick={() => message.info('内部工具账号由管理员统一管理，忘记密码请联系管理员重置')}
                >
                  忘记密码
                </a>
              </div>
            </Form.Item>
            <Form.Item style={{ marginBottom: 0 }}>
              <Button type="primary" htmlType="submit" block loading={loading}>
                登录
              </Button>
            </Form.Item>
          </Form>
          {/* 仅开发期显示：生产 SEED_DEMO_DATA=false，这两个账号根本不存在，
              显示出来既误导用户，也等于对外宣告系统有 demo 账号。生产构建会摇除。 */}
          {import.meta.env.DEV && (
            <p style={{ textAlign: 'center', color: brand.textSecondary, marginTop: 16, fontSize: 12 }}>
              演示账号：<b>admin</b> / <b>editor</b>（密码均为 <b>demo1234</b>）
            </p>
          )}
        </div>
        <p style={{ color: brand.textSecondary, marginTop: 24, fontSize: 13 }}>
          内部工具 · 仅授权账号访问
        </p>
      </div>
    </div>
  )
}
