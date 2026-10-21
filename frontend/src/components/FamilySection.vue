<template>
  <view class="family-section" :class="{ 'family-child': user?.role === 'child' }">
    <view class="family-heading"><view><text class="page-title">Семья</text><text class="page-description">{{ family?.name || 'Ваша экосемья' }} · только общие ресурсы</text></view><button role="button" v-if="family?.is_admin" class="family-primary" :disabled="busy" @click="invite">Пригласить участника семьи</button></view>
    <view v-if="error" class="notice notice-error" role="alert">{{ error }}</view>
    <view v-if="success" class="notice notice-success" role="status">{{ success }}</view>
    <view v-if="invitation" class="surface invitation-panel"><text class="section-title">Приглашение создано</text><text>Передайте этот одноразовый код будущему участнику. Он действует 7 дней.</text><text class="invitation-code" selectable>{{ invitation.token }}</text><text>Участник вводит код в разделе «Семья» под своим профилем. Код не даёт права распоряжаться чужими счетами.</text></view>
    <view v-if="loading && !family" class="loading-panel">Загружаем семью…</view>
    <template v-if="family">
      <view class="surface family-panel"><text class="section-title">Участники семьи</text><view v-for="member in family.members" :key="member.id" class="member-row"><view class="member-main"><view class="member-avatar">{{ member.role === 'child' ? 'С' : displayName(member).slice(0, 1) }}</view><view><text class="member-name">{{ displayName(member) }}</text><text class="member-role">{{ member.role === 'child' ? 'Ребёнок' : 'Взрослый' }}{{ member.id === user?.id && family.is_admin ? ' · администратор' : '' }}</text></view></view><button role="button" v-if="family.is_admin && member.id !== user?.id" class="family-remove" :aria-label="`Удалить участника ${displayName(member)}`" :disabled="busy" @click="removing = member">Удалить участника</button></view></view>
      <view class="family-resources"><view class="surface family-panel"><text class="section-title">Общие счета</text><view v-if="!family.accounts.length" class="family-empty-symbol"><AppIcon name="wallet" :size="27" color="#7181af" /></view><text v-if="!family.accounts.length" class="family-empty">Общих счетов пока нет. Личные счета здесь не отображаются.</text><view v-for="account in family.accounts" :key="account.id" class="shared-card"><text>Общий счёт № {{ account.id }}</text><text class="shared-money">{{ formatMoney(account.balance) }} BYN</text><text>{{ account.active ? 'Активен' : 'Заморожен' }}</text></view></view><view class="surface family-panel"><text class="section-title">Общие копилки</text><view v-if="!family.pigs.length" class="family-empty-symbol"><AppIcon name="pig" :size="29" color="#aa7f69" /></view><text v-if="!family.pigs.length" class="family-empty">Общих копилок пока нет. Копилки отдельных пользователей скрыты.</text><view v-for="pig in family.pigs" :key="pig.id" class="shared-card"><text>{{ pig.name }}</text><text class="shared-money">{{ formatMoney(pig.current_balance) }} BYN</text><text>Цель {{ formatMoney(pig.goal_balance) }} BYN</text></view></view></view>
    </template>
    <view v-if="!family && !loading" class="surface family-panel"><text class="section-title">Есть приглашение?</text><text class="family-empty">Вступить можно только в одну семью. Для ребёнка в ней должен состоять его законный представитель.</text><view class="join-row"><input v-model="inviteCode" class="family-code-input" placeholder="Код приглашения" :disabled="busy" /><button role="button" class="family-primary" :disabled="busy || !inviteCode.trim()" @click="accept">Принять приглашение</button></view></view>
    <view v-if="removing" class="family-overlay"><view role="dialog" aria-modal="true" aria-label="Удаление участника" class="surface family-confirm"><text class="section-title">Удалить {{ displayName(removing) }} из семьи?</text><view v-if="error" class="notice notice-error" role="alert">{{ error }}</view><text>Участник потеряет доступ к ресурсам экосемьи. Его счета, деньги и история сохранятся.</text><view class="join-row"><button role="button" class="family-secondary" :disabled="busy" @click="removing = null">Отмена</button><button role="button" class="family-remove" :disabled="busy" @click="remove">Подтвердить удаление</button></view></view></view>
  </view>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue';
