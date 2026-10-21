<template>
  <view class="app-shell">
    <view class="topbar" :inert="transferOpen ? true : undefined" :aria-hidden="transferOpen ? true : undefined">
      <view class="topbar-inner">
        <view class="brand"><view class="brand-mark">сб</view><text>Семейный банк</text></view>
        <view class="profile"><text class="demo-pill">ДЕМО</text><view class="avatar">{{ currentUser?.role === 'child' ? 'С' : 'Р' }}</view><text class="profile-label">{{ demoProfiles.find(p => p.id === demoUserId)?.label }}</text></view>
      </view>
      <view class="demo-switch"><text>Демо-профиль:</text><button role="button" v-for="profile in demoProfiles" :key="profile.id" :class="{ 'demo-profile-active': demoUserId === profile.id }" :disabled="posting || pigLocked || transferUnknown || refreshing || switching" @click="changeDemoProfile(profile.id)">{{ profile.label }}</button></view>
    </view>

    <view class="page-content" :inert="transferOpen ? true : undefined" :aria-hidden="transferOpen ? true : undefined">
      <view class="page-heading">
        <view><text class="eyebrow">ВАШИ ФИНАНСЫ</text><text class="page-title">Всё важное — рядом</text><text class="page-description">Счета, накопления и переводы в одном месте.</text></view>
        <view class="heading-actions">
          <button v-if="currentUser?.role === 'parent'" ref="transferTrigger" role="button" tabindex="0" class="open-transfer-button" aria-haspopup="dialog" :aria-expanded="transferOpen" :disabled="initialLoading || accounts.length < 2 || pigLocked" @click="openTransfer" @keydown.enter.prevent="openTransfer" @keydown.space.prevent="openTransfer">Перевести деньги <text>↗</text></button>
          <button role="button" class="refresh-button" :disabled="refreshing || posting" @click="refreshAll(false)"><text :class="{ spinning: refreshing }">↻</text><text>{{ refreshing ? 'Обновляем' : 'Обновить' }}</text></button>
        </view>
      </view>

      <view v-if="loadError" class="notice notice-error" role="alert"><text class="notice-title">Не удалось обновить данные</text><text>{{ loadError }}</text><text v-if="accounts.length">Ниже показаны последние полученные остатки.</text></view>

      <view v-if="initialLoading" class="loading-panel"><view class="loader" /><text>Загружаем ваши счета…</text></view>

      <template v-else-if="accounts.length">
        <view class="overview-grid">
          <view class="balance-panel">
            <view class="balance-panel-top"><text class="balance-label">Всего на счетах</text><text class="currency-label">BYN</text></view>
            <text class="total-balance">{{ totals.balance }}</text>
            <view class="balance-breakdown">
              <view><view class="dot-label"><text class="dot dot-mint" /><text>Доступно для трат</text></view><text class="breakdown-value">{{ totals.available }} BYN</text></view>
              <view><view class="dot-label"><text class="dot dot-lime" /><text>В копилках</text></view><text class="breakdown-value">{{ totals.reserved }} BYN</text></view>
            </view>
            <view class="balance-decoration decoration-one" /><view class="balance-decoration decoration-two" />
          </view>
          <view class="intro-panel"><view class="intro-symbol">↗</view><text class="intro-title">Маленькие шаги. Большие планы.</text><text class="intro-description">Деньги в копилках входят в общий баланс, но недоступны для обычного перевода.</text><view class="intro-footnote"><text class="small-dot" /><text>Учебное демо · без реальных денег</text></view></view>
        </view>

        <view class="section-heading"><text class="section-title">Мои счета</text><text class="section-caption">{{ accounts.length }} {{ accountCountLabel }}</text></view>
        <view class="accounts-grid">
          <view v-for="(account, index) in accounts" :key="account.id" class="account-card" :class="{ 'account-frozen': !account.active }">
            <view class="account-card-heading"><view class="account-icon">▤</view><view class="account-identity"><text class="account-title">{{ accountName(account, index) }}</text><text class="muted-text">Счёт № {{ account.id }}</text></view><text class="status-pill" :class="{ 'status-frozen': !account.active }">{{ account.active ? 'Активен' : 'Заморожен' }}</text></view>
            <view class="account-amount"><text>{{ money(account.active_balance) }}</text><text class="amount-currency">BYN</text></view>
            <text class="account-cash-label">Доступно для трат · накопления показаны в копилках</text>
            <view class="account-limit"><text>Лимит переводов</text><text>{{ account.limit === null ? 'Не установлен' : `${money(account.limit)} BYN / ${periodLabel(account.limit_period)}` }}</text></view>
          </view>
        </view>

        <PigSection :key="currentUser?.id" :user="currentUser" :accounts="accounts" :refresh-key="pigRefreshKey" :money-locked="posting || transferUnknown" @changed="refreshAll(false)" @locked="pigLocked = $event" />

        <view class="workspace-grid">
          <view class="surface history-panel">
            <view class="panel-heading"><view><text class="section-title">История переводов</text><text class="panel-caption">Последние операции выбранного счёта</text></view><text class="history-badge">{{ transactions.length }}</text></view>
            <view class="account-tabs"><button role="button" v-for="account in accounts" :key="account.id" class="account-tab" :class="{ 'account-tab-active': historyAccountId === account.id }" :disabled="posting" @click="selectHistoryAccount(account.id)">{{ accountName(account) }}</button></view>
            <view v-if="historyError" class="notice notice-error" role="alert"><text>{{ historyError }}</text><button role="button" class="text-button" :disabled="historyLoading || posting" @click="loadHistory(historyAccountId)">Обновить историю</button></view>
            <view v-if="historyLoading && !transactions.length" class="history-empty"><view class="loader" /><text>Загружаем переводы…</text></view>
            <view v-else-if="!transactions.length && !historyError" class="history-empty"><view class="empty-symbol">⇄</view><text class="empty-title">Здесь появится первый перевод</text><text>Переведите небольшую сумму между своими счетами, и операция появится в истории.</text></view>
            <view v-else class="transaction-list"><view v-for="transaction in transactions" :key="transaction.id" class="transaction-row"><view class="transaction-icon" :class="{ 'transaction-incoming': transaction.recipient === historyAccountId }">{{ transaction.recipient === historyAccountId ? '↙' : '↗' }}</view><view class="transaction-content"><text class="transaction-title">{{ transactionTitle(transaction) }}</text><text class="transaction-date">{{ dateLabel(transaction.data) }}</text></view><text class="transaction-amount" :class="{ 'transaction-positive': transaction.recipient === historyAccountId }">{{ transaction.recipient === historyAccountId ? '+' : '−' }}{{ money(transaction.amount) }}<text class="transaction-currency"> BYN</text></text></view></view>
            <text v-if="transactions.length === 50" class="history-note">Показаны последние 50 переводов.</text>
          </view>
        </view>
      </template>

      <view v-else-if="!loadError" class="surface no-accounts"><text class="empty-title">Пока нет доступных счетов</text><text>Когда счёт появится в профиле, здесь можно будет посмотреть баланс и выполнить перевод.</text></view>

      <view class="page-footer"><view class="connection-state"><text class="connection-dot" :class="{ 'connection-offline': loadError }" /><text>{{ loadError ? 'Нет связи с API' : lastUpdated ? `Обновлено ${lastUpdated} · каждые 10 сек.` : 'Подключаемся к API' }}</text></view><text>Семейный банк · учебный прототип</text></view>
    </view>

    <view v-if="transferOpen" class="modal-overlay" @click.self="closeTransfer">
      <view ref="transferDialog" class="surface transfer-panel transfer-dialog" role="dialog" aria-modal="true" aria-labelledby="transfer-dialog-title" aria-describedby="transfer-dialog-description" tabindex="-1" @click.stop>
        <view class="panel-heading transfer-dialog-heading">
          <view><text id="transfer-dialog-title" class="section-title">Перевести деньги</text><text id="transfer-dialog-description" class="panel-caption">Между своими счетами</text></view>
          <button role="button" tabindex="0" class="modal-close" aria-label="Закрыть окно перевода" :disabled="posting || transferUnknown" :aria-disabled="posting || transferUnknown" @click="closeTransfer" @keydown.enter.prevent="closeTransfer" @keydown.space.prevent="closeTransfer">×</button>
        </view>
        <view class="transfer-dialog-body">
          <view v-if="transferSuccess" class="notice notice-success" role="status"><text class="notice-title">Перевод выполнен</text><text>{{ transferSuccess }}</text></view>
          <view v-if="transferError" class="notice notice-error" role="alert"><text>{{ transferError }}</text></view>
          <view v-if="transferUnknown" class="notice notice-error">
            <text>Новый перевод заблокирован до проверки результата предыдущего.</text>
            <button role="button" tabindex="0" v-if="!unknownChecked" class="text-button" :disabled="posting || refreshing" @click="verifyUnknownTransfer" @keydown.enter.prevent="verifyUnknownTransfer" @keydown.space.prevent="verifyUnknownTransfer">Проверить остатки и историю</button>
            <template v-else>
              <text>Остатки и история счёта списания обновлены. Проверьте, появилась ли операция в списке ниже.</text>
              <view class="verification-history">
                <text v-if="!transactions.length" class="verification-empty">В истории этого счёта пока нет переводов.</text>
                <view v-for="transaction in transactions" :key="transaction.id" class="verification-row">
                  <view><text class="transaction-title">{{ transactionTitle(transaction) }}</text><text class="transaction-date">{{ dateLabel(transaction.data) }}</text></view>
                  <text class="verification-amount">{{ transaction.recipient === historyAccountId ? '+' : '−' }}{{ money(transaction.amount) }} BYN</text>
                </view>
              </view>
              <button role="button" tabindex="0" class="text-button" @click="prepareNewTransfer" @keydown.enter.prevent="prepareNewTransfer" @keydown.space.prevent="prepareNewTransfer">История проверена — начать новый перевод</button>
            </template>
            <text v-if="loadError || historyError">Проверка пока не завершена. {{ loadError || historyError }}</text>
          </view>

          <view class="form-field"><text class="field-label">Откуда</text><picker tabindex="0" role="button" aria-label="Выбрать счёт списания" :aria-disabled="posting || transferUnknown" @keydown.enter.prevent="openPickerWithKeyboard" @keydown.space.prevent="openPickerWithKeyboard" :value="sourceIndex" :range="accountOptions" range-key="label" :disabled="posting || transferUnknown" @change="changeSource"><view class="select-field"><view><text class="select-title">{{ sourceAccount ? accountName(sourceAccount) : 'Выберите счёт' }}</text><text v-if="sourceAccount" class="select-description">Доступно {{ money(sourceAccount.active_balance) }} BYN</text></view><text class="select-chevron">⌄</text></view></picker></view>
          <view class="form-field"><text class="field-label">Куда</text><picker tabindex="0" role="button" aria-label="Выбрать счёт получателя" :aria-disabled="posting || transferUnknown" @keydown.enter.prevent="openPickerWithKeyboard" @keydown.space.prevent="openPickerWithKeyboard" :value="recipientIndex" :range="accountOptions" range-key="label" :disabled="posting || transferUnknown" @change="changeRecipient"><view class="select-field"><view><text class="select-title">{{ recipientAccount ? accountName(recipientAccount) : 'Выберите счёт' }}</text><text v-if="recipientAccount" class="select-description">Счёт № {{ recipientAccount.id }}</text></view><text class="select-chevron">⌄</text></view></picker></view>
          <view class="form-field"><text class="field-label">Сумма перевода</text><view class="amount-input-wrap"><input v-model="amountInput" class="amount-input" aria-label="Сумма перевода в BYN" type="text" inputmode="decimal" placeholder="0,00" :disabled="posting || transferUnknown" maxlength="18" @input="clearTransferError" /><text>BYN</text></view><text v-if="formHint" class="field-hint" :class="{ 'field-hint-error': amountInput && !canSubmit }">{{ formHint }}</text></view>
          <button role="button" tabindex="0" class="primary-button" :aria-disabled="!canSubmit || posting || refreshing" :disabled="!canSubmit || posting || refreshing" :loading="posting" @click="submitTransfer" @keydown.enter.prevent="submitTransfer" @keydown.space.prevent="submitTransfer">{{ posting ? 'Выполняем перевод…' : 'Перевести' }}<text v-if="!posting"> →</text></button>
          <text class="transfer-footnote">Остаток и лимит проверяются при выполнении перевода.</text>
          <text v-if="posting" class="modal-state-message" role="status">Дождитесь завершения перевода, чтобы закрыть окно.</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, nextTick, onUnmounted, ref, watch } from 'vue';
