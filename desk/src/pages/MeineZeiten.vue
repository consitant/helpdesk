<template>
  <div class="flex flex-col flex-1 overflow-hidden">
    <!-- Kopf -->
    <header class="flex items-center justify-between border-b border-outline-gray-2 px-5 py-3 flex-shrink-0">
      <h1 class="text-lg font-semibold text-ink-gray-9">Meine Zeiten</h1>
      <div class="flex items-center gap-3">
        <div class="flex rounded-md border border-outline-gray-2 overflow-hidden text-sm">
          <button
            class="px-3 py-1"
            :class="mode === 'day' ? 'bg-surface-gray-3 font-medium' : 'text-ink-gray-6'"
            @click="setMode('day')"
          >Tag</button>
          <button
            class="px-3 py-1 border-l border-outline-gray-2"
            :class="mode === 'week' ? 'bg-surface-gray-3 font-medium' : 'text-ink-gray-6'"
            @click="setMode('week')"
          >Woche</button>
        </div>
        <div class="flex items-center gap-2">
          <Button variant="ghost" icon="chevron-left" @click="shift(-1)" />
          <span class="text-sm text-ink-gray-8 min-w-[180px] text-center">{{ rangeLabel }}</span>
          <Button variant="ghost" icon="chevron-right" @click="shift(1)" />
          <Button variant="subtle" label="Heute" size="sm" @click="goToday" />
        </div>
      </div>
    </header>

    <!-- Summe -->
    <div class="flex items-center gap-8 px-5 py-3 border-b border-outline-gray-1 flex-shrink-0">
      <div class="flex flex-col">
        <span class="text-xs text-ink-gray-5">Summe {{ mode === 'day' ? 'Tag' : 'Woche' }}</span>
        <span class="text-xl font-semibold text-ink-gray-9">{{ formatHours(data?.total_hours) }} Std.</span>
      </div>
      <div class="flex flex-col">
        <span class="text-xs text-ink-gray-5">Einträge</span>
        <span class="text-xl font-semibold text-ink-gray-9">{{ data?.entries?.length || 0 }}</span>
      </div>
    </div>

    <!-- Liste -->
    <div class="flex-1 overflow-y-auto px-5 py-4">
      <div v-if="resource.loading" class="flex justify-center py-10">
        <Button :loading="true" variant="ghost" size="2xl" />
      </div>
      <div v-else-if="!data?.entries?.length" class="text-sm text-ink-gray-5 py-10 text-center">
        Keine Zeitbuchungen in diesem Zeitraum.
      </div>
      <table v-else class="w-full text-sm">
        <thead>
          <tr class="text-left text-ink-gray-5 border-b border-outline-gray-2">
            <th class="py-2 pr-3 font-medium">Datum</th>
            <th class="py-2 pr-3 font-medium">Von–Bis</th>
            <th class="py-2 pr-3 font-medium text-right">Std.</th>
            <th class="py-2 pr-3 font-medium">Ticket</th>
            <th class="py-2 pr-3 font-medium">Tätigkeit</th>
            <th class="py-2 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in data.entries" :key="row.name" class="border-b border-outline-gray-1 align-top">
            <td class="py-2 pr-3 text-ink-gray-7 whitespace-nowrap">{{ datePart(row.from_time) }}</td>
            <td class="py-2 pr-3 text-ink-gray-7 whitespace-nowrap">{{ timePart(row.from_time) }}–{{ timePart(row.to_time) }}</td>
            <td class="py-2 pr-3 text-right text-ink-gray-8">{{ formatHours(row.hours) }}</td>
            <td class="py-2 pr-3">
              <RouterLink v-if="row.ticket" :to="`/tickets/${row.ticket}`" class="text-ink-gray-9 hover:underline">
                {{ row.ticket }}
              </RouterLink>
              <span v-else class="text-ink-gray-5">—</span>
            </td>
            <td class="py-2 pr-3 text-ink-gray-7">{{ row.activity || row.subject || "—" }}</td>
            <td class="py-2">
              <Badge :theme="row.docstatus === 1 ? 'green' : 'gray'" :label="row.docstatus === 1 ? 'Eingereicht' : 'Entwurf'" size="sm" />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Badge, Button, createResource } from "frappe-ui";
import { computed, ref, watch } from "vue";

type Mode = "day" | "week";
const mode = ref<Mode>("day");
const anchor = ref<Date>(startOfToday());

function startOfToday(): Date {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d;
}
function iso(d: Date): string {
  return d.toISOString().slice(0, 10);
}
function addDays(d: Date, n: number): Date {
  const r = new Date(d);
  r.setDate(r.getDate() + n);
  return r;
}
function startOfWeek(d: Date): Date {
  const r = new Date(d);
  const dow = (r.getDay() + 6) % 7; // Montag = 0
  return addDays(r, -dow);
}

const range = computed(() => {
  if (mode.value === "day") {
    return { from: iso(anchor.value), to: iso(anchor.value) };
  }
  const start = startOfWeek(anchor.value);
  return { from: iso(start), to: iso(addDays(start, 6)) };
});

const rangeLabel = computed(() => {
  if (mode.value === "day") return fmt(anchor.value);
  const start = startOfWeek(anchor.value);
  return `${fmt(start)} – ${fmt(addDays(start, 6))}`;
});

function fmt(d: Date): string {
  return d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
}

const resource = createResource({
  url: "axovend.service.get_my_timesheets",
  makeParams: () => ({ from_date: range.value.from, to_date: range.value.to }),
  auto: true,
});
const data = computed(() => resource.data);

watch(range, () => resource.reload());

function setMode(m: Mode) {
  mode.value = m;
}
function shift(dir: number) {
  anchor.value = addDays(anchor.value, mode.value === "day" ? dir : dir * 7);
}
function goToday() {
  anchor.value = startOfToday();
}

function formatHours(h: any): string {
  return (Number(h) || 0).toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function datePart(dt: string): string {
  if (!dt) return "—";
  const d = String(dt).slice(0, 10).split("-");
  return d.length === 3 ? `${d[2]}.${d[1]}.${d[0]}` : String(dt);
}
function timePart(dt: string): string {
  return dt ? String(dt).slice(11, 16) : "—";
}
</script>
