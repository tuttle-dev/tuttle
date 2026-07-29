/**
 * Verification run for the "additional contract charges" feature.
 *
 * Walks the Harry Tuttle demo data and captures the four states that matter:
 * the charges on a contract, the collapsed opt-in in the form, the expanded
 * editor, and the preview shown when creating an invoice.
 *
 * Usage (from ui/):  npx tsx scripts/verify-contract-charges.ts <out-dir>
 */

import { _electron as electron } from "playwright";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const CONTRACT_TITLE = "On-Site Boiler Retrofit";

// The Electron launch occasionally wedges, most often on the very first run
// after the demo database is rebuilt. Fail rather than hang.
const watchdog = setTimeout(() => {
  console.error("Watchdog: giving up after 240s");
  process.exit(1);
}, 240_000);
watchdog.unref();

async function main() {
  const outDir = path.resolve(process.argv[2] ?? "../artifacts/contract-charges");
  fs.mkdirSync(outDir, { recursive: true });

  const uiDir = path.resolve(__dirname, "..");
  const app = await electron.launch({
    args: [path.join(uiDir, "dist-electron/main.js")],
    cwd: uiDir,
    env: { ...process.env, NODE_ENV: "production" },
  });

  const window = await app.firstWindow();
  await window.setViewportSize({ width: 1280, height: 900 });
  await window.evaluate(() => {
    localStorage.setItem("tuttle-theme", "dark");
    document.documentElement.classList.add("dark");
  });
  await window.waitForLoadState("networkidle");
  await window.waitForTimeout(2500);

  const demoButton = window.locator("text=Try with demo data");
  if (await demoButton.isVisible({ timeout: 2000 }).catch(() => false)) {
    await demoButton.click();
    await window.waitForTimeout(6000);
  } else {
    await window.evaluate(async () => {
      const t = (window as any).tuttle;
      await t.rpc("users.ensure_demo", {});
      await t.rpc("users.switch", { db_file: "harry-tuttle.db" });
    });
    await window.waitForTimeout(1000);
    await window.reload();
    await window.waitForLoadState("networkidle");
    await window.waitForTimeout(3000);
  }

  await window.evaluate(() => document.documentElement.classList.add("dark"));
  await window.locator("nav").first().waitFor({ state: "visible", timeout: 15000 });

  const shot = async (name: string) => {
    const file = path.join(outDir, `${name}.png`);
    await window.screenshot({ path: file, type: "png", animations: "disabled", timeout: 60000 });
    console.log(`✓ ${file}`);
  };

  // ── 1. Contract detail shows the charges ────────────────────────────────
  await window.locator("nav button", { hasText: "Contracts" }).click();
  await window.waitForTimeout(1500);
  await window.locator("button", { hasText: CONTRACT_TITLE }).first().click();
  await window.waitForTimeout(1200);
  await shot("1-contract-detail-charges");

  // ── 2. Edit form: the opt-in is collapsed, no inputs on screen ──────────
  await window.locator("button", { hasText: /^Edit$/ }).first().click();
  await window.waitForTimeout(1200);
  await shot("2-form-charges-expanded-existing");

  // ── 3. A contract without charges shows only the collapsed control ──────
  const cancel = () => window.locator("button", { hasText: "Cancel" }).first().click();
  await cancel();
  await window.waitForTimeout(800);
  const plainContract = window.locator("button", { hasText: "Heating Repair – Sam Lowry" }).first();
  if (await plainContract.isVisible().catch(() => false)) {
    await plainContract.click();
    await window.waitForTimeout(1000);
    await window.locator("button", { hasText: /^Edit$/ }).first().click();
    await window.waitForTimeout(1200);
    await shot("3-form-charges-collapsed");

    await window.locator("button[aria-label='More information about additional charges']").hover();
    await window.waitForTimeout(600);
    await shot("3b-form-charges-hint-open");

    await window.locator("button", { hasText: "Additional charges" }).first().click();
    await window.waitForTimeout(500);
    await window.locator("button", { hasText: "Add charge" }).first().click();
    await window.waitForTimeout(800);
    await shot("4-form-charges-expanded-new-row");
    await cancel();
    await window.waitForTimeout(600);
  }

  // ── 5. Invoice creation shows what the charges will add ─────────────────
  await window.locator("nav button", { hasText: "Invoicing" }).click();
  await window.waitForTimeout(1500);
  await window.locator("button", { hasText: "Create Invoice" }).first().click();
  await window.waitForTimeout(2000);

  await window.locator("select").first().selectOption({ label: "Boiler Retrofit" });
  await window.waitForTimeout(2000);
  await shot("5-invoice-dialog-charge-preview");

  await app.close();
  clearTimeout(watchdog);
  console.log("\nDone.");
}

main().catch(async (err) => {
  console.error("Verification failed:", err);
  process.exit(1);
});
