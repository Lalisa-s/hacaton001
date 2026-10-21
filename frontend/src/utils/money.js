// API передаёт деньги целыми копейками. Десятичную строку не умножаем на 100:
// это сохраняет точность, в том числе около Number.MAX_SAFE_INTEGER.
const MAX_KOPECKS = String(Number.MAX_SAFE_INTEGER);
const NBSP = '\u00a0';

/** Преобразует положительную сумму BYN в копейки; неверный ввод возвращает null. */
export function parseMoney(value) {
  if (typeof value !== 'string') return null;
  const match = /^([0-9]+)(?:[.,]([0-9]{1,2}))?$/.exec(value.trim());
  if (!match) return null;

  const fraction = (match[2] || '').padEnd(2, '0');
  const kopecks = `${match[1]}${fraction}`.replace(/^0+/, '') || '0';
  if (kopecks === '0'
      || kopecks.length > MAX_KOPECKS.length
      || (kopecks.length === MAX_KOPECKS.length && kopecks > MAX_KOPECKS)) {
    return null;
  }
  return Number(kopecks);
}

/** Форматирует целые неотрицательные копейки: 123456 → «1 234,56». */
export function formatMoney(kopecks) {
  if (typeof kopecks !== 'number') {
    throw new TypeError('Сумма должна быть числом копеек.');
  }
  if (!Number.isSafeInteger(kopecks) || kopecks < 0) {
    throw new RangeError('Сумма должна быть безопасным неотрицательным целым числом.');
  }
  const digits = String(kopecks).padStart(3, '0');
  const whole = digits.slice(0, -2).replace(/\B(?=([0-9]{3})+(?![0-9]))/g, NBSP);
  return `${whole},${digits.slice(-2)}`;
}
