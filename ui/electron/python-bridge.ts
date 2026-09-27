import { spawn, ChildProcess } from "node:child_process";
import path from "node:path";
import readline from "node:readline";

type PendingRequest = {
  resolve: (value: unknown) => void;
  reject: (reason: unknown) => void;
};

/**
 * Manages the Python RPC core process.
 * Communicates via newline-delimited JSON-RPC 2.0 over stdio.
 *
 * In dev mode, spawns .venv/bin/python -m tuttle.rpc_server.
 * In production (packaged app), spawns the PyInstaller-bundled binary
 * from the app's resources directory.
 */
export class PythonBridge {
  private process: ChildProcess | null = null;
  private rl: readline.Interface | null = null;
  private pending = new Map<number, PendingRequest>();
  /** Receives JSON-RPC notifications (messages without an id), e.g. progress. */
  onNotification: ((method: string, params: unknown) => void) | null = null;
  private nextId = 1;
  private projectRoot: string;
  private isPackaged: boolean;
  private resourcesPath: string;

  constructor(projectRoot: string, isPackaged: boolean, resourcesPath: string) {
    this.projectRoot = projectRoot;
    this.isPackaged = isPackaged;
    this.resourcesPath = resourcesPath;
    this.spawn();
  }

  private spawn() {
    let cmd: string;
    let args: string[];
    let cwd: string;
    let env: NodeJS.ProcessEnv;

    if (this.isPackaged) {
      const exeName =
        process.platform === "win32" ? "tuttle-rpc.exe" : "tuttle-rpc";
      cmd = path.join(this.resourcesPath, "tuttle-rpc", exeName);
      args = [];
      cwd = path.join(this.resourcesPath, "tuttle-rpc");
      env = { ...process.env, PYTHONUNBUFFERED: "1" };
      console.log(`[python-bridge] production mode, spawning: ${cmd}`);
    } else {
      const venvBin = process.platform === "win32" ? "Scripts" : "bin";
      const pyExe = process.platform === "win32" ? "python.exe" : "python";
      cmd = path.join(this.projectRoot, ".venv", venvBin, pyExe);
      args = ["-m", "tuttle.rpc_server"];
      cwd = this.projectRoot;
      env = {
        ...process.env,
        PYTHONPATH: this.projectRoot,
        PYTHONUNBUFFERED: "1",
      };
      console.log(
        `[python-bridge] dev mode, spawning: ${cmd} ${args.join(" ")}`
      );
    }

    console.log(`[python-bridge] cwd: ${cwd}`);

    this.process = spawn(cmd, args, {
      cwd,
      stdio: ["pipe", "pipe", "pipe"],
      env,
    });

    this.process.stderr?.on("data", (data: Buffer) => {
      console.error(`[python] ${data.toString().trimEnd()}`);
    });

    this.process.on("exit", (code) => {
      console.error(`[python] process exited with code ${code}`);
      for (const [, req] of this.pending) {
        req.reject(new Error(`Python process exited (code ${code})`));
      }
      this.pending.clear();
    });

    this.rl = readline.createInterface({ input: this.process.stdout! });
    this.rl.on("line", (line: string) => {
      try {
        const response = JSON.parse(line);
        if (response.id == null && typeof response.method === "string") {
          this.onNotification?.(response.method, response.params);
          return;
        }
        const req = this.pending.get(response.id);
        if (req) {
          this.pending.delete(response.id);
          if (response.error) {
            req.reject(new Error(response.error.message || "RPC error"));
          } else {
            req.resolve(response.result);
          }
        }
      } catch (err) {
        console.error("[python] failed to parse response:", line, err);
      }
    });
  }

  call(method: string, params: Record<string, unknown> = {}): Promise<unknown> {
    return new Promise((resolve, reject) => {
      if (!this.process?.stdin?.writable) {
        reject(new Error("Python process not running"));
        return;
      }

      const id = this.nextId++;
      this.pending.set(id, { resolve, reject });

      const request = JSON.stringify({
        jsonrpc: "2.0",
        id,
        method,
        params,
      });

      this.process.stdin.write(request + "\n");
    });
  }

  kill() {
    this.rl?.close();
    if (this.process) {
      this.process.kill("SIGTERM");
      const proc = this.process;
      setTimeout(() => {
        if (!proc.killed) proc.kill("SIGKILL");
      }, 3000);
    }
    this.process = null;
  }
}
