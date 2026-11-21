import { expect, test } from '@playwright/test'

test('journal search and calendar plans survive reload', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Get Started' }).first().click()

  await page.getByRole('button', { name: 'Farm Journal' }).click()
  await page.getByLabel('Title').fill('E2E persistence observation')
  await page.getByLabel('Notes').fill('Saved from the browser acceptance test.')
  await page.getByRole('button', { name: 'Save entry' }).click()
  await expect(page.getByText('E2E persistence observation')).toBeVisible()
  await page.getByRole('searchbox', { name: 'Search journal' }).fill('persistence observation')
  await expect(page.getByText('E2E persistence observation')).toBeVisible()

  await page.getByRole('button', { name: 'Crop Calendar' }).click()
  await page.getByRole('button', { name: 'Create plan' }).click()
  await expect(page.getByRole('heading', { name: 'Estimated growth stages' })).toBeVisible()

  await page.getByRole('button', { name: 'Knowledge Hub', exact: true }).click()
  await page.getByRole('searchbox', { name: 'Search crops' }).fill('mango')
  await expect(page.getByText('1 crop shown')).toBeVisible()
  await expect(page.getByText('Mango', { exact: true })).toBeVisible()
  await expect(page.getByText('Tomato', { exact: true })).toHaveCount(0)

  await page.reload()
  await page.getByRole('button', { name: 'Get Started' }).first().click()
  await page.getByRole('button', { name: 'Farm Journal' }).click()
  await expect(page.getByText('E2E persistence observation')).toBeVisible()
  await page.getByRole('button', { name: 'Crop Calendar' }).click()
  await expect(page.getByRole('heading', { name: 'Estimated growth stages' })).toBeVisible()
})
