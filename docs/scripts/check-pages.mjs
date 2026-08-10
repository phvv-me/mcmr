// Documentation gate, checked on every build.
//
//   1. Every internal link resolves to a page the build actually served.
//   2. No em dash, colon, or semicolon in prose, the house punctuation rule.
//
// Links are checked against `dist/`, which is the only authority on what the site really serves
// once the `/mcmr` base path is baked into every href. Punctuation is checked against the
// Markdown source with frontmatter, code, tables, and component blocks stripped, since none of
// those are prose.

import { readdir, readFile, stat } from 'node:fs/promises';
import { join, relative, resolve } from 'node:path';

const docs = resolve(import.meta.dirname, '..');
const content = join(docs, 'src/content/docs');
const dist = join(docs, 'dist');

async function walk(dir, match) {
  const found = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) found.push(...(await walk(path, match)));
    else if (match(entry.name)) found.push(path);
  }
  return found;
}

// The house rule is prose without em dashes, colons, or semicolons. Colons stay legal inside
// code, tables, frontmatter, links, and component imports, which are syntax rather than prose.
function punctuation(markdown) {
  const body = markdown
    .replace(/^---\n[\s\S]*?\n---\n/, '')
    .replace(/```[\s\S]*?```/g, '')
    .replace(/<([A-Z][A-Za-z]*)\b[\s\S]*?<\/\1>/g, ' ')
    .replace(/<[A-Z][A-Za-z]*\b[\s\S]*?\/>/g, ' ');
  const offenders = [];
  for (const line of body.split('\n')) {
    const lead = line.trimStart();
    if (lead.startsWith('|') || lead.startsWith('import ') || lead.startsWith('{') || lead.startsWith('<')) continue;
    const bare = line
      .replace(/`[^`]*`/g, '')
      .replace(/https?:\/\/\S*/g, '')
      .replace(/\[[^\]]*\]\([^)]*\)/g, '');
    if (bare.includes('—')) offenders.push(['em dash', line]);
    if (bare.includes(';')) offenders.push(['semicolon', line]);
    if (/\w:(\s|$)/.test(bare)) offenders.push(['colon', line]);
  }
  return offenders;
}

const failures = [];

for (const path of await walk(content, (name) => name.endsWith('.md') || name.endsWith('.mdx'))) {
  const source = await readFile(path, 'utf8');
  const where = relative(docs, path);
  const wordCount = source.match(/\S+/g)?.length ?? 0;
  if (wordCount > 400) failures.push(`${where} has ${wordCount} words, above the 400 word limit.`);
  for (const [kind, line] of punctuation(source)) {
    failures.push(`${where} uses a ${kind} in prose. ${line.trim().slice(0, 80)}`);
  }
}

// Every href the built site emits has to land on something the built site serves.
const pages = await walk(dist, (name) => name.endsWith('.html'));
const links = new Set();
for (const path of pages) {
  const html = await readFile(path, 'utf8');
  for (const [, href] of html.matchAll(/href="(\/mcmr[^"#?]*)/g)) links.add(`${href} ${relative(dist, path)}`);
}

for (const entry of links) {
  const [href, from] = entry.split(' ');
  const target = join(dist, href.replace(/^\/mcmr/, ''));
  const candidates = [target, join(target, 'index.html'), `${target}.html`];
  const resolved = await Promise.all(
    candidates.map((candidate) =>
      stat(candidate).then(
        (info) => info.isFile(),
        () => false,
      ),
    ),
  );
  if (!resolved.some(Boolean)) failures.push(`${from} links to ${href}, which the build does not serve.`);
}

if (failures.length) {
  console.error(`\ncheck-pages found ${failures.length} problems\n`);
  for (const failure of failures) console.error(`  ${failure}`);
  process.exit(1);
}

console.log(`check-pages passed over ${pages.length} built pages`);
