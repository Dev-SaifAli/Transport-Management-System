import { createRouter, createWebHistory, type Router } from 'vue-router'

import { routerBasePath } from '@/config'

/**
 * Router base is configurable (VITE_APP_BASE_PATH) so the app works when
 * served from a Frappe subpath such as /dispatch/.
 */
const router: Router = createRouter({
  history: createWebHistory(routerBasePath),
  routes: [
    { path: '/', redirect: '/dashboard' },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('@/features/dashboard/DashboardView.vue'),
      meta: { title: 'Dashboard' },
    },
    // Modules below are part of the approved navigation, but their screen
    // designs have not been provided yet. They render an explicit
    // "design pending" state until the designs are approved (Phase 4).
    {
      path: '/dispatch-board',
      name: 'dispatch-board',
      component: () => import('@/features/dispatch-board/components/DispatchBoardView.vue'),
      meta: { title: 'Dispatch Board' },
    },
    {
      path: '/dispatch-board/table',
      name: 'dispatch-table',
      component: () => import('@/features/dispatch-board/components/DispatchTableView.vue'),
      meta: { title: 'Dispatch — Table View' },
    },
    {
      path: '/transport-jobs',
      name: 'transport-jobs',
      component: () => import('@/features/placeholder/AwaitingDesignView.vue'),
      meta: { title: 'Transport Jobs', pendingDesign: true },
    },
    {
      path: '/create-trip',
      name: 'create-trip',
      component: () => import('@/features/trips/CreateTripView.vue'),
      meta: { title: 'Create Trip' },
    },
    {
      path: '/fleet-availability',
      name: 'fleet-availability',
      component: () => import('@/features/placeholder/AwaitingDesignView.vue'),
      meta: { title: 'Fleet Availability', pendingDesign: true },
    },
        {
      path: '/quotations',
      name: 'quotations',
      component: () => import('@/features/quotations/QuotationsView.vue'),
      meta: { title: 'Transport Quotations' },
    },
    { path: '/quotations/new', name: 'quotation-new', component: () => import('@/features/quotations/QuotationFormView.vue'), meta: { title: 'New Transport Quotation' } },
    { path: '/quotations/:id/edit', name: 'quotation-edit', component: () => import('@/features/quotations/QuotationFormView.vue'), meta: { title: 'Edit Transport Quotation' } },
    { path: '/quotations/:id', name: 'quotation-details', component: () => import('@/features/quotations/QuotationDetailsView.vue'), meta: { title: 'Quotation Details' } },
    {
      path: '/reports',
      name: 'reports',
      component: () => import('@/features/placeholder/AwaitingDesignView.vue'),
      meta: { title: 'Reports', pendingDesign: true },
    },
    { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

router.afterEach((to) => {
  const title = to.meta.title as string | undefined
  document.title = title ? `${title} · AL RANA Dispatch Portal` : 'AL RANA Dispatch Portal'
})

export default router
