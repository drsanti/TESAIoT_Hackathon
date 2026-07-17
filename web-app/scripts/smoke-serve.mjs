#!/usr/bin/env node
/**
 * Minimal HTTP server for web-app smoke tests.
 * Mirrors Bitstream Studio "Serve Web App Folder": user folder + /@bitstream/ SDK.
 *
 * Usage: node scripts/smoke-serve.mjs [port]
 */
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WEB_ROOT = path.resolve(__dirname, '..');
const SDK_ROOT = path.resolve(WEB_ROOT, '../../extension/out/webview/@bitstream');
const PORT = Number(process.argv[2] || 8899);
const SDK_PREFIX = '/@bitstream/';

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json',
  '.md': 'text/markdown; charset=utf-8',
};

function safeJoin(root, urlPath) {
  const rel = decodeURIComponent(urlPath.split('?')[0]).replace(/^\/+/, '');
  const abs = path.resolve(root, rel);
  if (!abs.startsWith(root)) return null;
  return abs;
}

function sendFile(res, filePath) {
  const ext = path.extname(filePath);
  res.setHeader('Content-Type', MIME[ext] || 'application/octet-stream');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Cache-Control', 'no-store');
  fs.createReadStream(filePath).pipe(res);
}

const server = http.createServer((req, res) => {
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    res.statusCode = 405;
    res.end();
    return;
  }
  const pathname = (req.url ?? '/').split('?')[0] ?? '/';

  if (pathname.startsWith(SDK_PREFIX) && fs.existsSync(SDK_ROOT)) {
    const sdkFile = safeJoin(SDK_ROOT, pathname.slice(SDK_PREFIX.length));
    if (sdkFile && fs.existsSync(sdkFile) && fs.statSync(sdkFile).isFile()) {
      if (req.method === 'HEAD') {
        res.end();
        return;
      }
      sendFile(res, sdkFile);
      return;
    }
  }

  let filePath = safeJoin(WEB_ROOT, pathname === '/' ? 'index.html' : pathname.slice(1));
  if (filePath && fs.existsSync(filePath) && fs.statSync(filePath).isDirectory()) {
    filePath = path.join(filePath, 'index.html');
  }
  if (!filePath || !fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
    res.statusCode = 404;
    res.end(`404 ${pathname}`);
    return;
  }
  if (req.method === 'HEAD') {
    res.end();
    return;
  }
  sendFile(res, filePath);
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`[smoke-serve] http://127.0.0.1:${PORT}/`);
  console.log(`[smoke-serve] SDK: ${fs.existsSync(SDK_ROOT) ? SDK_ROOT : '(missing — vendor fallback only)'}`);
});
