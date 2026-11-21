import { expect, test } from '@playwright/test'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const leafImage = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '../../data/leaf_field_test/Potato___Early_blight/test_backus-056-potato-blight.jpg',
)

test('leaf upload displays a real API prediction and Grad-CAM', async ({ page }) => {
  test.setTimeout(120_000)
  await page.goto('/')
  await page.getByRole('button', { name: 'Get Started' }).first().click()
  await page.locator('input[type="file"]').setInputFiles(leafImage)
  await expect(page.getByRole('heading', { name: 'Top 3 guesses' })).toBeVisible({
    timeout: 90_000,
  })
  await expect(page.getByRole('img', { name: 'Photo you submitted' })).toBeVisible()
  await expect(
    page.getByRole('img', {
      name: 'Heatmap overlay on your photo; red areas influenced the result most',
    }),
  ).toBeVisible()
  await expect(page.getByText(/Demo mode|placeholder/i)).toHaveCount(0)
})

test('backend failure shows an error instead of a fabricated prediction', async ({ page }) => {
  await page.route('**/api/analyse', (route) => route.abort())
  await page.goto('/')
  await page.getByRole('button', { name: 'Get Started' }).first().click()
  await page.locator('input[type="file"]').setInputFiles(leafImage)
  await expect(
    page.getByRole('heading', { name: "Can't reach the analysis service" }),
  ).toBeVisible({ timeout: 30_000 })
  await expect(page.getByRole('heading', { name: 'Top 3 guesses' })).toHaveCount(0)
})
