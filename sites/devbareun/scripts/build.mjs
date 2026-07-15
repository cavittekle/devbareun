import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = path.resolve(projectRoot, "..", "..");
const frontendRoot = path.join(repositoryRoot, "frontend");
const outputRoot = path.join(projectRoot, "dist");
const clientRoot = path.join(outputRoot, "client");
const serverRoot = path.join(outputRoot, "server");

const excludedNames = new Set([
  ".env",
  ".env.example",
  ".gitignore",
  ".netlify",
  ".vercel",
  ".vercelignore",
  "README.md",
  "build",
  "dist",
  "member-dashboard-app",
  "netlify.toml",
  "node_modules",
  "public",
  "vercel.json",
  "workspace",
]);

await rm(outputRoot, { recursive: true, force: true });
await mkdir(serverRoot, { recursive: true });
await cp(frontendRoot, clientRoot, {
  recursive: true,
  filter(source) {
    const relative = path.relative(frontendRoot, source);
    if (!relative) return true;
    return !relative.split(path.sep).some((segment) => excludedNames.has(segment));
  },
});

const workerSource = await readFile(new URL("../worker/index.js", import.meta.url), "utf8");
await writeFile(path.join(serverRoot, "index.js"), workerSource);

console.log(`Built Sites bundle from ${frontendRoot}`);
