import { useState } from 'react'
import { Card, Table, Button, Modal, Form, Input, App, Space, Tag, Spin } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { useAsyncData } from '../../hooks/useAsyncData'
import AsyncBoundary from '../../components/AsyncBoundary'
import { getTones, createTone, updateTone, deleteTone } from '../../services'
import type { Tone } from '../../types'
import { brand } from '../../theme/tokens'

/** 账号/调性管理：文案生成的「账号语感」在此增删改（生成页只负责选用）。 */
export default function AccountsPage() {
  const { message, modal } = App.useApp()
  const { data, loading, error, reload, setData } = useAsyncData(getTones)
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<Tone | null>(null)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()

  const openAdd = () => {
    setEditing(null)
    form.resetFields()
    setOpen(true)
  }
  const openEdit = (t: Tone) => {
    setEditing(t)
    form.setFieldsValue(t)
    setOpen(true)
  }

  const submit = () => {
    form.validateFields().then(async (v) => {
      setSaving(true)
      try {
        if (editing) {
          const updated = await updateTone(editing.id, v)
          setData((prev) => (prev ?? []).map((t) => (t.id === editing.id ? updated : t)))
          message.success('账号已更新')
        } else {
          const created = await createTone(v)
          setData((prev) => [...(prev ?? []), created])
          message.success('账号已新增')
        }
        setOpen(false)
        setEditing(null)
        form.resetFields()
      } catch (e) {
        message.error(e instanceof Error ? e.message : '保存失败')
      } finally {
        setSaving(false)
      }
    })
  }

  const confirmDelete = (t: Tone) =>
    modal.confirm({
      title: `删除账号「${t.name}」？`,
      content: '该账号的参考爆款样本会一并删除；历史已生成的变体不受影响。',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await deleteTone(t.id)
          setData((prev) => (prev ?? []).filter((x) => x.id !== t.id))
          message.success(`账号「${t.name}」已删除`)
        } catch (e) {
          message.error(e instanceof Error ? e.message : '删除失败')
        }
      },
    })

  const columns = [
    {
      title: '账号 (handle)',
      dataIndex: 'handle',
      render: (h: string) => <Tag color="blue" bordered={false}>{h}</Tag>,
    },
    { title: '名称/语感', dataIndex: 'name', render: (n: string) => <b>{n}</b> },
    { title: '语感描述', dataIndex: 'desc', render: (d: string) => <span style={{ color: brand.textSecondary }}>{d}</span> },
    {
      title: '操作',
      width: 160,
      render: (_: unknown, t: Tone) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(t)}>编辑</Button>
          <Button size="small" danger icon={<DeleteOutlined />} onClick={() => confirmDelete(t)}>删除</Button>
        </Space>
      ),
    },
  ]

  if (error) return <AsyncBoundary loading={false} error={error} onRetry={reload}>{null}</AsyncBoundary>
  if (loading || !data) return <div style={{ textAlign: 'center', padding: 80 }}><Spin /></div>

  return (
    <Card
      title="账号 / 调性管理"
      extra={<Button type="primary" icon={<PlusOutlined />} onClick={openAdd}>新增账号</Button>}
    >
      <div style={{ marginBottom: 12, color: brand.textSecondary, fontSize: 13 }}>
        这里管理你自己的「账号语感」——只有你能看到和维护，其他用户互不可见。每个账号有独立的参考爆款样本
        （在生成页「参考爆款」里维护，同样只归属该账号），生成时选中某账号即按其语感 + 爆款风格产出。
      </div>
      <Table rowKey="id" columns={columns} dataSource={data} pagination={false} size="middle" />

      <Modal
        title={editing ? '编辑账号' : '新增账号'}
        open={open}
        onOk={submit}
        confirmLoading={saving}
        onCancel={() => { setOpen(false); setEditing(null); form.resetFields() }}
        okText={editing ? '保存' : '新增'}
        cancelText="取消"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item label="账号 handle" name="handle" rules={[{ required: true, message: '请输入 handle，如 @akun_demo' }]}>
            <Input placeholder="@akun_demo" />
          </Form.Item>
          <Form.Item label="名称 / 语感" name="name" rules={[{ required: true, message: '请输入账号名称' }]}>
            <Input placeholder="如：犀利散户体" />
          </Form.Item>
          <Form.Item label="语感描述" name="desc" rules={[{ required: true, message: '请输入语感描述' }]}>
            <Input placeholder="如：短句 · 大量俚语" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}
