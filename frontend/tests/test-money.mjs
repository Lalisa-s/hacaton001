import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const source = await readFile(new URL('../src/utils/money.js', import.meta.url), 'utf8');
const { parseMoney, formatMoney } = await import(
  `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`
);

test('parseMoney accepts BYN with a comma or dot and returns exact kopecks', () => {
  const examples = [
    ['1', 100], ['12.5', 1250], ['12,50', 1250], ['0.01', 1], ['0,1', 10],
    ['  200,00  ', 20000], ['\t1.25\n', 125], ['00012.05', 1205],
    ['00000000000000000000000000000000000000000.01', 1],
    ['90071992547409.90', Number.MAX_SAFE_INTEGER - 1],
    ['90071992547409,91', Number.MAX_SAFE_INTEGER],
  ];
  for (const [input, expected] of examples) {
    assert.equal(parseMoney(input), expected, JSON.stringify(input));
  }
});

test('parseMoney rejects zero, signs, thousands, scientific notation and partial input', () => {
  const examples = [
    '', ' ', '0', '00', '0.00', '000,00', '-0', '-1', '+1',
    '.50', ',50', '1.', '1,', '1.001', '1,001', '1.2.3', '1,2,3',
    '1 000', '1\u00a0000', '1\u202f000', '1_000', '1,000.00', '1.000,00',
    '1e2', '1E2', '0x10', 'NaN', 'Infinity', '12 BYN', '12руб', '１２',
  ];
  for (const input of examples) assert.equal(parseMoney(input), null, JSON.stringify(input));
});

test('parseMoney rejects non-string input without coercion', () => {
  for (const input of [undefined, null, 1, 1.5, NaN, Infinity, true, [], {}, new String('1')]) {
    assert.equal(parseMoney(input), null);
  }
});

test('parseMoney rejects amounts above the shared JSON safe integer boundary', () => {
  for (const input of [
    '90071992547409.92', '90071992547410', '9007199254740991',
    '99999999999999999999999999999999999999.99',
  ]) {
    assert.equal(parseMoney(input), null, input);
  }
});

test('formatMoney keeps two decimal digits and uses a nonbreaking thousands separator', () => {
  const examples = [
    [0, '0,00'], [-0, '0,00'], [1, '0,01'], [10, '0,10'], [99, '0,99'],
    [100, '1,00'], [20000, '200,00'], [123456, '1\u00a0234,56'],
    [123456789, '1\u00a0234\u00a0567,89'],
    [Number.MAX_SAFE_INTEGER, '90\u00a0071\u00a0992\u00a0547\u00a0409,91'],
  ];
  for (const [input, expected] of examples) assert.equal(formatMoney(input), expected);
});

test('formatMoney rejects non-numeric values and invalid numeric amounts', () => {
  for (const input of ['100', null, undefined, true, [], {}, 100n]) {
    assert.throws(() => formatMoney(input), TypeError);
  }
  for (const input of [-1, 0.01, NaN, Infinity, -Infinity, Number.MAX_SAFE_INTEGER + 1]) {
    assert.throws(() => formatMoney(input), RangeError);
  }
});

test('positive amounts round-trip exactly, including near the safe integer boundary', () => {
  const examples = [1, 9, 10, 99, 100, 101, 10001, 123456789];
  for (let distance = 0; distance < 100; distance += 1) {
    examples.push(Number.MAX_SAFE_INTEGER - distance);
  }
  for (const amount of examples) {
    const input = formatMoney(amount).replaceAll('\u00a0', '');
    assert.equal(parseMoney(input), amount, input);
  }
});
