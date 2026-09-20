import { readFileSync } from 'node:fs';
import { existsSync } from 'node:fs';

const files = {
  html: readFileSync(new URL('../dist/index.html', import.meta.url), 'utf8'),
  app: readFileSync(new URL('../dist/app.js', import.meta.url), 'utf8'),
  css: readFileSync(new URL('../dist/styles.css', import.meta.url), 'utf8'),
  beta: readFileSync(new URL('../dist/beta.html', import.meta.url), 'utf8')
};

const required = [
  ['beta identifier', files.html, 'Beta pública · v0.9'],
  ['status dialog', files.html, 'projectInfoDialog'],
  ['independent-project notice', files.html, 'No es una web oficial de la Junta de Andalucía'],
  ['creator credit', files.html, 'Creada por Teacher MikeSL'],
  ['public user guide', files.html, 'guia.html'],
  ['professional review reminder', files.html, 'professionalReminder'],
  ['prompt schema marker', files.app, '[PROMPTDOCENTES]'],
  ['prompt schema version', files.app, 'schema_version: 1.0'],
  ['generator version', files.app, 'generator_version: beta-0.9'],
  ['resource identifier', files.app, 'resource_id:'],
  ['curriculum mode', files.app, 'curriculum_mode:'],
  ['dialog styling', files.css, '.project-dialog'],
  ['post-prompt handoff', files.html, 'Convierte el prompt en tu recurso'],
  ['skill tutorial', files.html, 'skillGuideDialog'],
  ['direct no-install route', files.html, 'Sin instalar nada'],
  ['free-account fallback', files.html, 'cuenta personal gratuita'],
  ['accessible handoff status', files.html, 'id="handoffStatus" role="status" aria-live="polite"'],
  ['beta test plan', files.beta, 'Pruebas recomendadas'],
  ['anonymous feedback warning', files.beta, 'no recoge ni almacena tus respuestas'],
  ['reproducible error report', files.beta, 'resultado esperado y resultado obtenido']
];

const failures = required.filter(([, content, token]) => !content.includes(token));
const forbidden = [
  ['browser storage', /\b(?:localStorage|sessionStorage|indexedDB)\b/],
  ['outbound request API', /\b(?:fetch|XMLHttpRequest)\s*\(/]
].filter(([, pattern]) => pattern.test(files.app));

if (!existsSync(new URL('../dist/downloads/promptdocentes-recursos-beta.zip', import.meta.url))) {
  failures.push(['skill download package']);
}

if (failures.length || forbidden.length) {
  for (const [label] of failures) console.error(`Missing: ${label}`);
  for (const [label] of forbidden) console.error(`Unexpected: ${label}`);
  process.exit(1);
}

console.log('Beta readiness checks passed: disclosure, curriculum coverage, stable prompt metadata and local-only form handling.');
