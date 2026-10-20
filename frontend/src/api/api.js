// Модуль для существующего uni-app проекта. Зависимости устанавливать не нужно.
// baseUrl содержит /api/v1; request передаётся из uni-app или из теста.

const SAFE_MESSAGES = {
  VALIDATION_ERROR: 'Проверьте введённые данные.',
  INSUFFICIENT_FUNDS: 'На счёте недостаточно доступных средств.',
  ACCOUNT_FROZEN: 'Счёт заморожен.',
  LIMIT_EXCEEDED: 'Лимит операций превышен.',
  ACCESS_DENIED: 'Нет разрешения на эту операцию.',
  NOT_FOUND: 'Запрошенный объект не найден.',
};

export class ApiError extends Error {
  constructor({ status = 0, code, message, details = [] }) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function safeToken(value, fallback) {
  return typeof value === 'string' && /^[A-Za-z][A-Za-z0-9_]{0,63}$/.test(value)
    ? value
    : fallback;
}

function safeDetails(details) {
  if (!Array.isArray(details)) return [];
  return details.slice(0, 20).filter(isObject).map((detail) => {
    // FastAPI иногда возвращает input и ctx: их не сохраняем и не показываем.
    // Сохраняем только путь поля и тип ошибки, без исходных значений и msg.
    const rawPath = Array.isArray(detail.loc)
      ? detail.loc
      : typeof detail.field === 'string' ? detail.field.split('.') : [];
    const field = rawPath.slice(0, 8).map((part) => {
      if (Number.isSafeInteger(part) && part >= 0) return String(part);
      return safeToken(part, 'field');
    }).join('.');
    return { field, code: safeToken(detail.code || detail.type, 'invalid_value') };
  });
}

function httpError(status, body) {
  let code = `HTTP_${status}`;
  let details = [];
  if (isObject(body) && isObject(body.error)) {
    code = safeToken(body.error.code, code);
    details = safeDetails(body.error.details);
  } else if (isObject(body) && Array.isArray(body.detail)) {
    code = 'VALIDATION_ERROR';
    details = safeDetails(body.detail);
  }
  // detail:string и произвольные message сервера не выводятся в интерфейс.
  const message = (Object.prototype.hasOwnProperty.call(SAFE_MESSAGES, code)
    ? SAFE_MESSAGES[code] : undefined)
    || (status === 401 ? 'Требуется вход в приложение.'
      : status === 403 ? 'Нет разрешения на эту операцию.'
      : status === 404 ? 'Запрошенный объект не найден.'
      : status >= 500 ? 'Сервер временно недоступен.'
      : 'Не удалось выполнить запрос.');
  return new ApiError({ status, code, message, details });
}

function requirePositiveInteger(value, name) {
  if (!Number.isSafeInteger(value) || value <= 0) {
    throw new TypeError(`${name}: ожидается положительное целое число.`);
  }
}

export function createApi({ baseUrl, request }) {
  if (typeof baseUrl !== 'string'
      || !/^https?:\/\/[^/\s?#]+(?:\/[^\s?#]*)?$/.test(baseUrl.trim())) {
    throw new TypeError('Укажите полный HTTP(S) адрес backend с /api/v1.');
  }
  if (typeof request !== 'function') {
    throw new TypeError('Передайте request: options => uni.request(options).');
  }
  const apiBase = baseUrl.trim().replace(/\/+$/, '');

  function send(method, path, data) {
    return new Promise((resolve, reject) => {
      const options = {
        url: `${apiBase}${path}`,
        method,
        header: { Accept: 'application/json', 'Content-Type': 'application/json' },
        dataType: 'json',
        timeout: 10000,
        success(response) {
          const status = response && response.statusCode;
          const body = response && response.data;
          if (!Number.isInteger(status) || status < 100 || status > 599) {
            reject(new ApiError({
              code: 'INVALID_RESPONSE', message: 'Сервер вернул некорректный ответ.',
            }));
            return;
          }
          if (status < 200 || status >= 300) {
            reject(httpError(status, body));
            return;
          }
          // uni.request уже разобрал JSON. HTML, строка с JSON и null не подходят.
          // Эти методы ожидают тело ответа; 204 без тела им не соответствует.
          if (!isObject(body) && !Array.isArray(body)) {
            reject(new ApiError({
              status, code: 'INVALID_RESPONSE',
              message: 'Ответ сервера не соответствует формату JSON API.',
            }));
            return;
          }
          resolve(body);
        },
        fail() {
          // errMsg может содержать URL и технические подробности; не сохраняем.
          reject(new ApiError({
            code: 'NETWORK_ERROR', message: 'Не удалось связаться с сервером.',
          }));
        },
      };
      if (data !== undefined) options.data = data;
      try {
        request(options);
      } catch {
        reject(new ApiError({
          code: 'NETWORK_ERROR', message: 'Не удалось связаться с сервером.',
        }));
      }
    });
  }

  return {
    // Реализованный endpoint существующего backend.
    getHealth() {
      return send('GET', '/health');
    },

    // ПРОЕКТ КОНТРАКТА: endpoint пока отсутствует в backend.
    getAccount(id) {
      requirePositiveInteger(id, 'id');
      return send('GET', `/accounts/${id}`);
    },

    // ПРОЕКТ КОНТРАКТА: endpoint пока отсутствует в backend.
    // cender/recipient — ID счетов; amount — целые копейки BYN.
    createTransaction({ cender, recipient, amount }) {
      requirePositiveInteger(cender, 'cender');
      requirePositiveInteger(recipient, 'recipient');
      requirePositiveInteger(amount, 'amount');
      // Собираем новый объект: balance, роль и другие поля сюда не попадут.
      return send('POST', '/transactions', { cender, recipient, amount });
    },
  };
}