import { onHide, onShow } from '@dcloudio/uni-app';
import { api, getDemoUserId, setDemoUserId } from '../../api/client.js';
import { formatMoney, parseMoney } from '../../utils/money.js';
import PigSection from '../../components/PigSection.vue';

const currentUser = ref(null);
const pigRefreshKey = ref(0);
const pigLocked = ref(false);
const switching = ref(false);
const demoUserId = ref(getDemoUserId());
const demoProfiles = [{ id: 10, label: 'Родитель' }, { id: 20, label: 'Ребёнок' }, { id: 11, label: 'Участник семьи' }];
const transferOpen = ref(false);
const transferDialog = ref(null);
const transferTrigger = ref(null);
const accounts = ref([]);
const transactions = ref([]);
const initialLoading = ref(true);
const refreshing = ref(false);
const posting = ref(false);
const historyLoading = ref(false);
const loadError = ref('');
const historyError = ref('');
const transferError = ref('');
const transferSuccess = ref('');
const transferUnknown = ref(false);
const unknownChecked = ref(false);
const amountInput = ref('');
const sourceId = ref(null);
const recipientId = ref(null);
const historyAccountId = ref(null);
const lastUpdated = ref('');
let pollTimer;
let visible = false;
let alive = true;
let historyGeneration = 0;
let previousFocus = null;
let previousBodyOverflow = '';
let modalEnvironmentActive = false;

