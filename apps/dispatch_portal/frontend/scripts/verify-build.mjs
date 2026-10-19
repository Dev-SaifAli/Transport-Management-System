import assert from 'node:assert/strict'
import { readFile, stat } from 'node:fs/promises'
import { dirname, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const frontendDir = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const bundleDir = resolve(frontendDir, '../dispatch_portal/public/frontend')
const assetPrefix = '/assets/dispatch_portal/frontend/'
const builtIndex = await readFile(resolve(bundleDir, 'index.html'), 'utf8')
const page = await readFile(resolve(frontendDir, '../dispatch_portal/www/dispatch.html'), 'utf8')
const bootScript = '<script>window.frappeBoot = {{ frappe_boot_json }};</script>'

assert(page.includes(bootScript), 'Frappe page must inject the session/CSRF bootstrap')
assert.equal(page.replace(bootScript, '').replace(/\s+/g, ''), builtIndex.replace(/\s+/g, ''),
  'Frappe page must match the generated Vue entry')

for (const [name, html] of [['Vue entry', builtIndex], ['Frappe page', page]]) {
  const references = [...html.matchAll(/(?:src|href)=["']([^"']+)["']/g)]
    .map((match) => match[1]).filter((url) => !url.startsWith('https://'))
  assert(references.some((url) => url.endsWith('.js')), `${name}: missing JavaScript entry`)
  assert(references.some((url) => url.endsWith('.css')), `${name}: missing stylesheet`)
  let hasLiveApiConfig = false
  for (const url of references) {
    assert(url.startsWith(assetPrefix), `${name}: unexpected asset URL ${url}`)
    const file = resolve(bundleDir, url.slice(assetPrefix.length))
    assert(file.startsWith(`${bundleDir}${sep}`), `Asset escapes bundle directory: ${url}`)
    assert((await stat(file)).isFile(), `${name}: missing bundled file ${url}`)
    if (url.endsWith('.js')) {
      const script = await readFile(file, 'utf8')
      hasLiveApiConfig ||= /["']?VITE_API_MOCK["']?\s*:\s*["'`]false["'`]/.test(script)
    }
  }
  assert(hasLiveApiConfig, `${name}: production bundle must embed VITE_API_MOCK=false`)
  console.log(`${name}: ${references.length} bundled asset references verified`)
}
