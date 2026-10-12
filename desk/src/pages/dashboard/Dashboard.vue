<template>
  <!-- axovend (TG §85): Agenten-Performance. Daten: axovend.helpdesk_dashboard.get_dashboard -->
  <div class="flex flex-col flex-1 overflow-hidden">
    <LayoutHeader>
      <template #left-header>
        <div class="text-lg font-medium text-ink-gray-9">
          {{ data?.ist_leitung ? "Dashboard – Agenten-Performance" : "Mein Dashboard" }}
        </div>
      </template>
    </LayoutHeader>

    <div class="flex-1 overflow-y-auto p-4 sm:p-5">
      <!-- Filter -->
      <div class="mb-4 flex flex-wrap items-center gap-2">
        <div class="flex rounded-md border border-outline-gray-2 overflow-hidden text-sm">
          <button
            v-for="(p, i) in presets"
            :key="p.value"
            class="px-2.5 py-1"
            :class="[
              i > 0 ? 'border-l border-outline-gray-2' : '',
              preset === p.value ? 'bg-surface-gray-3 font-medium text-ink-gray-9' : 'text-ink-gray-6',
            ]"
            @click="setPreset(p.value)"
          >
            {{ p.label }}
          </button>
        </div>
        <div class="flex items-center gap-1">
          <Button variant="ghost" icon="chevron-left" :disabled="preset === 'frei'" @click="shift(-1)" />
          <span class="text-sm text-ink-gray-8 min-w-[150px] text-center">{{ rangeLabel }}</span>
          <Button variant="ghost" icon="chevron-right" :disabled="preset === 'frei'" @click="shift(1)" />
        </div>
        <template v-if="preset === 'frei'">
          <FormControl type="date" v-model="fromDate" class="w-36" />
          <span class="text-ink-gray-5">–</span>
          <FormControl type="date" v-model="toDate" class="w-36" />
        </template>
        <FormControl
          v-if="(data?.teams?.length || 0) > 1"
          type="select"
          class="w-40"
          v-model="team"
          :options="[{ label: 'Alle Teams', value: '' }, ...(data?.teams || []).map((t) => ({ label: t, value: t }))]"
        />
        <FormControl
          v-if="data?.ist_leitung"
          type="select"
          class="w-48"
          v-model="agent"
          :options="[{ label: 'Alle Agenten', value: '' }, ...(data?.agenten || [])]"
        />
        <Button v-if="resource.loading" :loading="true" variant="ghost" />
      </div>

      <div v-if="resource.error" class="text-sm text-ink-red-4 py-6">
        {{ resource.error?.messages?.[0] || resource.error }}
      </div>

      <template v-if="data">
        <!-- Kacheln -->
        <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3 mb-4">
          <div
            v-for="k in kacheln"
            :key="k.titel"
            class="border border-outline-gray-2 rounded-md p-3 flex flex-col gap-1"
            :class="k.link ? 'cursor-pointer hover:bg-surface-gray-1' : ''"
            :title="k.hilfe"
            @click="k.link && openTickets(k.link)"
          >
            <span class="text-xs text-ink-gray-5">{{ k.titel }}</span>
            <span class="text-2xl font-semibold text-ink-gray-9">{{ k.wert }}</span>
            <span class="text-xs text-ink-gray-5">{{ k.sub }}</span>
          </div>
        </div>

        <!-- Agenten-Tabelle -->
        <div class="border border-outline-gray-2 rounded-md mb-4">
          <div class="flex items-center justify-between px-3 py-2 border-b border-outline-gray-2">
            <span class="text-base font-medium text-ink-gray-9">
              {{ data.ist_leitung ? "Agenten" : "Meine Kennzahlen und Team-Summe" }}
            </span>
            <span class="text-xs text-ink-gray-5 hidden sm:inline">
              Zeiten in Stunden Geschäftszeit · Klick auf eine Zahl öffnet die Tickets
            </span>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-sm whitespace-nowrap">
              <thead>
                <tr class="text-left text-ink-gray-5 border-b border-outline-gray-2">
                  <th
                    v-for="c in spalten"
                    :key="c.key"
                    class="py-2 px-3 font-medium select-none cursor-pointer hover:text-ink-gray-8"
                    :class="c.key === 'agent_name' ? 'sticky left-0 bg-surface-white z-10' : 'text-right'"
                    :title="c.hilfe"
                    @click="sortiere(c.key)"
                  >
                    {{ c.label }}
                    <span v-if="sortKey === c.key">{{ sortAsc ? "▲" : "▼" }}</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="z in sortierteZeilen"
                  :key="z.agent"
                  class="border-b border-outline-gray-1 hover:bg-surface-gray-1"
                >
                  <td class="py-2 px-3 sticky left-0 bg-surface-white z-10 text-ink-gray-9 font-medium">
                    {{ z.agent_name }}
                  </td>
                  <td class="py-2 px-3 text-right">
                    <a class="zahl" @click="openTickets(offenFilter(z.agent))">{{ z.offen }}</a>
                    <span v-if="z.wartend" class="text-ink-gray-5 text-xs"> ({{ z.wartend }} wartend)</span>
                  </td>
                  <td class="py-2 px-3 text-right">
                    <a class="zahl" :class="z.ueberfaellig ? 'text-ink-red-4' : ''" @click="openTickets(ueberfaelligFilter(z.agent))">{{ z.ueberfaellig }}</a>
                  </td>
                  <td class="py-2 px-3 text-right text-ink-gray-7">{{ z.sla_verletzt_offen }}</td>
                  <td class="py-2 px-3 text-right text-ink-gray-7">{{ z.neu_zugewiesen }}</td>
                  <td class="py-2 px-3 text-right">
                    <a class="zahl" @click="openTickets(geloestFilter(z.agent))">{{ z.geloest }}</a>
                  </td>
                  <td class="py-2 px-3 text-right text-ink-gray-7">{{ zeit(z.fr_avg_h, z.fr_median_h, z.fr_n) }}</td>
                  <td class="py-2 px-3 text-right text-ink-gray-7">{{ zeit(z.res_avg_h, z.res_median_h, z.res_n) }}</td>
                  <td class="py-2 px-3 text-right" :class="slaFarbe(z.sla_pct)">{{ pct(z.sla_pct, z.sla_n) }}</td>
                  <td class="py-2 px-3 text-right text-ink-gray-7">{{ z.antworten }}</td>
                  <td class="py-2 px-3 text-right text-ink-gray-7">{{ z.kommentare }}</td>
                  <td class="py-2 px-3 text-right text-ink-gray-7">{{ std(z.stunden) }}</td>
                  <td class="py-2 px-3 text-right text-ink-gray-7">{{ std(z.stunden_abrechenbar) }}</td>
                </tr>
                <tr v-if="!sortierteZeilen.length">
                  <td :colspan="spalten.length" class="py-6 text-center text-ink-gray-5">Keine Agenten im Filter.</td>
                </tr>
              </tbody>
              <tfoot v-if="data.team_summe">
                <tr class="bg-surface-gray-1 font-medium text-ink-gray-8">
                  <td class="py-2 px-3 sticky left-0 bg-surface-gray-1 z-10">
                    {{ data.team ? `Team ${data.team}` : data.ist_leitung ? "Alle Agenten" : "Mein Team" }}
                  </td>
                  <td class="py-2 px-3 text-right">{{ data.team_summe.offen }}</td>
                  <td class="py-2 px-3 text-right">{{ data.team_summe.ueberfaellig }}</td>
                  <td class="py-2 px-3 text-right">{{ data.team_summe.sla_verletzt_offen }}</td>
                  <td class="py-2 px-3 text-right" title="Summe der Zuweisungen (Mehrfachzuweisung zählt je Agent)">{{ data.team_summe.neu_zugewiesen }}</td>
                  <td class="py-2 px-3 text-right">{{ data.team_summe.geloest }}</td>
                  <td class="py-2 px-3 text-right">{{ zeit(data.team_summe.fr_avg_h, data.team_summe.fr_median_h, data.team_summe.fr_n) }}</td>
                  <td class="py-2 px-3 text-right">{{ zeit(data.team_summe.res_avg_h, data.team_summe.res_median_h, data.team_summe.res_n) }}</td>
                  <td class="py-2 px-3 text-right">{{ pct(data.team_summe.sla_pct, data.team_summe.sla_n) }}</td>
                  <td class="py-2 px-3 text-right">{{ data.team_summe.antworten }}</td>
                  <td class="py-2 px-3 text-right">{{ data.team_summe.kommentare }}</td>
                  <td class="py-2 px-3 text-right">{{ std(data.team_summe.stunden) }}</td>
                  <td class="py-2 px-3 text-right">{{ std(data.team_summe.stunden_abrechenbar) }}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>

        <!-- Wochenverlauf -->
        <div class="border border-outline-gray-2 rounded-md min-h-80 mb-4">
          <AxisChart :config="chartConfig" />
        </div>

        <!-- Hinweise -->
        <div v-if="data.hinweise?.length" class="text-xs text-ink-gray-5 flex flex-col gap-1 mb-2">
          <span v-for="h in data.hinweise" :key="h">ⓘ {{ h }}</span>
        </div>
        <div class="text-xs text-ink-gray-5">
          Zuordnung nach aktueller Zuweisung des Tickets. Ø/Median in Stunden Geschäftszeit laut SLA-Kalender
          (Lösungszeit ohne Wartezeit); in Klammern die Anzahl Tickets. SLA-Einhaltung = im Zeitraum gelöste
          Tickets mit erfüllter SLA ÷ gelöste Tickets mit SLA-Ergebnis.
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { LayoutHeader } from "@/components";
import { AxisChart, Button, createResource, dayjs, FormControl, usePageMeta } from "frappe-ui";
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

