/**
 * Files the hooks and views a release changes as pending changelog entries, so the release notes
 * name them. Run from the root of the plugin checkout, with full history and tags, before the
 * changelog is written.
 *
 * Compared with the last release tag:
 *  - the `apply_filters` / `do_action` calls in `src/` whose name is a complete string literal. A hook
 *    is added when the current tree has it and the tag's tree does not, removed the other way round,
 *    so one that moved, or that still has another call elsewhere, is not listed;
 *  - the `src/views/**.php` templates `git diff` reports as changed.
 *
 * Each kind becomes one tweak entry, `changelog/analyze-hooks-<added|removed|changed>-<kind>.yaml`,
 * so a second run rewrites the same files. An entry changelog.md or readme.txt already carries,
 * or another pending file holds, is not written again.
 *
 * Only erasable TypeScript syntax is used: Node runs this file as it is.
 */
import { execFileSync } from 'node:child_process';
import { appendFileSync, existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';

type Kind = 'filters' | 'actions' | 'views';
type Change = 'Added' | 'Removed' | 'Changed';
type Entry = { change: Change; kind: Kind; names: string[] };

const SRC = 'src';
const RELEASE_TAG = /^[0-9]+\.[0-9]+\.[0-9]+(\.[0-9]+)?$/;
const FUNCTIONS: Record<string, Kind> = { apply_filters: 'filters', apply_filters_ref_array: 'filters', do_action: 'actions', do_action_ref_array: 'actions' };
// A name that is a plain string literal, closed by `,` or `)`: one built from a variable,
// interpolation or concatenation (`'tec_' . $name`) is not a name.
const HOOK_CALL = /\b(apply_filters(?:_ref_array)?|do_action(?:_ref_array)?)\(\s*(?:'([^'$]+)'|"([^"$]+)")\s*[,)]/g;
const VIEW_FILE = /^src\/views\/(.+)\.php$/;

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

/** The hook names the source text calls, per kind. */
export function hooks(source: string): Record<'filters' | 'actions', Set<string>> {
  const found = { filters: new Set<string>(), actions: new Set<string>() };
  for (const m of source.matchAll(HOOK_CALL)) found[FUNCTIONS[m[1]] as 'filters' | 'actions'].add(m[2] ?? m[3]);
  return found;
}

/** The entries between the tag's source, the current source and the changed files. */
export function analyze(before: string, after: string, changedFiles: string[]): Entry[] {
  const [old, now] = [hooks(before), hooks(after)];
  const entries: Entry[] = [];
  for (const kind of ['filters', 'actions'] as const) {
    const came = [...now[kind]].filter((n) => !old[kind].has(n));
    const gone = [...old[kind]].filter((n) => !now[kind].has(n));
    if (came.length) entries.push({ change: 'Added', kind, names: came.sort() });
    if (gone.length) entries.push({ change: 'Removed', kind, names: gone.sort() });
  }
  const views = changedFiles.flatMap((f) => VIEW_FILE.exec(f)?.[1] ?? []);
  if (views.length) entries.push({ change: 'Changed', kind: 'views', names: [...new Set(views)].sort() });
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
  // Rewritten from scratch: a file from an earlier run whose change was since reverted must go.
  for (const f of readdirSync('changelog').filter((n) => /^analyze-hooks-.*\.yaml$/.test(n))) rmSync(`changelog/${f}`);
  // git grep exits 1 when nothing matches, which is an empty tree, not a failure.
  const calls = (...tree: string[]) => {
    try { return git('grep', '-I', '-h', '-E', '(apply_filters|do_action)', ...tree, '--', SRC); } catch { return ''; }
  };
  let written = 0;
  for (const entry of analyze(calls(tag), calls(), git('diff', '--name-only', tag, '--', SRC).split('\n'))) {
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
