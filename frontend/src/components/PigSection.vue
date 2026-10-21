<template>
  <view class="pig-section">
    <view class="section-heading">
      <view><text class="section-title">{{ user?.role === 'child' ? 'Мои копилки' : 'Копилки экосемьи' }}</text><text class="panel-caption">На общие мечты может откладывать каждый участник семьи.</text></view>
      <view class="pig-heading-actions"><button role="button" v-if="user?.role === 'child'" class="pig-create" :disabled="locked" @click="open('fund-code', null)">Пополнить по номеру</button><button role="button" v-if="children.length" class="pig-create" :disabled="locked" @click="openCreate">+ Создать копилку</button></view>
    </view>
    <view v-if="error" class="notice notice-error" role="alert"><text>{{ error }}</text><button role="button" class="text-button" :disabled="locked" @click="reload">Обновить копилки</button></view>
    <view v-if="success" class="notice notice-success" role="status"><text>{{ success }}</text></view>
    <view v-if="uncertain" class="notice notice-error" role="alert">
      <text>Результат операции пока неизвестен. Повторная отправка заблокирована.</text>
      <button role="button" v-if="!checked" class="text-button" :disabled="busy || loading" @click="verifyOperation">Обновить копилки и проверить результат</button>
      <template v-else><text>Данные обновлены. Проверьте сумму копилки и состояние запроса ниже.</text><button role="button" class="text-button" @click="acknowledge">Результат проверен — продолжить</button></template>
    </view>
    <view v-if="!loaded && loading" class="pig-empty">Загружаем копилки…</view>
    <view v-else-if="!activePigs.length && !error" class="pig-empty"><text>{{ closedPigs.length ? 'Все копилки разбиты. Можно начать новую цель.' : 'Пока нет копилок. Дайте первой копилке имя и начните копить.' }}</text></view>
    <view class="pig-grid">
      <view v-for="pig in activePigs" :key="pig.id" class="pig-card">
        <view class="pig-card-head"><view class="pig-symbol">◒</view><view class="pig-heading"><text class="pig-name">{{ pig.name }}</text><text class="pig-owner">{{ memberName(pig.child_user_id) }} · копилка № {{ pig.id }}</text></view><button role="button" v-if="canManage(pig)" class="pig-rename" :aria-label="`Переименовать копилку ${pig.name}`" :disabled="locked" @click="open('rename', pig)">✎</button></view>
        <text class="pig-balance">{{ money(pig.current_balance) }} <text>BYN</text></text>
        <view class="pig-progress"><view :style="{ width: progress(pig) + '%' }" /></view>
        <view class="pig-progress-label"><text>{{ progress(pig) }}% цели</text><text>Цель {{ money(pig.goal_balance) }} BYN</text></view>
        <text class="pig-explanation">Эти накопления нельзя потратить. После разбития они вернутся в доступный остаток счёта.</text>
        <view v-if="pig.pending_request_id" class="pig-pending"><text>◷ Запрос на разбитие отправлен родителю</text></view>
        <view class="pig-buttons"><button role="button" class="pig-fund" :disabled="locked || !accounts.some(a => a.active)" @click="open('fund', pig)">Пополнить копилку</button><button role="button" v-if="canManage(pig)" class="pig-break" :disabled="locked || (user?.role === 'child' && !!pig.pending_request_id)" @click="open('break', pig)">Разбить копилку</button></view>
      </view>
    </view>
    <view v-if="requests.length" class="pig-requests surface">
      <text class="section-title">{{ user?.role === 'child' ? 'Мои запросы родителю' : 'Запросы детей' }}</text>
      <view v-for="request in shownRequests" :key="request.id" class="pig-request-row">
        <view class="pig-request-description"><text class="pig-request-name">{{ pigName(request.pig_id) }}</text><text>{{ memberName(request.child_user_id) }} · {{ statusLabel(request.status) }}</text></view>
        <view v-if="request.status === 'pending' && user?.id === request.parent_id" class="pig-request-actions"><button role="button" class="pig-approve" :disabled="locked" @click="open('approve', pigs.find(p => p.id === request.pig_id), request)">Разрешить разбитие</button><button role="button" class="pig-reject" :disabled="locked" @click="resolveRequest(request, 'reject')">Отклонить</button></view>
      </view>
    </view>
    <view v-if="closedPigs.length" class="pig-archive"><text>Разбитые копилки: {{ closedPigs.map(p => p.name).join(', ') }}. Их накопления доступны на счетах-владельцах.</text></view>

    <view v-if="dialog" class="pig-overlay" @click.self="closeDialog">
      <view class="pig-dialog" role="dialog" aria-modal="true" aria-labelledby="pig-dialog-title" @click.stop>
        <view class="pig-dialog-heading"><text id="pig-dialog-title" class="section-title">{{ dialogTitle }}</text><button role="button" class="pig-close" aria-label="Закрыть окно копилки" :disabled="busy" @click="closeDialog">×</button></view>
        <view v-if="actionError" class="notice notice-error" role="alert"><text>{{ actionError }}</text></view>
        <template v-if="dialog === 'create' || dialog === 'rename'">
          <text class="field-label">Название копилки</text><input v-model="nameInput" class="pig-input" aria-label="Название копилки" placeholder="Например, Велосипед" maxlength="100" :focus="true" :disabled="busy" />
        </template>
        <template v-if="dialog === 'create'">
          <view v-if="user?.role === 'parent'" class="form-field"><text class="field-label">Для кого копилка</text><picker :value="childIndex" :range="children.map(c => ({label: memberName(c.id)}))" range-key="label" :disabled="busy" @change="changeChild"><view class="pig-select">{{ memberName(selectedChild?.id) }} ⌄</view></picker></view>
          <view class="form-field"><text class="field-label">Счёт-владелец</text><picker :value="createAccountIndex" :range="createAccounts.map(a => ({label: `Счёт № ${a.id}`}))" range-key="label" :disabled="busy" @change="createAccountId = createAccounts[Number($event.detail.value)]?.id"><view class="pig-select">{{ createAccountId ? `Счёт № ${createAccountId}` : 'Нет связанного счёта' }} ⌄</view></picker></view>
          <view class="form-field"><text class="field-label">Сколько хотите накопить, BYN</text><input v-model="goalInput" class="pig-input" aria-label="Цель копилки в BYN" placeholder="300,00" type="text" inputmode="decimal" :disabled="busy" /></view>
        </template>
        <template v-if="dialog === 'fund' || dialog === 'fund-code'">
          <text class="pig-dialog-note">Пополнить копилку могут все участники экосемьи со своих счетов.</text>
          <view v-if="dialog === 'fund-code'" class="form-field"><text class="field-label">Номер копилки из вашей экосемьи</text><input v-model="pigCodeInput" class="pig-input" placeholder="Например, 500" inputmode="numeric" :disabled="busy" /><text class="pig-dialog-note">Номер можно узнать у владельца. Чужие накопления и список его копилок не раскрываются.</text></view>
          <view class="form-field"><text class="field-label">С какого счёта</text><picker :value="fundAccountIndex" :range="accounts.map(a => ({label: `Счёт № ${a.id} · доступно ${money(a.active_balance)} BYN`}))" range-key="label" :disabled="busy" @change="fundAccountId = accounts[Number($event.detail.value)]?.id"><view class="pig-select">Счёт № {{ fundAccountId }} · {{ fundAccount ? money(fundAccount.active_balance) : '0,00' }} BYN ⌄</view></picker></view>
          <view class="form-field"><text class="field-label">Сумма пополнения, BYN</text><input v-model="amountInput" class="pig-input" aria-label="Сумма пополнения копилки" placeholder="0,00" type="text" inputmode="decimal" :focus="true" :disabled="busy" /></view>
        </template>
        <template v-if="dialog === 'break' || dialog === 'approve'">
          <text class="pig-dialog-note">{{ user?.role === 'child' ? 'Мы отправим запрос вашему назначенному родителю. Пока он не подтвердит разбитие, накопления останутся в копилке.' : `После подтверждения ${money(selectedPig?.current_balance || 0)} BYN станут доступны на счёте № ${selectedPig?.account_id}. Копилка будет закрыта.` }}</text>
        </template>
        <button role="button" class="pig-submit" :disabled="!validAction || busy" :aria-disabled="!validAction || busy" :loading="busy" @click="submitAction">{{ busy ? 'Сохраняем…' : actionLabel }}</button>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, onUnmounted, ref, watch } from 'vue';
