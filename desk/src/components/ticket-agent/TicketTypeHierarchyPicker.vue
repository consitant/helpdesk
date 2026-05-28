<template>
  <!--
    3-stufiger Ticket-Type-Picker (Axovend Hierarchie):
      1) Ticket-Art   (Intern/Extern, Select aus HD Ticket Type.ticket_art)
      2) Kategorie    (Top-Level HD Ticket Type, parent leer, gefiltert nach Art)
      3) Unter-Kategorie (Child HD Ticket Type, gefiltert nach Kategorie)

    Emits:
      - update:ticketType (string)    final HD Ticket Type name
      - update:ticketArt  (string)    "Intern" | "Extern" | ""

    Layout-Konvention: jeder Schritt rendert separat, wir steuern Gap & Width selbst.
    Wir verzichten bewusst auf die :deep(.form-control-core div) Regel von TicketDetailsTab
    indem wir eigene scoped Styles definieren.
  -->
  <div class="ttp-root flex flex-col gap-2 w-full">
    <FormControl
      type="select"
      class="ttp-field w-full"
      :label="__('Ticket-Art')"
      :options="ticketArtOptions"
      :modelValue="ticketArt"
      :disabled="disabled"
      @update:model-value="(val:string) => onTicketArtChange(val)"
    />
    <Link
      class="ttp-field w-full"
      :page-length="20"
      :label="__('Kategorie')"
      :placeholder="ticketArt ? __('Kategorie wählen') : __('Erst Ticket-Art wählen')"
      doctype="HD Ticket Type"
      :filters="topLevelFilters"
      :modelValue="topLevelTicketType"
      :disabled="disabled || !ticketArt"
      @update:model-value="onTopLevelChange"
    />
    <Link
      class="ttp-field w-full"
      :page-length="20"
      :label="__('Unter-Kategorie')"
      :placeholder="topLevelTicketType ? __('Unter-Kategorie wählen') : __('Erst Kategorie wählen')"
      doctype="HD Ticket Type"
      :filters="subTypeFilters"
      :modelValue="subTypeValue"
      :required="required"
      :disabled="disabled || !topLevelTicketType"
      @update:model-value="(val:string) => onSubTypeChange(val)"
    />
  </div>
</template>

<script setup lang="ts">
import { Link } from "@/components";
import { __ } from "@/translation";
import { FormControl, createResource } from "frappe-ui";
import { computed, ref, watch } from "vue";

interface Props {
  // Aktueller HD Ticket Type (z.B. "Bug (PE)") oder leer
  modelValue?: string;
  // Optionaler aktueller custom_ticket_art Wert vom Dokument als Fallback
  ticketArtValue?: string;
  required?: boolean;
  disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: "",
  ticketArtValue: "",
  required: false,
  disabled: false,
});

const emit = defineEmits<{
  (e: "update:modelValue", val: string): void;
  (e: "update:ticketArt", val: string): void;
}>();

const ticketArt = ref<string>("");
const topLevelTicketType = ref<string>("");

type TypeInfo = { parent: string; ticket_art: string };
const typeInfoCache = ref<Record<string, TypeInfo>>({});

const ticketArtOptions = [
  { label: "", value: "" },
  { label: "Intern", value: "Intern" },
  { label: "Extern", value: "Extern" },
];

const subTypeValue = computed(() => {
  const v = props.modelValue || "";
  // Wenn ticket_type == top, dann ist Unter-Kategorie noch nicht gewählt
  if (v && v === topLevelTicketType.value) return "";
  return v;
});

// Filter im LIST-OF-LISTS Format. Robust über search_link / get_list.
const topLevelFilters = computed(() => {
  if (!ticketArt.value) {
    // Keine Art gewählt: unmögliche Filter -> keine Ergebnisse
    return [["name", "=", "__none__"]];
  }
  return [
    ["parent_ticket_type", "is", "not set"],
    ["ticket_art", "=", ticketArt.value],
    ["disabled", "=", 0],
  ];
});

const subTypeFilters = computed(() => {
  if (!topLevelTicketType.value) {
    return [["name", "=", "__none__"]];
  }
  return [
    ["parent_ticket_type", "=", topLevelTicketType.value],
    ["disabled", "=", 0],
  ];
});

const typeLookup = createResource({
  url: "frappe.client.get_value",
  makeParams: (args: any) => ({
    doctype: "HD Ticket Type",
    filters: { name: args.name },
    fieldname: ["parent_ticket_type", "ticket_art"],
  }),
});

