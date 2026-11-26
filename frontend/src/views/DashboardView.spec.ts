import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { api } from '../api/client'
import DashboardView from './DashboardView.vue'

describe('dashboard material count', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('shows the stored material count', async () => {
    vi.spyOn(api, 'countSources').mockResolvedValue({ total: 125 })
    const wrapper = mount(DashboardView, { global: { stubs: ['RouterLink'] } })

    expect(wrapper.get('[aria-live="polite"]').text()).toContain('正在加载')
    await flushPromises()
    expect(wrapper.get('[aria-live="polite"]').text()).toContain('125')

    wrapper.unmount()
  })

  it('shows an unavailable count when the request fails', async () => {
    vi.spyOn(api, 'countSources').mockRejectedValue(new Error('offline'))
    const wrapper = mount(DashboardView, { global: { stubs: ['RouterLink'] } })

    await flushPromises()
    expect(wrapper.get('[aria-live="polite"]').text()).toBe('暂时无法读取')

    wrapper.unmount()
  })
})