import { api } from '../api/client.js';
import { formatMoney, parseMoney } from '../utils/money.js';

const props = defineProps({ user: { type: Object, default: null }, accounts: { type: Array, default: () => [] }, refreshKey: { type: Number, default: 0 }, moneyLocked: { type: Boolean, default: false } });
const emit = defineEmits(['changed', 'locked']);
const pigs = ref([]), requests = ref([]), members = ref([]);
const loading = ref(false), loaded = ref(false), busy = ref(false), uncertain = ref(false), checked = ref(false);
const error = ref(''), success = ref(''), actionError = ref(''), dialog = ref('');
const selectedPig = ref(null), selectedRequest = ref(null);
const nameInput = ref(''), goalInput = ref(''), amountInput = ref('');
const pigCodeInput = ref('');
const childId = ref(null), createAccountId = ref(null), fundAccountId = ref(null);
let alive = true;
const locked = computed(() => busy.value || uncertain.value || props.moneyLocked);
const activePigs = computed(() => pigs.value.filter(p => !p.closed));
const closedPigs = computed(() => pigs.value.filter(p => p.closed));
const children = computed(() => members.value.filter(m => m.role === 'child' && (props.user?.role === 'child' ? m.id === props.user.id : m.parent_id === props.user?.id)));
const selectedChild = computed(() => children.value.find(c => c.id === childId.value));
const childIndex = computed(() => Math.max(0, children.value.findIndex(c => c.id === childId.value)));
const createAccounts = computed(() => props.accounts.filter(a => selectedChild.value?.accounts.includes(a.id)));
const createAccountIndex = computed(() => Math.max(0, createAccounts.value.findIndex(a => a.id === createAccountId.value)));
const fundAccount = computed(() => props.accounts.find(a => a.id === fundAccountId.value));
const fundAccountIndex = computed(() => Math.max(0, props.accounts.findIndex(a => a.id === fundAccountId.value)));
const shownRequests = computed(() => [...requests.value].sort((a, b) => (a.status === 'pending' ? 0 : 1) - (b.status === 'pending' ? 0 : 1) || b.id - a.id).slice(0, 8));
const dialogTitle = computed(() => ({ create: 'Новая копилка', rename: 'Название копилки', fund: `Пополнить «${selectedPig.value?.name || ''}»`, 'fund-code': 'Пополнить семейную копилку', break: props.user?.role === 'child' ? 'Попросить разбить копилку' : 'Разбить копилку', approve: 'Подтвердить разбитие' })[dialog.value] || 'Копилка');
const actionLabel = computed(() => ({ create: 'Создать копилку', rename: 'Сохранить название', fund: 'Пополнить', 'fund-code': 'Пополнить', break: props.user?.role === 'child' ? 'Отправить запрос родителю' : 'Разбить копилку', approve: 'Подтвердить и разбить' })[dialog.value]);
const pigCode = computed(() => /^[1-9][0-9]*$/.test(pigCodeInput.value) && Number.isSafeInteger(Number(pigCodeInput.value)) ? Number(pigCodeInput.value) : null);
const validAction = computed(() => {
  if (uncertain.value || props.moneyLocked) return false;
  if (dialog.value === 'rename') return !!nameInput.value.trim();
  if (dialog.value === 'create') return !!nameInput.value.trim() && parseMoney(goalInput.value) !== null && !!createAccountId.value && !!selectedChild.value;
  if (dialog.value === 'fund' || dialog.value === 'fund-code') { const amount = parseMoney(amountInput.value); return (dialog.value !== 'fund-code' || pigCode.value !== null) && !!fundAccount.value?.active && amount !== null && amount <= fundAccount.value.active_balance; }
  return ['break', 'approve'].includes(dialog.value);
});
function money(value) { return formatMoney(value); }
function memberName(id) { return id === 20 ? 'Саша' : members.value.find(m => m.id === id)?.login || `Участник № ${id ?? '—'}`; }
function pigName(id) { return pigs.value.find(p => p.id === id)?.name || `Копилка № ${id}`; }
function statusLabel(status) { return { pending: 'Ожидает решения родителя', approved: 'Разбитие разрешено', rejected: 'Родитель отклонил запрос' }[status] || status; }
function progress(pig) { return Math.min(100, Math.floor(pig.current_balance / pig.goal_balance * 100)); }
function canManage(pig) { return props.user?.id === pig.child_user_id || props.user?.id === pig.parent_id; }
function message(error) { return error?.name === 'ApiError' ? error.message : 'Не удалось получить данные. Попробуйте обновить.'; }

