import {
  LayoutDashboard,
  FileText,
  Settings,
  Command,
  Newspaper,
  BookOpen,
} from 'lucide-react'
import { type SidebarData } from '../types'

export const sidebarData: SidebarData = {
  user: {
    name: 'AI Agent',
    email: 'agent@trading.ai',
    avatar: '',
  },
  teams: [
    {
      name: 'AI 交易大脑',
      logo: Command,
      plan: 'OpenBB + TradingAgents',
    },
  ],
  navGroups: [
    {
      title: '核心功能',
      items: [
        {
          title: '控制台',
          url: '/',
          icon: LayoutDashboard,
        },
        {
          title: '财联社情报',
          url: '/cls-news',
          icon: Newspaper,
        },
        {
          title: 'TradingView情报',
          url: '/tv-news',
          icon: Newspaper,
        },
        {
          title: '决策报告',
          url: '/reports',
          icon: FileText,
        },
        {
          title: '投资日记',
          url: '/investment-diary',
          icon: BookOpen,
        },
        {
          title: '系统设置',
          url: '/settings',
          icon: Settings,
        },
      ],
    },
  ],
}
