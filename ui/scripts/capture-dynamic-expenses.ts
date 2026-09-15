/**
 * Capture the five dynamic-expense screenshots for PR #522, on Harry Tuttle's demo data.
 *
 * Run from ui/:  npx tsx scripts/capture-dynamic-expenses.ts
 *
 * One pass: before shots, the form in percentage mode, then the after shots.
 */

import { _electron as electron, type Page } from "playwright";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";
import { frameScreenshot } from "./frame-screenshot";

const __dirname_ = path.dirname(fileURLToPath(import.meta.url));
const UI_DIR = path.resolve(__dirname_, "..");
const OUT_DIR = path.resolve(UI_DIR, "../assets/images/dynamic-expenses");

const RATE = "19.6";
const MAX_BASE = "66150"; // German health-insurance ceiling, 2025

async function shoot(window: Page, name: string) {
  const outPath = path.join(OUT_DIR, `${name}.png`);
  const rawPath = outPath.replace(/\.png$/, ".raw.png");
  await window.screenshot({ path: rawPath, type: "png" });
  await frameScreenshot(rawPath, outPath);
  fs.unlinkSync(rawPath);
  console.log(`✓ ${name}`);
}

async function goTo(window: Page, label: string) {
  await window.locator("nav button", { hasText: label }).first().click();
  await window.waitForTimeout(2500);
}

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });

  const app = await electron.launch({
    args: [path.join(UI_DIR, "dist-electron/main.js")],
    cwd: UI_DIR,
    env: { ...process.env, NODE_ENV: "production" },
  });

  const window = await app.firstWindow();
  await window.setViewportSize({ width: 1152, height: 768 });
  const dark = () =>
    window.evaluate(() => {
      localStorage.setItem("tuttle-theme", "dark");
      document.documentElement.classList.add("dark");
    });
  await dark();

  await window.waitForLoadState("networkidle");
  await window.waitForTimeout(3000);

  const demoButton = window.locator("text=Try with demo data");
  if (await demoButton.isVisible({ timeout: 2000 }).catch(() => false)) {
    console.log("onboarding — activating demo user");
    await demoButton.click();
    await window.waitForTimeout(5000);
  } else {
    console.log("switching to the demo user");
    await window.evaluate(async () => {
      const t = (window as any).tuttle;
      await t.rpc("users.ensure_demo", {});
      await t.rpc("users.switch", { db_file: "harry-tuttle.db" });
    });
    await window.waitForTimeout(1000);
    window.reload();
    await window.waitForLoadState("networkidle");
    await window.waitForTimeout(3000);
  }
  await window.locator("nav").first().waitFor({ state: "visible", timeout: 15000 });

  // The demo user ships without an operating country, which zeroes the tax line
  // and hides the deductible path entirely. demo.py already describes Harry as
  // taxed in Germany. Also clears any dynamic expense left by an earlier run.
  console.log("setting the operating country, clearing old dynamic expenses");
  const prep = await window.evaluate(async () => {
    const t = (window as any).tuttle;
    await t.rpc("users.update_profile", { profile: { operating_country: "Germany" } });
    const res = await t.rpc("salary.get_expenses", {});
    const dynamic = (res.data || []).filter((e: any) => e.rate != null);
    for (const e of dynamic) await t.rpc("salary.delete_expense", { expense_id: e.id });
    return { removed: dynamic.length };
  });
  console.log(`  removed ${prep.removed} stale dynamic expense(s)`);

  window.reload();
  await window.waitForLoadState("networkidle");
  await window.waitForTimeout(3000);
  await dark();

  // ── before ────────────────────────────────────────────────────────────────
  await goTo(window, "Salary");
  await shoot(window, "dynamic-expense-salary-before");
  await goTo(window, "Tax & Reserves");
  await shoot(window, "dynamic-expense-tax-before");

  // ── the form, in percentage mode ──────────────────────────────────────────
  await goTo(window, "Expenses");
  await window.locator("button", { hasText: "New" }).first().click();
  await window.waitForTimeout(600);

  await window.locator('input[placeholder="e.g. Health Insurance"]').fill("Health Insurance");
  await window.locator("button", { hasText: "Percentage of income" }).first().click();
  await window.waitForTimeout(300);
  await window.locator('input[placeholder="e.g. 19.6"]').fill(RATE);
  await window.locator('input[placeholder="max"]').fill(MAX_BASE);
  await window.locator('input[type="checkbox"]').first().check();
  await window.locator("select").filter({ hasText: "Health Care" }).first().selectOption("health");
  await window.waitForTimeout(600);
  await shoot(window, "dynamic-expense-form");

  await window.locator("button", { hasText: "Save" }).first().click();
  await window.waitForTimeout(2500);

  // ── after ─────────────────────────────────────────────────────────────────
  await goTo(window, "Salary");
  await shoot(window, "dynamic-expense-salary-after");
  await goTo(window, "Tax & Reserves");
  await shoot(window, "dynamic-expense-tax-after");

  await app.close();
  console.log("done");
}

main().catch((err) => {
  console.error("capture failed:", err);
  process.exit(1);
});
