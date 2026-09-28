const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("tuttle", {
  rpc: (method, params) =>
    ipcRenderer.invoke("rpc", method, params || {}),
  readFile: (filePath) =>
    ipcRenderer.invoke("read-file", filePath),
  platform: process.platform,
  onUpdateAvailable: (cb) => {
    const handler = (_e, info) => cb(info);
    ipcRenderer.on("update-available", handler);
    return () => ipcRenderer.removeListener("update-available", handler);
  },
  onUpdateNotAvailable: (cb) => {
    const handler = (_e, info) => cb(info);
    ipcRenderer.on("update-not-available", handler);
    return () => ipcRenderer.removeListener("update-not-available", handler);
  },
  onUpdateDownloaded: (cb) => {
    const handler = (_e, info) => cb(info);
    ipcRenderer.on("update-downloaded", handler);
    return () => ipcRenderer.removeListener("update-downloaded", handler);
  },
  onUpdateError: (cb) => {
    const handler = (_e, info) => cb(info);
    ipcRenderer.on("update-error", handler);
    return () => ipcRenderer.removeListener("update-error", handler);
  },
  onUpdateProgress: (cb) => {
    const handler = (_e, info) => cb(info);
    ipcRenderer.on("update-progress", handler);
    return () => ipcRenderer.removeListener("update-progress", handler);
  },
  onRpcProgress: (cb) => {
    const handler = (_e, info) => cb(info);
    ipcRenderer.on("rpc-progress", handler);
    return () => ipcRenderer.removeListener("rpc-progress", handler);
  },
  getUpdateState: () => ipcRenderer.invoke("get-update-state"),
  checkForUpdate: () => ipcRenderer.send("check-for-update"),
  openExternal: (url) => ipcRenderer.send("open-external", url),
  quitAndInstall: () => ipcRenderer.send("quit-and-install"),
});
