// Script-owned Playwright smoke: login via real browser, navbar renders, no JS errors.
// Usage: node admin_smoke.mjs [login] [password]
import { chromium } from 'playwright';

const BASE = process.env.UPASS_BASE_URL || 'http://localhost:8070';
const LOGIN = process.argv[2] || 'admin@demo.com';
const PASS = process.argv[3] || 'admin123';
const IGNORE = /favicon|manifest\.json|websocket|bus\/|service.?worker|sourcemap/i;

const errors = [];
const browser = await chromium.launch();
const page = await browser.newPage();
page.on('pageerror', (e) => errors.push(`pageerror: ${e}`));
page.on('console', (m) => { if (m.type() === 'error' && !IGNORE.test(m.text())) errors.push(`console: ${m.text()}`); });
page.on('response', (r) => { if (r.status() >= 500) errors.push(`HTTP ${r.status()} ${r.url()}`); });

try {
  await page.goto(`${BASE}/web/login`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.fill('input[name="login"]', LOGIN);
  await page.fill('input[name="password"]', PASS);
  await Promise.all([
    page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 45000 }),
    page.click('button[type="submit"]'),
  ]);
  // Odoo 19 web client: navbar or home menu must appear; login page must be gone.
  await page.waitForSelector('.o_navbar, .o_home_menu, .o_main_navbar', { timeout: 45000 });
  if (page.url().includes('/web/login')) throw new Error('still on login page — auth failed');
  await page.waitForTimeout(4000); // let lazy assets/owl mounts settle and surface errors
  await page.screenshot({ path: `/tmp/upass_smoke_${LOGIN.replace(/[^a-z0-9]/gi, '_')}.png`, fullPage: false });
} catch (e) {
  errors.push(`fatal: ${e.message || e}`);
}
await browser.close();

if (errors.length) {
  console.error(`SMOKE FAILED for ${LOGIN}:`);
  for (const e of errors) console.error('  - ' + e);
  process.exit(1);
}
console.log(`SMOKE PASSED for ${LOGIN} (screenshot in /tmp)`);
