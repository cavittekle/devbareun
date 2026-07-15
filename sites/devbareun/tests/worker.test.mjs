import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import worker from "../dist/server/index.js";

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const clientRoot = path.join(projectRoot, "dist", "client");

const mimeTypes = new Map([
  [".css", "text/css; charset=utf-8"],
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".png", "image/png"],
  [".svg", "image/svg+xml"],
  [".webp", "image/webp"],
]);

const env = {
  ASSETS: {
    async fetch(request) {
      const pathname = decodeURIComponent(new URL(request.url).pathname);
      const localPath = path.join(clientRoot, pathname.replace(/^\/+/, ""));
      try {
        const body = await readFile(localPath);
        return new Response(body, {
          headers: { "content-type": mimeTypes.get(path.extname(localPath)) ?? "application/octet-stream" },
        });
      } catch {
        return new Response("Not found", { status: 404 });
      }
    },
  },
};

test("serves the approved DevBareun landing page", async () => {
  const response = await worker.fetch(new Request("https://example.com/"), env);
  const html = await response.text();

  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html/);
  assert.equal(response.headers.get("x-frame-options"), "DENY");
  assert.match(html, /Construction project/);
  assert.match(html, /Schedule Recovery/);
  assert.match(html, /Cost Control/);
  assert.match(html, /Material Continuity/);
  assert.match(html, /Risk &amp; Decisions/);
});

test("supports friendly member routes", async () => {
  const response = await worker.fetch(new Request("https://example.com/dashboard"), env);
  const html = await response.text();

  assert.equal(response.status, 200);
  assert.match(html, /Member Workspace/);
});

test("returns the branded 404 page for unknown routes", async () => {
  const response = await worker.fetch(new Request("https://example.com/not-a-real-page"), env);
  const html = await response.text();

  assert.equal(response.status, 404);
  assert.match(html, /DevBareun/i);
});
