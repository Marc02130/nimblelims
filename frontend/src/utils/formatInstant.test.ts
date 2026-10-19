import { spawnSync } from 'child_process';
import fs from 'fs';
import os from 'os';
import path from 'path';
import ts from 'typescript';

/**
 * jsdom keeps the timezone it started with, so this runs the real formatter
 * in a fresh Node process whose TZ is America/New_York.
 */
const renderInNewYork = (): {
  zone: string;
  z: string;
  naive: string;
  offset: string;
  empty: string;
  undef: string;
  blank: string;
} => {
  const sourcePath = path.join(__dirname, 'localDate.ts');
  const source = fs.readFileSync(sourcePath, 'utf8');
  const compiled = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
    },
  }).outputText;
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'format-instant-'));
  const modulePath = path.join(dir, 'localDate.js');
  const runnerPath = path.join(dir, 'run.js');
  fs.writeFileSync(modulePath, compiled);
  fs.writeFileSync(
    runnerPath,
    `
      const { formatInstant } = require(${JSON.stringify(modulePath)});
      process.stdout.write(JSON.stringify({
        zone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        z: formatInstant('2026-10-18T23:23:00Z'),
        naive: formatInstant('2026-10-18T23:23:00'),
        offset: formatInstant('2026-10-18T23:23:00+00:00'),
        empty: formatInstant(null),
        undef: formatInstant(undefined),
        blank: formatInstant(''),
      }));
    `,
  );
  const result = spawnSync(process.execPath, [runnerPath], {
    env: { ...process.env, TZ: 'America/New_York' },
    encoding: 'utf8',
  });
  fs.rmSync(dir, { recursive: true, force: true });
  if (result.status !== 0) {
    throw new Error(result.stderr || result.stdout || 'formatter process failed');
  }
  return JSON.parse(result.stdout);
};

describe('formatInstant', () => {
  const rendered = renderInNewYork();

  it('renders a UTC instant in America/New_York local time', () => {
    expect(rendered.zone).toBe('America/New_York');
    expect(rendered.z).toContain('7:23');
    expect(rendered.z).not.toContain('11:23');
  });

  it('treats a zoneless instant as UTC, not as local wall time', () => {
    expect(rendered.naive).toBe(rendered.z);
    expect(rendered.naive).toContain('7:23');
    expect(rendered.naive).not.toContain('11:23');
  });

  it('accepts an explicit +00:00 offset', () => {
    expect(rendered.offset).toBe(rendered.z);
  });

  it('returns an empty string when there is no instant', () => {
    expect(rendered.empty).toBe('');
    expect(rendered.undef).toBe('');
    expect(rendered.blank).toBe('');
  });
});