const presets = [
  { value: "woche", label: "Woche" },
  { value: "monat", label: "Monat" },
  { value: "quartal", label: "Quartal" },
  { value: "frei", label: "Frei" },
];
const preset = ref("monat");
const anker = ref(dayjs());
const fromDate = ref("");
const toDate = ref("");
const team = ref("");
const agent = ref("");

function rangeFor(p: string, a: any): [any, any] {
  if (p === "woche") {
    const s = a.subtract((a.day() + 6) % 7, "day");
    return [s, s.add(6, "day")];
  }
  if (p === "quartal") {
    const s = a.month(Math.floor(a.month() / 3) * 3).startOf("month");
    return [s, s.add(2, "month").endOf("month")];
  }
  return [a.startOf("month"), a.endOf("month")];
}

function applyPreset() {
  if (preset.value === "frei") return;
  const [s, e] = rangeFor(preset.value, anker.value);
  fromDate.value = s.format("YYYY-MM-DD");
  toDate.value = e.format("YYYY-MM-DD");
}

function setPreset(p: string) {
  preset.value = p;
  anker.value = dayjs();
  applyPreset();
}

function shift(dir: number) {
  const unit = preset.value === "woche" ? "week" : "month";
  const n = preset.value === "quartal" ? 3 : 1;
  anker.value = anker.value.add(dir * n, unit);
  applyPreset();
}
applyPreset();

