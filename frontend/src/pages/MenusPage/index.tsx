import { useState } from 'react'
import { Card, Table, Button, Modal, Form, Input, Select, Switch, InputNumber, Checkbox, App, Space, Tag, Spin } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, LockOutlined } from '@ant-design/icons'
import { useAsyncData } from '../../hooks/useAsyncData'
import AsyncBoundary from '../../components/AsyncBoundary'
import { getAllMenus, createMenu, updateMenu, deleteMenu } from '../../services'
import { useMenu } from '../../menu/MenuContext'
import { ICON_NAMES, renderMenuIcon } from '../../layout/menuIcons'
import { KNOWN_ROUTES } from '../../menu/routes'
import type { MenuItem, Role } from '../../types'
import { brand } from '../../theme/tokens'

const ROLE_OPTIONS = [
  { value: 'editor', label: '素材员' },
  { value: 'admin', label: '管理员' },
]

const ICON_OPTIONS = ICON_NAMES.map((name) => ({
  value: name,
  label: (
    <Space size={6}>
      {renderMenuIcon(name)}
      <span>{name}</span>
    </Space>
  ),
}))

const PATH_OPTIONS = KNOWN_ROUTES.map((r) => ({ value: r.path, label: `${r.label}（${r.path}）` }))

/** 菜单管理（admin）：数据驱动侧栏——增删改现有页面的菜单项（名称/图标/路径/排序/可见角色/启用）。 */
export default function MenusPage() {
  const { message, modal } = App.useApp()
  const { reload: reloadSider } = useMenu()
  const { data, loading, error, reload, setData } = useAsyncData(getAllMenus)
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<MenuItem | null>(null)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()

  const afterChange = () => {
    reload() // 刷新本页表格
    reloadSider() // 侧栏即时反映
  }

  const openAdd = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ order: (data?.length ?? 0) + 1, visibleRoles: ['editor', 'admin'], enabled: true, icon: 'AppstoreOutlined' })
    setOpen(true)
  }
  const openEdit = (m: MenuItem) => {
    setEditing(m)
    form.setFieldsValue({ label: m.label, path: m.path, icon: m.icon, order: m.order, visibleRoles: m.visibleRoles, enabled: m.enabled })
    setOpen(true)
  }

  const submit = () => {
    form.validateFields().then(async (v) => {
      setSaving(true)
      try {
        if (editing) {
          await updateMenu(editing.id, v)
          message.success('菜单项已更新')
        } else {
          await createMenu(v)
          message.success('菜单项已新增')
        }
        setOpen(false)
        setEditing(null)
        form.resetFields()
        afterChange()
      } catch (e) {
        message.error(e instanceof Error ? e.message : '保存失败')
      } finally {
        setSaving(false)
      }
    })
  }

  const toggleEnabled = async (m: MenuItem, enabled: boolean) => {
    setData((prev) => (prev ?? []).map((x) => (x.id === m.id ? { ...x, enabled } : x)))
    try {
      await updateMenu(m.id, { enabled })
      reloadSider()
    } catch (e) {
      setData((prev) => (prev ?? []).map((x) => (x.id === m.id ? { ...x, enabled: !enabled } : x))) // 回滚
      message.error(e instanceof Error ? e.message : '操作失败')
    }
  }

  const confirmDelete = (m: MenuItem) =>
    modal.confirm({
      title: `删除菜单项「${m.label}」？`,
      content: '仅从侧栏移除该导航项，页面本身与后端不受影响。',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await deleteMenu(m.id)
          message.success(`菜单项「${m.label}」已删除`)
          afterChange()
        } catch (e) {
          message.error(e instanceof Error ? e.message : '删除失败')
        }
      },
    })

  const columns = [
    { title: '图标', dataIndex: 'icon', width: 64, render: (icon: string) => <span style={{ fontSize: 18 }}>{renderMenuIcon(icon)}</span> },
    { title: '名称', dataIndex: 'label', render: (l: string, m: MenuItem) => <b>{l}{m.locked && <LockOutlined style={{ marginLeft: 6, color: brand.textSecondary }} />}</b> },
    { title: '路径', dataIndex: 'path', render: (p: string) => <Tag bordered={false}>{p}</Tag> },
    { title: '排序', dataIndex: 'order', width: 70 },
    {
      title: '可见角色',
      dataIndex: 'visibleRoles',
      render: (roles: Role[]) => (roles ?? []).map((r) => (
        <Tag key={r} color={r === 'admin' ? 'blue' : 'default'}>{r === 'admin' ? '管理员' : '素材员'}</Tag>
      )),
    },
    {
      title: '启用',
      dataIndex: 'enabled',
      width: 80,
      render: (en: boolean, m: MenuItem) => <Switch checked={en} onChange={(c) => toggleEnabled(m, c)} />,
    },
    {
      title: '操作',
      width: 160,
      fixed: 'right' as const,
      render: (_: unknown, m: MenuItem) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(m)}>编辑</Button>
          <Button size="small" danger icon={<DeleteOutlined />} disabled={m.locked} onClick={() => confirmDelete(m)}>删除</Button>
        </Space>
      ),
    },
  ]

  if (error) return <AsyncBoundary loading={false} error={error} onRetry={reload}>{null}</AsyncBoundary>
  if (loading || !data) return <div style={{ textAlign: 'center', padding: 80 }}><Spin /></div>

  return (
    <Card
      title="菜单管理"
      extra={<Button type="primary" icon={<PlusOutlined />} onClick={openAdd}>新增菜单</Button>}
    >
      <div style={{ marginBottom: 12, color: brand.textSecondary, fontSize: 13 }}>
        侧栏导航由此表驱动。可增删改现有页面的菜单项（名称/图标/排序/按角色可见/启用）。路径只能选已存在的页面——菜单不创建新页面。
        锁定项（用户/菜单管理）不可删除，防误配自锁。
      </div>
      <Table rowKey="id" columns={columns} dataSource={data} pagination={false} size="middle" scroll={{ x: 'max-content' }} />

      <Modal
        title={editing ? '编辑菜单项' : '新增菜单项'}
        open={open}
        onOk={submit}
        confirmLoading={saving}
        onCancel={() => { setOpen(false); setEditing(null); form.resetFields() }}
        okText={editing ? '保存' : '新增'}
        cancelText="取消"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item label="名称" name="label" rules={[{ required: true, message: '请输入菜单名称' }]}>
            <Input placeholder="如：消耗看板" />
          </Form.Item>
          <Form.Item label="路径（已存在的页面）" name="path" rules={[{ required: true, message: '请选择路径' }]}>
            <Select options={PATH_OPTIONS} showSearch optionFilterProp="label" placeholder="选择页面路由" />
          </Form.Item>
          <Form.Item label="图标" name="icon" rules={[{ required: true, message: '请选择图标' }]}>
            <Select options={ICON_OPTIONS} showSearch optionFilterProp="value" />
          </Form.Item>
          <Form.Item label="排序" name="order" rules={[{ required: true, message: '请输入排序值' }]}>
            <InputNumber min={0} style={{ width: '100%' }} placeholder="数字越小越靠前" />
          </Form.Item>
          <Form.Item label="可见角色" name="visibleRoles" rules={[{ required: true, message: '至少选择一个角色' }]}>
            <Checkbox.Group options={ROLE_OPTIONS} />
          </Form.Item>
          <Form.Item label="启用" name="enabled" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}
