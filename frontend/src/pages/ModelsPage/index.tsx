import { useState } from 'react'
import {
  Card, Table, Button, Modal, Form, Select, Input, InputNumber, Switch, App, Tag, Space, Spin, Alert, Tooltip,
} from 'antd'
import {
  EditOutlined, DeleteOutlined, PlusOutlined, ThunderboltOutlined,
  CheckCircleFilled, CloseCircleFilled, LoadingOutlined,
} from '@ant-design/icons'
import { useAsyncData } from '../../hooks/useAsyncData'
import AsyncBoundary from '../../components/AsyncBoundary'
import {
  getLlmModels, createLlmModel, updateLlmModel, deleteLlmModel, verifyLlmModel,
  getModels, updateModel,
} from '../../services'
import type { LlmModel, ModelConfig } from '../../types'
import { brand } from '../../theme/tokens'

async function fetchAll() {
  const [models, configs] = await Promise.all([getLlmModels(), getModels()])
  return { models, configs }
}

/** 长报错截断给 toast 用（完整原因见「连通状态」列 Tooltip） */
const brief = (s: string, max = 60) => (s.length > max ? `${s.slice(0, max)}…` : s)

const providerTag = (p: string) =>
  p === 'anthropic'
    ? <Tag color="purple" bordered={false}>Anthropic</Tag>
    : <Tag color="cyan" bordered={false}>OpenAI 兼容</Tag>

