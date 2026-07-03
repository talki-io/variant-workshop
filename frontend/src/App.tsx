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
const ComponentsPage = lazy(() => import('./pages/ComponentsPage'))

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
            <Route path="/components" element={<ComponentsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/generate" replace />} />
        </Routes>
      </Suspense>
    </ErrorBoundary>
  )
}
