import { useState } from 'react'
import { Card, Table, Button, Modal, Form, Input, Select, Switch, App, Space, Tag, Spin } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, KeyOutlined } from '@ant-design/icons'
import { useAsyncData } from '../../hooks/useAsyncData'
import AsyncBoundary from '../../components/AsyncBoundary'
import { getUsers, createUser, updateUser, deleteUser, resetUserPassword } from '../../services'
import { useAuth } from '../../auth/AuthContext'
import type { User, Role } from '../../types'
import { brand } from '../../theme/tokens'

const ROLE_OPTIONS = [
  { value: 'editor', label: '素材员（editor）' },
  { value: 'admin', label: '管理员（admin）' },
]

/** 用户管理（admin）：增删改用户、改角色、重置密码、启用/停用。 */
export default function UsersPage() {
  const { user: me } = useAuth()
  const { message, modal } = App.useApp()
  const { data, loading, error, reload, setData } = useAsyncData(getUsers)
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<User | null>(null)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()
  // 重置密码弹窗
  const [pwOpen, setPwOpen] = useState(false)
  const [pwTarget, setPwTarget] = useState<User | null>(null)
  const [pwSaving, setPwSaving] = useState(false)
  const [pwForm] = Form.useForm()

  const openAdd = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ role: 'editor' })
    setOpen(true)
  }
  const openEdit = (u: User) => {
    setEditing(u)
    form.setFieldsValue({ name: u.name, role: u.role })
    setOpen(true)
  }

  const submit = () => {
    form.validateFields().then(async (v) => {
      setSaving(true)
      try {
        if (editing) {
          const updated = await updateUser(editing.id, { name: v.name, role: v.role })
          setData((prev) => (prev ?? []).map((u) => (u.id === editing.id ? updated : u)))
          message.success('用户已更新')
        } else {
          const created = await createUser({ name: v.name, role: v.role, password: v.password })
          setData((prev) => [...(prev ?? []), created])
          message.success('用户已新增')
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

  const toggleActive = async (u: User, active: boolean) => {
    setData((prev) => (prev ?? []).map((x) => (x.id === u.id ? { ...x, active } : x)))
    try {
      await updateUser(u.id, { active })
      message.success(active ? `已启用「${u.name}」` : `已停用「${u.name}」`)
    } catch (e) {
      setData((prev) => (prev ?? []).map((x) => (x.id === u.id ? { ...x, active: !active } : x))) // 回滚
      message.error(e instanceof Error ? e.message : '操作失败')
    }
  }

  const openReset = (u: User) => {
    setPwTarget(u)
    pwForm.resetFields()
    setPwOpen(true)
  }
  const submitReset = () => {
    pwForm.validateFields().then(async (v) => {
      if (!pwTarget) return
      setPwSaving(true)
      try {
        await resetUserPassword(pwTarget.id, v.password)
        message.success(`「${pwTarget.name}」密码已重置`)
        setPwOpen(false)
        setPwTarget(null)
      } catch (e) {
        message.error(e instanceof Error ? e.message : '重置失败')
      } finally {
        setPwSaving(false)
      }
    })
  }

  const confirmDelete = (u: User) =>
    modal.confirm({
      title: `删除用户「${u.name}」？`,
      content: '会一并删除该用户名下的账号与参考文案、生成会话；历史用量记录保留。此操作不可撤销。',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await deleteUser(u.id)
          setData((prev) => (prev ?? []).filter((x) => x.id !== u.id))
          message.success(`用户「${u.name}」已删除`)
        } catch (e) {
          message.error(e instanceof Error ? e.message : '删除失败')
        }
      },
    })

  const columns = [
    { title: '用户名', dataIndex: 'name', render: (n: string, u: User) => <b>{n}{u.id === me?.id && <Tag color="green" bordered={false} style={{ marginLeft: 8 }}>我</Tag>}</b> },
    {
      title: '角色',
      dataIndex: 'role',
      width: 140,
      render: (r: Role) => <Tag color={r === 'admin' ? 'blue' : 'default'}>{r === 'admin' ? '管理员' : '素材员'}</Tag>,
    },
    {
      title: '启用',
      dataIndex: 'active',
      width: 90,
      render: (a: boolean | undefined, u: User) => (
        <Switch
          checked={a !== false}
          disabled={u.id === me?.id}
          onChange={(checked) => toggleActive(u, checked)}
        />
      ),
    },
    {
      title: '操作',
      width: 240,
      render: (_: unknown, u: User) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(u)}>编辑</Button>
          <Button size="small" icon={<KeyOutlined />} onClick={() => openReset(u)}>重置密码</Button>
          <Button size="small" danger icon={<DeleteOutlined />} disabled={u.id === me?.id} onClick={() => confirmDelete(u)}>删除</Button>
        </Space>
      ),
    },
  ]

  if (error) return <AsyncBoundary loading={false} error={error} onRetry={reload}>{null}</AsyncBoundary>
  if (loading || !data) return <div style={{ textAlign: 'center', padding: 80 }}><Spin /></div>

  return (
    <Card
      title="用户管理"
      extra={<Button type="primary" icon={<PlusOutlined />} onClick={openAdd}>新增用户</Button>}
    >
      <div style={{ marginBottom: 12, color: brand.textSecondary, fontSize: 13 }}>
        管理系统用户与角色。停用为软删（不能登录、现存会话失效，可随时启用）。为防自锁，不能停用/删除自己或最后一个管理员。
      </div>
      <Table rowKey="id" columns={columns} dataSource={data} pagination={false} size="middle" scroll={{ x: 'max-content' }} />

      <Modal
        title={editing ? '编辑用户' : '新增用户'}
        open={open}
        onOk={submit}
        confirmLoading={saving}
        onCancel={() => { setOpen(false); setEditing(null); form.resetFields() }}
        okText={editing ? '保存' : '新增'}
        cancelText="取消"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item label="用户名" name="name" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input placeholder="如：zhangwei" />
          </Form.Item>
          <Form.Item label="角色" name="role" rules={[{ required: true, message: '请选择角色' }]}>
            <Select options={ROLE_OPTIONS} />
          </Form.Item>
          {!editing && (
            <Form.Item label="初始密码" name="password" rules={[{ required: true, message: '请输入密码' }, { min: 8, message: '密码至少 8 位' }]}>
              <Input.Password placeholder="至少 8 位" autoComplete="new-password" />
            </Form.Item>
          )}
        </Form>
      </Modal>

      <Modal
        title={`重置密码 · ${pwTarget?.name ?? ''}`}
        open={pwOpen}
        onOk={submitReset}
        confirmLoading={pwSaving}
        onCancel={() => { setPwOpen(false); setPwTarget(null); pwForm.resetFields() }}
        okText="重置"
        cancelText="取消"
      >
        <Form form={pwForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item label="新密码" name="password" rules={[{ required: true, message: '请输入新密码' }, { min: 8, message: '密码至少 8 位' }]}>
            <Input.Password placeholder="至少 8 位" autoComplete="new-password" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}
