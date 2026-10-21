<template>
  <view class="app-shell" :class="isChild ? 'child-theme' : 'adult-theme'">
    <view class="topbar" :inert="transferOpen ? true : undefined" :aria-hidden="transferOpen ? true : undefined">
      <view class="topbar-inner">
        <view class="brand"><image class="brand-logo" :src="brandLogo" mode="aspectFit" aria-label="Логотип MOBY ОЧАГ" /><view><text class="brand-name">MOBY ОЧАГ</text><text class="brand-caption">{{ isChild ? 'Место, где растут мечты' : 'Финансы, которые объединяют' }}</text></view></view>
        <view class="main-navigation" role="tablist" aria-label="Разделы приложения"><button v-for="tab in navigation" :key="tab.id" role="tab" :aria-selected="activeSection === tab.id" :class="['navigation-tab', { 'navigation-active': activeSection === tab.id }]" :disabled="navigationLocked" @click="openSection(tab.id)"><AppIcon :name="tab.icon" :size="19" :color="activeSection === tab.id ? '#ffce66' : '#949db8'" /><text>{{ tab.label }}</text></button></view>
        <view class="profile-switcher"><text class="demo-label">ДЕМО</text><view class="profile-options"><button role="button" v-for="profile in demoProfiles" :key="profile.id" :class="{ 'profile-selected': demoUserId === profile.id }" :disabled="navigationLocked || refreshing || switching" @click="changeDemoProfile(profile.id)">{{ profile.label }}</button></view></view>
      </view>
    </view>
    <view class="page-content" :inert="transferOpen ? true : undefined" :aria-hidden="transferOpen ? true : undefined">
      <FamilySection v-if="familyOpen" :key="demoUserId" :user="currentUser" :refresh-key="pigRefreshKey" @changed="refreshAll(false)" @locked="familyLocked = $event" />
      <template v-else>
        <view class="page-heading"><view><text class="eyebrow">{{ isChild ? 'ТВОЙ МАЛЕНЬКИЙ БОЛЬШОЙ МИР' : 'ЛИЧНЫЙ КАБИНЕТ' }}</text><text class="page-title">{{ pageTitle }}</text><text class="page-description">{{ pageDescription }}</text></view><view class="heading-actions"><button v-if="!isChild && dashboardTab === 'overview'" ref="transferTrigger" role="button" tabindex="0" class="open-transfer-button" aria-haspopup="dialog" :aria-expanded="transferOpen" :disabled="initialLoading || accounts.length < 2 || pigLocked" @click="openTransfer" @keydown.enter.prevent="openTransfer" @keydown.space.prevent="openTransfer"><AppIcon name="arrow" color="#ffffff" :size="18" /><text>Перевести деньги</text></button><button role="button" aria-label="Обновить данные" class="refresh-button" :disabled="refreshing || posting" @click="refreshAll(false)"><AppIcon name="refresh" :size="18" :class="{ spinning: refreshing }" /></button></view></view>
        <view v-if="loadError" class="notice notice-error" role="alert"><text class="notice-title">Не удалось обновить данные</text><text>{{ loadError }}</text><text v-if="accounts.length">Показаны последние полученные остатки.</text></view>
        <view v-if="initialLoading" class="loading-panel"><view class="loader" /><text>Собираем всё самое важное…</text></view>
        <template v-else-if="accounts.length">
          <view v-show="dashboardTab === 'overview'">
            <view class="overview-grid"><view class="balance-panel"><view class="balance-panel-top"><text class="balance-label">{{ isChild ? 'Можно потратить' : 'Доступно на ваших счетах' }}</text><view class="balance-emblem"><AppIcon name="wallet" :size="22" color="#ccd3e5" /></view></view><view class="balance-number"><text class="total-balance">{{ totals.available }}</text><text class="currency-label">BYN</text></view><view class="balance-breakdown"><view><text class="breakdown-label">{{ isChild ? 'Ждут в копилках' : 'Зарезервировано в копилках' }}</text><text class="breakdown-value">{{ totals.reserved }} BYN</text></view><view><text class="breakdown-label">Всего с накоплениями</text><text class="breakdown-value">{{ totals.balance }} BYN</text></view></view><view class="balance-decoration" /></view>
              <view class="intro-panel"><view class="dream-illustration"><view class="dream-orbit orbit-one" /><view class="dream-orbit orbit-two" /><view class="dream-coin"><AppIcon :name="isChild ? 'spark' : 'pig'" :size="46" color="#425179" /></view><text class="dream-star star-one">✦</text><text class="dream-star star-two">✧</text></view><text class="intro-title">{{ isChild ? 'У каждой мечты есть начало' : 'Большие планы начинаются с малого' }}</text><text class="intro-description">{{ isChild ? 'Придумай мечту, дай копилке имя и собирай на неё вместе с семьёй.' : 'Создавайте копилки для детей и помогайте всей семьёй приближать их цели.' }}</text><button role="button" class="intro-action" :disabled="navigationLocked" @click="openSection('pigs')"><text>{{ isChild ? 'К моим мечтам' : 'Открыть копилки' }}</text><AppIcon name="arrow" :size="17" /></button></view></view>
            <view class="section-heading"><view><text class="section-title">{{ isChild ? 'Твои деньги на каждый день' : 'Ваши счета' }}</text><text class="panel-caption">{{ isChild ? 'Здесь только то, что можно тратить.' : 'Доступные остатки без денег, отложенных в копилки.' }}</text></view><text class="section-caption">{{ accounts.length }} {{ accountCountLabel }}</text></view>
            <view class="accounts-grid" :class="{ 'accounts-grid-single': accounts.length === 1 }"><view v-for="(account, index) in accounts" :key="account.id" class="account-card" :class="{ 'account-frozen': !account.active }"><view class="account-card-heading"><view class="account-icon"><AppIcon name="wallet" :size="23" /></view><view class="account-identity"><text class="account-title">{{ accountName(account, index) }}</text><text class="muted-text">Счёт · {{ account.id }}</text></view><text class="status-pill" :class="{ 'status-frozen': !account.active }">{{ account.active ? 'Активен' : 'Заморожен' }}</text></view><view class="account-amount"><text>{{ money(account.active_balance) }}</text><text class="amount-currency">BYN</text></view><view class="account-limit"><text>Лимит переводов</text><text>{{ account.limit === null ? 'Без ограничений' : `${money(account.limit)} BYN / ${periodLabel(account.limit_period)}` }}</text></view></view></view>
            <view class="quick-links"><button role="button" class="quick-link" :disabled="navigationLocked" @click="openSection('history')"><view class="quick-icon"><AppIcon name="history" :size="23" /></view><view><text class="quick-title">{{ isChild ? 'Куда и откуда?' : 'История операций' }}</text><text class="quick-caption">{{ isChild ? 'Посмотри свои переводы' : 'Все переводы в одном месте' }}</text></view><AppIcon name="arrow" :size="19" /></button><button role="button" class="quick-link" :disabled="navigationLocked" @click="openSection('family')"><view class="quick-icon"><AppIcon name="family" :size="23" /></view><view><text class="quick-title">{{ isChild ? 'Моя команда — семья' : 'Ваша семья' }}</text><text class="quick-caption">{{ isChild ? 'Вместе мечтать веселее' : 'Участники и общие ресурсы' }}</text></view><AppIcon name="arrow" :size="19" /></button></view>
          </view>
          <PigSection v-show="dashboardTab === 'pigs'" :key="currentUser?.id" :user="currentUser" :accounts="accounts" :refresh-key="pigRefreshKey" :money-locked="posting || transferUnknown" @changed="refreshAll(false)" @locked="pigLocked = $event" />
          <view v-show="dashboardTab === 'history'" class="surface history-panel"><view class="panel-heading"><view><text class="section-title">{{ isChild ? 'Твои переводы' : 'История переводов' }}</text><text class="panel-caption">Выберите счёт, чтобы посмотреть его операции</text></view><text class="history-badge">{{ transactions.length }}</text></view><view class="account-tabs"><button role="button" v-for="account in accounts" :key="account.id" class="account-tab" :class="{ 'account-tab-active': historyAccountId === account.id }" :disabled="posting" @click="selectHistoryAccount(account.id)">{{ accountName(account) }}</button></view><view v-if="historyError" class="notice notice-error" role="alert"><text>{{ historyError }}</text><button role="button" class="text-button" :disabled="historyLoading || posting" @click="loadHistory(historyAccountId)">Обновить историю</button></view><view v-if="historyLoading && !transactions.length" class="history-empty"><view class="loader" /><text>Загружаем переводы…</text></view><view v-else-if="!transactions.length && !historyError" class="history-empty"><view class="empty-symbol"><AppIcon name="history" :size="32" /></view><text class="empty-title">Пока ни одного перевода</text><text>Когда деньги придут или уйдут, операция появится здесь.</text></view><view v-else class="transaction-list"><view v-for="transaction in transactions" :key="transaction.id" class="transaction-row"><view class="transaction-icon" :class="{ 'transaction-incoming': transaction.recipient === historyAccountId }">{{ transaction.recipient === historyAccountId ? '↙' : '↗' }}</view><view class="transaction-content"><text class="transaction-title">{{ transactionTitle(transaction) }}</text><text class="transaction-date">{{ dateLabel(transaction.data) }}</text></view><text class="transaction-amount" :class="{ 'transaction-positive': transaction.recipient === historyAccountId }">{{ transaction.recipient === historyAccountId ? '+' : '−' }}{{ money(transaction.amount) }}<text class="transaction-currency"> BYN</text></text></view></view><text v-if="transactions.length === 50" class="history-note">Показаны последние 50 переводов.</text></view>
        </template>
        <view v-else-if="!loadError" class="surface no-accounts"><text class="empty-title">Пока нет доступных счетов</text><text>Ваши счета появятся здесь после подключения.</text></view>
      </template>
      <view class="page-footer"><view class="connection-state"><text class="connection-dot" :class="{ 'connection-offline': loadError }" /><text>{{ loadError ? 'Данные временно недоступны' : lastUpdated ? `Обновлено ${lastUpdated}` : 'Подключаемся' }}</text></view><text>Демонстрация · без реальных денег</text></view>
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
import FamilySection from '../../components/FamilySection.vue';
import AppIcon from '../../components/AppIcon.vue';
import brandLogo from './img.png';