const rangeLabel = computed(() => {
  const s = dayjs(fromDate.value);
  const e = dayjs(toDate.value);
  if (!s.isValid() || !e.isValid()) return "";
  if (preset.value === "monat") return s.format("MM/YYYY");
  if (preset.value === "quartal") return `Q${Math.floor(s.month() / 3) + 1}/${s.year()}`;
  return `${s.format("DD.MM.")} – ${e.format("DD.MM.YYYY")}`;
});

const resource = createResource({
  url: "axovend.helpdesk_dashboard.get_dashboard",
  makeParams: () => ({
    from_date: fromDate.value,
    to_date: toDate.value,
    team: team.value || null,
    agent: agent.value || null,
  }),
  auto: true,
});
const data = computed<any>(() => resource.data);

watch([fromDate, toDate, team, agent], () => {
  if (fromDate.value && toDate.value) resource.reload();
});
watch(team, () => {
  agent.value = "";
});

// Tabelle
const spalten = [
  { key: "agent_name", label: "Agent" },
  { key: "offen", label: "Offen", hilfe: "Aktuell zugewiesene, nicht gelöste Tickets (inkl. wartend)" },
  { key: "ueberfaellig", label: "Überfällig", hilfe: "Offen (nicht wartend) und SLA-Frist (Reaktion bzw. Lösung) überschritten" },
  { key: "sla_verletzt_offen", label: "SLA verletzt", hilfe: "Offene Tickets mit SLA-Status „Failed“" },
  { key: "neu_zugewiesen", label: "Neu zugewiesen", hilfe: "Im Zeitraum zugewiesene Tickets (auch wenn später weitergegeben)" },
  { key: "geloest", label: "Gelöst", hilfe: "Im Zeitraum gelöste/abgeschlossene Tickets" },
  { key: "fr_avg_h", label: "Erstreaktion Ø / Med.", hilfe: "Stunden Geschäftszeit bis zur ersten Antwort; Tickets mit erster Antwort im Zeitraum" },
  { key: "res_avg_h", label: "Lösungszeit Ø / Med.", hilfe: "Stunden Geschäftszeit bis zur Lösung abzüglich Wartezeit; im Zeitraum gelöste Tickets" },
  { key: "sla_pct", label: "SLA %", hilfe: "Im Zeitraum gelöste Tickets mit erfüllter SLA ÷ gelöste mit SLA-Ergebnis" },
  { key: "antworten", label: "Antworten", hilfe: "Ausgehende E-Mails an Kunden im Zeitraum" },
  { key: "kommentare", label: "Kommentare", hilfe: "Interne Kommentare im Zeitraum" },
  { key: "stunden", label: "Stunden", hilfe: "Erfasste Zeit (Timesheet) im Zeitraum" },
  { key: "stunden_abrechenbar", label: "davon abr.", hilfe: "Zeitbuchungen mit Abrechnungsentscheidung „Abrechnen“" },
];
const sortKey = ref("offen");
const sortAsc = ref(false);
function sortiere(k: string) {
  if (sortKey.value === k) sortAsc.value = !sortAsc.value;
  else {
    sortKey.value = k;
    sortAsc.value = k === "agent_name";
  }
}
const sortierteZeilen = computed(() => {
  const rows = [...(data.value?.zeilen || [])];
  const k = sortKey.value;
  rows.sort((a, b) => {
    const va = a[k] ?? -Infinity;
    const vb = b[k] ?? -Infinity;
    const r = typeof va === "string" ? va.localeCompare(vb) : va - vb;
    return sortAsc.value ? r : -r;
  });
  return rows;
});

