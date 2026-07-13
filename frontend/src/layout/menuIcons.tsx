import type { ComponentType } from 'react'
import {
  EditOutlined,
  ReadOutlined,
  TeamOutlined,
  RobotOutlined,
  LineChartOutlined,
  DatabaseOutlined,
  AppstoreOutlined,
  UserOutlined,
  UsergroupAddOutlined,
  SettingOutlined,
  FileTextOutlined,
  BellOutlined,
  SearchOutlined,
  DashboardOutlined,
  BarChartOutlined,
  PieChartOutlined,
  CloudOutlined,
  ApiOutlined,
  ThunderboltOutlined,
  SafetyOutlined,
  ProfileOutlined,
  ScheduleOutlined,
  TagsOutlined,
  FolderOutlined,
  GlobalOutlined,
  KeyOutlined,
  HomeOutlined,
  MenuOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons'

/**
 * 菜单图标白名单注册表。antd 图标是静态 import + tree-shaking，无法按任意名字动态取用，
 * 故只有登记在此的图标才能被数据驱动菜单渲染。键集必须与后端 routers/menus.py 的 ICON_NAMES 一致。
 */
export const MENU_ICONS: Record<string, ComponentType<Record<string, unknown>>> = {
  EditOutlined,
  ReadOutlined,
  TeamOutlined,
  RobotOutlined,
  LineChartOutlined,
  DatabaseOutlined,
  AppstoreOutlined,
  UserOutlined,
  UsergroupAddOutlined,
  SettingOutlined,
  FileTextOutlined,
  BellOutlined,
  SearchOutlined,
  DashboardOutlined,
  BarChartOutlined,
  PieChartOutlined,
  CloudOutlined,
  ApiOutlined,
  ThunderboltOutlined,
  SafetyOutlined,
  ProfileOutlined,
  ScheduleOutlined,
  TagsOutlined,
  FolderOutlined,
  GlobalOutlined,
  KeyOutlined,
  HomeOutlined,
  MenuOutlined,
  UnorderedListOutlined,
}

export const ICON_NAMES = Object.keys(MENU_ICONS)

/** 按名渲染菜单图标；未知名字回退到通用图标（不崩）。 */
export function renderMenuIcon(name: string) {
  const Icon = MENU_ICONS[name] ?? AppstoreOutlined
  return <Icon />
}
