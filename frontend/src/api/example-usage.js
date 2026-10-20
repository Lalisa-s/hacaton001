import { ApiError, createApi } from './api.js';

// Передайте сюда адрес из конфигурации вашего frontend.
// Для телефона и другого ПК нужен LAN-адрес компьютера с backend, не localhost.
// Формат: http://<BACKEND_LAN_IP>:8000/api/v1
export function configureApi(apiBaseUrl) {
  return createApi({
    baseUrl: apiBaseUrl,
    request: (options) => uni.request(options),
  });
}

export async function checkBackend(api) {
  const health = await api.getHealth();
  // health — уже JS-объект { status: 'ok' }, JSON.parse не нужен.
  return health.status === 'ok';
}

// Будущие вызовы: начнут работать после реализации соответствующих endpoint.
export async function loadAccountExample(api, accountId) {
  const account = await api.getAccount(accountId);
  // account.balance хранит целые копейки. Форматируем без округления дробной суммы.
  const displayedBalance = `${Math.trunc(account.balance / 100)}.${String(account.balance % 100).padStart(2, '0')} BYN`;
  return { account, displayedBalance };
}

export async function transferExample(api, senderAccountId, recipientAccountId) {
  try {
    // Пример суммы: 12,50 BYN = 1250 копеек; не 12.50 в JSON.
    const transaction = await api.createTransaction({
      cender: senderAccountId,
      recipient: recipientAccountId,
      amount: 1250,
    });
    // После успеха заново запрашиваем состояние, рассчитанное backend.
    // Ошибка следующего GET не означает неуспех уже совершённого перевода.
    return transaction;
  } catch (error) {
    if (error instanceof ApiError) {
      // message безопасен для интерфейса; details содержит только поля и коды.
      // Не показывайте сырые HTTP-ответы, пароли и технический error.stack.
      // При NETWORK_ERROR результат перевода может быть неизвестен:
      // проверьте историю после восстановления связи; POST не повторяйте.
      throw error;
    }
    throw error;
  }
}
