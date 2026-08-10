import { mkdir, readdir, readFile, rm, writeFile } from 'node:fs/promises';
import { join, relative, resolve } from 'node:path';

const repository = resolve(import.meta.dirname, '../..');
const sourceRoots = [
  join(repository, 'src/mcmr/rules'),
  join(repository, 'src/mcmr_datahub/rules'),
];
const outputRoot = join(repository, 'docs/src/content/docs/docs/rules');
const headings = ['Definition', 'Evidence', 'Exceptions', 'Examples', 'References'];

async function walk(directory) {
  const paths = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) paths.push(...(await walk(path)));
    else if (entry.name.endsWith('.py')) paths.push(path);
  }
  return paths;
}

function cleanDocstring(raw) {
  return raw
    .split('\n')
    .map((line) => (line.startsWith('    ') ? line.slice(4) : line))
    .join('\n')
    .trim();
}

function sections(documentation) {
  const positions = headings.map((heading) => {
    const marker = new RegExp(`^${heading}\\n-+\\n`, 'm');
    const match = marker.exec(documentation);
    if (!match) throw new Error(`Missing ${heading} in a rule docstring`);
    return { heading, start: match.index, body: match.index + match[0].length };
  });
  const result = { summary: documentation.slice(0, positions[0].start).trim() };
  for (const [index, position] of positions.entries()) {
    const end = positions[index + 1]?.start ?? documentation.length;
    result[position.heading.toLowerCase()] = documentation.slice(position.body, end).trim();
  }
  return result;
}

function prose(text) {
  return text
    .split(/(`[^`]*`)/g)
    .map((part, index) =>
      index % 2
        ? part
        : part
            .replaceAll('—', ',')
            .replaceAll(';', ',')
            .replace(/([A-Za-z0-9]):(?=\s|$)/g, '$1.'),
    )
    .join('');
}

function fenced(text, language) {
  const longest = Math.max(0, ...[...text.matchAll(/`+/g)].map((match) => match[0].length));
  const fence = '`'.repeat(Math.max(4, longest + 1));
  const supportedLanguage = language === 'cuda' ? 'c' : language;
  return `${fence}${supportedLanguage}\n${text}\n${fence}`;
}

function example(text) {
  const marker = /^([^\n]+)\n~+\n\.\. code-block:: ([^\n]+)\n\n/gm;
  const matches = [...text.matchAll(marker)];
  if (!matches.length) return prose(text);
  const rendered = [];
  const prefix = text.slice(0, matches[0].index).trim();
  if (prefix) rendered.push(prose(prefix));
  for (const [index, match] of matches.entries()) {
    const start = (match.index ?? 0) + match[0].length;
    const end = matches[index + 1]?.index ?? text.length;
    const code = text
      .slice(start, end)
      .trimEnd()
      .split('\n')
      .map((line) => (line.startsWith('   ') ? line.slice(3) : line))
      .join('\n');
    rendered.push(`### ${prose(match[1])}\n\n${fenced(code, match[2])}`);
  }
  return rendered.join('\n\n');
}

function references(text) {
  const lines = text.split('\n').map((line) => line.trim()).filter(Boolean);
  const rendered = [];
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const next = lines[index + 1];
    if (next?.startsWith('http')) {
      rendered.push(`- ${prose(line)}. [Open reference](${next})`);
      index += 1;
    } else if (line.startsWith('http')) rendered.push(`- [Open reference](${line})`);
    else rendered.push(`- ${prose(line)}`);
  }
  return rendered.join('\n');
}

function sourceParts(path) {
  const root = sourceRoots.find((candidate) => !relative(candidate, path).startsWith('..'));
  if (!root) throw new Error(`Rule source is outside the built-in roots ${path}`);
  return relative(root, path).split('/');
}

function scope(path) {
  const name = sourceParts(path)[0];
  return name === 'general' ? 'all languages' : name;
}