const sourceAccount = computed(() => accounts.value.find((account) => account.id === sourceId.value));
const recipientAccount = computed(() => accounts.value.find((account) => account.id === recipientId.value));
const sourceIndex = computed(() => Math.max(0, accounts.value.findIndex((account) => account.id === sourceId.value)));
const recipientIndex = computed(() => Math.max(0, accounts.value.findIndex((account) => account.id === recipientId.value)));
const accountOptions = computed(() => accounts.value.map((account) => ({ label: `${accountName(account)} · № ${account.id}` })));
const amount = computed(() => parseMoney(amountInput.value));
const canSubmit = computed(() => !!sourceAccount.value && !!recipientAccount.value
  && !transferUnknown.value
  && sourceId.value !== recipientId.value && sourceAccount.value.active && recipientAccount.value.active
  && amount.value !== null && amount.value <= sourceAccount.value.active_balance);
const accountCountLabel = computed(() => {
  const count = accounts.value.length;
  return count % 10 === 1 && count % 100 !== 11 ? 'счёт' : count % 10 >= 2 && count % 10 <= 4 && !(count % 100 >= 12 && count % 100 <= 14) ? 'счёта' : 'счетов';
});
const totals = computed(() => {
  // Каждый остаток безопасен для JS, но сумма нескольких счетов может быть больше.
  let balance = BigInt(0);
  let available = BigInt(0);
  for (const account of accounts.value) {
    balance += BigInt(account.balance);
    available += BigInt(account.active_balance);
  }
  return { balance: formatTotal(balance), available: formatTotal(available), reserved: formatTotal(balance - available) };
});
const formHint = computed(() => {
  if (accounts.value.length < 2) return 'Для перевода нужны два счёта.';
  if (sourceId.value === recipientId.value) return 'Выберите разные счета.';
  if (!sourceAccount.value?.active || !recipientAccount.value?.active) return 'Один из выбранных счетов заморожен.';
  if (!amountInput.value) return 'Укажите сумму в BYN, например 12,50.';
  if (amount.value === null) return 'Введите сумму больше нуля, не более двух знаков после запятой.';
  if (amount.value > sourceAccount.value.active_balance) return 'Сумма больше доступного остатка.';
  return 'Без комиссии в этом демо.';
});

