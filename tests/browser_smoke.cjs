// Disposable test account only. Real Android/iOS behavior requires manual checks.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const url = process.env.SENSO_TEST_URL || 'http://127.0.0.1:8564';
const password = 'browser-coffee-ritual-2026';
const renewed = 'browser-new-tea-ritual-2026';

(async () => {
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}),
    args: ['--no-sandbox'],
  });
  const errors = [];
  async function open() {
    const context = await browser.newContext({ viewport: { width: 1360, height: 1000 } });
    const page = await context.newPage();
    page.on('pageerror', e => errors.push(e.message));
    page.setDefaultTimeout(45000);
    await page.goto(url);
    await page.locator('flt-semantics-placeholder').evaluate(e => e.click());
    return page;
  }
  async function enter(page, values) {
    const fields = page.getByRole('textbox');
    for (const [index, value] of values.entries()) {
      await fields.nth(index).click();
      // Flutter creates and focuses its editing input after the semantics click.
      await page.waitForTimeout(400);
      await page.keyboard.type(value, { delay: 30 });
      assert.equal(await fields.nth(index).inputValue(), value);
    }
  }
  async function login(page, secret) {
    await page.getByRole('button', { name: '로그인', exact: true }).click();
    await enter(page, ['browser_smoke', secret]);
    await page.getByRole('button', { name: '로그인', exact: true }).click();
    await page.getByRole('button', { name: '로그아웃', exact: true }).waitFor();
  }
  try {
    const first = await open();
    const second = await open();
    await login(first, password);
    await login(second, password);
    await first.setViewportSize({ width: 390, height: 844 });
    await first.getByRole('tab', { name: '나', exact: true }).click();
    const downloadEvent = first.waitForEvent('download');
    await first.getByRole('button', { name: '내 데이터 내보내기 (ZIP)', exact: true }).click();
    const download = await downloadEvent;
    const path = await download.path();
    execFileSync(process.env.PYTHON || 'python', ['-c',
      'import sys,zipfile,json; z=zipfile.ZipFile(sys.argv[1]); d=json.loads(z.read("data.json")); assert d["beans"][0]["name"]=="Browser test tea"; assert "accounts.db" not in z.namelist()', path]);
    await first.getByRole('button', { name: '비밀번호 바꾸기', exact: true }).click();
    await enter(first, [password, renewed, renewed]);
    await first.getByRole('button', { name: '바꾸기', exact: true }).click();
    await second.getByRole('button', { name: '로그인', exact: true }).waitFor();
    await first.getByRole('button', { name: '로그아웃', exact: true }).waitFor();
    await login(second, renewed);
    await first.getByRole('button', { name: '계정 삭제', exact: true }).click();
    await enter(first, ['browser_smoke', renewed]);
    await first.getByRole('button', { name: '영구 삭제', exact: true }).click();
    await first.getByRole('button', { name: '로그인', exact: true }).waitFor();
    await second.getByRole('button', { name: '로그인', exact: true }).waitFor();
    assert.deepEqual(errors, []);
    console.log('PASS: desktop login; 390px ZIP download; password revocation; two-device deletion');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