async function reload() {
  if (!props.user || loading.value || !alive) return false;
  loading.value = true;
  try {
    const [pigData, requestData, memberData] = await Promise.all([api.getPigs(), api.getPigRequests(), api.getFamilyMembers()]);
    if (!alive) return false;
    pigs.value = pigData.items; requests.value = requestData.items; members.value = memberData.items;
    error.value = ''; loaded.value = true;
    return true;
  } catch (failure) { if (alive) error.value = message(failure); return false; }
  finally { if (alive) loading.value = false; }
}
function open(type, pig, request = null) {
  if (locked.value) return;
  dialog.value = type; selectedPig.value = pig; selectedRequest.value = request;
  nameInput.value = pig?.name || ''; amountInput.value = ''; pigCodeInput.value = ''; actionError.value = '';
  fundAccountId.value = props.accounts.find(a => a.active)?.id ?? null;
}
function openCreate() {
  open('create', null);
  goalInput.value = ''; childId.value = children.value[0]?.id ?? null;
  createAccountId.value = createAccounts.value[0]?.id ?? null;
}
function changeChild(event) { childId.value = children.value[Number(event.detail.value)]?.id ?? null; createAccountId.value = createAccounts.value[0]?.id ?? null; }
function closeDialog() { if (!busy.value) dialog.value = ''; }
function isUnknown(failure) { return !failure?.status || failure.status >= 500 || failure.code === 'INVALID_RESPONSE'; }
async function runOperation(operation, doneMessage) {
  if (locked.value) return;
  busy.value = true; actionError.value = ''; success.value = '';
  try {
    await operation();
    if (!alive) return;
    success.value = doneMessage; dialog.value = '';
    const refreshed = await reload();
    if (!refreshed) success.value += ' Операция уже выполнена; обновите данные позже.';
    emit('changed');
  } catch (failure) {
    if (!alive) return;
    if (isUnknown(failure)) { uncertain.value = true; checked.value = false; dialog.value = ''; error.value = 'Не удалось подтвердить результат операции. Проверьте копилки и запросы перед новой попыткой.'; }
    else if (dialog.value) actionError.value = message(failure);
    else error.value = message(failure);
  } finally { if (alive) busy.value = false; }
}
function submitAction() {
  if (!validAction.value || busy.value) return;
  const pig = selectedPig.value;
  if (dialog.value === 'create') return runOperation(() => api.createPig({ account_id: createAccountId.value, child_user_id: childId.value, name: nameInput.value.trim(), goal_balance: parseMoney(goalInput.value) }), 'Копилка создана. Теперь её может пополнять экосемья.');
  if (dialog.value === 'rename') return runOperation(() => api.renamePig(pig.id, nameInput.value.trim()), 'Название копилки сохранено.');
  if (dialog.value === 'fund') return runOperation(() => api.contributePig(pig.id, { account_id: fundAccountId.value, amount: parseMoney(amountInput.value) }), 'Копилка пополнена. Накопления недоступны для обычных трат.');
  if (dialog.value === 'fund-code') return runOperation(() => api.contributePig(pigCode.value, { account_id: fundAccountId.value, amount: parseMoney(amountInput.value) }), 'Взнос в семейную копилку выполнен.');
  if (dialog.value === 'approve') return resolveRequest(selectedRequest.value, 'approve');
  if (dialog.value === 'break') return props.user.role === 'child'
    ? runOperation(() => api.requestPigBreak(pig.id), 'Запрос отправлен вашему родителю. Накопления пока остаются в копилке.')
    : runOperation(() => api.breakPig(pig.id), 'Копилка разбита. Накопления доступны на счёте-владельце.');
}
function resolveRequest(request, decision) { return runOperation(() => api.respondToPigRequest(request.id, decision), decision === 'approve' ? 'Запрос одобрен. Копилка разбита, деньги доступны на счёте-владельце.' : 'Запрос отклонён. Накопления остаются в копилке.'); }
async function verifyOperation() { if (await reload()) { checked.value = true; emit('changed'); } }
function acknowledge() { if (checked.value) { uncertain.value = false; checked.value = false; error.value = ''; } }
function handleEscape(event) { if (event.key === 'Escape') closeDialog(); }
if (typeof document !== 'undefined') document.addEventListener('keydown', handleEscape);
watch(() => locked.value, value => emit('locked', value));
watch([() => props.refreshKey, () => props.user?.id], () => { if (!busy.value) reload(); }, { immediate: true });
onUnmounted(() => { alive = false; if (typeof document !== 'undefined') document.removeEventListener('keydown', handleEscape); });
</script>

