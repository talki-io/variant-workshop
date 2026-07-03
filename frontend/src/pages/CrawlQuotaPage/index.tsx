import { useState } from 'react'
import {
  Card, Table, Tag, Switch, Button, Badge, Space, Modal, Form, Input, InputNumber,
  Select, Row, Col, Alert, Spin, App, Dropdown, Empty,
} from 'antd'
import { PlusOutlined, ThunderboltOutlined, ReloadOutlined, MoreOutlined } from '@ant-design/icons'
import AsyncBoundary from '../../components/AsyncBoundary'
import { useAsyncData } from '../../hooks/useAsyncData'
import { getSources, getQuota, crawlSource, createSource, updateSource, deleteSource, updateQuota } from '../../services'
import type { CrawlSource, SourceType } from '../../types'
import { brand } from '../../theme/tokens'

const typeColor: Record<SourceType, string> = { RSS: 'orange', 搜索API: 'green', Playwright: 'purple' }

async function fetchAll() {
  const [sources, quota] = await Promise.all([getSources(), getQuota()])
  return { sources, config: quota.config, users: quota.users }
}

export default function CrawlQuotaPage() {
  const { message, modal } = App.useApp()
  const { data, loading, error, reload, setData } = useAsyncData(fetchAll)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form] = Form.useForm()
  const [quotaForm] = Form.useForm()
  const [saving, setSaving] = useState(false)

  const setEnabledLocal = (id: string, enabled: boolean) =>
    setData((prev) =>
      prev ? { ...prev, sources: prev.sources.map((s) => (s.id === id ? { ...s, enabled } : s)) } : prev,
    )

  // 启用开关落库：乐观更新 + 失败回滚
  const toggle = async (id: string, enabled: boolean) => {
    setEnabledLocal(id, enabled)
    try {
      await updateSource(id, { enabled })
    } catch (e) {
      setEnabledLocal(id, !enabled)
      message.error(e instanceof Error ? e.message : '更新失败，已回滚')
    }
  }

  const handleCrawl = async (r: CrawlSource) => {
    try {
      const res = await crawlSource(r.id)
      if (res.ok) message.success(`「${r.name}」抓取完成：新增 ${res.inserted}、去重 ${res.skipped}`)
      else message.warning(`「${r.name}」${res.message}`)
    } catch (e) {
      message.error(e instanceof Error ? e.message : '抓取失败')
    } finally {
      reload() // 刷新健康状态/上次抓取时间
    }
  }

  const openAdd = () => {
    setEditingId(null)
    form.resetFields()
    setModalOpen(true)
  }

  const openEdit = (r: CrawlSource) => {
    setEditingId(r.id)
    form.setFieldsValue(r)
    setModalOpen(true)
  }

  const confirmDelete = (r: CrawlSource) =>
    modal.confirm({
      title: `删除抓取源「${r.name}」？`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await deleteSource(r.id)
          setData((prev) => (prev ? { ...prev, sources: prev.sources.filter((s) => s.id !== r.id) } : prev))
          message.success(`抓取源「${r.name}」已删除`)
        } catch (e) {
          message.error(e instanceof Error ? e.message : '删除失败')
        }
      },
    })

  const columns = [
    { title: '源名称', dataIndex: 'name' },
    { title: '类型', dataIndex: 'type', render: (t: SourceType) => <Tag color={typeColor[t]} bordered={false}>{t}</Tag> },
    { title: 'URL', dataIndex: 'url', render: (u: string) => <a href={u} target="_blank" rel="noreferrer" style={{ color: brand.primary }}>{u}</a> },
    { title: '抓取频率', dataIndex: 'frequency' },
    { title: '上次抓取时间', dataIndex: 'lastCrawl' },
    {
      title: '健康状态',
      dataIndex: 'health',
      render: (h: CrawlSource['health']) =>
        h === 'ok' ? <Badge status="success" text="正常" /> : <Badge status="error" text="改版异常" />,
    },
    {
      title: '启用状态',
      dataIndex: 'enabled',
      render: (e: boolean, r: CrawlSource) => <Switch checked={e} onChange={(v) => toggle(r.id, v)} />,
    },
    {
      title: '操作',
      render: (_: unknown, r: CrawlSource) => (
        <Space>
          <Button size="small" icon={<ThunderboltOutlined />} onClick={() => handleCrawl(r)}>
            立即抓取
          </Button>
          <Dropdown
            menu={{
              items: [{ key: 'edit', label: '编辑' }, { key: 'del', label: '删除', danger: true }],
              onClick: ({ key }) => (key === 'edit' ? openEdit(r) : confirmDelete(r)),
            }}
          >
            <Button size="small" type="text" icon={<MoreOutlined />} />
          </Dropdown>
        </Space>
      ),
    },
  ]

  const onSubmit = () => {
    form.validateFields().then(async (v) => {
      try {
        if (editingId) {
          const updated = await updateSource(editingId, {
            name: v.name, type: v.type, url: v.url, frequency: v.frequency,
          })
          setData((prev) =>
            prev ? { ...prev, sources: prev.sources.map((s) => (s.id === editingId ? updated : s)) } : prev,
          )
        } else {
          const created = await createSource({ name: v.name, type: v.type, url: v.url, frequency: v.frequency })
          setData((prev) => (prev ? { ...prev, sources: [...prev.sources, created] } : prev))
        }
        message.success(editingId ? '抓取源已更新' : '抓取源已新增')
        setModalOpen(false)
        setEditingId(null)
        form.resetFields()
      } catch (e) {
        message.error(e instanceof Error ? e.message : '保存失败')
      }
    })
  }

  // 保存配额/限流配置落库
  const saveQuota = async () => {
    let v: Record<string, unknown>
    try {
      v = await quotaForm.validateFields()
    } catch {
      return // 校验未过
    }
    setSaving(true)
    try {
      const res = await updateQuota({
        perUserDaily: v.perUserDaily as number,
        overThresholdPct: v.overThresholdPct as number,
        circuitBreaker: v.circuitBreaker as boolean,
        breakerCondition: v.breakerCondition as string,
        globalDaily: v.globalDaily as number,
      })
      setData((prev) => (prev ? { ...prev, config: res.config, users: res.users } : prev))
      message.success('配置已保存')
    } catch (e) {
      message.error(e instanceof Error ? e.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  if (error) {
    return <AsyncBoundary loading={false} error={error} onRetry={reload}>{null}</AsyncBoundary>
  }
  if (loading || !data) return <div style={{ textAlign: 'center', padding: 80 }}><Spin /></div>

  const { sources, config: quota, users } = data

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* 抓取源配置 */}
      <Card
        title="抓取源配置"
        extra={<Button type="primary" icon={<PlusOutlined />} onClick={openAdd}>新增抓取源</Button>}
      >
        <Alert
          type="info"
          showIcon
          message="请遵守目标站点的 robots 协议与 ToS，尊重版权与使用边界。"
          style={{ marginBottom: 16, background: 'var(--app-soft-primary)', border: 'none' }}
        />
        <Table rowKey="id" columns={columns} dataSource={sources} pagination={{ pageSize: 10 }} size="middle" />
      </Card>

      {/* 配额与限流 */}
      <Row gutter={16}>
        <Col span={14}>
          <Card title="配额与限流">
            <Form form={quotaForm} layout="vertical" initialValues={quota}>
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item label="单用户日 token 限额" name="perUserDaily">
                    <InputNumber style={{ width: '100%' }} suffix="tokens" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="超额提醒阈值 (%)" name="overThresholdPct">
                    <InputNumber style={{ width: '100%' }} suffix="%" />
                  </Form.Item>
                </Col>
              </Row>
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item label="异常调用熔断" name="circuitBreaker" valuePropName="checked">
                    <Switch />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="触发条件" name="breakerCondition">
                    <Select options={[
                      { value: quota.breakerCondition, label: quota.breakerCondition },
                      { value: '错误率 ≥ 30% 且持续 3 分钟', label: '错误率 ≥ 30% 且持续 3 分钟' },
                    ]} />
                  </Form.Item>
                </Col>
              </Row>
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item label="全局日预算" name="globalDaily">
                    <InputNumber style={{ width: '100%' }} suffix="tokens" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="全局已用">
                    <Input
                      disabled
                      value={`${quota.globalUsed.toLocaleString()} tokens (${quota.globalUsedPct}%)`}
                    />
                  </Form.Item>
                </Col>
              </Row>
              <Button type="primary" loading={saving} onClick={saveQuota}>保存配置</Button>
            </Form>
          </Card>
        </Col>
        <Col span={10}>
          <Card
            title="按用户配额使用情况"
            extra={<Button type="link" icon={<ReloadOutlined />} onClick={reload}>刷新</Button>}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
              {users.length === 0 && <Empty description="暂无用户配额数据" />}
              {users.map((u) => {
                const pct = u.total > 0 ? Math.round((u.used / u.total) * 100) : 0
                const barPct = Math.min(pct, 100) // 条宽封顶 100%，超额不溢出容器
                const color = pct >= 90 ? brand.error : pct >= 60 ? brand.warning : brand.success
                return (
                  <div key={u.name} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <span style={{ width: 92, fontSize: 13, flex: 'none' }}>{u.name}</span>
                    <div style={{ flex: 1, minWidth: 0, height: 8, background: 'var(--app-track)', borderRadius: 999, overflow: 'hidden' }}>
                      <div style={{ width: `${barPct}%`, height: '100%', background: pct >= 100 ? brand.error : brand.primary, borderRadius: 999 }} />
                    </div>
                    <span style={{ fontSize: 12, color: brand.textSecondary, width: 90, flex: 'none', textAlign: 'right' }}>
                      {(u.used / 1000).toFixed(1)}k / {(u.total / 1000).toFixed(0)}k
                    </span>
                    <span style={{ width: 40, flex: 'none', textAlign: 'right', color, fontWeight: 600, fontSize: 13 }}>{pct}%</span>
                  </div>
                )
              })}
            </div>
          </Card>
        </Col>
      </Row>

      {/* 新增抓取源 Modal */}
      <Modal
        title={editingId ? '编辑抓取源' : '新增抓取源'}
        open={modalOpen}
        onOk={onSubmit}
        onCancel={() => { setModalOpen(false); setEditingId(null); form.resetFields() }}
        okText={editingId ? '保存' : '新增'}
        cancelText="取消"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item label="源名称" name="name" rules={[{ required: true }]}>
            <Input placeholder="如：行业资讯 RSS" />
          </Form.Item>
          <Form.Item label="类型" name="type" rules={[{ required: true }]}>
            <Select options={[{ value: 'RSS' }, { value: '搜索API' }, { value: 'Playwright' }]} />
          </Form.Item>
          <Form.Item label="URL" name="url" rules={[{ required: true }]}>
            <Input placeholder="https://…" />
          </Form.Item>
          <Form.Item label="抓取频率" name="frequency" rules={[{ required: true }]}>
            <Select options={[{ value: '每 15 分钟' }, { value: '每 30 分钟' }, { value: '每 60 分钟' }, { value: '每 2 小时' }]} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
