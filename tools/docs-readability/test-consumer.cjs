const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const path = require('node:path');
const entry = path.resolve(__dirname, 'bin/docs-lint');
const cwd = path.join(__dirname, 'fixtures/consumer');
function run(...args) {
  return spawnSync(entry, args, { cwd, encoding: 'utf8' });
}
assert.equal(run('good.md').status, 0, 'unselected bad file is excluded');
const bad = run('bad.md');
// The consumer's configuration must not override the pinned kit rules.
assert.equal(bad.status, 1);
assert.match(bad.stderr, /HUM001/);
assert.match(bad.stderr, /HUM002/);
assert.match(bad.stderr, /HUM003/);
assert.equal(run('.').status, 1, 'directory includes bad document');
const missing = run('good.md', 'missing.md');
assert.equal(missing.status, 2);
assert.match(missing.stderr, /path does not exist: missing\.md/);
assert.equal(run().status, 2);
console.log('Consumer entrypoint checks passed.');
