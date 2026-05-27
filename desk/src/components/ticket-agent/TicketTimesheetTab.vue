<template>
  <div class="flex flex-col flex-1 overflow-y-auto px-5 py-4 gap-5">
    <!-- Plan / Ist -->
    <div class="flex items-center gap-8 flex-shrink-0">
      <div class="flex flex-col">
        <span class="text-xs text-ink-gray-5">Ist-Stunden</span>
        <span class="text-lg font-semibold text-ink-gray-9">
          {{ formatHours(data?.total_hours) }}
        </span>
      </div>
      <div class="flex flex-col">
        <span class="text-xs text-ink-gray-5">Plan-Stunden</span>
        <div class="flex items-center gap-2">
          <input
            v-model.number="plannedInput"
            type="number"
            step="0.25"
            min="0"
            class="w-20 rounded border border-outline-gray-2 px-2 py-1 text-sm"
          />
          <Button
            label="Speichern"
            size="sm"
            :loading="plannedResource.loading"
            @click="savePlanned"
          />
        </div>
      </div>
    </div>

    <!-- Eingabeformular -->
    <div class="rounded-lg border border-outline-gray-2 p-4 flex flex-col gap-3 flex-shrink-0">
      <span class="text-sm font-medium text-ink-gray-8">Zeit erfassen</span>
      <div class="grid grid-cols-2 gap-3">
        <FormControl
          v-model="form.activity_date"
          type="date"
          label="Datum"
        />
        <div class="grid grid-cols-2 gap-2">
          <FormControl v-model="form.from_time" type="time" label="Von" />
          <FormControl v-model="form.to_time" type="time" label="Bis" />
        </div>
        <!-- Felder DL-Artikel + Abrechnungskategorie im SPA ausgeblendet (axovend):
             werden erst beim Verbuchen/Abrechnen in ERPNext gepflegt. Backend-Logik bleibt erhalten. -->
        <div v-if="false" class="flex flex-col gap-1">
          <span class="text-xs text-ink-gray-5">Dienstleistungs-Artikel</span>
          <Link doctype="Item" :value="form.service_item" @change="(v) => (form.service_item = v)" />
        </div>
        <FormControl
          v-if="false"
          v-model="form.billing_category"
          type="select"
          label="Abrechnungskategorie"
          :options="billingOptions"
        />
      </div>
      <FormControl
        v-model="form.description"
        type="textarea"
        label="Kommentar — was wurde gemacht?"
        :rows="2"
      />
      <div class="flex justify-end">
        <Button
          label="Buchen"
          variant="solid"
          :loading="logResource.loading"
          @click="submit"
        />
      </div>
    </div>

    <!-- Tabelle aller Einträge -->
    <div class="flex-1">
      <div
        v-if="!data?.entries?.length"
        class="text-sm text-ink-gray-5 py-6 text-center"
      >
        Noch keine Zeiteinträge auf diesem Ticket.
      </div>
      <table v-else class="w-full text-sm">
        <thead>
          <tr class="text-left text-ink-gray-5 border-b border-outline-gray-2">
            <th class="py-2 pr-3 font-medium">Mitarbeiter</th>
            <th class="py-2 pr-3 font-medium">Datum</th>
            <th class="py-2 pr-3 font-medium">Von–Bis</th>
            <th class="py-2 pr-3 font-medium text-right">Std.</th>
            <th class="py-2 pr-3 font-medium">Tätigkeit</th>
            <th class="py-2 pr-3 font-medium">Abrechnung</th>
            <th class="py-2 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in data.entries"
            :key="row.name"
            class="border-b border-outline-gray-1 align-top"
          >
            <td class="py-2 pr-3 text-ink-gray-8">{{ row.employee_name }}</td>
            <td class="py-2 pr-3 text-ink-gray-7">{{ datePart(row.from_time) }}</td>
            <td class="py-2 pr-3 text-ink-gray-7">
              {{ timePart(row.from_time) }}–{{ timePart(row.to_time) }}
            </td>
            <td class="py-2 pr-3 text-right text-ink-gray-8">
              {{ formatHours(row.hours) }}
            </td>
            <td class="py-2 pr-3 text-ink-gray-7">{{ row.description || "—" }}</td>
            <td class="py-2 pr-3 text-ink-gray-7">{{ row.billing_category || "—" }}</td>
            <td class="py-2">
              <Badge
                :theme="row.docstatus === 1 ? 'green' : 'gray'"
                :label="row.docstatus === 1 ? 'Eingereicht' : 'Entwurf'"
                size="sm"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Link } from "@/components";
import { Badge, Button, FormControl, createResource, toast } from "frappe-ui";
import { computed, reactive, ref, watch } from "vue";

const props = defineProps<{ ticketId: string }>();

const billingOptions = [
  { label: "—", value: "" },
  { label: "Abgerechnet", value: "Abgerechnet" },
  { label: "Gegen Vertrag", value: "Gegen Vertrag" },
  { label: "Kulanz", value: "Kulanz" },
  { label: "Garantie", value: "Garantie" },
];

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

const form = reactive({
  activity_date: today(),
  from_time: "",
  to_time: "",
  service_item: "",
  billing_category: "",
  description: "",
});

const plannedInput = ref(0);

const timesheets = createResource({
  url: "axovend.service.get_ticket_timesheets",
  params: { ticket: props.ticketId },
  auto: true,
  onSuccess: (d: any) => {
    plannedInput.value = d?.planned_hours || 0;
  },
});
const data = computed(() => timesheets.data);

watch(
  () => props.ticketId,
  (id) => {
    timesheets.update({ params: { ticket: id } });
    timesheets.reload();
  }
);

const logResource = createResource({ url: "axovend.service.log_ticket_time" });
const plannedResource = createResource({
  url: "axovend.service.set_ticket_planned_hours",
});

function submit() {
  if (!form.service_item || !form.from_time || !form.to_time) {
    toast.error("Bitte Artikel, Von- und Bis-Zeit ausfüllen.");
    return;
  }
  logResource.submit(
    {
      ticket: props.ticketId,
      service_item: form.service_item,
      activity_date: form.activity_date,
      from_time: form.from_time,
      to_time: form.to_time,
      billing_category: form.billing_category,
      description: form.description,
    },
    {
      onSuccess: (r: any) => {
        toast.success((r && r.message) || "Zeit gebucht.");
        form.from_time = "";
        form.to_time = "";
        form.service_item = "";
        form.billing_category = "";
        form.description = "";
        timesheets.reload();
      },
      onError: (e: any) => toast.error(errMsg(e)),
    }
  );
}

function savePlanned() {
  plannedResource.submit(
    { ticket: props.ticketId, hours: plannedInput.value || 0 },
    {
      onSuccess: () => {
        toast.success("Plan-Stunden gespeichert.");
        timesheets.reload();
      },
      onError: (e: any) => toast.error(errMsg(e)),
    }
  );
}

function errMsg(e: any): string {
  return (e && (e.messages?.join(", ") || e.message)) || "Fehler bei der Buchung.";
}

function formatHours(h: any): string {
  return (Number(h) || 0).toLocaleString("de-DE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}
function datePart(dt: string): string {
  if (!dt) return "—";
  const d = dt.slice(0, 10).split("-");
  return d.length === 3 ? `${d[2]}.${d[1]}.${d[0]}` : dt;
}
function timePart(dt: string): string {
  return dt ? dt.slice(11, 16) : "—";
}
</script>