const currentUser = ref(null);
const familyOpen = ref(false);
const dashboardTab = ref('overview');
const isChild = computed(() => demoUserId.value === 20);
const activeSection = computed(() => familyOpen.value ? 'family' : dashboardTab.value);
const navigationLocked = computed(() => posting.value || pigLocked.value || familyLocked.value || transferUnknown.value || switching.value);
const navigation = computed(() => [
  {id:'overview', label:isChild.value ? 'Мои деньги' : 'Обзор', icon:'home'},
  {id:'pigs', label:isChild.value ? 'Мои мечты' : 'Копилки', icon:'pig'},
  {id:'history', label:'История', icon:'history'},
  {id:'family', label:'Семья', icon:'family'},
]);
const pageTitle = computed(() => dashboardTab.value === 'pigs' ? (isChild.value ? 'Мечтай. Копи. Повторяй ✦' : 'Ближе к большим планам') : dashboardTab.value === 'history' ? (isChild.value ? 'История твоих денег' : 'Каждый перевод под контролем') : isChild.value ? 'Привет, Саша! ✦' : 'Всё важное — рядом');
const pageDescription = computed(() => dashboardTab.value === 'pigs' ? (isChild.value ? 'Маленькие шаги к тому, чего тебе хочется.' : 'Накопления детей и запросы на разбитие копилок.') : dashboardTab.value === 'history' ? 'Поступления и переводы по вашим счетам.' : isChild.value ? 'Твои деньги сегодня. Твои мечты на завтра.' : 'Управляйте деньгами и заботьтесь о будущем семьи.');
function openSection(section) {
  if (navigationLocked.value) return;
  familyOpen.value = section === 'family';
  if (section !== 'family') dashboardTab.value = section;
}

