// @ts-check
import { test, expect } from '@playwright/test';

/** 시나리오별로 깨끗한 상태: e2e/scenarios.md 참고 */
async function loadHomeFresh(page) {
  await page.goto('/index.html');
  await page.evaluate(() => {
    try {
      localStorage.clear();
      sessionStorage.clear();
    } catch (_) {}
  });
  await page.reload();
  await expect(page.locator('#loading')).toBeHidden({ timeout: 15_000 });
}

test.describe('정처기 실기 키워드 앱', () => {
  test('S1: 홈 초기 로딩', async ({ page }) => {
    await loadHomeFresh(page);
    await expect(page.locator('#home-screen')).toBeVisible();
    await expect(page.getByText('정처기 실기')).toBeVisible();
    await expect(page.locator('#home-sub')).toContainText(/키워드/);
  });

  test('S2: 순서대로 — 카드 뒤집기 → 정답 → 카운터 증가', async ({ page }) => {
    await loadHomeFresh(page);
    await page.getByRole('button', { name: /순서대로/ }).click();
    await expect(page.locator('#study-screen')).toBeVisible();
    await expect(page.locator('#study-counter')).toContainText(/1\s*\/\s*\d+/);

    await page.locator('#card-front').click();
    await expect(page.locator('#action-row')).toBeVisible();
    await expect(page.locator('#main-card')).toHaveClass(/flipped/);

    await page.getByRole('button', { name: '정답' }).click();
    await expect(page.locator('#study-counter')).toContainText(/2\s*\/\s*\d+/);
  });

  test('S3: 테마 토글 아이콘 변경', async ({ page }) => {
    await loadHomeFresh(page);
    const themeBtn = page.locator('#theme-btn');
    const before = await themeBtn.textContent();
    await themeBtn.click();
    const after = await themeBtn.textContent();
    expect(before).not.toBe(after);
  });

  test('S4: 통계 화면 진입', async ({ page }) => {
    await loadHomeFresh(page);
    await page.getByRole('button', { name: /통계 보기/ }).click();
    await expect(page.locator('#stats-screen')).toBeVisible();
    await expect(page.getByText('학습 통계')).toBeVisible();
  });

  test('S5: 학습 중 홈 복귀 시 이어하기 표시', async ({ page }) => {
    await loadHomeFresh(page);
    await page.getByRole('button', { name: /순서대로/ }).click();
    await expect(page.locator('#study-counter')).toContainText(/1\s*\/\s*\d+/);
    await page.locator('#top-bar-study-back').click();
    await expect(page.locator('#resume-btn')).toBeVisible();
    await expect(page.locator('#resume-btn')).toContainText(/이어하기/);
    await expect(page.locator('#resume-btn')).toContainText(/순서대로/);
  });

  test('S6: 오답 후 오답만 모드 활성화', async ({ page }) => {
    await loadHomeFresh(page);
    await page.getByRole('button', { name: /순서대로/ }).click();
    await page.locator('#card-front').click();
    await page.getByRole('button', { name: '오답' }).click();
    await expect(page.locator('#study-counter')).toContainText(/2\s*\/\s*\d+/);
    await page.locator('#top-bar-study-back').click();
    const btnWrong = page.locator('#btn-wrong');
    await expect(btnWrong).toBeEnabled();
    await expect(page.locator('#bdg-wrong')).toBeVisible();
  });

  test('S7: 카드 앞면 Enter로 뒤집기', async ({ page }) => {
    await loadHomeFresh(page);
    await page.getByRole('button', { name: /순서대로/ }).click();
    await page.locator('#card-front').focus();
    await page.keyboard.press('Enter');
    await expect(page.locator('#action-row')).toBeVisible();
    await expect(page.locator('#main-card')).toHaveClass(/flipped/);
  });

  test('S8: 랜덤 모드 라벨', async ({ page }) => {
    await loadHomeFresh(page);
    await page.getByRole('button', { name: /랜덤/ }).click();
    await expect(page.locator('#study-screen')).toBeVisible();
    await expect(page.locator('#study-mode-lbl')).toContainText(/랜덤/);
  });
});
