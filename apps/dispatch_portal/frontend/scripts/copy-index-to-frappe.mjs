import { copyFile, mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const frontendDir = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const builtIndex = resolve(frontendDir, '../dispatch_portal/public/frontend/index.html')
const frappePage = resolve(frontendDir, '../dispatch_portal/www/dispatch.html')

const index = await readFile(builtIndex, 'utf8')
const bootScript = '<script>window.frappeBoot = {{ frappe_boot_json }};</script>'
const page = index.includes('window.frappeBoot')
  ? index
  : index.replace('</head>', `    ${bootScript}\n  </head>`)

await mkdir(dirname(frappePage), { recursive: true })
await writeFile(frappePage, page)

// Keep this explicit so a future build cannot silently leave a stale page shell.
await copyFile(builtIndex, resolve(frontendDir, '../dispatch_portal/public/frontend/index.html'))
