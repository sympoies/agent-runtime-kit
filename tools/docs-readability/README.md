# Shared documentation readability checks

The [writing policy](../../core/policies/human-docs.md) describes the human
review. The lint rules provide a small, reproducible check alongside that review.
Node.js 22 or newer and npm are required.

Run `npm ci --prefix tools/docs-readability`, then run
`npm test --prefix tools/docs-readability` and
`npm run lint --prefix tools/docs-readability`. The lint command checks the
policy; `bash scripts/ci/all.sh` installs the locked dependencies and runs both.

## Use in another repository

Check out this kit at a reviewed, full merge commit SHA and record that pin in
the consumer's setup or CI. Install its locked dependencies with
`npm ci --ignore-scripts --prefix <kit-checkout>/tools/docs-readability`.
From the consumer's working directory, run:

```sh
<kit-checkout>/tools/docs-readability/bin/docs-lint README.md docs/guide.md
```

Pass the maintained files or directories to check; directories are searched
recursively for Markdown files. Paths are relative to the working directory.
Missing paths fail with exit code 2; findings return 1 and a clean run returns
0. Only the supplied paths are linted. Do not copy the rules or configuration
into the consumer: the entrypoint loads them from the pinned checkout. Expand
the list as maintained documents are cleaned, and run the same command in local
validation and CI using the consumer's resource wrapper where applicable.

The checks flag three consecutive bold-label bullets, prose paragraphs longer
than 600 Unicode code points, and paragraphs with two em dashes or headings
with emoji. Code blocks and tables are excluded; inline code and link URLs do
not count as prose. Reference link definitions permit long URLs. Use a local
lint disable with a reason when preserving a quotation requires an exception.
Lint does not judge whether the answer or example is useful.
