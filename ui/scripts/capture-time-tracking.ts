/**
 * Capture the time-tracking timer screenshots for the README and PR.
 *
 * Usage (from ui/):
 *   TUTTLE_DATA_DIR=/tmp/tuttle-shots npx tsx scripts/capture-time-tracking.ts
 *
 * TUTTLE_DATA_DIR is required: the script seeds manual entries into the
 * current month and backdates the running timer, so it must never point at a
 * data directory anyone cares about.
 *
 * Writes:
 *   assets/images/screenshot-timetracking.png     — README: timer running
 *       mid-session, month grid populated, status bar mirroring the timer
 *   assets/images/time-tracking/day-entries.png   — a day's entries with the
 *       inline "Add entry" row open
 *   assets/images/time-tracking/timer-pending.png — stopped without a project:
 *       the bar asks for one before saving
 */

import { _electron as electron } from "playwright";
import { execFileSync } from "child_process";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";
import { frameScreenshot } from "./frame-screenshot";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const DEMO_DB = "harry-tuttle.db";
const TITLE_INPUT = 'input[placeholder="What are you working on?"]';

async function main() {
  const dataDir = process.env.TUTTLE_DATA_DIR;
  if (!dataDir) {
    console.error("Set TUTTLE_DATA_DIR to a scratch directory; this script seeds entries and backdates the timer.");
    process.exit(1);
  }
  const uiDir = path.resolve(__dirname, "..");
  const repoDir = path.resolve(uiDir, "..");
  const imagesDir = path.join(repoDir, "assets/images");
  const outDir = path.join(imagesDir, "time-tracking");
  fs.mkdirSync(outDir, { recursive: true });

  console.log("Launching Electron app...");
  const app = await electron.launch({
    args: [path.join(uiDir, "dist-electron/main.js")],
    cwd: uiDir,
    env: { ...process.env, NODE_ENV: "production" },
  });

  const window = await app.firstWindow();
  await window.setViewportSize({ width: 1152, height: 800 });

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

  const openTimeTracking = async () => {
    await window.locator("nav button", { hasText: "Time Tracking" }).click();
    await window.waitForTimeout(2500);
  };

  // The timer context reads its start time from the backend on mount, so a
  // reload is what makes a backdated start show up as elapsed time.
  const reloadToTimeTracking = async () => {
    window.reload();
    await window.waitForLoadState("networkidle");
    await window.waitForTimeout(3000);
    await window.locator("nav").first().waitFor({ state: "visible", timeout: 15000 });
    await forceDark();
    await openTimeTracking();
  };

  const backdateTimer = (hours: number, minutes: number, seconds: number) => {
    const py = [
      "import datetime",
      "from tuttle.app_db import AppDatabase",
      `delta = datetime.timedelta(hours=${hours}, minutes=${minutes}, seconds=${seconds})`,
      "start = datetime.datetime.now(tz=datetime.timezone.utc) - delta",
      'AppDatabase().set_setting("timetracking.timer_start", start.isoformat())',
    ].join("\n");
    execFileSync("uv", ["run", "--no-sync", "python", "-c", py], {
      cwd: repoDir,
      env: { ...process.env, TUTTLE_DATA_DIR: dataDir },
      stdio: "inherit",
    });
  };

  const shoot = async (outPath: string, opts: { keepMouse?: boolean } = {}) => {
    if (!opts.keepMouse) await window.mouse.move(640, 40);
    const rawPath = outPath.replace(/\.png$/, ".raw.png");
    await window.screenshot({ path: rawPath, type: "png" });
    await frameScreenshot(rawPath, outPath);
    fs.unlinkSync(rawPath);
    console.log(`✓ ${outPath}`);
  };

  const projectSelect = () => window.locator(TITLE_INPUT).locator("xpath=following-sibling::select");

  // ── Seed a few entries into the current month ─────────────────────────────
  const tags: string[] = await window.evaluate(async () => {
    const t = (window as any).tuttle;
    const res = await t.rpc("timetracking.get_project_tags", {});
    const list = Array.isArray(res) ? res : res?.data ?? [];
    return list.map((p: any) => p.tag);
  });
  if (tags.length === 0) throw new Error("The demo user has no projects to track time on.");
  const [primary, secondary = tags[0]] = tags;

  const today = new Date();
  const dayIso = (day: number) =>
    `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
  const plan = [
    { off: 1, tag: primary, start: "09:00", end: "12:30", title: "Firewall rule review" },
    { off: 1, tag: secondary, start: "14:00", end: "16:00", title: "Weekly client call" },
    { off: 2, tag: primary, start: "10:00", end: "15:00", title: "Pen-test write-up" },
    { off: 4, tag: secondary, start: "09:30", end: "11:00", title: "Sprint planning" },
    { off: 5, tag: primary, start: "13:00", end: "17:30", title: "Log analysis" },
    { off: 7, tag: primary, start: "09:00", end: "12:00", title: "Kickoff workshop" },
  ]
    .filter((e) => today.getDate() - e.off >= 1)
    .map((e) => ({
      tag: e.tag, title: e.title, date: dayIso(today.getDate() - e.off), start_time: e.start, end_time: e.end,
    }));
  await window.evaluate(async (entries) => {
    const t = (window as any).tuttle;
    for (const entry of entries) await t.rpc("timetracking.add_manual_entry", entry);
  }, plan);

  // ── Shot 1: timer running (README) ────────────────────────────────────────
  await openTimeTracking();
  await window.locator(TITLE_INPUT).fill("Reviewing firewall rules");
  await projectSelect().selectOption(primary);
  await window.locator('button[title="Start timer"]').click();
  await window.waitForTimeout(800);
  backdateTimer(1, 12, 37);
  await reloadToTimeTracking();
  await shoot(path.join(imagesDir, "screenshot-timetracking.png"));

  // ── Shot 2: a day's entries with the add-entry row open ───────────────────
  const yesterday = today.getDate() - 1;
  await window
    .locator("button")
    .filter({ has: window.locator("span", { hasText: new RegExp(`^${yesterday}$`) }) })
    .first()
    .click();
  await window.waitForTimeout(600);
  const addEntry = window.locator("button", { hasText: "Add entry" });
  await addEntry.scrollIntoViewIfNeeded();
  await addEntry.click();
  await window.waitForTimeout(400);
  await window.locator("button", { hasText: "Cancel" }).scrollIntoViewIfNeeded();
  await window.locator("div.group").filter({ hasText: "Firewall rule review" }).hover();
  await window.waitForTimeout(300);
  await shoot(path.join(outDir, "day-entries.png"), { keepMouse: true });

  // ── Shot 3: stopped without a project ─────────────────────────────────────
  await window.locator('button[title="Discard timer"]').click();
  await window.waitForTimeout(300);
  await window.locator('button[title="Close"]').click();
  await window.locator(TITLE_INPUT).fill("Untangling the VPN config");
  await projectSelect().selectOption("");
  await window.locator('button[title="Start timer"]').click();
  await window.waitForTimeout(800);
  backdateTimer(0, 47, 12);
  await reloadToTimeTracking();
  await window.locator('button[title="Stop timer"]').first().click();
  await window.waitForTimeout(400);
  await shoot(path.join(outDir, "timer-pending.png"));

  await window.locator('button[title="Discard timer"]').click();
  await app.close();
  console.log("Done.");
}

main().catch((err) => {
  console.error("Capture failed:", err);
  process.exit(1);
});
