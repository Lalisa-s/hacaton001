import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

// api.js предназначен для сборки uni-app. Data URL позволяет проверить ES-модуль
// без package.json, npm install и изменения существующего frontend-проекта.
const source = await readFile(new URL('../src/api/api.js', import.meta.url), 'utf8');
const { createApi, ApiError } = await import(
  `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`
);
const baseUrl = 'http://backend.test/api/v1';
const calls = [];
function reply(statusCode, data) {
  return (options) => {
    calls.push(options);
    options.success({ statusCode, data });
  };
}

const health = createApi({ baseUrl, request: reply(200, { status: 'ok' }) });
assert.deepEqual(await health.getHealth(), { status: 'ok' });
assert.equal(calls.at(-1).url, `${baseUrl}/health`);
assert.equal(calls.at(-1).dataType, 'json');
assert.equal(calls.at(-1).data, undefined);

const transfer = createApi({ baseUrl, request: reply(201, { id: 1, amount: 1250 }) });
assert.deepEqual(await transfer.createTransaction({
  cender: 3, recipient: 5, amount: 1250, balance: 999999,
}), { id: 1, amount: 1250 });
assert.equal(calls.at(-1).method, 'POST');
assert.deepEqual(calls.at(-1).data, { cender: 3, recipient: 5, amount: 1250 });
assert.equal(typeof calls.at(-1).data, 'object');
assert.equal(calls.at(-1).header['Content-Type'], 'application/json');
assert.throws(() => transfer.createTransaction({ cender: 3, recipient: 5, amount: 12.5 }), TypeError);

const account = createApi({ baseUrl: `${baseUrl}/`, request: reply(200, { id: 3 }) });
assert.deepEqual(await account.getAccount(3), { id: 3 });
assert.equal(calls.at(-1).url, `${baseUrl}/accounts/3`);
assert.throws(() => account.getAccount('3'), TypeError);

const list = createApi({ baseUrl, request: reply(200, []) });
assert.deepEqual(await list.getHealth(), []); // Common parser accepts object/array.
for (const badBody of ['{"status":"ok"}', '<html>error</html>', null, 7, true, undefined]) {
  const api = createApi({ baseUrl, request: reply(200, badBody) });
  await assert.rejects(api.getHealth(), (error) => error instanceof ApiError
    && error.status === 200 && error.code === 'INVALID_RESPONSE');
}
await assert.rejects(createApi({ baseUrl, request: reply(204, undefined) }).getHealth(),
  { code: 'INVALID_RESPONSE', status: 204 });

const business = createApi({ baseUrl, request: reply(409, {
  error: { code: 'INSUFFICIENT_FUNDS', message: 'private balance 999', details: [] },
}) });
await assert.rejects(business.getHealth(), (error) => error.status === 409
  && error.code === 'INSUFFICIENT_FUNDS' && !error.message.includes('999'));

const validation = createApi({ baseUrl, request: reply(422, { detail: [{
  loc: ['body', 'amount'], type: 'greater_than', msg: 'secret', input: 'secret', ctx: { secret: true },
}] }) });
await assert.rejects(validation.getHealth(), (error) => {
  assert.equal(error.code, 'VALIDATION_ERROR');
  assert.deepEqual(error.details, [{ field: 'body.amount', code: 'greater_than' }]);
  assert.equal(JSON.stringify(error).includes('secret'), false);
  return true;
});
const missing = createApi({ baseUrl, request: reply(404, { detail: 'private record' }) });
await assert.rejects(missing.getHealth(), (error) => error.status === 404
  && error.code === 'HTTP_404' && !error.message.includes('private'));

let attempts = 0;
const offline = createApi({ baseUrl, request(options) {
  attempts += 1;
  options.fail({ errMsg: 'private URL' });
} });
await assert.rejects(offline.createTransaction({ cender: 3, recipient: 5, amount: 1250 }),
  (error) => error.status === 0 && error.code === 'NETWORK_ERROR'
    && !JSON.stringify(error).includes('private'));
assert.equal(attempts, 1);

const throws = createApi({ baseUrl, request() { throw new Error('private'); } });
await assert.rejects(throws.getHealth(), { code: 'NETWORK_ERROR' });
assert.throws(() => createApi({ baseUrl: '', request() {} }), TypeError);
assert.throws(() => createApi({ baseUrl }), TypeError);
console.log('OK: JSON serialization/parsing, HTTP errors, validation, transport errors, no retry.');
