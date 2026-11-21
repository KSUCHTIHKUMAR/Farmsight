import { expect, test } from '@playwright/test'

test('landing page navigation reaches every main application area', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Know your crop before it shows.' })).toBeVisible()
  await page.getByRole('button', { name: 'Get Started' }).first().click()

  const areas = [
    ['Diagnose Leaf', 'Diagnose Leaf'],
    ['Grade Produce', 'Grade Produce'],
    ['Identify Pest', 'Identify Pest'],
    ['Farm Overview', 'Farm Overview'],
    ['Knowledge Hub', 'Knowledge Hub'],
    ['Crop Care Guide', 'Crop Care Guide'],
    ['Crop Calendar', 'Crop Calendar'],
    ['Farm Journal', 'Farm Journal'],
  ] as const

  for (const [navigationLabel, heading] of areas) {
    await page.getByRole('button', { name: navigationLabel, exact: true }).click()
    await expect(page.getByRole('heading', { name: heading }).first()).toBeVisible()
  }
})

test('mobile layout exposes the scan flow and navigation without a language selector', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await expect(page.getByRole('group', { name: 'Language' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Get Started' }).first()).toBeVisible()
  await page.getByRole('button', { name: 'Get Started' }).first().click()
  await expect(page.getByRole('group', { name: 'Language' })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'What are you analysing today?' })).toBeVisible()
  await page.getByRole('button', { name: /Diagnose Leaf/ }).click()
  await expect(page.getByRole('heading', { name: 'Add your photo' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Upload Photo' })).toBeVisible()
})

test('language selector is absent and the app stays in English', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('farmsight.lang', 'te'))
  await page.goto('/')
  await expect(page.locator('html')).toHaveAttribute('lang', 'en')
  await expect(page.getByRole('group', { name: 'Language' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Get Started' }).first()).toBeVisible()
  await page.getByRole('button', { name: 'Get Started' }).first().click()
  await expect(page.locator('html')).toHaveAttribute('lang', 'en')
  await expect(page.getByRole('group', { name: 'Language' })).toHaveCount(0)
})
