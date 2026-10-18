import { app, BrowserWindow, ipcMain, nativeTheme, screen, shell, type BrowserWindowConstructorOptions } from "electron";
import path from "node:path";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { PythonBridge } from "./python-bridge";
import { autoUpdater, checkForUpdates, getUpdateState, initUpdater } from "./updater";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let mainWindow: BrowserWindow | null = null;
let pythonBridge: PythonBridge | null = null;

const MIN_WIDTH = 1024;
const MIN_HEIGHT = 700;
const COMFORTABLE_WIDTH = 1280;
// Height of the view toolbar (h-13), which doubles as the title bar.
const TITLE_BAR_HEIGHT = 52;

// Open centered on the display under the cursor: half its width on wide
// displays, a comfortable width on smaller ones, never past the screen.
function initialBounds() {
  const { workArea } = screen.getDisplayNearestPoint(screen.getCursorScreenPoint());
  const width = Math.min(workArea.width, Math.max(Math.round(workArea.width / 2), COMFORTABLE_WIDTH));
  const height = Math.min(workArea.height, Math.max(Math.round(workArea.height * 0.9), MIN_HEIGHT));
  return {
    width,
    height,
    x: workArea.x + Math.round((workArea.width - width) / 2),
    y: workArea.y + Math.round((workArea.height - height) / 2),
  };
}

// The view toolbar doubles as the title bar on every platform. macOS keeps
// its traffic lights over the sidebar; Windows and Linux draw their window
// buttons over the toolbar (window controls overlay), in the colours the
// renderer sends for its theme. Until then they match the dark default.
function titleBarOptions(): BrowserWindowConstructorOptions {
  if (process.platform === "darwin") {
    return { titleBarStyle: "hiddenInset", trafficLightPosition: { x: 16, y: 18 } };
  }
  return {
    titleBarStyle: "hidden",
    titleBarOverlay: { color: "#292929", symbolColor: "#f5f5f7", height: TITLE_BAR_HEIGHT },
  };
}

function createWindow() {
  mainWindow = new BrowserWindow({
    title: "Tuttle",
    ...initialBounds(),
    minWidth: MIN_WIDTH,
    minHeight: MIN_HEIGHT,
    show: false,
    ...titleBarOptions(),
    backgroundColor: "#292929",
    webPreferences: {
      preload: path.join(__dirname, "../electron/preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      plugins: true,
    },
  });

  mainWindow.once("ready-to-show", () => {
    mainWindow?.show();
  });

  if (process.env.VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL);
    mainWindow.webContents.openDevTools({ mode: "detach" });
  } else {
    mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

app.name = "Tuttle";

app.whenReady().then(async () => {
  const isPackaged = app.isPackaged;
  const projectRoot = isPackaged
    ? app.getAppPath()
    : path.resolve(__dirname, "../..");
  const resourcesPath = isPackaged
    ? process.resourcesPath
    : "";
  pythonBridge = new PythonBridge(projectRoot, isPackaged, resourcesPath);
  pythonBridge.onNotification = (method, params) => {
    if (method === "progress") mainWindow?.webContents.send("rpc-progress", params);
  };

  ipcMain.handle("rpc", async (_event, method: string, params: Record<string, unknown>) => {
    if (!pythonBridge) throw new Error("Python bridge not initialised");
    console.log(`[main] rpc: ${method}`);
    try {
      const result = await pythonBridge.call(method, params);
      return result;
    } catch (err) {
      console.error(`[main] rpc error in ${method}:`, err);
      throw err;
    }
  });

  ipcMain.handle("read-file", async (_event, filePath: string) => {
    try {
      const data = fs.readFileSync(filePath);
      return { ok: true, data: data.toString("base64") };
    } catch {
      return { ok: false, data: null };
    }
  });

  // Ensure DB exists before showing UI
  try {
    await pythonBridge.call("db.ensure", {});
    console.log("[main] db.ensure complete");
  } catch (err) {
    console.error("[main] db.ensure failed:", err);
  }

  createWindow();

  if (!process.env.VITE_DEV_SERVER_URL) {
    initUpdater(() => mainWindow);
  }

  ipcMain.on("check-for-update", () => {
    if (!mainWindow) return;
    if (process.env.VITE_DEV_SERVER_URL) {
      mainWindow.webContents.send("update-not-available", {
        version: "dev",
      });
      return;
    }
    checkForUpdates(true);
  });

  ipcMain.handle("get-update-state", () => getUpdateState());

  ipcMain.on("open-external", (_event, url: string) => {
    if (typeof url === "string" && /^https?:\/\//.test(url)) {
      shell.openExternal(url);
    }
  });

  ipcMain.on("quit-and-install", () => {
    autoUpdater.quitAndInstall();
  });

  // Native UI (menus, dialogs, the window buttons' hover shade on Windows)
  // follows Tuttle's theme choice rather than the system's.
  ipcMain.on("set-theme-source", (_event, source: unknown) => {
    if (source === "system" || source === "light" || source === "dark") {
      nativeTheme.themeSource = source;
    }
  });

  ipcMain.on("set-title-bar-colors", (_event, colors: { color?: unknown; symbolColor?: unknown }) => {
    if (process.platform === "darwin" || !mainWindow) return;
    if (typeof colors?.color !== "string" || typeof colors.symbolColor !== "string") return;
    try {
      mainWindow.setTitleBarOverlay({ color: colors.color, symbolColor: colors.symbolColor, height: TITLE_BAR_HEIGHT });
    } catch (err) {
      console.error("[main] set-title-bar-colors failed:", err);
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

app.on("before-quit", () => {
  pythonBridge?.kill();
});
