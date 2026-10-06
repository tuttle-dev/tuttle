import { autoUpdater } from "electron-updater";
import type { BrowserWindow } from "electron";

export { autoUpdater };

const CHECK_INTERVAL_MS = 4 * 60 * 60 * 1000;

export type UpdateState =
  | { status: "idle" }
  | { status: "downloading"; version: string; percent: number }
  | { status: "ready"; version: string };

let state: UpdateState = { status: "idle" };
// Set while a check the user asked for (Settings → Check for updates) is in
// flight: only then do "no update" and failures reach the UI. Background
// checks fail silently (e.g. offline) and only log.
let userInitiated = false;
// On macOS, closing the window keeps the app running and "activate" opens a
// new one, so look the window up on every send. Holding on to the first one
// made every later send throw "Object has been destroyed".
let getWindow: () => BrowserWindow | null = () => null;

function send(channel: string, payload: unknown) {
  const win = getWindow();
  if (win && !win.isDestroyed()) win.webContents.send(channel, payload);
}

export function getUpdateState(): UpdateState {
  return state;
}

export function checkForUpdates(byUser: boolean) {
  if (state.status === "ready") {
    // Already downloaded; don't re-download, just re-announce it.
    if (byUser) send("update-downloaded", { version: state.version });
    return;
  }
  if (state.status === "downloading") {
    if (byUser) send("update-available", { version: state.version });
    return;
  }
  userInitiated = byUser;
  autoUpdater.checkForUpdates().catch((err) => {
    // Also surfaces via the "error" event; nothing more to do here.
    console.error("[updater] check failed:", err);
  });
}

export function initUpdater(currentWindow: () => BrowserWindow | null) {
  getWindow = currentWindow;
  autoUpdater.autoDownload = true;
  autoUpdater.autoInstallOnAppQuit = false;

  autoUpdater.on("update-available", (info) => {
    state = { status: "downloading", version: info.version, percent: 0 };
    send("update-available", { version: info.version });
    userInitiated = false;
  });

  autoUpdater.on("update-not-available", (info) => {
    if (userInitiated) {
      send("update-not-available", { version: info.version });
    }
    userInitiated = false;
  });

  autoUpdater.on("download-progress", (progress) => {
    if (state.status !== "downloading") return;
    state = { ...state, percent: Math.round(progress.percent) };
    send("update-progress", { version: state.version, percent: state.percent });
  });

  autoUpdater.on("update-downloaded", (info) => {
    state = { status: "ready", version: info.version };
    send("update-downloaded", { version: info.version });
  });

  autoUpdater.on("error", (err) => {
    console.error("[updater]", err);
    const wasDownloading = state.status === "downloading";
    if (wasDownloading) state = { status: "idle" };
    if (userInitiated || wasDownloading) {
      send("update-error", {
        message: wasDownloading
          ? "The update could not be downloaded. Tuttle will try again later, or use Settings → Check for updates. Details are in the application log."
          : "Couldn't check for updates. Check your internet connection and try again. Details are in the application log.",
      });
    }
    userInitiated = false;
  });

  checkForUpdates(false);
  setInterval(() => checkForUpdates(false), CHECK_INTERVAL_MS);
}
