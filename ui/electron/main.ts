import { app, BrowserWindow, ipcMain, shell } from "electron";
import path from "node:path";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { PythonBridge } from "./python-bridge";
import { autoUpdater, initUpdater } from "./updater";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let mainWindow: BrowserWindow | null = null;
let pythonBridge: PythonBridge | null = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    title: "Tuttle",
    width: 1440,
    height: 960,
    minWidth: 1024,
    minHeight: 700,
    show: false,
    titleBarStyle: "hiddenInset",
    trafficLightPosition: { x: 16, y: 18 },
    backgroundColor: "#292929",
    webPreferences: {
      preload: path.join(__dirname, "../electron/preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      plugins: true,
    },
  });

  mainWindow.once("ready-to-show", () => {
    mainWindow?.maximize();
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

  if (!process.env.VITE_DEV_SERVER_URL && mainWindow) {
    initUpdater(mainWindow);
  }

  ipcMain.on("check-for-update", () => {
    if (!mainWindow) return;
    if (process.env.VITE_DEV_SERVER_URL) {
      mainWindow.webContents.send("update-not-available", {
        version: "dev",
      });
      return;
    }
    autoUpdater.checkForUpdates().catch((err) => {
      mainWindow!.webContents.send("update-error", {
        message: err?.message ?? String(err),
      });
    });
  });

  ipcMain.on("open-external", (_event, url: string) => {
    if (typeof url === "string" && /^https?:\/\//.test(url)) {
      shell.openExternal(url);
    }
  });

  ipcMain.on("quit-and-install", () => {
    autoUpdater.quitAndInstall();
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
