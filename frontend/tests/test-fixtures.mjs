// Проверка тех же файлов JSON, которые валидируются Python/Pydantic.
// Это инструмент проверки через Node.js, не код для включения в uni-app.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const readJson = async (name) => JSON.parse(
  await readFile(new URL(`../../docs/json-exchange/examples/${name}`, import.meta.url), 'utf8'),
);
const data = await readJson('entities.json');
const request = await readJson('transfer-request.json');
const account = await readJson('account-response.json');
const transaction = await readJson('transfer-response.json');
const submission = await readJson('test-submit.json');

assert.deepEqual(Object.keys(request).sort(), ['amount', 'cender', 'recipient']);
assert.equal(request.amount, 2500); // 25.00 BYN
assert.ok(Number.isSafeInteger(request.amount));
assert.ok(Number.isSafeInteger(request.cender));
assert.ok(Number.isSafeInteger(request.recipient));
assert.equal(account.balance, 10000);
assert.equal(account.active_balance, 7000);
assert.equal(transaction.data, '2026-10-20T10:30:00Z');
assert.equal(new Date(transaction.data).toISOString(), '2026-10-20T10:30:00.000Z');
assert.equal(submission.answers['1'], 0);
assert.equal(typeof Object.keys(data.Test[0].questions)[0], 'string');

for (const item of data.Account) {
  assert.ok(item.pigs.every(Number.isSafeInteger));
  assert.ok(item.transactions_history.every(Number.isSafeInteger));
  const reserved = data.Pig.filter((pig) => pig.account_id === item.id)
    .reduce((total, pig) => total + pig.current_balance, 0);
  assert.equal(item.active_balance, item.balance - reserved);
  assert.ok(Number.isSafeInteger(item.balance));
}
assert.equal(data.News[0].test.id, data.News[0].test_id);

function noSecrets(value) {
  if (value === null || typeof value !== 'object') return;
  for (const [key, nested] of Object.entries(value)) {
    assert.ok(!['password', 'right_answer'].includes(key));
    noSecrets(nested);
  }
}
noSecrets(data);
assert.deepEqual(JSON.parse(JSON.stringify(data)), data);
console.log('OK: Python-generated JSON parsed in JavaScript; exact names, money, IDs, dates, no secrets.');