// Formatierung
const fmt = (v: number) => v.toLocaleString("de-DE", { maximumFractionDigits: 1 });
function zeit(avg: number | null, med: number | null, n: number) {
  if (avg == null) return "—";
  return `${fmt(avg)} / ${fmt(med ?? 0)} (${n})`;
}
function pct(v: number | null, n: number) {
  return v == null ? "—" : `${v} % (${n})`;
}
function std(v: number) {
  return v ? fmt(v) : "—";
}
function slaFarbe(v: number | null) {
  if (v == null) return "text-ink-gray-5";
  if (v >= 80) return "text-ink-green-3";
  if (v >= 50) return "text-ink-amber-3";
  return "text-ink-red-4";
}

// Ticketlisten-Links (/tickets?filters=…)
const offeneStatus = computed(() => [...(data.value?.status?.open || []), ...(data.value?.status?.paused || [])]);
const assignF = (a: string) => ({ _assign: ["like", `%"${a}"%`] });
function teamF() {
  return data.value?.team ? { agent_group: data.value.team } : {};
}
function offenFilter(a?: string) {
  return { ...teamF(), ...(a ? assignF(a) : {}), status: ["in", offeneStatus.value] };
}
function ueberfaelligFilter(a?: string) {
  return {
    ...teamF(),
    ...(a ? assignF(a) : {}),
    status: ["in", data.value?.status?.open || []],
    resolution_by: ["<", dayjs().format("YYYY-MM-DD HH:mm:ss")],
  };
}
function geloestFilter(a?: string) {
  return {
    ...teamF(),
    ...(a ? assignF(a) : {}),
    status: ["in", data.value?.status?.resolved || []],
    resolution_date: ["between", [data.value.zeitraum.von, data.value.zeitraum.bis]],
  };
}
function neuFilter() {
  return { ...teamF(), creation: ["between", [data.value.zeitraum.von, data.value.zeitraum.bis]] };
}
function openTickets(filters: Record<string, any>) {
  router.push({ name: "TicketsAgent", query: { filters: JSON.stringify(filters) } });
}