function openTransfer() {
  if (initialLoading.value || accounts.value.length < 2 || pigLocked.value) return;
  transferSuccess.value = '';
  if (!transferUnknown.value) transferError.value = '';
  transferOpen.value = true;
}
function closeTransfer() {
  if (posting.value || transferUnknown.value) return;
  transferOpen.value = false;
}
function elementOf(component) { return component?.$el || component; }
function openPickerWithKeyboard(event) {
  if (posting.value || transferUnknown.value) return;
  event.currentTarget?.click?.();
}
function handleModalKeydown(event) {
  if (!transferOpen.value || event.defaultPrevented) return;
  if (event.key === 'Escape') {
    event.preventDefault();
    closeTransfer();
    return;
  }
  if (event.key !== 'Tab') return;
  const dialog = elementOf(transferDialog.value);
  if (!dialog?.querySelectorAll) return;
  const focusable = Array.from(dialog.querySelectorAll('input, button, select, textarea, a[href], [tabindex]:not([tabindex="-1"])'))
    .filter((element) => !element.matches('[disabled], [aria-disabled="true"]') && element.getClientRects().length);
  if (!focusable.length) {
    event.preventDefault();
    dialog.focus();
    return;
  }
  const activeElement = document.activeElement;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (event.shiftKey && (activeElement === first || activeElement === dialog || !dialog.contains(activeElement))) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && (activeElement === last || !dialog.contains(activeElement))) {
    event.preventDefault();
    first.focus();
  }
}
function releaseModalEnvironment() {
  if (typeof document === 'undefined' || !modalEnvironmentActive) return;
  document.removeEventListener('keydown', handleModalKeydown);
  document.body.style.overflow = previousBodyOverflow;
  modalEnvironmentActive = false;
}
watch(transferOpen, async (isOpen) => {
  // DOM используется только для H5: Vue refs сохраняют совместимость страницы с uni-app.
  if (typeof document === 'undefined') return;
  if (isOpen) {
    previousFocus = document.activeElement;
    previousBodyOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    document.addEventListener('keydown', handleModalKeydown);
    modalEnvironmentActive = true;
    await nextTick();
    if (transferOpen.value && alive) elementOf(transferDialog.value)?.focus?.({ preventScroll: true });
  } else {
    releaseModalEnvironment();
    await nextTick();
    if (!alive || transferOpen.value) return;
    const target = previousFocus?.isConnected && previousFocus !== document.body
      ? previousFocus : elementOf(transferTrigger.value);
    target?.focus?.({ preventScroll: true });
  }
});

function formatTotal(value) {
  const digits = value.toString().padStart(3, '0');
  return `${digits.slice(0, -2).replace(/\B(?=(\d{3})+(?!\d))/g, ' ')}${','}${digits.slice(-2)}`;
}
function money(value) { return formatMoney(value); }
async function changeDemoProfile(id) {
  if (id === demoUserId.value || posting.value || pigLocked.value || transferUnknown.value || refreshing.value || switching.value) return;
  switching.value = true;
  setDemoUserId(id);
  demoUserId.value = id;
  currentUser.value = null;
  accounts.value = [];
  transactions.value = [];
  sourceId.value = null;
  recipientId.value = null;
  historyAccountId.value = null;
  historyGeneration += 1;
  initialLoading.value = true;
  transferSuccess.value = '';
  transferError.value = '';
  try { await refreshAll(false); }
  finally { switching.value = false; }
}
function accountName(account, fallbackIndex) {
  if (!account) return 'Счёт';
  const index = fallbackIndex ?? accounts.value.findIndex((item) => item.id === account.id);
  if (currentUser.value?.role === 'child') return index === 0 ? 'Мой счёт' : `Мой счёт ${index + 1}`;
  return index === 0 ? 'Основной счёт' : index === 1 ? 'Дополнительный счёт' : `Счёт ${index + 1}`;
}
function periodLabel(period) { return { daily: 'день', weekly: 'неделю', monthly: 'месяц' }[period] || 'период'; }
function safeError(error) { return error?.name === 'ApiError' && typeof error.message === 'string' ? error.message : 'Не удалось получить данные. Попробуйте обновить страницу.'; }
function dateLabel(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Minsk' });
}
function transactionTitle(transaction) {
  const incoming = transaction.recipient === historyAccountId.value;
  const otherId = incoming ? transaction.cender : transaction.recipient;
  const other = accounts.value.find((account) => account.id === otherId);
  return `${incoming ? 'Со счёта' : 'На счёт'} «${other ? accountName(other) : `№ ${otherId}`}»`;
}
function clearTransferError() { transferError.value = ''; }
function changeSource(event) {
  sourceId.value = accounts.value[Number(event.detail.value)]?.id ?? null;
  if (sourceId.value === recipientId.value) recipientId.value = accounts.value.find((account) => account.id !== sourceId.value)?.id ?? null;
  clearTransferError();
}
function changeRecipient(event) {
  recipientId.value = accounts.value[Number(event.detail.value)]?.id ?? null;
  clearTransferError();
}

async function loadHistory(accountId) {
  if (accountId === null || posting.value || !alive) return;
  const generation = ++historyGeneration;
  historyLoading.value = true;
  historyError.value = '';
  try {
    const response = await api.getTransactions(accountId, { limit: 50, offset: 0 });
    if (alive && generation === historyGeneration && accountId === historyAccountId.value) transactions.value = response.items;
  } catch (error) {
    if (alive && generation === historyGeneration) historyError.value = safeError(error);
  } finally {
    if (alive && generation === historyGeneration) historyLoading.value = false;
  }
}
function selectHistoryAccount(accountId) {
  if (accountId === historyAccountId.value || posting.value) return;
  historyAccountId.value = accountId;
  transactions.value = [];
  loadHistory(accountId);
}

