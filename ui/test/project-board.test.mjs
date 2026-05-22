import assert from "node:assert/strict";
import {execFileSync} from "node:child_process";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import {pathToFileURL} from "node:url";

const outDir = await fs.mkdtemp(path.join(os.tmpdir(), "tuttle-project-board-"));
const tsc = path.join("node_modules", ".bin", "tsc");

execFileSync(tsc, [
  "src/components/business/projectBoard.ts",
  "--target", "ES2021",
  "--module", "ES2020",
  "--moduleResolution", "node",
  "--outDir", outDir,
  "--skipLibCheck",
], {stdio: "inherit"});

const modulePath = path.join(outDir, "projectBoard.js");
const {projectColumnAfterCompletedToggle} = await import(pathToFileURL(modulePath));

assert.equal(projectColumnAfterCompletedToggle("Active"), "Completed");
assert.equal(projectColumnAfterCompletedToggle("Upcoming"), "Completed");
assert.equal(projectColumnAfterCompletedToggle("Lead"), "Completed");
assert.equal(projectColumnAfterCompletedToggle("Completed"), "Active");