function lane(path) {
  return sourceParts(path)[1];
}

function family(path) {
  return sourceParts(path)[2].replaceAll('_', ' ');
}

function slug(identifier) {
  return identifier.toLowerCase();
}

function introduction(rule) {
  const sourceUrl = `https://github.com/phvv-me/mcmr/blob/main/${rule.path}#L${rule.line}`;
  return `---
title: ${JSON.stringify(`${rule.id} · ${rule.name}`)}
description: ${JSON.stringify(rule.documentation.summary)}
---

${prose(rule.documentation.summary)}

This is a \`${rule.lane}\` rule for ${rule.scope}. [Read its implementation](${sourceUrl}).
`;
}

function page(rule) {
  return `${introduction(rule)}

## Definition

${prose(rule.documentation.definition)}

## Evidence

${prose(rule.documentation.evidence)}

## Exceptions

${prose(rule.documentation.exceptions)}

## Examples

${example(rule.documentation.examples)}

## References

${references(rule.documentation.references)}
`;
}

function definitionPage(rule) {
  return `${introduction(rule)}

## Definition

${prose(rule.documentation.definition)}

[Continue with evidence and references](/mcmr/docs/rules/catalog/${slug(rule.id)}-evidence/), or
[open the examples](/mcmr/docs/rules/catalog/${slug(rule.id)}-examples/).
`;
}

function evidencePage(rule) {
  const sourceUrl = `https://github.com/phvv-me/mcmr/blob/main/${rule.path}#L${rule.line}`;
  return `---
title: ${JSON.stringify(`${rule.id} · evidence`)}
description: ${JSON.stringify(`Evidence, exceptions, and references for ${rule.id}.`)}
---

This page continues [${rule.id}](/mcmr/docs/rules/catalog/${slug(rule.id)}/) directly from its
source docstring. [Read its implementation](${sourceUrl}).

## Evidence

${prose(rule.documentation.evidence)}

## Exceptions

${prose(rule.documentation.exceptions)}

## References

${references(rule.documentation.references)}
`;
}

function examplesPage(rule) {
  const sourceUrl = `https://github.com/phvv-me/mcmr/blob/main/${rule.path}#L${rule.line}`;
  return `---
title: ${JSON.stringify(`${rule.id} · examples`)}
description: ${JSON.stringify(`Source examples for ${rule.id}.`)}
---

These examples come directly from [${rule.id}](/mcmr/docs/rules/catalog/${slug(rule.id)}/).
[Read their source](${sourceUrl}).

${example(rule.documentation.examples)}
`;
}

function words(markdown) {
  return markdown.trim().split(/\s+/).filter(Boolean).length;
}