async function verifyUnknownTransfer() {
  if (posting.value || refreshing.value) return;
  historyAccountId.value = sourceId.value;
  transactions.value = [];
  await refreshAll(false);
  unknownChecked.value = !loadError.value && !historyError.value;
}
function prepareNewTransfer() {
  if (!unknownChecked.value) return;
  amountInput.value = '';
  transferError.value = '';
  transferUnknown.value = false;
  unknownChecked.value = false;
  nextTick(() => elementOf(transferDialog.value)?.querySelector?.('input')?.focus());
}

async function refreshAll(silent = false) {
  if (refreshing.value || posting.value || !alive) return;
  refreshing.value = true;
  if (!silent) loadError.value = '';
  try {
    const [profile, response] = await Promise.all([api.getMe(), api.getAccounts()]);
    if (!alive) return;
    currentUser.value = profile;
    accounts.value = response.items;
    pigRefreshKey.value += 1;
    if (!accounts.value.some((account) => account.id === sourceId.value)) sourceId.value = accounts.value[0]?.id ?? null;
    if (!accounts.value.some((account) => account.id === recipientId.value)) recipientId.value = accounts.value.find((account) => account.id !== sourceId.value)?.id ?? null;
    if (!accounts.value.some((account) => account.id === historyAccountId.value)) {
      historyAccountId.value = accounts.value[0]?.id ?? null;
      transactions.value = [];
    }
    loadError.value = '';
    lastUpdated.value = new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
    await loadHistory(historyAccountId.value);
  } catch (error) {
    if (alive) loadError.value = safeError(error);
  } finally {
    if (alive) { refreshing.value = false; initialLoading.value = false; }
  }
}

async function submitTransfer() {
  if (!canSubmit.value || posting.value || refreshing.value) return;
  const payload = { cender: sourceId.value, recipient: recipientId.value, amount: amount.value };
  posting.value = true;
  transferError.value = '';
  transferSuccess.value = '';
  // Не позволяем более раннему GET истории заменить результат обновления после POST.
  historyGeneration += 1;
  historyLoading.value = false;
  try {
    await api.createTransaction(payload);
    if (!alive) return;
    transferSuccess.value = `${money(payload.amount)} BYN переведено. Обновляем остатки и историю.`;
    amountInput.value = '';
    // Подтверждение POST сохраняется даже при ошибке следующего GET.
    posting.value = false;
    await refreshAll(false);
    if (alive) transferSuccess.value = `${money(payload.amount)} BYN переведено.${loadError.value || historyError.value ? ' Перевод уже выполнен; обновите остатки и историю позже.' : ''}`;
  } catch (error) {
    if (alive) {
      const uncertain = !error?.status || error.status >= 500 || error.code === 'INVALID_RESPONSE';
      transferUnknown.value = uncertain;
      unknownChecked.value = false;
      transferError.value = uncertain
        ? 'Не удалось подтвердить результат перевода. Обновите историю и проверьте операцию перед новой попыткой. Запрос автоматически не повторяется.'
        : safeError(error);
    }
  } finally {
    if (alive) posting.value = false;
  }
}

onShow(() => {
  visible = true;
  refreshAll(true);
  clearInterval(pollTimer);
  pollTimer = setInterval(() => { if (visible && !posting.value && !refreshing.value) refreshAll(true); }, 10000);
});
onHide(() => { visible = false; clearInterval(pollTimer); });
onUnmounted(() => { alive = false; visible = false; clearInterval(pollTimer); historyGeneration += 1; releaseModalEnvironment(); });
</script>

