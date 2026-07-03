import { useState } from 'react'
import { Card, Col, Row, Statistic, Progress, Segmented, Table, Button, Avatar, Tag, Spin, Space, Tooltip, Select } from 'antd'
import {
  DatabaseFilled,
  DollarOutlined,
  TeamOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  DownloadOutlined,
  UserOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons'
import { Area } from '@ant-design/charts'
import AsyncBoundary from '../../components/AsyncBoundary'
import { useAsyncData } from '../../hooks/useAsyncData'
import { getDashboard } from '../../services'
import type { UsageDetail } from '../../types'
import { brand } from '../../theme/tokens'

const MODEL_COLORS = ['#2563EB', '#14B8A6', '#8B5CF6'] // Haiku / Sonnet / Opus

function fmt(n: number) {
  return n.toLocaleString('en-US')
}

/** 坐标轴/数值缩写：2000000 → 2.0M，800000 → 800K */
function abbrNum(n: number): string {
  if (n >= 1e6) return `${+(n / 1e6).toFixed(1)}M`
  if (n >= 1e3) return `${Math.round(n / 1e3)}K`
  return `${n}`
}

/** 按周聚合（label 取每 7 天一段的末日），供「按周」粒度 */
function toWeekly(rows: { date: string; model: string; tokens: number }[]) {
  const dates = [...new Set(rows.map((r) => r.date))].sort()
  const label = new Map<string, string>()
  dates.forEach((d, i) => label.set(d, dates[Math.min(dates.length - 1, Math.floor(i / 7) * 7 + 6)]))
  const agg = new Map<string, number>()
  for (const r of rows) {
    const k = `${label.get(r.date)}|${r.model}`
    agg.set(k, (agg.get(k) ?? 0) + r.tokens)
  }
  return [...agg.entries()].map(([k, tokens]) => {
    const [date, model] = k.split('|')
    return { date, model, tokens }
  })
}

// 趋势色：按各指标语义决定"上升是否为好"（token/成本下降=好，用户数上升=好）
function Trend({ v, goodWhenUp = true }: { v: number; goodWhenUp?: boolean }) {
  const up = v >= 0
  const good = up === goodWhenUp
  return (
    <span style={{ color: good ? brand.success : brand.error, fontSize: 13 }}>
      较昨日 {up ? <ArrowUpOutlined /> : <ArrowDownOutlined />} {Math.abs(v)}%
    </span>
  )
}

function KpiTitle({ text, tip }: { text: string; tip: string }) {
  return (
    <Space size={4}>
      <span>{text}</span>
      <Tooltip title={tip}>
        <InfoCircleOutlined style={{ color: brand.textSecondary, fontSize: 12 }} />
      </Tooltip>
    </Space>
  )
}

const BIG_VALUE = { fontWeight: 700, fontSize: 30 } as const

export default function DashboardPage() {
  const { data, loading, error, reload } = useAsyncData(getDashboard)
  const [range, setRange] = useState<string>('30天')
  const [gran, setGran] = useState<'day' | 'week'>('day')

  if (error) {
    return <AsyncBoundary loading={false} error={error} onRetry={reload}>{null}</AsyncBoundary>
  }
  if (loading || !data) return <div style={{ textAlign: 'center', padding: 80 }}><Spin /></div>

  const { kpi, daily, topUsers, details } = data
  const maxTop = topUsers.length ? Math.max(...topUsers.map((u) => u.tokens)) : 1

  // 时间范围过滤（客户端切片）：按去重日期取最近 N 天
  const days = range === '今日' ? 1 : range === '7天' ? 7 : 30
  const keepDates = new Set([...new Set(daily.map((d) => d.date))].slice(-days))
  const rangeDaily = daily.filter((d) => keepDates.has(d.date))
  const shownDaily = gran === 'week' ? toWeekly(rangeDaily) : rangeDaily
  const trendTitle = range === '今日' ? '今日 token 消耗趋势（按模型）' : `近 ${days} 天 token 消耗趋势（按模型）`

  const exportCsv = () => {
    const header = ['用户', '时间', '模型', '输入token', '输出token', '成本', '场景']
    const rows = details.map((d) => [d.user, d.time, d.model, d.inputTokens, d.outputTokens, d.cost, d.scene])
    const csv = [header, ...rows]
      .map((r) => r.map((x) => `"${String(x).replace(/"/g, '""')}"`).join(','))
      .join('\n')
    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '消耗明细.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  const columns = [
    { title: '用户', dataIndex: 'user', render: (v: string) => <Space><Avatar size={22} icon={<UserOutlined />} />{v}</Space> },
    { title: '时间', dataIndex: 'time', sorter: (a: UsageDetail, b: UsageDetail) => a.time.localeCompare(b.time) },
    { title: '模型', dataIndex: 'model', render: (v: string) => <Tag color={v.includes('Opus') ? 'purple' : v.includes('Sonnet') ? 'cyan' : 'blue'} bordered={false}>{v}</Tag> },
    { title: '输入 token', dataIndex: 'inputTokens', align: 'right' as const, render: fmt },
    { title: '输出 token', dataIndex: 'outputTokens', align: 'right' as const, render: fmt },
    { title: '成本 (¥)', dataIndex: 'cost', align: 'right' as const, render: (v: number) => `¥ ${v.toFixed(2)}` },
    { title: '场景', dataIndex: 'scene', render: (v: string) => <span style={{ color: brand.textSecondary }}>{v}</span> },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <Segmented options={['今日', '7天', '30天', '自定义']} value={range} onChange={(v) => setRange(v as string)} />
      </div>

      {/* KPI */}
      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <Statistic
                title={<KpiTitle text="今日总 token" tip="今日所有模型消耗的 token 总量（输入 + 输出）" />}
                value={kpi.todayTokens}
                valueStyle={{ color: brand.primary, ...BIG_VALUE }}
              />
              <Avatar shape="square" size={40} icon={<DatabaseFilled />} style={{ background: 'var(--app-soft-primary)', color: brand.primary }} />
            </div>
            <Trend v={kpi.tokensTrend} goodWhenUp={false} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <Statistic
                title={<KpiTitle text="今日总成本 (¥)" tip="今日 token 消耗折算的人民币成本" />}
                value={kpi.todayCost}
                precision={2}
                valueStyle={BIG_VALUE}
              />
              <Avatar shape="square" size={40} icon={<DollarOutlined />} style={{ background: 'var(--app-soft-success)', color: brand.success }} />
            </div>
            <Trend v={kpi.costTrend} goodWhenUp={false} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <Statistic
                title={<KpiTitle text="活跃用户数" tip="今日有生成/使用记录的用户数" />}
                value={kpi.activeUsers}
                valueStyle={BIG_VALUE}
              />
              <Avatar shape="square" size={40} icon={<TeamOutlined />} style={{ background: 'var(--app-soft-violet)', color: '#8B5CF6' }} />
            </div>
            <Trend v={kpi.usersTrend} goodWhenUp />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <Progress type="circle" percent={kpi.quotaUsedPct} size={72} strokeColor={brand.primary} />
              <div>
                <div style={{ color: brand.textSecondary, fontSize: 13 }}>
                  <KpiTitle text="本月配额使用率" tip="本月已用 token 占全局配额的比例" />
                </div>
                <div style={{ marginTop: 6, fontSize: 12 }}>已使用 <b style={{ color: brand.primary }}>{kpi.quotaUsed} tokens</b></div>
                <div style={{ fontSize: 12 }}>总配额 <b>{kpi.quotaTotal} tokens</b></div>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 图表 */}
      <Row gutter={16}>
        <Col span={14}>
          <Card
            title={trendTitle}
            extra={
              <Select
                size="small"
                value={gran}
                onChange={setGran}
                style={{ width: 88 }}
                options={[
                  { value: 'day', label: '按天' },
                  { value: 'week', label: '按周' },
                ]}
              />
            }
          >
            <Area
              data={shownDaily}
              xField="date"
              yField="tokens"
              colorField="model"
              stack
              height={280}
              shapeField="smooth"
              scale={{ color: { range: MODEL_COLORS } }}
              // 半透明层叠填充 + 顶边描线，营造设计图的分层面积质感
              style={{ fillOpacity: 0.5, lineWidth: 2 }}
              // 每个数据点圆点标记（白描边），对齐设计图；stack 会自动让点落到各层顶边
              point={{ sizeField: 3, style: { fillOpacity: 1, lineWidth: 1.5, stroke: '#fff' } }}
              // 图例：顶部填充圆点
              legend={{
                color: {
                  position: 'top',
                  layout: { justifyContent: 'flex-start' },
                  itemMarker: 'circle',
                  itemMarkerSize: 10,
                },
              }}
              axis={{
                x: { tickCount: 8, title: false },
                y: { title: 'token', labelFormatter: (v: number) => abbrNum(Number(v)) },
              }}
              tooltip={{ items: [{ channel: 'y', valueFormatter: (v: number) => fmt(Number(v)) }] }}
            />
          </Card>
        </Col>
        <Col span={10}>
          <Card title="消耗 Top 10 用户（按总 token）">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {topUsers.map((u) => (
                <div key={u.rank} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ width: 16, textAlign: 'right', color: brand.textSecondary, fontSize: 13 }}>{u.rank}</span>
                  <Avatar size={22} icon={<UserOutlined />} />
                  <span style={{ width: 44, fontSize: 13 }}>{u.name}</span>
                  <div style={{ flex: 1, height: 14, background: 'var(--app-track)', borderRadius: 4, overflow: 'hidden' }}>
                    <div style={{ width: `${(u.tokens / maxTop) * 100}%`, height: '100%', background: brand.primary, borderRadius: 4 }} />
                  </div>
                  <span style={{ width: 56, textAlign: 'right', fontSize: 12, color: brand.textSecondary }}>
                    {abbrNum(u.tokens)}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </Col>
      </Row>

      {/* 明细表 */}
      <Card
        title="消耗明细"
        extra={<Button icon={<DownloadOutlined />} onClick={exportCsv}>导出 CSV</Button>}
      >
        <Table
          rowKey="id"
          columns={columns}
          dataSource={details}
          pagination={{ pageSize: 5, showSizeChanger: true, showTotal: (t) => `共 ${t} 条` }}
          size="middle"
        />
      </Card>
    </div>
  )
}
