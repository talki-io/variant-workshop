import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { Spin } from 'antd'
import AppLayout from './layout/AppLayout'
import { RequireAdmin, RequireAuth } from './auth/guards'
import ErrorBoundary from './components/ErrorBoundary'
import GlobalErrorNotifier from './components/GlobalErrorNotifier'
import LoginPage from './pages/LoginPage'

// 路由级懒加载：各页面按需拆包，看板的图表大包仅在进入 /dashboard 时才请求
const GeneratePage = lazy(() => import('./pages/GeneratePage'))
const NewsPage = lazy(() => import('./pages/NewsPage'))
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const CrawlQuotaPage = lazy(() => import('./pages/CrawlQuotaPage'))
const AccountsPage = lazy(() => import('./pages/AccountsPage'))
const ModelsPage = lazy(() => import('./pages/ModelsPage'))
// 组件走查页只用于开发期视觉回归，是全项目唯一依赖 dev-only/mocks 假数据的入口。
// import.meta.env.DEV 在生产构建中被静态替换为 false，该分支连同动态 import 一并被摇除，
// mock 数据因此不会进入生产产物。
const ComponentsPage = import.meta.env.DEV
  ? lazy(() => import('./dev-only/ComponentsPage'))
  : null

function PageFallback() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: 120 }}>
      <Spin size="large" />
    </div>
  )
}

export default function App() {
  return (
    <ErrorBoundary>
      <GlobalErrorNotifier />
      <Suspense fallback={<PageFallback />}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            element={
              <RequireAuth>
                <AppLayout />
              </RequireAuth>
            }
          >
            <Route index element={<Navigate to="/generate" replace />} />
            <Route path="/generate" element={<GeneratePage />} />
            <Route path="/news" element={<NewsPage />} />
            <Route
              path="/dashboard"
              element={
                <RequireAdmin>
                  <DashboardPage />
                </RequireAdmin>
              }
            />
            <Route
              path="/crawl-quota"
              element={
                <RequireAdmin>
                  <CrawlQuotaPage />
                </RequireAdmin>
              }
            />
            <Route
              path="/accounts"
              element={
                <RequireAdmin>
                  <AccountsPage />
                </RequireAdmin>
              }
            />
            <Route
              path="/models"
              element={
                <RequireAdmin>
                  <ModelsPage />
                </RequireAdmin>
              }
            />
            {ComponentsPage && <Route path="/components" element={<ComponentsPage />} />}
          </Route>
          <Route path="*" element={<Navigate to="/generate" replace />} />
        </Routes>
      </Suspense>
    </ErrorBoundary>
  )
}