async function resolveTypeInfo(typeName: string): Promise<TypeInfo> {
  if (!typeName) return { parent: "", ticket_art: "" };
  if (typeName in typeInfoCache.value) return typeInfoCache.value[typeName];
  try {
    const res = await typeLookup.submit({ name: typeName });
    const payload = (res && (res.message ?? res)) || {};
    const info: TypeInfo = {
      parent: (payload?.parent_ticket_type as string) || "",
      ticket_art: (payload?.ticket_art as string) || "",
    };
    typeInfoCache.value[typeName] = info;
    return info;
  } catch (e) {
    return { parent: "", ticket_art: "" };
  }
}

// Initial-Sync aus modelValue + ticketArtValue
async function syncFromValue(typeName: string) {
  if (!typeName) {
    ticketArt.value = props.ticketArtValue || "";
    topLevelTicketType.value = "";
    return;
  }
  const info = await resolveTypeInfo(typeName);
  const top = info.parent || typeName;
  topLevelTicketType.value = top;
  let art = info.ticket_art;
  if (!art && info.parent) {
    const parentInfo = await resolveTypeInfo(info.parent);
    art = parentInfo.ticket_art;
  }
  if (!art) art = props.ticketArtValue || "";
  ticketArt.value = art || "";
}

watch(
  () => props.modelValue,
  (val) => {
    syncFromValue(val || "");
  },
  { immediate: true }
);

watch(
  () => props.ticketArtValue,
  (val) => {
    // Falls extern Art geändert wird und noch kein Ticket-Type da ist
    if (!props.modelValue && val && val !== ticketArt.value) {
      ticketArt.value = val;
    }
  }
);

function onTicketArtChange(val: string) {
  if (val === ticketArt.value) return;
  ticketArt.value = val || "";
  emit("update:ticketArt", ticketArt.value);
  const currentSub = props.modelValue;
  if (!val) {
    topLevelTicketType.value = "";
    if (currentSub) emit("update:modelValue", "");
    return;
  }
  if (currentSub) {
    resolveTypeInfo(currentSub).then((info) => {
      const effectiveTop = info.parent || currentSub;
      resolveTypeInfo(effectiveTop).then((topInfo) => {
        if (topInfo.ticket_art && topInfo.ticket_art !== val) {
          topLevelTicketType.value = "";
          emit("update:modelValue", "");
        }
      });
    });
  } else {
    topLevelTicketType.value = "";
  }
}

function onTopLevelChange(val: string) {
  if (val === topLevelTicketType.value) return;
  topLevelTicketType.value = val || "";
  const currentSub = props.modelValue;
  if (!val) {
    if (currentSub) emit("update:modelValue", "");
    return;
  }
  if (!currentSub) {
    emit("update:modelValue", val);
    typeInfoCache.value[val] = { parent: "", ticket_art: ticketArt.value };
    return;
  }
  resolveTypeInfo(currentSub).then((info) => {
    const effectiveTop = info.parent || currentSub;
    if (effectiveTop !== val) {
      emit("update:modelValue", val);
      typeInfoCache.value[val] = { parent: "", ticket_art: ticketArt.value };
    }
  });
}

function onSubTypeChange(val: string) {
  if (val) {
    typeInfoCache.value[val] = {
      parent: topLevelTicketType.value || "",
      ticket_art: ticketArt.value || "",
    };
  }
  emit("update:modelValue", val);
}
</script>

<style scoped>
/*
  Eigene, ENG gefasste Styles. Wir wenden KEINE Wildcard div-Regel an
  (das war der Bug in TicketDetailsTab: :deep(.form-control-core div) hat
  alle inneren Divs auf display:flex/width:100% gezwungen und damit das
  vertikale Stapeln der drei Pickers zerschossen).
*/
.ttp-root {
  width: 100%;
}

.ttp-field {
  width: 100%;
}

:deep(.ttp-field > div) {
  /* Wrapper von FormControl / Link soll volle Breite einnehmen */
  width: 100%;
}

:deep(.ttp-field button) {
  @apply text-base rounded h-7 py-1.5 border border-outline-gray-2 bg-surface-white placeholder-ink-gray-4 hover:border-outline-gray-3 hover:shadow-sm focus:bg-surface-white focus:border-outline-gray-4 focus:shadow-sm focus:ring-0 focus-visible:ring-0 text-ink-gray-8 transition-colors w-full dark:[color-scheme:dark];
}

:deep(.ttp-field button > div) {
  @apply truncate;
}

:deep(.ttp-field select) {
  @apply text-base rounded h-7 py-1.5 border border-outline-gray-2 bg-surface-white placeholder-ink-gray-4 hover:border-outline-gray-3 hover:shadow-sm focus:bg-surface-white focus:border-outline-gray-4 focus:shadow-sm focus:ring-0 focus-visible:ring-0 text-ink-gray-8 transition-colors w-full dark:[color-scheme:dark];
}
</style>
