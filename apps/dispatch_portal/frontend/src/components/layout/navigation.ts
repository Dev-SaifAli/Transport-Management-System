import {
  BarChart3,
  Briefcase,
  CirclePlus,
  FileText,
  Gauge,
  Trello,
  Truck,
  type LucideIcon,
} from 'lucide-vue-next'

export interface NavItem {
  title: string
  to: string
  icon: LucideIcon
}

export interface NavSection {
  label: string
  items: NavItem[]
}

/**
 * Sidebar navigation, matching the provided Dashboard design.
 * Only modules present in the approved design are listed here.
 */
export const navigationSections: NavSection[] = [
  {
    label: 'Overview',
    items: [
      { title: 'Dashboard', to: '/dashboard', icon: Gauge },
      { title: 'Dispatch Board', to: '/dispatch-board', icon: Trello },
      { title: 'Transport Jobs', to: '/transport-jobs', icon: Briefcase },
    ],
  },
  {
    label: 'Operations',
     items: [
      { title: 'Create Trip', to: '/create-trip', icon: CirclePlus },
      { title: 'Quotations', to: '/quotations', icon: FileText },
      { title: 'Fleet Availability', to: '/fleet-availability', icon: Truck },
    ],
  },
  {
    label: 'Insights',
    items: [
      { title: 'Reports', to: '/reports', icon: BarChart3 },
    ],
  },
]
