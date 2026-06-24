import { cpSync, existsSync, mkdirSync, readdirSync, rmSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const workspaceApp = resolve(root, "member-dashboard-app");
const workspaceDist = resolve(workspaceApp, "dist");
const workspaceOutput = resolve(root, "workspace");
const vercelOutput = resolve(root, "public");
const npmCommand = "npm";
const checkOnly = process.argv.includes("--check-only");
const hasNodeModules = existsSync(resolve(workspaceApp, "node_modules"));
const outputExcludes = new Set([
  "member-dashboard-app",
  "node_modules",
  "public",
  "scripts",
  "workspace",
  "package.json",
  "package-lock.json",
  "README.md",
  ".env",
  ".env.example",
  ".vercelignore",
  ".gitignore"
]);

function run(command, args, cwd) {
  const childCommand = process.platform === "win32" ? "cmd.exe" : command;
  const childArgs = process.platform === "win32" ? ["/d", "/s", "/c", [command, ...args].join(" ")] : args;
  const result = spawnSync(childCommand, childArgs, {
    cwd,
    stdio: "inherit",
    shell: false
  });
  if (result.error) {
    console.error(result.error.message);
  }
  if (result.status !== 0) {
    process.exit(result.status || 1);
  }
}

if (!existsSync(resolve(workspaceApp, "package.json"))) {
  throw new Error("member-dashboard-app/package.json was not found.");
}

run(npmCommand, [process.env.CI || !hasNodeModules ? "ci" : "install"], workspaceApp);
run(npmCommand, ["run", "build"], workspaceApp);

if (checkOnly) {
  process.exit(0);
}

rmSync(workspaceOutput, { recursive: true, force: true });
mkdirSync(workspaceOutput, { recursive: true });
cpSync(workspaceDist, workspaceOutput, { recursive: true });

rmSync(vercelOutput, { recursive: true, force: true });
mkdirSync(vercelOutput, { recursive: true });
for (const entry of readdirSync(root)) {
  if (outputExcludes.has(entry)) continue;
  const source = join(root, entry);
  const target = join(vercelOutput, entry);
  if (statSync(source).isDirectory()) {
    cpSync(source, target, { recursive: true });
  } else {
    cpSync(source, target);
  }
}
cpSync(workspaceDist, resolve(vercelOutput, "workspace"), { recursive: true });

console.log("Built React workspace into frontend/workspace/ and Vercel output into frontend/public/");
