/**
 * Smoke test for the deposit / final invoice flow (issue #326).
 *
 * Usage (from ui/):
 *   TUTTLE_DATA_DIR=../artifacts/smoke-data npx tsx scripts/smoke-deposit.ts ../artifacts/ui
 */

import { _electron as electron } from "playwright";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function main() {
  const outDir = path.resolve(process.argv[2] || "../artifacts/ui");
  fs.mkdirSync(outDir, { recursive: true });
  const uiDir = path.resolve(__dirname, "..");
  const shot = async (win: any, name: string) => {
    const p = path.join(outDir, `${name}.png`);
    await win.screenshot({ path: p, type: "png" });
    console.log(`  ✓ ${p}`);
  };

  const app = await electron.launch({
    args: [path.join(uiDir, "dist-electron/main.js")],
    cwd: uiDir,
    env: { ...process.env, NODE_ENV: "production" },
  });

  const win = await app.firstWindow();
  await win.setViewportSize({ width: 1280, height: 860 });
  await win.evaluate(() => {
    localStorage.setItem("tuttle-theme", "dark");
    document.documentElement.classList.add("dark");
  });
  await win.waitForLoadState("networkidle");
  await win.waitForTimeout(2500);

  const demoButton = win.locator("text=Try with demo data");
  if (await demoButton.isVisible({ timeout: 2000 }).catch(() => false)) {
    console.log("Onboarding — activating demo user");
    await demoButton.click();
    await win.waitForTimeout(6000);
  } else {
    await win.evaluate(async () => {
      const t = (window as any).tuttle;
      await t.rpc("users.ensure_demo", {});
      await t.rpc("users.switch", { db_file: "harry-tuttle.db" });
    });
    await win.waitForTimeout(1000);
    await win.reload();
    await win.waitForLoadState("networkidle");
    await win.waitForTimeout(3000);
  }

  await win.locator("nav").first().waitFor({ state: "visible", timeout: 20000 });
  await win.evaluate(() => {
    localStorage.setItem("tuttle-theme", "dark");
    document.documentElement.classList.add("dark");
  });

  // ── Contracts: the payment schedule editor and its invoiced markers ───────
  console.log("Contracts view");
  await win.locator("nav button", { hasText: "Contracts" }).click();
  await win.waitForTimeout(1500);
  await win.locator("text=Heating System Modernisation").first().click();
  await win.waitForTimeout(1200);
  await shot(win, "01-contract-payment-schedule");

  // ── Invoicing: the deposit chain, badges, and schedule status ─────────────
  console.log("Invoicing view");
  await win.locator("nav button", { hasText: "Invoicing" }).click();
  await win.waitForTimeout(2000);
  await shot(win, "02-invoicing-list");

  // ── Create dialog: document type picker and open-milestone selector ───────
  console.log("Create Invoice dialog");
  await win.locator("button", { hasText: "Create Invoice" }).first().click();
  await win.waitForTimeout(1000);
  await win.locator("select").first().selectOption({ label: "Heating Modernisation" });
  await win.waitForTimeout(1200);
  await shot(win, "03-create-dialog-document-type");

  await win.locator("button", { hasText: /^\s*Deposit\s*$/ }).click();
  await win.waitForTimeout(500);
  await win.locator("select").nth(1).selectOption({ index: 1 });
  await win.waitForTimeout(500);
  await shot(win, "04-create-dialog-milestone-selected");

  console.log("Creating the deposit invoice");
  await win.locator("button", { hasText: /Create Deposit Invoice/ }).click();
  await win.waitForTimeout(12000);
  await shot(win, "05-invoicing-after-deposit");

  // ── Settle the schedule: the last open milestone becomes the final invoice ─
  console.log("Creating the final invoice");
  await win.locator("button", { hasText: "Create Invoice" }).first().click();
  await win.waitForTimeout(1000);
  await win.locator("select").first().selectOption({ label: "Heating Modernisation" });
  await win.waitForTimeout(1200);
  await win.locator("button", { hasText: /^\s*Deposit\s*$/ }).click();
  await win.waitForTimeout(500);
  await win.locator("select").nth(1).selectOption({ index: 1 });
  await win.waitForTimeout(500);
  await shot(win, "06-create-dialog-last-milestone");
  await win.locator("button", { hasText: /Create Final Invoice/ }).click();
  await win.waitForTimeout(12000);
  await shot(win, "07-invoicing-after-final");

  // ── The chain view: final invoice with its deposits nested underneath ──────
  const finalRow = win.locator("text=Final").first();
  if (await finalRow.isVisible({ timeout: 2000 }).catch(() => false)) {
    await finalRow.click();
    await win.waitForTimeout(1500);
    await shot(win, "08-final-invoice-detail");
  }

  const errors = await win.locator("text=/Failed|Error|could not/i").allTextContents();
  if (errors.length) console.log("⚠ on-screen messages:", errors.slice(0, 5));

  await app.close();
  console.log("done");
}

main().catch((err) => {
  console.error("Smoke test failed:", err);
  process.exit(1);
});