import { api } from '../api/client.js';
import AppIcon from './AppIcon.vue';
import { formatMoney } from '../utils/money.js';
const props = defineProps({ user: { type: Object, default: null }, refreshKey: { type: Number, default: 0 } });
const emit = defineEmits(['changed', 'locked']);
const family = ref(null), loading = ref(false), busy = ref(false), invitation = ref(null), removing = ref(null);
const error = ref(''), success = ref(''), inviteCode = ref('');
let alive = true;
function displayName(member) { return ({ demo_parent: 'Родитель Саши', demo_child: 'Саша', demo_family_parent: 'Другой родитель' })[member.login] || member.login; }
function errorMessage(failure) { return failure?.name === 'ApiError' ? failure.message : 'Не удалось выполнить действие. Обновите данные.'; }
async function reload() {
  if (loading.value || !alive) return;
  loading.value = true;
  try { const result = await api.getFamily(); if (alive) { family.value = result; error.value = ''; } }
  catch (failure) { if (alive) { error.value = errorMessage(failure); if (failure.status === 403) family.value = null; } }
  finally { if (alive) loading.value = false; }
}
async function action(operation, message) {
  if (busy.value) return;
  busy.value = true; error.value = ''; success.value = '';
  try { await operation(); if (alive) { success.value = message; await reload(); emit('changed'); } }
  catch (failure) { if (alive) error.value = errorMessage(failure); }
  finally { if (alive) busy.value = false; }
}
function invite() { return action(async () => { invitation.value = await api.inviteFamily(); }, 'Приглашение готово. Передайте код участнику.'); }
function accept() { return action(async () => { await api.acceptFamilyInvitation(inviteCode.value.trim()); inviteCode.value = ''; }, 'Вы присоединились к семье.'); }
function remove() { const id = removing.value?.id; if (!id) return; return action(async () => { await api.removeFamilyMember(id); removing.value = null; }, 'Участник отключён от семьи. Счета и деньги сохранены.'); }
watch(busy, value => emit('locked', value));
watch(() => props.refreshKey, () => { if (!busy.value) reload(); });
onMounted(reload);
onUnmounted(() => { alive = false; });
</script>

<style scoped>

.family-heading { display:flex;align-items:center;justify-content:space-between;gap:25px;margin-bottom:30px; }
.family-primary { background:#2463eb;color:white;padding:14px 19px;font-size:13px;font-weight:550;min-height:46px; }
.family-secondary { padding:13px 18px;background:#e5e8f2;color:#5a6c9f;font-size:13px;min-height:44px; }
.family-panel,.invitation-panel { margin:22px 0; }
.member-row { display:flex;align-items:center;justify-content:space-between;gap:20px;padding:21px 0;border-bottom:1px solid #e5e8f1; }.member-row:last-child { border:0;padding-bottom:0; }.member-main { display:flex;align-items:center;gap:14px; }.member-avatar { width:43px;height:43px;flex-shrink:0;display:flex;align-items:center;justify-content:center;border-radius:14px;background:#e5e9f3;color:#5d70a4;font-size:16px;font-weight:600; }
.member-name { display:block;font-size:14px;font-weight:550;color:#3a4668; }.member-role { display:block;font-size:11px;color:#7e8db7;margin-top:5px; }
.family-remove { padding:11px 14px;background:#fbf1e8;color:#ac896b;font-size:11px;min-height:40px; }
.family-resources { display:grid;grid-template-columns:1fr 1fr;gap:22px; }.family-resources .family-panel { margin-top:0;min-height:235px; }.family-empty-symbol { display:flex;align-items:center;justify-content:center;width:53px;height:53px;border-radius:16px;background:#e9ecf5;margin-top:25px; }.family-resources .family-panel:last-child .family-empty-symbol { background:#f8ebe5; }.family-empty { display:block;color:#7988b3;font-size:12px;line-height:1.9;margin-top:14px;max-width:350px; }
.shared-card { display:flex;flex-direction:column;gap:10px;padding-top:22px;margin-top:22px;border-top:1px solid #e7eaf1;font-size:13px;color:#6d7ead; }.shared-money { font-size:28px;color:#3c496b;font-weight:650;letter-spacing:-.5px; }
.invitation-panel { display:flex;flex-direction:column;gap:15px;font-size:13px;color:#6d7ead;line-height:1.8;background:#eff2f9; }.invitation-code { user-select:all;overflow-wrap:anywhere;padding:17px;background:#dfe4f1;border:1px dashed #8998c3;border-radius:12px;color:#46557d;font-size:16px;font-family:monospace; }
.join-row { display:flex;gap:12px;flex-wrap:wrap;margin-top:22px; }.family-code-input { flex:1;min-width:180px;height:47px;border:1px solid #d4d9e7;padding:12px 15px;font-size:14px;border-radius:11px; }
.family-overlay { position:fixed;inset:0;z-index:130;background:#141c48aa;backdrop-filter:blur(5px);display:flex;align-items:center;justify-content:center;padding:20px; }.family-confirm { max-width:450px;width:100%;display:flex;flex-direction:column;gap:20px;font-size:13px;line-height:1.9;color:#6d7ead;box-shadow:0 25px 100px #17215b33; }.family-confirm .join-row { justify-content:flex-end;margin-top:5px; }.family-confirm .family-remove { font-size:12px;min-height:44px; }
.family-child .family-panel { border-radius:25px;background:#fef9f7; }.family-child .member-avatar { border-radius:50%;background:#d0d9f0; }.family-child .family-empty-symbol { border-radius:50%;background:#d8dff2; }
@media(max-width:760px) { .family-heading { flex-direction:column;align-items:flex-start;gap:20px; }.family-primary { font-size:12px; }.family-resources { grid-template-columns:1fr;gap:0; }.member-row { gap:12px;align-items:flex-start;flex-wrap:wrap; }.member-main { min-width:160px; }.member-name { font-size:13px; }.family-remove { padding:10px 12px;font-size:10px;margin-left:57px;min-height:37px; }.family-resources .family-panel { min-height:220px; }.family-confirm .family-remove { margin-left:0; }.join-row>button { flex:1; }.family-overlay { padding:14px; } }

</style>
