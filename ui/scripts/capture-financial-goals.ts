/**
 * Capture the Financial Goals card screenshots for the README / PR.
 *
 * Usage (from ui/):
 *   npx tsx scripts/capture-financial-goals.ts
 *
 * Writes into assets/images/financial-goals/:
 *   financial-goals-card.png  — the card against Harry Tuttle's demo goals
 *   financial-goals-form.png  — the inline create form
 *
 * The demo goals are the point of the first shot: "Service van replacement
 * fund" is due in a later year, so it reads that year's revenue rather than
 * the current year-to-date figure, while "Workshop tool upgrade" is already
 * covered and carries the reached marker.
 */

import { _electron as electron } from "playwright";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";
import { frameScreenshot } from "./frame-screenshot";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const DEMO_DB = "harry-tuttle.db";

async function main() {
  const uiDir = path.resolve(__dirname, "..");
  const outDir = path.resolve(uiDir, "../assets/images/financial-goals");
  fs.mkdirSync(outDir, { recursive: true });

  console.log("Launching Electron app...");
  const app = await electron.launch({
    args: [path.join(uiDir, "dist-electron/main.js")],
    cwd: uiDir,
    env: { ...process.env, NODE_ENV: "production" },
  });

  const window = await app.firstWindow();
  await window.setViewportSize({ width: 1152, height: 768 });

  const forceDark = () =>
    window.evaluate(() => {
      localStorage.setItem("tuttle-theme", "dark");
      document.documentElement.classList.add("dark");
    });

  await forceDark();
  await window.waitForLoadState("networkidle");
  await window.waitForTimeout(3000);

  const demoButton = window.locator("text=Try with demo data");
  if (await demoButton.isVisible({ timeout: 2000 }).catch(() => false)) {
    console.log("Onboarding detected — activating demo user...");
    await demoButton.click();
    await window.waitForTimeout(5000);
  } else {
    console.log("Ensuring demo user exists and switching...");
    await window.evaluate(async (dbFile) => {
      const t = (window as any).tuttle;
      await t.rpc("users.ensure_demo", {});
      await t.rpc("users.switch", { db_file: dbFile });
    }, DEMO_DB);
    await window.waitForTimeout(1000);
    window.reload();
    await window.waitForLoadState("networkidle");
    await window.waitForTimeout(3000);
  }

  await window.locator("nav").first().waitFor({ state: "visible", timeout: 15000 });
  await forceDark();
  await window.waitForTimeout(500);

  console.log("Navigating to Dashboard...");
  await window.locator("nav button", { hasText: "Dashboard" }).click();
  await window.waitForTimeout(2500);

  // The card sits below the revenue chart, so bring it fully into view.
  const heading = window.locator("h2", { hasText: "Financial Goals" });
  await heading.scrollIntoViewIfNeeded();
  await window.mouse.wheel(0, 400);
  await window.waitForTimeout(800);

  const shoot = async (name: string) => {
    const outPath = path.join(outDir, `${name}.png`);
    const rawPath = outPath.replace(/\.png$/, ".raw.png");
    await window.screenshot({ path: rawPath, type: "png" });
    await frameScreenshot(rawPath, outPath);
    fs.unlinkSync(rawPath);
    console.log(`✓ ${outPath}`);
  };

  await shoot("financial-goals-card");

  console.log("Opening the create form...");
  await window.locator("button", { hasText: "Add Goal" }).click();
  await window.waitForTimeout(400);
  await window.locator('input[placeholder="e.g. Yearly revenue"]').fill("Yearly revenue");
  await window.locator('input[placeholder="60000"]').fill("90000");
  await window.locator('input[type="date"]').last().fill("2026-12-31");
  // Move focus off the date field so no cell sits highlighted in the shot.
  await window.locator('input[placeholder="e.g. Yearly revenue"]').focus();
  await heading.scrollIntoViewIfNeeded();
  await window.mouse.wheel(0, 400);
  await window.waitForTimeout(600);

  await shoot("financial-goals-form");

  await app.close();
  console.log("Done.");
}

main().catch((err) => {
  console.error("Capture failed:", err);
  process.exit(1);
});
