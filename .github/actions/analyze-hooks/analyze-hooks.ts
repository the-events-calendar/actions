/**
 * Files the hooks and views a release changes as pending changelog entries, so the release notes
 * name them. Run from the root of the plugin checkout, with full history and tags, before the
 * changelog is written.
 *
 * `git diff -U0 <last release tag> -- src` is read for:
 *  - added and removed `apply_filters` / `do_action` calls whose name is a string literal on the
 *    call's line. A hook that only moved inside the diff is in both lists and is dropped;
 *  - changed `src/views/**.php` templates.
 *
 * Each kind becomes one tweak entry, `changelog/analyze-hooks-<added|removed|changed>-<kind>.yaml`,
 * so a second run rewrites the same files. An entry changelog.md or readme.txt already carries,
 * or another pending file holds, is not written again.
 *
 * Only erasable TypeScript syntax is used: Node runs this file as it is.
 */
import { execFileSync } from 'node:child_process';
import { appendFileSync, existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';

type Kind = 'filters' | 'actions' | 'views';
type Change = 'Added' | 'Removed' | 'Changed';
type Entry = { change: Change; kind: Kind; names: string[] };

const SRC = 'src';
const RELEASE_TAG = /^[0-9]+\.[0-9]+\.[0-9]+(\.[0-9]+)?$/;
const FUNCTIONS: Record<string, Kind> = { apply_filters: 'filters', apply_filters_ref_array: 'filters', do_action: 'actions', do_action_ref_array: 'actions' };
// A name that is a plain string literal; one built from a variable or interpolation is not a name.
const HOOK_CALL = /\b(apply_filters(?:_ref_array)?|do_action(?:_ref_array)?)\(\s*(?:'([^'$]+)'|"([^"$]+)")/g;
const VIEW_FILE = /^diff --git a\/src\/views\/(.+)\.php /;

const git = (...args: string[]): string =>
  execFileSync('git', args, { encoding: 'utf8', maxBuffer: 1 << 30, stdio: ['ignore', 'pipe', 'inherit'] });

/** The newest release tag reachable from HEAD, on the whole name: ft-002 or 6.18.3-rc1 would shorten the range. */
export function lastReleaseTag(tags: string[]): string | undefined {
  const parts = (t: string) => t.split('.').map(Number);
  return tags.filter((t) => RELEASE_TAG.test(t)).sort((a, b) => {
    const [x, y] = [parts(a), parts(b)];
    for (let i = 0; i < Math.max(x.length, y.length); i++) {
      if ((x[i] ?? 0) !== (y[i] ?? 0)) return (x[i] ?? 0) - (y[i] ?? 0);
    }
    return 0;
  }).pop();
}

/** The entries a unified diff of src/ holds. */
export function analyze(diff: string): Entry[] {
  const added: Record<string, Set<string>> = { filters: new Set(), actions: new Set() };
  const removed: Record<string, Set<string>> = { filters: new Set(), actions: new Set() };
  const views = new Set<string>();

  for (const line of diff.split('\n')) {
    const view = VIEW_FILE.exec(line);
    if (view) views.add(view[1]);
    // +++ and --- are file headers, not lines.
    if (!/^[+-]/.test(line) || /^(\+\+\+|---)/.test(line)) continue;
    for (const m of line.matchAll(HOOK_CALL)) {
      (line[0] === '+' ? added : removed)[FUNCTIONS[m[1]]].add(m[2] ?? m[3]);
    }
  }

  const entries: Entry[] = [];
  for (const kind of ['filters', 'actions'] as const) {
    const gone = [...removed[kind]].filter((n) => !added[kind].has(n));
    const came = [...added[kind]].filter((n) => !removed[kind].has(n));
    if (came.length) entries.push({ change: 'Added', kind, names: came.sort() });
    if (gone.length) entries.push({ change: 'Removed', kind, names: gone.sort() });
  }
  if (views.size) entries.push({ change: 'Changed', kind: 'views', names: [...views].sort() });
  return entries;
}

export const text = (e: Entry): string => `${e.change} ${e.kind}: ${e.names.map((n) => `\`${n}\``).join(', ')}`;

/** Entries already carried, as `Type-text` with whitespace removed, the way the common import compares. */
function knownEntries(): Set<string> {
  const squash = (s: string) => s.replace(/\s+/g, '');
  const known = new Set<string>();
  for (const file of ['changelog.md', 'readme.txt']) {
    if (!existsSync(file)) continue;
    for (const m of readFileSync(file, 'utf8').matchAll(/^\* ([A-Za-z]+) - (.*)$/gm)) known.add(squash(`${m[1]}-${m[2]}`));
  }
  if (existsSync('changelog')) {
    for (const f of readdirSync('changelog').filter((n) => n.endsWith('.yaml') && !n.startsWith('analyze-hooks-'))) {
      const body = readFileSync(`changelog/${f}`, 'utf8');
      const type = /^type:\s*["']?(\w+)/m.exec(body)?.[1];
      const entry = /^entry:\s*(?:"((?:[^"\\]|\\.)*)"|'((?:[^']|'')*)'|(.+))$/m.exec(body);
      if (type && entry) {
        known.add(squash(`${type[0].toUpperCase()}${type.slice(1)}-${(entry[1] ?? entry[2] ?? entry[3]).replace(/\\(.)/g, '$1')}`));
      }
    }
  }
  return known;
}

function main(): void {
  const summary = process.env.GITHUB_STEP_SUMMARY;
  const note = (line: string) => summary && appendFileSync(summary, `${line}\n`);

  const tag = lastReleaseTag(git('tag', '--merged', 'HEAD').split('\n'));
  if (!tag) {
    console.log('::error::No release tag is reachable from HEAD, so there is no last release to compare with. Check out with fetch-depth: 0.');
    process.exit(1);
  }
  note(`## Hook and view changes since ${tag}`);

  const known = knownEntries();
  mkdirSync('changelog', { recursive: true });
  let written = 0;
  for (const entry of analyze(git('diff', '-U0', tag, '--', SRC))) {
    const body = text(entry);
    if (known.has(`Tweak-${body.replace(/\s+/g, '')}`)) {
      note(`- skipped \`${body}\`, the plugin already has it`);
      continue;
    }
    const file = `changelog/analyze-hooks-${entry.change.toLowerCase()}-${entry.kind}.yaml`;
    // JSON strings are valid YAML double-quoted scalars, so no name can break out of the entry.
    writeFileSync(file, `significance: patch\ntype: tweak\nentry: ${JSON.stringify(body)}\n`);
    note(`- \`${file}\`: ${body}`);
    written++;
  }
  console.log(`Wrote ${written} hook and view changelog entries (since ${tag}).`);
}

if (process.argv[1] === import.meta.filename) main();
