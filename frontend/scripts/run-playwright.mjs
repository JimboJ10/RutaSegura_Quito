import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { resolve, dirname } from 'node:path';
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const result = spawnSync(process.execPath, [resolve(root, 'node_modules/@playwright/test/cli.js'), ...process.argv.slice(2)], {
  cwd: root, stdio: 'inherit', env: { ...process.env, PLAYWRIGHT_BROWSERS_PATH: process.env.PLAYWRIGHT_BROWSERS_PATH || resolve(root, '.playwright-browsers') },
});
if (result.error) console.error(result.error);
process.exit(result.status ?? 1);