// Kacheln
const kacheln = computed(() => {
  const k = data.value?.kacheln;
  if (!k) return [];
  const a = data.value.ist_leitung && data.value.agent ? data.value.agent : undefined;
  return [
    {
      titel: "Offen gesamt",
      wert: k.offen,
      sub: `${k.offen_wartend} wartend · ${k.offen_unzugewiesen} ohne Zuweisung`,
      hilfe: "Alle nicht gelösten Tickets im Filter",
      link: offenFilter(a),
    },
    { titel: "Neu im Zeitraum", wert: k.neu, sub: "angelegte Tickets", hilfe: "Im Zeitraum angelegte Tickets", link: a ? null : neuFilter() },
    {
      titel: "Gelöst im Zeitraum",
      wert: k.geloest,
      sub: k.geloest_ohne_zuweisung ? `${k.geloest_ohne_zuweisung} ohne Zuweisung` : "abgeschlossen",
      hilfe: "Im Zeitraum gelöste/abgeschlossene Tickets",
      link: geloestFilter(a),
    },
    {
      titel: "Erstreaktion Ø",
      wert: k.fr_avg_h == null ? "—" : `${fmt(k.fr_avg_h)} h`,
      sub: k.fr_median_h == null ? "" : `Median ${fmt(k.fr_median_h)} h · ${k.fr_n} Tickets`,
      hilfe: "Stunden Geschäftszeit bis zur ersten Antwort (erste Antwort im Zeitraum)",
    },
    {
      titel: "SLA-Einhaltung",
      wert: k.sla_pct == null ? "—" : `${k.sla_pct} %`,
      sub: `von ${k.sla_n} gelösten Tickets`,
      hilfe: "Gelöste Tickets im Zeitraum mit erfüllter SLA",
    },
    {
      titel: "Überfällig (offen)",
      wert: k.ueberfaellig,
      sub: "SLA-Frist überschritten",
      hilfe: "Offene, nicht wartende Tickets mit überschrittener Reaktions- oder Lösungsfrist",
      link: ueberfaelligFilter(a),
    },
  ];
});

const chartConfig = computed(() => ({
  type: "axis",
  title: "Verlauf je Woche (mind. 12 Wochen)",
  subtitle: "Neu angelegte vs. gelöste Tickets",
  data: (data.value?.wochen || []).map((w: any) => ({ Woche: w.label, Neu: w.neu, Gelöst: w.geloest })),
  xAxis: { key: "Woche", type: "category" },
  yAxis: { title: "Tickets" },
  series: [
    { name: "Neu", type: "bar" },
    { name: "Gelöst", type: "bar" },
  ],
  colors: ["#318AD8", "#48BB74"],
}));

usePageMeta(() => ({ title: "Dashboard" }));
</script>

<style scoped>
.zahl {
  @apply cursor-pointer text-ink-gray-9 hover:underline;
}
</style>