const familyLocked = ref(false);
const pigRefreshKey = ref(0);
const pigLocked = ref(false);
const switching = ref(false);
const demoUserId = ref(getDemoUserId());
const demoProfiles = [{ id: 10, label: 'Родитель' }, { id: 20, label: 'Ребёнок' }];
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
  if (id === demoUserId.value || posting.value || pigLocked.value || familyLocked.value || transferUnknown.value || refreshing.value || switching.value) return;
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

page { background:#f4f6fb;color:#20274b;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
view,text,button,input { box-sizing:border-box; }
button { margin:0;padding:0;font:inherit;line-height:1.4;border-radius:12px;cursor:pointer; }
button::after { border:0; }
button[disabled],button[aria-disabled="true"] { opacity:.45;cursor:not-allowed; }
button:focus-visible,[role="tab"]:focus-visible { outline:3px solid #6a7fb9;outline-offset:4px; }
.app-shell { min-height:100vh;background:#f4f6fb; }
.topbar { background:#20256b;color:white;position:sticky;top:0;z-index:30;box-shadow:0 3px 16px #17215b0c; }
.topbar-inner { max-width:1240px;margin:auto;padding:18px 36px;display:flex;align-items:center;justify-content:space-between;gap:28px; }
.brand { display:flex;align-items:center;gap:12px;flex-shrink:0; }.brand-logo { width:46px;height:46px;display:block;border-radius:14px;overflow:hidden; }.brand-name { display:block;font-size:18px;font-weight:750;letter-spacing:.4px; }.brand-caption { display:block;font-size:10px;color:#949db8;margin-top:4px; }
.main-navigation { display:flex;gap:5px;align-items:center; }.navigation-tab { display:flex;align-items:center;justify-content:center;gap:8px;padding:13px 15px;background:transparent;color:#949db8;font-size:13px;white-space:nowrap;transition:background .18s; }.navigation-tab:hover { background:#ffffff0b; }.navigation-tab.navigation-active { color:#ffffff;background:#ffffff13;box-shadow:inset 0 -2px 0 #ffce66;border-radius:10px 10px 4px 4px; }
.profile-switcher { display:flex;flex-direction:column;align-items:flex-end;gap:6px; }.demo-label { font-size:8px;letter-spacing:1.5px;color:#949db8; }.profile-options { display:flex;padding:3px;border-radius:9px;background:#ffffff09;border:1px solid #ffffff16; }.profile-options>button { font-size:10px;padding:7px 10px;color:#949db8;background:transparent;border-radius:6px; }.profile-options>button.profile-selected { background:#e7edff;color:#2c4083;font-weight:600; }
.page-content { max-width:1160px;margin:auto;padding:42px 36px 24px; }
.page-heading { display:flex;align-items:center;justify-content:space-between;gap:24px;margin-bottom:30px; }.eyebrow { display:block;font-size:10px;font-weight:650;letter-spacing:1.7px;color:#7283b0;margin-bottom:12px; }.page-title { display:block;font-size:34px;line-height:1.2;font-weight:700;letter-spacing:-1.1px;color:#20274b; }.page-description { display:block;font-size:13px;line-height:1.7;color:#6274a6;margin-top:10px; }.heading-actions { display:flex;gap:10px;align-items:center;flex-shrink:0; }
.open-transfer-button { display:flex;align-items:center;justify-content:center;gap:10px;padding:14px 19px;min-height:46px;background:#2463eb;color:white;font-size:13px;font-weight:600;box-shadow:0 4px 12px #2463eb1a; }.open-transfer-button:hover { background:#194fc9; }.refresh-button { display:flex;align-items:center;justify-content:center;width:46px;height:46px;background:white;border:1px solid #d9dde9;border-radius:12px; }
.overview-grid { display:grid;grid-template-columns:1.35fr 1fr;gap:22px;margin-bottom:36px; }.balance-panel { background:#3035b6;border-radius:22px;position:relative;overflow:hidden;color:white;padding:28px 32px;min-height:280px; }.balance-panel-top { display:flex;align-items:center;justify-content:space-between;position:relative;z-index:1; }.balance-label { font-size:14px;color:#d0d5e3; }.balance-emblem { display:flex;align-items:center;justify-content:center;width:39px;height:39px;border:1px solid #ffffff25;background:#ffffff08;border-radius:12px; }.balance-number { display:flex;align-items:baseline;gap:12px;margin:10px 0 32px;position:relative;z-index:1; }.total-balance { font-size:clamp(30px,4vw,50px);line-height:1.2;font-weight:650;letter-spacing:-1.9px;overflow-wrap:anywhere;min-width:0; }.currency-label { font-size:16px;color:#929cba; }
.balance-breakdown { display:grid;grid-template-columns:1fr 1fr;gap:18px;position:relative;z-index:1;border-top:1px solid #ffffff1c;padding-top:20px; }.breakdown-label { display:block;font-size:11px;line-height:1.5;color:#8f9bbd; }.breakdown-value { display:block;font-size:16px;font-weight:550;margin-top:7px;overflow-wrap:anywhere; }.balance-decoration { position:absolute;width:280px;height:280px;border:45px solid #ffffff04;border-radius:50%;top:-30px;right:-90px;pointer-events:none; }
.intro-panel { background:#e5e8f0;border:1px solid #d7dce8;border-radius:22px;padding:25px 28px;position:relative;overflow:hidden;display:flex;flex-direction:column;align-items:flex-start; }.intro-title { display:block;font-size:23px;line-height:1.25;letter-spacing:-.5px;font-weight:650;max-width:250px;margin-top:4px;position:relative;z-index:1; }.intro-description { display:block;color:#5a6da0;font-size:12px;line-height:1.8;max-width:290px;margin:12px 0 19px;position:relative;z-index:1; }.intro-action { margin-top:auto;display:flex;align-items:center;gap:10px;color:#3a4666;font-size:12px;font-weight:600;background:#d2d8e9;border-radius:10px;padding:11px 14px;position:relative;z-index:1; }
.dream-illustration { position:absolute;width:180px;height:180px;right:-46px;bottom:-36px;pointer-events:none;opacity:.6; }.dream-orbit { position:absolute;border:1px solid #8f9bbc60;border-radius:50%;inset:8px; }.orbit-two { inset:26px; }.dream-coin { position:absolute;inset:48px;display:flex;align-items:center;justify-content:center;border-radius:50%;background:#7d93cf;box-shadow:0 0 0 10px #cad3ea80; }.dream-star { position:absolute;font-size:25px;color:#57699b; }.star-one { top:15px;left:25px; }.star-two { bottom:20px;right:28px;font-size:34px; }
.section-heading { display:flex;align-items:center;justify-content:space-between;gap:20px;margin-bottom:18px; }.section-title { display:block;font-size:20px;font-weight:650;letter-spacing:-.4px;color:#29324a; }.section-caption { font-size:11px;color:#7787b2;border:1px solid #d7dce8;background:#e8ebf2;padding:6px 10px;border-radius:8px;white-space:nowrap; }.panel-caption { display:block;font-size:12px;line-height:1.6;color:#6e7fad;margin-top:6px; }
.accounts-grid { display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px;margin-bottom:24px; }.account-card { background:white;border:1px solid #d8dde9;border-radius:17px;padding:23px 25px 18px;box-shadow:0 3px 10px #17215b08; }.account-card-heading { display:flex;align-items:center;gap:12px; }.account-icon { width:42px;height:42px;display:flex;align-items:center;justify-content:center;background:#e7eaf2;border-radius:12px;flex-shrink:0; }.account-identity { flex:1;min-width:0; }.account-title { display:block;font-size:14px;font-weight:600;color:#35405f; }.muted-text { display:block;font-size:11px;color:#808eb7;margin-top:4px; }.status-pill { font-size:10px;color:#516290;background:#e8ebf5;padding:5px 9px;border-radius:6px; }.status-frozen { color:#917684;background:#f4edf0; }.account-amount { display:flex;align-items:baseline;gap:8px;font-size:31px;font-weight:650;letter-spacing:-.8px;margin:24px 0 22px;color:#29324a;overflow-wrap:anywhere; }.amount-currency { font-size:13px;color:#7b8bb5;font-weight:400;letter-spacing:0; }.account-limit { display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;border-top:1px solid #e7eaf1;padding-top:14px;font-size:11px;color:#7b8ab4; }.account-limit>text:last-child { color:#526493; }
.accounts-grid-single { grid-template-columns:1fr; }
.child-theme .account-card { display:grid;grid-template-columns:1fr auto;gap:0 24px; }.child-theme .account-amount { grid-column:2;grid-row:1;margin:0;align-self:center; }.child-theme .account-limit { grid-column:1 / -1;margin-top:20px; }
.quick-links { display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:4px; }.quick-link { width:100%;display:flex;align-items:center;gap:15px;text-align:left;background:#e8eaf1;border:1px solid #d7dce8;border-radius:15px;padding:17px 20px; }.quick-link>view:nth-child(2) { flex:1; }.quick-icon { display:flex;align-items:center;justify-content:center;width:38px;height:38px;background:#ffffffa0;border-radius:11px; }.quick-title { display:block;font-size:13px;font-weight:600;color:#3c496b; }.quick-caption { display:block;font-size:11px;color:#6d7ead;margin-top:5px; }
.surface { background:white;border:1px solid #d8dde9;border-radius:18px;padding:26px; }.panel-heading { display:flex;align-items:center;justify-content:space-between;gap:15px;margin-bottom:22px; }.history-badge { display:flex;align-items:center;justify-content:center;min-width:30px;height:30px;border-radius:9px;font-size:12px;color:#566798;background:#e8ebf3; }.account-tabs { display:flex;flex-wrap:wrap;gap:8px;padding-bottom:20px;border-bottom:1px solid #e2e5ee; }.account-tab { padding:10px 14px;font-size:12px;color:#6b7cab;background:#f0f1f6;border:1px solid transparent;border-radius:9px; }.account-tab-active { color:#3b496e;background:#e0e5f1;border-color:#c9d0e4;font-weight:600; }.transaction-row { display:flex;align-items:center;gap:14px;padding:20px 0;border-bottom:1px solid #e7eaf1; }.transaction-row:last-child { border:0; }.transaction-icon { display:flex;align-items:center;justify-content:center;width:42px;height:42px;flex-shrink:0;background:#ebedf3;color:#6476a8;font-size:22px;border-radius:13px; }.transaction-incoming { background:#e4e9f6;color:#546595; }.transaction-content { flex:1;min-width:0; }.transaction-title { display:block;font-size:13px;font-weight:500;line-height:1.6; }.transaction-date { display:block;color:#8392ba;font-size:11px;margin-top:4px; }.transaction-amount { font-size:16px;font-weight:600;white-space:nowrap; }.transaction-positive { color:#435587; }.transaction-currency { color:#8594bb;font-size:10px;font-weight:400; }.history-empty { display:flex;flex-direction:column;align-items:center;justify-content:center;gap:11px;min-height:270px;max-width:330px;margin:auto;text-align:center;color:#7080ae;font-size:13px;line-height:1.8; }.empty-symbol { width:68px;height:68px;display:flex;align-items:center;justify-content:center;background:#e9ecf5;border-radius:21px;margin-bottom:4px; }.empty-title { font-size:16px;font-weight:600;color:#4a5a84; }.history-note { display:block;text-align:center;color:#7988b3;font-size:11px;margin-top:20px; }
.notice { display:flex;flex-direction:column;gap:5px;padding:15px 18px;border-radius:12px;font-size:12px;line-height:1.7;margin-bottom:20px; }.notice-error { background:#fbf0e8;color:#9b7359;border:1px solid #f1dfcf; }.notice-success { background:#e5e9f5;color:#4c5b86;border:1px solid #d0d7e9; }.notice-title { font-weight:650; }.text-button { align-self:flex-start;background:transparent;color:inherit;font-size:12px;padding:7px 0;text-decoration:underline;text-underline-offset:3px; }.loading-panel { min-height:320px;display:flex;align-items:center;justify-content:center;gap:14px;color:#6577a8;font-size:14px; }.loader { width:22px;height:22px;border-radius:50%;border:2px solid #d0d6e6;border-top-color:#566899;animation:spin 1s linear infinite; }.spinning { animation:spin 1s linear infinite; }@keyframes spin { to { transform:rotate(360deg); } }.no-accounts { display:flex;flex-direction:column;gap:12px;align-items:center;text-align:center;padding:65px 25px;color:#7484b1;font-size:13px; }
.page-footer { display:flex;justify-content:space-between;gap:15px;flex-wrap:wrap;font-size:10px;color:#8694bb;margin-top:32px;padding-top:17px;border-top:1px solid #dde1ec; }.connection-state { display:flex;align-items:center;gap:7px; }.connection-dot { width:5px;height:5px;border-radius:50%;background:#6f80ae; }.connection-offline { background:#b99071; }
.modal-overlay { position:fixed;inset:0;z-index:100;display:flex;align-items:center;justify-content:center;padding:20px;background:#141c48aa;backdrop-filter:blur(5px); }.transfer-dialog { width:100%;max-width:470px;max-height:calc(100dvh - 40px);padding:0;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 25px 100px #17215b33;border-radius:22px; }.transfer-dialog:focus { outline:none; }.transfer-dialog-heading { padding:25px 26px 20px;border-bottom:1px solid #e7eaf1;margin:0;flex-shrink:0; }.modal-close { width:34px;height:34px;display:flex;align-items:center;justify-content:center;background:#ebeef5;color:#6b7cac;border-radius:10px;font-size:25px; }.transfer-dialog-body { padding:23px 26px 27px;overflow:auto;min-height:0;overscroll-behavior:contain; }.form-field { margin-top:19px; }.field-label { display:block;margin-bottom:8px;font-size:12px;color:#50618f;font-weight:550; }.select-field { display:flex;align-items:center;justify-content:space-between;padding:14px 16px;border:1px solid #d8dce8;background:#f5f7fb;border-radius:11px;min-height:66px; }.select-title { display:block;color:#394566;font-size:13px; }.select-description { display:block;color:#808eb7;font-size:11px;margin-top:5px; }.select-chevron { color:#7080ae;font-size:22px; }.amount-input-wrap { display:flex;align-items:center;gap:15px;border:1px solid #d1d6e5;border-radius:11px;padding:12px 16px; }.amount-input-wrap:focus-within { border-color:#7082b5;box-shadow:0 0 0 3px #c8d1eb40; }.amount-input { flex:1;min-width:0;height:40px;font-size:26px;color:#2e3b5e; }.amount-input-wrap>text { color:#7081af;font-size:13px; }.field-hint { display:block;line-height:1.6;color:#7787b2;font-size:11px;margin-top:8px; }.field-hint-error { color:#ac8060; }.primary-button { display:block;width:100%;background:#2463eb;color:white;font-size:14px;font-weight:600;padding:15px 20px;margin-top:24px; }.primary-button[disabled] { background:#8f9bbc; }.transfer-footnote,.modal-state-message { display:block;color:#7e8db6;text-align:center;font-size:11px;line-height:1.7;margin-top:12px; }.verification-history { border-top:1px solid #ecd9c8;border-bottom:1px solid #ecd9c8; }.verification-row { display:flex;justify-content:space-between;gap:12px;padding:12px 0; }.verification-amount { font-size:11px;white-space:nowrap; }.verification-empty { padding:12px 0;font-size:12px; }
/* The child area uses the same palette with warmer surfaces and playful shapes. */
.child-theme { background:linear-gradient(160deg,#edf3ff 0%,#fff7ee 70%); }.child-theme .brand-logo { border-radius:50%;box-shadow:0 0 0 3px #ffce6625; }.child-theme .page-title { font-size:36px;letter-spacing:-1.2px;color:#293f83; }.child-theme .eyebrow { color:#697bab; }.child-theme .balance-panel { border-radius:30px;background:#3856c5;box-shadow:0 8px 0 #ccd4e9; }.child-theme .balance-label { font-size:17px;color:#d5dcf0;font-weight:600; }.child-theme .total-balance { font-size:55px;color:#fff0c7; }.child-theme .balance-breakdown { border-top-style:dashed; }.child-theme .intro-panel { border-radius:30px;background:#edf0ff;border-color:#c9d1e8;padding-bottom:29px; }.child-theme .intro-title { max-width:240px;font-size:27px;color:#394d94; }.child-theme .intro-description { max-width:230px;color:#6073a6;font-size:13px; }.child-theme .dream-illustration { opacity:1;right:-30px;bottom:-17px;transform:rotate(-12deg); }.child-theme .intro-action { background:#d7e3ff;border-radius:14px;padding:13px 17px; }.child-theme .account-card { border-radius:24px;border:2px solid #d8ddea;background:#ffffff; }.child-theme .account-icon { border-radius:50%;background:#d2daf0;width:47px;height:47px; }.child-theme .quick-link { border-radius:22px;background:#dfe4f2;padding:20px;border:1px solid #ced5e8; }.child-theme .quick-icon { border-radius:50%;background:#eef1fb; }.child-theme .surface { border-radius:24px; }.child-theme .navigation-active { color:#ffffff; }
@media(min-width:1400px) { .page-content { padding-top:50px; } }
@media(max-width:1050px) { .topbar-inner { gap:15px;padding:16px 25px; }.brand-caption { display:none; }.brand-name { font-size:16px; }.brand-logo { width:39px;height:39px; }.navigation-tab { padding:12px 10px;font-size:12px;gap:6px; }.profile-options>button { padding:6px 8px; }.page-content { padding:32px 25px 22px; } }
@media(max-width:760px) { .topbar-inner { flex-wrap:wrap;padding:14px 19px 0;gap:16px; }.brand { flex:1; }.brand-name { font-size:16px; }.brand-logo { width:37px;height:37px; }.profile-switcher { margin-left:auto; }.demo-label { font-size:7px; }.profile-options>button { padding:6px 8px;font-size:9px; }.main-navigation { order:3;width:100%;gap:0;justify-content:space-between; }.navigation-tab { flex:1;padding:13px 4px 15px;flex-direction:column;gap:5px;font-size:10px;border-radius:8px 8px 0 0; }.page-content { padding:27px 18px 20px; }.page-heading { gap:14px;align-items:flex-start;margin-bottom:23px;flex-wrap:wrap; }.eyebrow { font-size:8px;letter-spacing:1.3px;margin-bottom:10px; }.page-title,.child-theme .page-title { font-size:28px;letter-spacing:-.8px; }.page-description { font-size:12px;max-width:310px; }.heading-actions { margin-top:3px; }.open-transfer-button { min-height:43px;padding:12px 15px;font-size:12px; }.refresh-button { width:43px;height:43px; }.overview-grid { grid-template-columns:1fr;gap:18px;margin-bottom:31px; }.balance-panel { padding:24px 25px;min-height:247px;border-radius:22px; }.total-balance,.child-theme .total-balance { font-size:46px; }.balance-number { margin-bottom:25px; }.balance-breakdown { padding-top:18px; }.breakdown-label { font-size:10px; }.breakdown-value { font-size:15px; }.intro-panel { min-height:195px;padding:22px 24px; }.intro-title { max-width:240px;font-size:22px; }.intro-description { max-width:250px;font-size:12px;margin-bottom:16px; }.dream-illustration { width:170px;height:170px;right:-30px;bottom:-26px; }.child-theme .intro-title { font-size:24px; }.child-theme .intro-panel { min-height:219px; }.child-theme .dream-illustration { right:-39px; }.accounts-grid { grid-template-columns:1fr;gap:13px;margin-bottom:17px; }.account-card { padding:21px 22px 17px; }.account-amount { font-size:30px;margin:21px 0; }.section-title { font-size:18px; }.panel-caption { font-size:11px; }.section-heading { gap:10px;align-items:flex-start; }.section-caption { font-size:10px; }.quick-links { grid-template-columns:1fr;gap:12px; }.quick-link { padding:17px 20px; }.surface { padding:22px; }.transaction-row { gap:10px; }.transaction-title { font-size:12px; }.transaction-amount { font-size:14px; }.transaction-currency { display:block;text-align:right;font-size:9px; }.account-tabs { gap:6px; }.account-tab { font-size:11px;padding:10px 12px; }.modal-overlay { padding:12px; }.transfer-dialog { padding:0;max-height:calc(100dvh - 24px); }.transfer-dialog-heading { padding:22px; }.transfer-dialog-body { padding:20px 22px 24px; }.page-footer { font-size:9px;gap:10px;margin-top:27px; } }
@media(max-width:760px) { .child-theme .account-card { display:block; }.child-theme .account-amount { margin:21px 0; }.child-theme .account-limit { margin-top:0; } }
@media(prefers-reduced-motion:reduce) { *,*::before,*::after { animation-duration:.01ms!important;transition:none!important; } }

</style>
