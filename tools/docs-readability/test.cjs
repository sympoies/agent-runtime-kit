const assert = require('node:assert/strict');
const markdownlint = require('markdownlint/sync');
const MarkdownIt = require('markdown-it');
const rules = require('./human-prose.cjs');
const config = require('./readability.json');

function errors(markdown) {
  const result = markdownlint.lint({
    strings: { fixture: markdown }, config, customRules: rules,
    markdownItFactory: () => new MarkdownIt()
  });
  return result.fixture.map(error => error.ruleNames[0]);
}
function check(name, markdown, expected) {
  assert.deepEqual(errors(markdown).filter(rule => rule.startsWith('HUM')), expected, name);
}
const bullets = n => Array.from({length: n}, (_, i) => `- **Label ${i}**: value`).join('\n');
check('two labels', bullets(2), []);
check('three labels', bullets(3), ['HUM001']);
check('separate runs', `${bullets(3)}\n- plain\n${bullets(3)}`, ['HUM001', 'HUM001']);
check('80 character labels', Array(3).fill(`- **${'x'.repeat(80)}** value`).join('\n'), ['HUM001']);
check('81 character labels', Array(3).fill(`- **${'x'.repeat(81)}** value`).join('\n'), []);
check('no separator', Array(3).fill('- **Label**value').join('\n'), []);
check('ordered list', '1. **One**: x\n2. **Two**: x\n3. **Three**: x', []);
check('600 code points', '中'.repeat(600), []);
check('601 code points', '😀'.repeat(601), ['HUM002']);
check('soft line breaks are one paragraph', `${'x'.repeat(300)}\n${'x'.repeat(300)}`, ['HUM002']);
check('separate paragraphs', `${'x'.repeat(300)}\n\n${'x'.repeat(300)}`, []);
check('list paragraph', `- ${'a '.repeat(301)}`, ['HUM002']);
check('inline code and link destination excluded', `Text \`${'x'.repeat(700)}\` [label](https://example.com/${'x'.repeat(700)})`, []);
check('link label included', `[${'x'.repeat(601)}](https://example.com)`, ['HUM002']);
check('one dash', 'One — two.', []);
check('two dashes', 'One — two — three.', ['HUM003']);
check('emoji heading', '# Hello 😀', ['HUM003']);
check('plain heading', '# Hello', []);
check('inline code excluded', 'Text `— —`.', []);
check('code and table excluded', `\`\`\`\n${'x'.repeat(601)} — —\n\`\`\`\n\n| Header |\n| --- |\n| ${'x'.repeat(601)} — — |`, []);
check('local disable', '<!-- markdownlint-disable HUM003 -- reason: preserve quotation -->\n\nOne — two — three.\n\n<!-- markdownlint-enable HUM003 -->', []);
function hasRule(markdown, rule) { return errors(markdown).includes(rule); }
assert.equal(hasRule('a'.repeat(120), 'MD013'), false);
assert.equal(hasRule('a'.repeat(121), 'MD013'), true);
assert.equal(hasRule('# ' + 'a'.repeat(78), 'MD013'), false);
assert.equal(hasRule('# ' + 'a'.repeat(79), 'MD013'), true);
assert.equal(hasRule('[ref]: https://example.com/' + 'a'.repeat(150), 'MD013'), false);
assert.equal(hasRule('```\n' + 'a'.repeat(150) + '\n```', 'MD013'), false);
assert.equal(hasRule('| Head |\n| --- |\n| ' + 'a'.repeat(150) + ' |', 'MD013'), false);
console.log('Readability fixture checks passed.');