<style scoped>
.pig-section { margin: 32px 0; }
.pig-create { background: #e6eee5; color: #315c43; padding: 11px 14px; font-size: 12px; }
.pig-heading-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.pig-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 20px; }
.pig-card { background: #fffdf6; border: 1px solid #ebe5d4; border-radius: 18px; padding: 24px; }
.pig-card-head { display: flex; align-items: center; gap: 12px; }
.pig-symbol { width: 44px; height: 44px; border-radius: 14px; background: #f2e8c8; color: #93783d; display: flex; align-items: center; justify-content: center; font-size: 29px; }
.pig-heading { flex: 1; min-width: 0; }.pig-name { display: block; font-size: 17px; font-weight: 650; overflow-wrap: anywhere; }.pig-owner { display: block; color: #9e9378; font-size: 11px; margin-top: 5px; }
.pig-rename { width: 32px; height: 32px; background: #f8f2e0; color: #8e815f; font-size: 19px; }
.pig-balance { display: block; margin: 25px 0 17px; font-size: 32px; font-weight: 650; letter-spacing: -1px; color: #5a5139; overflow-wrap: anywhere; }.pig-balance > text { font-size: 12px; font-weight: 400; color: #a5997a; letter-spacing: 0; }
.pig-progress { height: 6px; background: #eee8d6; border-radius: 9px; overflow: hidden; }.pig-progress > view { background: #bea45e; height: 100%; border-radius: 9px; transition: width .3s; }
.pig-progress-label { display: flex; justify-content: space-between; gap: 8px; font-size: 10px; color: #9d9275; margin-top: 9px; }.pig-explanation { display: block; font-size: 11px; color: #9b927c; line-height: 1.7; margin-top: 17px; }
.pig-buttons { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 20px; }.pig-fund,.pig-break { padding: 12px 15px; font-size: 11px; }.pig-fund { background: #e8eddc; color: #4b6b3a; flex: 1; }.pig-break { background: #f4ecdb; color: #927942; }
.pig-pending { font-size: 11px; color: #9a7b38; margin-top: 13px; }.pig-empty { padding: 25px; border: 1px dashed #d8decd; border-radius: 15px; color: #829178; font-size: 12px; text-align: center; }
.pig-requests { margin-top: 20px; }.pig-request-row { display: flex; align-items: center; justify-content: space-between; gap: 14px; border-top: 1px solid #edf0e8; margin-top: 16px; padding-top: 16px; }.pig-request-description { display: flex; flex-direction: column; gap: 5px; font-size: 11px; color: #8a9682; }.pig-request-name { font-size: 13px; color: #425a3b; font-weight: 600; }.pig-request-actions { display: flex; flex-wrap: wrap; gap: 8px; }.pig-approve,.pig-reject { font-size: 11px; padding: 10px 12px; }.pig-approve { background: #e6efdf; color: #4c7442; }.pig-reject { color: #9b7e65; background: #faf1e9; }.pig-archive { color: #8d9785; font-size: 11px; line-height: 1.7; margin-top: 14px; }
.pig-overlay { position: fixed; inset: 0; z-index: 120; background: #10261ecc; display: flex; align-items: center; justify-content: center; padding: 20px; backdrop-filter: blur(4px); }.pig-dialog { background: #fff; border-radius: 22px; padding: 26px; width: 100%; max-width: 460px; max-height: 90vh; overflow-y: auto; box-shadow: 0 20px 100px #0003; }.pig-dialog-heading { display: flex; align-items: center; justify-content: space-between; gap: 15px; margin-bottom: 25px; }.pig-close { width: 31px; height: 31px; background: #f1f4ef; color: #7b8a75; font-size: 25px; flex-shrink: 0; }.pig-dialog-note { display: block; color: #7d8977; font-size: 13px; line-height: 1.8; }.pig-input { border: 1px solid #dfe6d9; border-radius: 11px; padding: 14px; font-size: 16px; height: 52px; color: #34532b; }.pig-select { border: 1px solid #e3e8df; background: #f8faf6; padding: 15px; border-radius: 10px; font-size: 12px; color: #6d7f63; }.pig-submit { background: #315f43; color: white; width: 100%; margin-top: 26px; padding: 15px; font-size: 13px; }
@media(max-width:700px) { .pig-grid { grid-template-columns: 1fr; gap: 12px; }.pig-card { padding: 21px; }.pig-section .section-heading { align-items: flex-start; gap: 15px; flex-direction: column; }.pig-request-row { align-items: flex-start; flex-direction: column; }.pig-dialog { padding: 23px; border-radius: 18px; }.pig-overlay { padding: 14px; }.pig-create { font-size: 11px; } }
</style>
