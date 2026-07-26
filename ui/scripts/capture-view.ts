/**
 * Capture a screenshot of a single Tuttle app view.
 *
 * Usage (from ui/):
 *   npx tsx scripts/capture-view.ts <sidebar-id> <output-path>
 *
 * The script ensures the Harry Tuttle demo user is active and forces dark mode.
 */

import { _electron as electron } from "playwright";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";
import { frameScreenshot } from "./frame-screenshot";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const VIEW_LABELS: Record<string, string> = {
  dashboard: "Dashboard",
  timetracking: "Time Tracking",
  invoicing: "Invoicing",
  tax: "Tax & Reserves",
  salary: "Salary",
  import: "Import",
  timeline: "Timeline",
  projects: "Projects",
  contracts: "Contracts",
  clients: "Clients",
  contacts: "Contacts",
  settings: "Settings",
};

const DEMO_DB = "harry-tuttle.db";

async function main() {
  const [viewId, outFile] = process.argv.slice(2);

  if (!viewId || !outFile) {
    console.error("Usage: capture-view.ts <sidebar-id> <output-path>");
    console.error("Sidebar IDs:", Object.keys(VIEW_LABELS).join(", "));
    process.exit(1);
  }

  const label = VIEW_LABELS[viewId];
  if (!label) {
    console.error(`Unknown sidebar ID '${viewId}'.`);
    console.error("Valid IDs:", Object.keys(VIEW_LABELS).join(", "));
    process.exit(1);
  }

  const uiDir = path.resolve(__dirname, "..");
  const outPath = path.resolve(outFile);

  fs.mkdirSync(path.dirname(outPath), { recursive: true });

  console.log("Launching Electron app...");
  const app = await electron.launch({
    args: [path.join(uiDir, "dist-electron/main.js")],
    cwd: uiDir,
    env: { ...process.env, NODE_ENV: "production" },
  });

  const window = await app.firstWindow();
  await window.setViewportSize({ width: 1152, height: 768 });

  // Force dark mode before anything renders
  await window.evaluate(() => {
    localStorage.setItem("tuttle-theme", "dark");
    document.documentElement.classList.add("dark");
  });

  console.log("Waiting for app to load...");
  await window.waitForLoadState("networkidle");
  await window.waitForTimeout(3000);

  // Case 1: Fresh install — onboarding wizard is showing
  const demoButton = window.locator("text=Try with demo data");
  if (await demoButton.isVisible({ timeout: 2000 }).catch(() => false)) {
    console.log("Onboarding detected — activating demo user...");
    await demoButton.click();
    await window.waitForTimeout(5000);
  } else {
    // Case 2: App has users — ensure demo exists and switch to it via RPC
    console.log("Ensuring demo user exists and switching...");
    await window.evaluate(async () => {
      const t = (window as any).tuttle;
      await t.rpc("users.ensure_demo", {});
      await t.rpc("users.switch", { db_file: "harry-tuttle.db" });
    });
    // The app reloads on user switch
    await window.waitForTimeout(1000);
    window.reload();
    await window.waitForLoadState("networkidle");
    await window.waitForTimeout(3000);
  }

  await window.locator("nav").first().waitFor({ state: "visible", timeout: 15000 });

  // Re-apply dark mode after any reloads
  await window.evaluate(() => {
    localStorage.setItem("tuttle-theme", "dark");
    document.documentElement.classList.add("dark");
  });
  await window.waitForTimeout(500);

  console.log(`Navigating to ${label}...`);
  const navButton = window.locator("nav button", { hasText: label });
  await navButton.click();
  await window.waitForTimeout(2500);

  const rawPath = outPath.replace(/\.png$/, ".raw.png");
  await window.screenshot({ path: rawPath, type: "png" });

  console.log("Applying macOS window frame...");
  await frameScreenshot(rawPath, outPath);
  fs.unlinkSync(rawPath);
  console.log(`✓ ${outPath}`);

  await app.close();
}

main().catch((err) => {
  console.error("Capture failed:", err);
  process.exit(1);
});