const rules = [];
for (const path of (await Promise.all(sourceRoots.map(walk))).flat()) {
  const source = await readFile(path, 'utf8');
  for (const match of source.matchAll(/^@rule\(\s*["']([^"']+)["']/gm)) {
    const tail = source.slice(match.index);
    const implementation = /\n(?:async )?def ([A-Za-z_]\w*)\(/.exec(tail);
    if (!implementation) throw new Error(`Cannot read the rule after ${path}:${match.index}`);
    const functionSource = tail.slice(implementation.index);
    const documentation = /:\n    """([\s\S]*?)\n    """/.exec(functionSource);
    if (!documentation) throw new Error(`Cannot read the docstring for ${match[1]}`);
    const functionOffset = match.index + implementation.index + implementation[0].indexOf('def ');
    rules.push({
      id: match[1],
      name: implementation[1],
      path: relative(repository, path),
      line: source.slice(0, functionOffset).split('\n').length,
      scope: scope(path),
      lane: lane(path),
      family: family(path),
      documentation: sections(cleanDocstring(documentation[1])),
    });
  }
}

rules.sort((left, right) => left.id.localeCompare(right.id));
await rm(outputRoot, { recursive: true, force: true });
await mkdir(join(outputRoot, 'catalog'), { recursive: true });

const groups = Map.groupBy(rules, (rule) => rule.id.split('-', 1)[0]);
const groupLinks = [];
for (const [prefix, members] of [...groups.entries()].sort()) {
  const name = prefix.toLowerCase();
  const lanes = Map.groupBy(members, (rule) => rule.lane);
  const laneLinks = [];
  for (const [laneName, laneMembers] of [...lanes.entries()].sort()) {
    const laneSlug = `${name}-${laneName}`;
    const families = Map.groupBy(laneMembers, (rule) => rule.family);
    const sections = [...families.entries()]
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([familyName, familyMembers]) => {
        const entries = familyMembers
          .map((rule) => `- [\`${rule.id}\`](/mcmr/docs/rules/catalog/${slug(rule.id)}/)`)
          .join('\n');
        return `## ${familyName[0].toUpperCase()}${familyName.slice(1)}\n\n${entries}`;
      })
      .join('\n\n');
    const lanePage = `---
title: ${JSON.stringify(`${prefix} ${laneName} rules`)}
description: ${JSON.stringify(`Every ${laneName} ${prefix} rule grouped by family.`)}
---

This index groups every \`${laneName}\` \`${prefix}\` rule by family. Each rule page contains its
definition, evidence, exceptions, examples, implementation link, and cited references.

${sections}
`;
    if (words(lanePage) > 400) {
      throw new Error(`${prefix} ${laneName} index has ${words(lanePage)} words`);
    }
    await writeFile(join(outputRoot, `${laneSlug}.md`), lanePage);
    laneLinks.push(
      `- [${laneName[0].toUpperCase()}${laneName.slice(1)} rules](/mcmr/docs/rules/${laneSlug}/) with ${laneMembers.length} entries`,
    );
  }
  const markdown = `---
title: ${JSON.stringify(`${prefix} rules`)}
description: ${JSON.stringify(`Every ${prefix} rule, linked to its complete source-derived reference.`)}
---

This scope contains every \`${prefix}\` rule. Open a lane to browse its family subsections and
complete source-derived references.

${laneLinks.join('\n')}
`;
  await writeFile(join(outputRoot, `${name}.md`), markdown);
  groupLinks.push(`- [${prefix} rules](/mcmr/docs/rules/${name}/) with ${members.length} entries`);
}

const index = `---
title: "Rule reference"
description: "Every MCMR rule, generated from the docstring beside its implementation."
---

The rule reference is generated from source on every docs build. Each rule page preserves its
definition, evidence, exceptions, examples, and references. It also links to the exact source line.

Use site search for an identifier or callable name, or open an index below.

${groupLinks.join('\n')}
`;
await writeFile(join(outputRoot, 'index.md'), index);

const tooLong = [];
for (const rule of rules) {
  const complete = page(rule);
  if (words(complete) <= 400) {
    await writeFile(join(outputRoot, 'catalog', `${slug(rule.id)}.md`), complete);
    continue;
  }
  const definition = definitionPage(rule);
  const evidence = evidencePage(rule);
  const examples = examplesPage(rule);
  if (words(definition) > 400) tooLong.push(`${rule.id} definition has ${words(definition)} words`);
  if (words(evidence) > 400) tooLong.push(`${rule.id} evidence has ${words(evidence)} words`);
  if (words(examples) > 400) tooLong.push(`${rule.id} examples has ${words(examples)} words`);
  await writeFile(join(outputRoot, 'catalog', `${slug(rule.id)}.md`), definition);
  await writeFile(join(outputRoot, 'catalog', `${slug(rule.id)}-evidence.md`), evidence);
  await writeFile(join(outputRoot, 'catalog', `${slug(rule.id)}-examples.md`), examples);
}

if (tooLong.length) throw new Error(tooLong.join('\n'));
console.log(`generated ${rules.length} rule pages from source docstrings`);