export default function ModelsPage() {
  const { message, modal } = App.useApp()
  const { data, loading, error, reload, setData } = useAsyncData(fetchAll)
  const [mdlOpen, setMdlOpen] = useState(false)
  const [editingMdl, setEditingMdl] = useState<LlmModel | null>(null)
  const [editingScene, setEditingScene] = useState<ModelConfig | null>(null)
  const [saving, setSaving] = useState(false)
  const [verifyingId, setVerifyingId] = useState<string | null>(null)
  const [verifyMap, setVerifyMap] = useState<Record<string, { ok: boolean; text: string }>>({})
  const [mform] = Form.useForm()
  const [sform] = Form.useForm()

  const setModels = (fn: (m: LlmModel[]) => LlmModel[]) => setData((p) => (p ? { ...p, models: fn(p.models) } : p))
  const setConfigs = (fn: (c: ModelConfig[]) => ModelConfig[]) => setData((p) => (p ? { ...p, configs: fn(p.configs) } : p))

  // —— 模型库 ——
  const openAddMdl = () => { setEditingMdl(null); mform.resetFields(); mform.setFieldsValue({ provider: 'anthropic' }); setMdlOpen(true) }
  const openEditMdl = (m: LlmModel) => {
    setEditingMdl(m)
    mform.setFieldsValue({ name: m.name, provider: m.provider, modelId: m.modelId, baseUrl: m.baseUrl ?? '', apiKey: '' })
    setMdlOpen(true)
  }
  const submitMdl = () => {
    mform.validateFields().then(async (v) => {
      setSaving(true)
      try {
        const payload = {
          name: v.name, provider: v.provider, modelId: v.modelId,
          baseUrl: v.baseUrl?.trim() || null,
          // 编辑时留空 apiKey = 不改；新增时留空 = 无 key（anthropic 回退 .env）
          ...(v.apiKey?.trim() ? { apiKey: v.apiKey.trim() } : editingMdl ? {} : { apiKey: null }),
        }
        if (editingMdl) {
          const u = await updateLlmModel(editingMdl.id, payload)
          setModels((ms) => ms.map((x) => (x.id === editingMdl.id ? u : x)))
          clearVerify(editingMdl.id) // 配置已改，旧的连通结果作废
          message.success('模型已更新')
        } else {
          const c = await createLlmModel(payload)
          setModels((ms) => [...ms, c])
          message.success('模型已加入模型库')
        }
        setMdlOpen(false); setEditingMdl(null); mform.resetFields()
      } catch (e) {
        message.error(e instanceof Error ? e.message : '保存失败')
      } finally {
        setSaving(false)
      }
    })
  }
  const toggleMdl = async (m: LlmModel, enabled: boolean) => {
    setModels((ms) => ms.map((x) => (x.id === m.id ? { ...x, enabled } : x)))
    try { await updateLlmModel(m.id, { enabled }) } catch (e) {
      setModels((ms) => ms.map((x) => (x.id === m.id ? { ...x, enabled: !enabled } : x)))
      message.error(e instanceof Error ? e.message : '更新失败，已回滚')
    }
  }
  const delMdl = (m: LlmModel) =>
    modal.confirm({
      title: `从模型库删除「${m.name}」？`, okText: '删除', okType: 'danger', cancelText: '取消',
      onOk: async () => {
        try {
          await deleteLlmModel(m.id)
          setModels((ms) => ms.filter((x) => x.id !== m.id))
          clearVerify(m.id)
          message.success('已删除')
        } catch (e) { message.error(e instanceof Error ? e.message : '删除失败（可能正被场景绑定）') }
      },
    })
  // 清掉某模型的连通测试结果（配置改动/删除后旧结果会误导）
  const clearVerify = (id: string) =>
    setVerifyMap((v) => {
      if (!(id in v)) return v
      const next = { ...v }
      delete next[id]
      return next
    })

  const verify = async (m: LlmModel) => {
    setVerifyingId(m.id)
    // 厂商原始报错可能很长：toast 只给摘要，完整原因在「连通状态」列的 Tooltip 里
    const fail = (text: string) => {
      setVerifyMap((v) => ({ ...v, [m.id]: { ok: false, text } }))
      message.error(`「${m.name}」连通失败：${brief(text)}`)
    }
    try {
      const r = await verifyLlmModel(m.id)
      if (r.ok) {
        setVerifyMap((v) => ({ ...v, [m.id]: { ok: true, text: '连通正常' } }))
        message.success(`「${m.name}」连通正常`)
      } else {
        fail(r.error ?? '失败')
      }
    } catch (e) {
      fail(e instanceof Error ? e.message : '失败')
    } finally { setVerifyingId(null) }
  }

  // —— 场景绑定 ——
  const openEditScene = (s: ModelConfig) => {
    setEditingScene(s)
    sform.setFieldsValue({ modelId: s.modelId, maxTokens: s.maxTokens, temperature: s.temperature ?? undefined, enabled: s.enabled })
  }
  const submitScene = () => {
    sform.validateFields().then(async (v) => {
      if (!editingScene) return
      setSaving(true)
      try {
        const u = await updateModel(editingScene.scene, {
          modelId: v.modelId, maxTokens: v.maxTokens,
          temperature: v.temperature === undefined || v.temperature === null ? null : v.temperature,
          enabled: v.enabled,
        })
        setConfigs((cs) => cs.map((x) => (x.scene === editingScene.scene ? u : x)))
        message.success(`「${editingScene.label}」已保存，即时生效`)
        setEditingScene(null)
      } catch (e) { message.error(e instanceof Error ? e.message : '保存失败') } finally { setSaving(false) }
    })
  }

  if (error) return <AsyncBoundary loading={false} error={error} onRetry={reload}>{null}</AsyncBoundary>
  if (loading || !data) return <div style={{ textAlign: 'center', padding: 80 }}><Spin /></div>

  const { models, configs } = data
  const mdlName = (id: string) => models.find((m) => m.id === id)?.name ?? id
  const bindOptions = models.filter((m) => m.enabled).map((m) => ({ value: m.id, label: `${m.name}` }))

  // 连通状态：独立成列，不再挤进「操作」列（长错误文案会撑乱表格）
  const renderVerify = (_: unknown, m: LlmModel) => {
    if (verifyingId === m.id) {
      return <Tag icon={<LoadingOutlined />} color="processing" bordered={false}>测试中</Tag>
    }
    const r = verifyMap[m.id]
    if (!r) return <span style={{ color: brand.textSecondary }}>未测试</span>
    if (r.ok) {
      return <Tag icon={<CheckCircleFilled />} color="success" bordered={false}>连通正常</Tag>
    }
    // 失败原因可能很长（厂商原始报错）→ 收进 Tooltip，列内只显示定长标签
    return (
      <Tooltip title={r.text}>
        <Tag icon={<CloseCircleFilled />} color="error" bordered={false} style={{ cursor: 'help' }}>
          连通失败
        </Tag>
      </Tooltip>
    )
  }

  const mdlColumns = [
    { title: '模型名称', dataIndex: 'name', width: 170, render: (n: string) => <b>{n}</b> },
    { title: '厂商', dataIndex: 'provider', width: 120, render: providerTag },
    { title: '模型 ID', dataIndex: 'modelId', width: 190, render: (id: string) => <Tag bordered={false} style={{ background: 'var(--app-track)' }}>{id}</Tag> },
    {
      title: 'base_url',
      dataIndex: 'baseUrl',
      width: 240,
      render: (u: string | null) =>
        u ? (
          <Tooltip title={u}>
            <span
              style={{
                display: 'inline-block', maxWidth: 216, overflow: 'hidden',
                textOverflow: 'ellipsis', whiteSpace: 'nowrap', verticalAlign: 'bottom',
              }}
            >
              {u}
            </span>
          </Tooltip>
        ) : (
          <span style={{ color: brand.textSecondary }}>官方默认</span>
        ),
    },
    { title: '密钥', dataIndex: 'hasKey', width: 110, render: (h: boolean) => (h ? <Tag color="green" bordered={false}>已配</Tag> : <Tag bordered={false}>未配/环境</Tag>) },
    { title: '连通状态', key: 'verify', width: 120, render: renderVerify },
    { title: '启用', dataIndex: 'enabled', width: 80, render: (e: boolean, m: LlmModel) => <Switch checked={e} onChange={(v) => toggleMdl(m, v)} /> },
    {
      title: '操作',
      key: 'actions',
      width: 236,
      fixed: 'right' as const,
      render: (_: unknown, m: LlmModel) => (
        <Space size={4} style={{ whiteSpace: 'nowrap' }}>
          <Button size="small" icon={<ThunderboltOutlined />} loading={verifyingId === m.id} onClick={() => verify(m)}>测试</Button>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEditMdl(m)}>编辑</Button>
          <Button size="small" danger icon={<DeleteOutlined />} onClick={() => delMdl(m)}>删除</Button>
        </Space>
      ),
    },
  ]

  const sceneColumns = [
    { title: '管线场景', dataIndex: 'label', render: (l: string, s: ModelConfig) => <><b>{l}</b> <Tag bordered={false} style={{ marginLeft: 6, color: brand.textSecondary, background: 'var(--app-track)' }}>{s.scene}</Tag></> },
    { title: '绑定模型', dataIndex: 'modelId', render: (id: string) => <Tag color="geekblue" bordered={false}>{mdlName(id)}</Tag> },
    { title: 'max_tokens', dataIndex: 'maxTokens' },
    { title: 'temperature', dataIndex: 'temperature', render: (t: number | null) => (t == null ? <span style={{ color: brand.textSecondary }}>模型默认</span> : t) },
    { title: '启用', dataIndex: 'enabled', render: (e: boolean) => (e ? <Tag color="green" bordered={false}>启用</Tag> : <Tag bordered={false}>停用→回退默认</Tag>) },
    { title: '操作', width: 90, render: (_: unknown, s: ModelConfig) => <Button size="small" icon={<EditOutlined />} onClick={() => openEditScene(s)}>配置</Button> },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* 模型库 */}
      <Card title="模型库（多厂商）" extra={<Button type="primary" icon={<PlusOutlined />} onClick={openAddMdl}>新增模型</Button>}>
        <Alert
          type="info" showIcon
          message="维护可用模型。Anthropic 走原生（密钥留空则用 .env）；其他厂商（OpenAI/DeepSeek/Kimi/Qwen/Gemini兼容端点/各类中转）选「OpenAI 兼容」，填 base_url + 各自密钥。「测试」可验证连通性。"
          style={{ marginBottom: 16, background: 'var(--app-soft-primary)', border: 'none' }}
        />
        {/* scroll.x：列宽之和超出容器时横向滚动，避免挤压换行；操作列右侧吸附 */}
        <Table rowKey="id" columns={mdlColumns} dataSource={models} pagination={false} size="middle" scroll={{ x: 'max-content' }} />
      </Card>

      {/* 场景绑定 */}
      <Card title="管线场景绑定">
        <div style={{ marginBottom: 12, color: brand.textSecondary, fontSize: 13 }}>
          生成 / 清洗 / 合规 各绑定模型库里的一个模型 + 参数，保存即时生效。
        </div>
        <Table rowKey="scene" columns={sceneColumns} dataSource={configs} pagination={false} size="middle" />
      </Card>

      {/* 模型库 增改 Modal */}
      <Modal
        title={editingMdl ? '编辑模型' : '新增模型'}
        open={mdlOpen} onOk={submitMdl} confirmLoading={saving}
        onCancel={() => { setMdlOpen(false); setEditingMdl(null); mform.resetFields() }}
        okText={editingMdl ? '保存' : '新增'} cancelText="取消"
      >
        <Form form={mform} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item label="模型名称（展示用）" name="name" rules={[{ required: true }]}>
            <Input placeholder="如：DeepSeek Chat" />
          </Form.Item>
          <Form.Item label="厂商类型" name="provider" rules={[{ required: true }]}>
            <Select options={[{ value: 'anthropic', label: 'Anthropic（原生）' }, { value: 'openai', label: 'OpenAI 兼容（含各厂商/中转）' }]} />
          </Form.Item>
          <Form.Item label="模型 ID（厂商裸串）" name="modelId" rules={[{ required: true }]}>
            <Input placeholder="如：claude-sonnet-5 / deepseek-chat / gpt-4o" />
          </Form.Item>
          <Form.Item
            label="base_url" name="baseUrl"
            tooltip="OpenAI 兼容必填，如 https://api.deepseek.com/v1；Anthropic 留空用官方"
            dependencies={['provider']}
            rules={[({ getFieldValue }) => ({
              validator: (_, value) =>
                getFieldValue('provider') === 'openai' && !value?.trim()
                  ? Promise.reject(new Error('OpenAI 兼容模型必须填 base_url'))
                  : Promise.resolve(),
            })]}
          >
            <Input placeholder="https://api.deepseek.com/v1" />
          </Form.Item>
          <Form.Item label="API Key" name="apiKey" tooltip={editingMdl ? '留空=保持原密钥不变' : 'Anthropic 可留空用 .env；其他厂商必填'}>
            <Input.Password placeholder={editingMdl ? (editingMdl.hasKey ? '已配置，留空保持不变' : '未配置') : 'sk-…'} autoComplete="new-password" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 场景绑定 Modal */}
      <Modal
        title={editingScene ? `配置「${editingScene.label}」` : ''}
        open={!!editingScene} onOk={submitScene} confirmLoading={saving}
        onCancel={() => setEditingScene(null)} okText="保存并生效" cancelText="取消"
      >
        <Form form={sform} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item label="绑定模型（来自模型库）" name="modelId" rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="label" options={bindOptions} placeholder="选择模型" />
          </Form.Item>
          <Form.Item label="max_tokens" name="maxTokens" rules={[{ required: true }]}>
            <InputNumber min={1} max={64000} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="temperature（0–1，留空=模型默认）" name="temperature">
            <InputNumber min={0} max={1} step={0.1} style={{ width: '100%' }} placeholder="模型默认" />
          </Form.Item>
          <Form.Item label="启用（停用则回退内置默认模型）" name="enabled" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
