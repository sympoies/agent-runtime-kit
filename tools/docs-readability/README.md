# Shared documentation readability checks

The [writing policy](../../core/policies/human-docs.md) describes the human
review. The lint rules provide a small, reproducible check alongside that review.
Node.js 22 or newer and npm are required.

Run `npm ci --prefix tools/docs-readability`, then run
`npm test --prefix tools/docs-readability` and
`npm run lint --prefix tools/docs-readability`. The lint command checks the
policy; `bash scripts/ci/all.sh` installs the locked dependencies and runs both.

## Use in another repository

Copy `readability.json` and `human-prose.cjs` unchanged into
`vendor/docs-readability/` from a specific commit of this repository. Record
its repository URL, full commit SHA, and the SHA-256 of each copied file in a
`SOURCE.json` beside them. Update these files together in a reviewed change;
never fetch an unpinned branch during CI. Link to the policy rather than
copying it. Install `markdownlint-cli2` at exactly `0.24.0` with the consumer's
package manager and commit its lockfile. A repository without a Node package
can use an isolated package and lockfile under `tools/docs-lint/`.

A root `.markdownlint-cli2.cjs` can inventory maintained Markdown:

```javascript
module.exports = {
  config: require('./vendor/docs-readability/readability.json'),
  customRules: ['./vendor/docs-readability/human-prose.cjs'],
  globs: [
    '**/*.md',
    '#**/{journal,reports,devlog,evidence,archive,discussions}/**',
    '#**/{fixtures,testdata,vendor,node_modules,dist,.git}/**',
    '#**/NOW.md',
    '#**/CHANGELOG*.md'
  ]
};
```

Use `markdownlint-cli2 --no-globs README.md` to enforce only the first cleaned
file. Expand that explicit list as maintained documents are cleaned, including
new or modified maintained documents. Keep historical records and fixtures out
of the gate. Check for nested configs that override the shared rules. Run the
same command in the repository's existing local validation and CI, using its
resource wrapper where applicable.

The checks flag three consecutive bold-label bullets, prose paragraphs longer
than 600 Unicode code points, and paragraphs with two em dashes or headings
with emoji. Code blocks and tables are excluded; inline code and link URLs do
not count as prose. Reference link definitions permit long URLs. Use a local
lint disable with a reason when preserving a quotation requires an exception.
Lint does not judge whether the answer or example is useful.