<style>
page { background: #f4f6f5; color: #172e2b; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; }
view, text, button, input { box-sizing: border-box; }
button { margin: 0; padding: 0; font: inherit; border-radius: 12px; line-height: 1.35; }
button::after { border: 0; }
button[disabled] { opacity: .48; cursor: not-allowed; }
.app-shell { min-height: 100vh; }
.topbar { background: #2334c8; color: #fff; }
.topbar-inner { max-width: 1200px; min-height: 82px; margin: auto; padding: 18px 32px; display: flex; align-items: center; justify-content: space-between; gap: 20px; }
.brand { display: flex; align-items: center; gap: 13px; font-size: 21px; font-weight: 700; letter-spacing: -.6px; }
.brand-mark { width: 37px; height: 37px; display: flex; justify-content: center; align-items: center; border-radius: 12px; background: #97cfff; color: #2334c8; font-size: 22px; letter-spacing: -3px; padding-right: 3px; }
.profile { display: flex; align-items: center; gap: 12px; }
.demo-pill { color: #d7efcc; background: #ffffff12; padding: 6px 9px; border: 1px solid #ffffff20; border-radius: 7px; font-size: 10px; letter-spacing: 1.2px; font-weight: 700; }
.avatar { display: flex; justify-content: center; align-items: center; width: 33px; height: 33px; border-radius: 50%; background: #e6efe8; color: #31594d; font-size: 13px; font-weight: 700; }
.profile-label { font-size: 12px; color: #dfebe5; }
.demo-switch { max-width: 1200px; margin: auto; padding: 0 32px 15px; display: flex; gap: 7px; align-items: center; flex-wrap: wrap; font-size: 10px; color: #9db8a9; }
.demo-switch > button { font-size: 10px; background: #ffffff0b; color: #c3d6c9; padding: 7px 10px; border-radius: 7px; }
.demo-switch > button.demo-profile-active { color: #d6f6bd; background: #ffffff20; }
.account-cash-label { display: block; color: #8c9a90; font-size: 10px; line-height: 1.6; margin: 8px 0 19px; }
.page-content { max-width: 1200px; margin: auto; padding: 38px 32px 24px; }
.page-heading { display: flex; align-items: center; justify-content: space-between; gap: 20px; margin-bottom: 26px; }
.eyebrow { display: block; color: #6c8178; font-size: 10px; font-weight: 700; letter-spacing: 2px; margin-bottom: 8px; }
.page-title { display: block; font-size: 31px; font-weight: 700; letter-spacing: -1.1px; line-height: 1.2; }
.page-description { display: block; color: #7a8983; font-size: 13px; margin-top: 10px; }
.refresh-button { display: flex; justify-content: center; align-items: center; gap: 7px; background: #fff; border: 1px solid #e2e9e3; color: #416256; padding: 10px 15px; font-size: 12px; white-space: nowrap; min-width: 116px; }
.refresh-button > text:first-child { font-size: 22px; line-height: 16px; }
.overview-grid { display: grid; grid-template-columns: 1.5fr 1fr; gap: 20px; margin-bottom: 34px; }
.balance-panel { position: relative; overflow: hidden; background: #1b5146; border-radius: 22px; color: #fff; padding: 26px 30px; }
.balance-panel-top { display: flex; align-items: center; justify-content: space-between; position: relative; z-index: 1; }
.balance-label { color: #c5ded4; font-size: 13px; }
.currency-label { font-size: 11px; padding: 4px 9px; border: 1px solid #ffffff2e; border-radius: 6px; color: #d8e9e1; }
.total-balance { display: block; font-size: clamp(26px, 4vw, 44px); font-weight: 600; letter-spacing: -1.7px; margin: 12px 0 27px; position: relative; z-index: 1; overflow-wrap: anywhere; }
.balance-breakdown { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; position: relative; z-index: 1; }
.dot-label { display: flex; align-items: center; gap: 7px; color: #c5ded4; font-size: 11px; }
.dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.dot-mint { background: #9ac8b4; }.dot-lime { background: #ccf58a; }
.breakdown-value { display: block; font-size: 17px; font-weight: 600; margin-top: 8px; overflow-wrap: anywhere; }
.balance-decoration { position: absolute; width: 220px; height: 220px; border: 36px solid #ffffff04; border-radius: 50%; pointer-events: none; }
.decoration-one { top: -45px; right: -55px; }.decoration-two { top: 27px; right: -112px; }
.intro-panel { display: flex; flex-direction: column; background: #eaf0e5; border: 1px solid #e0e9d9; border-radius: 22px; padding: 22px 26px; position: relative; }
.intro-symbol { position: absolute; right: 23px; top: 22px; width: 34px; height: 34px; display: flex; align-items: center; justify-content: center; font-size: 24px; background: #d1e9b7; color: #45663a; border-radius: 50%; }
.intro-title { font-size: 24px; font-weight: 600; letter-spacing: -.7px; line-height: 1.23; padding-right: 35px; }
.intro-description { display: block; max-width: 290px; color: #74816c; font-size: 12px; line-height: 1.6; margin-top: 12px; }
.intro-footnote { display: flex; align-items: center; gap: 7px; margin-top: auto; padding-top: 17px; font-size: 10px; color: #73826d; }
.small-dot { width: 5px; height: 5px; border-radius: 50%; background: #8ba974; }
.section-heading { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
.section-title { display: block; font-size: 18px; font-weight: 650; letter-spacing: -.4px; }
.section-caption { font-size: 11px; color: #8c9a91; }
.accounts-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; margin-bottom: 26px; }
.account-card { background: #fff; border: 1px solid #e5ebe7; border-radius: 18px; padding: 21px 24px 16px; }
.account-card-heading { display: flex; align-items: center; gap: 12px; }
.account-icon { width: 40px; height: 40px; border-radius: 12px; background: #edf1f7; color: #61748d; font-size: 25px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.savings-icon { background: #f7f0db; color: #ad9050; }
.account-identity { flex: 1; min-width: 0; }
.account-title { display: block; font-size: 13px; font-weight: 600; }
.muted-text { display: block; font-size: 10px; color: #95a198; margin-top: 4px; }
.status-pill { font-size: 9px; color: #4b8d6a; background: #edf7ef; padding: 5px 8px; border-radius: 6px; }
.status-frozen { color: #8b788d; background: #f1eef5; }
.account-amount { display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px; font-size: 28px; font-weight: 600; letter-spacing: -.9px; margin-top: 22px; overflow-wrap: anywhere; }
.amount-currency { font-size: 12px; font-weight: 400; letter-spacing: 0; color: #9ba69e; }
.account-details { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding: 18px 0; }
.account-details > view { display: flex; flex-direction: column; gap: 5px; font-size: 10px; color: #8b9990; }
.detail-value { font-size: 12px; color: #4b6658; font-weight: 500; }
.account-limit { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; border-top: 1px solid #f0f3ef; padding-top: 13px; color: #9ba59e; font-size: 10px; }
.account-limit > text:last-child { color: #728578; }
.workspace-grid { display: grid; grid-template-columns: minmax(0, 1fr); gap: 20px; align-items: start; }
.surface { background: #fff; border: 1px solid #e5ebe7; border-radius: 18px; padding: 25px; }
.panel-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 23px; }
.panel-caption { display: block; font-size: 11px; color: #8d9a91; margin-top: 7px; }
.transfer-symbol { font-size: 25px; color: #689c81; }
.form-field { margin-top: 17px; }
.field-label { display: block; font-size: 11px; font-weight: 500; color: #6d8074; margin-bottom: 8px; }
.select-field { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 13px 15px; border: 1px solid #e6ece7; border-radius: 11px; background: #fafcf9; min-height: 64px; }
.select-title { display: block; font-size: 12px; font-weight: 500; color: #3b5a49; }
.select-description { display: block; font-size: 10px; color: #98a69c; margin-top: 5px; }
.select-chevron { color: #92a396; font-size: 20px; }
.amount-input-wrap { border: 1px solid #dfe7e0; border-radius: 11px; display: flex; align-items: center; gap: 12px; min-height: 59px; padding: 12px 15px; }
.amount-input-wrap:focus-within { border-color: #72a78d; box-shadow: 0 0 0 3px #6b9c7e12; }
.amount-input-wrap > text { font-size: 12px; color: #90a092; }
.amount-input { flex: 1; min-width: 0; height: 33px; font-size: 24px; color: #244f3c; letter-spacing: -.8px; }
.field-hint { display: block; color: #8c9c90; font-size: 10px; line-height: 1.5; margin-top: 8px; min-height: 15px; }
.field-hint-error { color: #ae745b; }
.primary-button { width: 100%; background: #205d49; color: #fff; padding: 15px 20px; font-size: 13px; font-weight: 600; margin-top: 22px; }
.primary-button[disabled] { background: #b9cec0; color: #fff; opacity: .8; }
.transfer-footnote { display: block; margin: 12px auto 0; max-width: 270px; text-align: center; font-size: 9px; line-height: 1.5; color: #99a69b; }
.history-badge { min-width: 25px; height: 25px; padding: 5px 7px; border-radius: 8px; background: #f1f5ef; color: #7e927d; font-size: 11px; text-align: center; }
.account-tabs { display: flex; flex-wrap: wrap; gap: 8px; border-bottom: 1px solid #edf1ed; padding-bottom: 17px; margin-bottom: 1px; }
.account-tab { font-size: 10px; color: #8c9c90; padding: 8px 11px; border-radius: 8px; background: #f5f7f4; border: 1px solid transparent; }
.account-tab-active { color: #3a7553; background: #eef6e9; border-color: #dce9d4; }
.transaction-row { display: flex; align-items: center; gap: 11px; padding: 19px 0; border-bottom: 1px solid #f0f3ef; }
.transaction-row:last-child { border-bottom: 0; }
.transaction-icon { display: flex; align-items: center; justify-content: center; width: 35px; height: 35px; border-radius: 11px; background: #f3f4f1; color: #8a9a87; font-size: 19px; flex-shrink: 0; }
.transaction-incoming { background: #edf7e9; color: #6d9a5b; }
.transaction-content { flex: 1; min-width: 0; }
.transaction-title { display: block; font-size: 11px; font-weight: 500; line-height: 1.5; }
.transaction-date { display: block; color: #a1aca2; font-size: 10px; margin-top: 5px; }
.transaction-amount { font-size: 13px; font-weight: 600; white-space: nowrap; }
.transaction-positive { color: #44855b; }
.transaction-currency { font-size: 9px; font-weight: 400; color: #99a397; }
.history-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; min-height: 280px; color: #9aa69b; font-size: 11px; line-height: 1.7; max-width: 320px; margin: auto; gap: 9px; }
.empty-symbol { width: 59px; height: 59px; margin-bottom: 4px; border-radius: 20px; background: #f1f6ee; font-size: 32px; color: #b1c5a7; display: flex; align-items: center; justify-content: center; }
.empty-title { display: block; font-size: 13px; font-weight: 600; color: #627b62; }
.history-note { display: block; text-align: center; color: #98a393; font-size: 10px; margin-top: 15px; }
.notice { display: flex; flex-direction: column; gap: 5px; padding: 13px 15px; margin-bottom: 18px; font-size: 11px; line-height: 1.65; border-radius: 10px; }
.notice-error { background: #82aed3; border: 1px solid #2334c8; color: #a56d53; }
.notice-success { background: #eef7eb; border: 1px solid #dfedda; color: #5b8051; }
.notice-title { font-weight: 600; }
.text-button { background: transparent; color: inherit; font-size: 11px; align-self: flex-start; padding-top: 5px; text-decoration: underline; }
.loading-panel { display: flex; align-items: center; justify-content: center; min-height: 350px; gap: 15px; color: #829886; font-size: 14px; }
.loader { width: 22px; height: 22px; border: 2px solid #dce9da; border-top-color: #719a70; border-radius: 50%; animation: spin 1s linear infinite; }
.spinning { display: inline-block; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.no-accounts { display: flex; flex-direction: column; gap: 13px; text-align: center; padding: 70px 30px; font-size: 12px; color: #93a08f; }
.page-footer { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; font-size: 9px; color: #a2ada1; margin-top: 30px; }
.connection-state { display: flex; align-items: center; gap: 6px; }
.connection-dot { display: inline-block; width: 5px; height: 5px; border-radius: 50%; background: #7bad77; }
.connection-offline { background: #cb9c7b; }
@media (min-width: 1500px) { .page-content { padding-top: 44px; } }
@media (max-width: 900px) { .topbar-inner { padding: 16px 24px; }.page-content { padding: 30px 24px 24px; }.overview-grid { grid-template-columns: 1.3fr 1fr; gap: 15px; }.balance-panel { padding: 24px; }.intro-panel { padding: 22px; }.intro-title { font-size: 21px; }.intro-description { font-size: 11px; }.workspace-grid { grid-template-columns: 1fr 1.15fr; gap: 15px; }.surface { padding: 21px; }.account-card { padding: 20px; }.transaction-row { gap: 8px; }.transaction-title { font-size: 10px; }.transaction-amount { font-size: 11px; }.transaction-currency { display: block; text-align: right; margin-top: 4px; } }
@media (max-width: 700px) { .topbar-inner { min-height: 68px; padding: 15px 20px; }.brand { font-size: 18px; gap: 10px; }.brand-mark { width: 32px; height: 32px; border-radius: 10px; font-size: 20px; }.profile-label, .avatar { display: none; }.page-content { padding: 27px 18px 22px; }.page-heading { align-items: flex-start; gap: 10px; }.page-title { font-size: 25px; letter-spacing: -.9px; }.eyebrow { font-size: 9px; }.page-description { font-size: 11px; max-width: 220px; line-height: 1.6; }.refresh-button { min-width: 0; font-size: 0; width: 38px; height: 38px; padding: 0; border-radius: 11px; margin-top: 15px; }.refresh-button > text:first-child { font-size: 24px; }.overview-grid { grid-template-columns: 1fr; margin-bottom: 27px; gap: 12px; }.balance-panel { padding: 25px; border-radius: 18px; }.total-balance { font-size: 40px; margin-bottom: 25px; }.breakdown-value { font-size: 16px; }.intro-panel { padding: 17px 20px; border-radius: 15px; }.intro-title { font-size: 17px; padding-right: 35px; }.intro-title br { display: none; }.intro-description { font-size: 11px; margin-top: 8px; max-width: none; padding-right: 15px; }.intro-symbol { top: 15px; right: 17px; width: 29px; height: 29px; font-size: 21px; }.intro-footnote { padding-top: 12px; font-size: 9px; }.accounts-grid { grid-template-columns: 1fr; gap: 12px; margin-bottom: 23px; }.account-card { padding: 19px 20px 15px; border-radius: 16px; }.account-amount { margin-top: 17px; font-size: 27px; }.account-details { padding: 16px 0; }.workspace-grid { grid-template-columns: 1fr; gap: 19px; }.surface { padding: 23px 21px; border-radius: 16px; }.section-title { font-size: 18px; }.history-empty { min-height: 235px; }.transaction-title { font-size: 11px; }.transaction-amount { font-size: 13px; }.transaction-currency { display: inline; font-size: 9px; }.history-panel { padding-bottom: 16px; }.page-footer { font-size: 9px; line-height: 1.6; margin-top: 25px; }.page-footer > text { display: none; } }
@media (max-width: 360px) { .page-content { padding-left: 13px; padding-right: 13px; }.brand { font-size: 16px; }.page-title { font-size: 23px; }.balance-panel { padding: 22px; }.total-balance { font-size: 35px; }.breakdown-value { font-size: 14px; }.balance-breakdown { gap: 12px; }.dot-label { font-size: 10px; }.transaction-currency { display: block; }.surface { padding: 21px 17px; } }
.heading-actions { display: flex; align-items: center; gap: 10px; }
.open-transfer-button { display: flex; justify-content: center; align-items: center; gap: 14px; padding: 12px 18px; border-radius: 11px; background: #205d49; color: #fff; font-size: 12px; font-weight: 600; white-space: nowrap; }
.open-transfer-button > text { font-size: 19px; line-height: 18px; }
.open-transfer-button[disabled] { background: #b9cec0; color: #fff; }
.workspace-grid { grid-template-columns: minmax(0, 1fr); }
.modal-overlay { position: fixed; inset: 0; z-index: 100; display: flex; align-items: center; justify-content: center; padding: 20px; background: rgba(14, 37, 30, .49); backdrop-filter: blur(4px); }
.transfer-dialog { width: 100%; max-width: 480px; max-height: calc(100vh - 40px); max-height: calc(100dvh - 40px); display: flex; flex-direction: column; padding: 0; box-shadow: 0 24px 100px #102f3940; border-radius: 21px; overflow: hidden; }
.transfer-dialog:focus { outline: none; }
.transfer-dialog-heading { flex-shrink: 0; margin: 0; padding: 23px 25px 19px; border-bottom: 1px solid #edf1ed; }
.modal-close { width: 33px; height: 33px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; padding: 0; border-radius: 10px; background: #f1f5ef; color: #758c78; font-size: 25px; font-weight: 400; line-height: 1; }
.modal-close:focus-visible, .open-transfer-button:focus-visible, .transfer-dialog .text-button:focus-visible, .transfer-dialog .primary-button:focus-visible { outline: 2px solid #83b699; outline-offset: 3px; }
.transfer-dialog-body { min-height: 0; padding: 21px 25px 25px; overflow-y: auto; overscroll-behavior: contain; scrollbar-gutter: stable; }
.transfer-dialog-body > .form-field:first-child { margin-top: 0; }
.modal-state-message { display: block; text-align: center; margin-top: 12px; color: #8b9a8e; font-size: 10px; line-height: 1.6; }
.verification-history { border-top: 1px solid #efdace; border-bottom: 1px solid #efdace; margin: 7px 0; }
.verification-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 11px 0; border-bottom: 1px solid #f0ded3; }
.verification-row:last-child { border-bottom: 0; }
.verification-row > view { flex: 1; min-width: 0; }
.verification-amount { font-size: 10px; font-weight: 600; white-space: nowrap; }
.verification-empty { display: block; padding: 10px 0; }
@media (max-width: 700px) { .page-heading { flex-wrap: wrap; }.heading-actions { width: 100%; margin-top: 8px; }.open-transfer-button { flex: 1; min-height: 43px; }.heading-actions .refresh-button { width: 43px; height: 43px; margin-top: 0; }.modal-overlay { padding: 12px; }.transfer-dialog { border-radius: 18px; max-height: calc(100vh - 24px); max-height: calc(100dvh - 24px); }.transfer-dialog-heading { padding: 21px 21px 17px; }.transfer-dialog-body { padding: 20px 21px 23px; } }
</style>
