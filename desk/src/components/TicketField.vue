<template>
  <div class="flex gap-2 pb-1 leading-5 items-center">
    <div class="w-[106px] shrink-0 truncate text-sm text-gray-600">
      <Tooltip :text="field.label">
        <span>{{ field.label }}</span>
      </Tooltip>
      <span v-if="field.required" class="text-red-500"> * </span>
    </div>
    <div
      class="-m-0.5 min-h-[28px] flex-1 items-center overflow-hidden p-0.5 text-base flex gap-1"
    >
      <component
        :is="component"
        :key="field.fieldname"
        :readonly="field.readonly"
        :disabled="field.disabled"
        v-bind="linkFilters ? { filters: linkFilters } : {}"
        class="form-control flex-1 min-w-0"
        :placeholder="field.placeholder || `Add ${field.label}`"
        :model-value="transValue"
        autocomplete="off"
        v-on="
          [...textFields, ...numberFields].includes(field.fieldtype)
            ? {
                blur: (event) => {
                  emitUpdate(field.fieldname, event.target.value);
                },
              }
            : {
                'update:model-value': (event) => {
                  emitUpdate(
                    field.fieldname,
                    event?.value || event?.target?.value || event
                  );
                },
              }
        "
      />
      <Tooltip
        v-if="erpnextOpenPath"
        :text="`In ERPNext öffnen: ${field.value}`"
      >
        <button
          type="button"
          class="shrink-0 p-1 rounded hover:bg-surface-gray-2 text-ink-gray-6 hover:text-ink-gray-8 cursor-pointer"
          @click.stop.prevent="openInErpnext"
          :aria-label="`In ERPNext öffnen: ${field.value}`"
        >
          <ExternalLinkIcon class="size-4" />
        </button>
      </Tooltip>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Autocomplete, Link } from "@/components";
import { ExternalLinkIcon } from "@/components/icons";
import { APIOptions, Field, FieldValue, TicketSymbol } from "@/types";
import { parseApiOptions } from "@/utils";
import {
  createResource,
  DatePicker,
  DateTimePicker,
  dayjs,
  FormControl,
  Tooltip,
} from "frappe-ui";
import { computed, h, inject, ref, watch } from "vue";

interface P {
  field: Field;
  value: FieldValue;
}

interface R {
  fieldname: Field["fieldname"];
  value: FieldValue;
}

interface E {
  (event: "change", value: R);
}

const props = defineProps<P>();
const emit = defineEmits<E>();

const apiOptions = createResource({
  url: props.field.url_method,
  auto: !!props.field.url_method,
  transform: (data: APIOptions) => {
    return parseApiOptions(data);
  },
});

const textFields = ["Long Text", "Small Text", "Text", "Text Editor", "Data"];
const numberFields = ["Int", "Float", "Currency", "Percent"];

const component = computed(() => {
  if (props.field.url_method) {
    return h(Autocomplete, {
      options: apiOptions.data,
    });
  } else if (props.field.fieldtype === "Link" && props.field.options) {
    return h(Link, {
      doctype: props.field.options,
      hideMe: true,
    });
  } else if (props.field.fieldtype === "Select") {
    return h(Autocomplete, {
      options: props.field.options
        .split("\n")
        .map((o) => ({ label: o, value: o })),
    });
  } else if (props.field.fieldtype === "Check") {
    return h(Autocomplete, {
      options: [
        {
          label: "Yes",
          value: 1,
        },
        {
          label: "No",
          value: 0,
        },
      ],
    });
  } else if (textFields.includes(props.field.fieldtype)) {
    return h(FormControl, {
      type: "text",
    });
  } else if (props.field.fieldtype === "Datetime") {
    return h(DateTimePicker, {
      format: `${window.date_format.toUpperCase()} ${window.time_format}`,
    });
  } else if (props.field.fieldtype === "Date") {
    return h(DatePicker, {
      id: props.field.fieldname,
      format: window.date_format.toUpperCase(),
    });
  }
  // else if (props.field.fieldtype === "Duration") {
  //   // console.log("HERE TIME");
  //   return h(DurationField, { showSeconds: false });
  // }
  else {
    return h(FormControl);
  }
});

const transValue = computed(() => {
  const fieldtype = props.field.fieldtype;
  if (fieldtype === "Check") {
    return props.value ? "Yes" : "No";
  } else if (fieldtype === "Date") {
    if (!props.value) return props.value;
    return dayjs(props.value).format(window.date_format.toUpperCase());
  }
  // else if (fieldtype === "Duration") {
  //   if (!props.value) return null;
  // }
  return props.value;
});

function emitUpdate(fieldname: Field["fieldname"], value: FieldValue) {
  emit("change", { fieldname, value });
}

// axovend: Felder, die per externem Link in ERPNext geöffnet werden sollen.
// Wert = ERPNext-DocType (kebab-case wird beim Link gebildet).
const EXTERNAL_LINK_FIELDS: Record<string, string> = {
  custom_quotation: "Quotation",
  custom_sales_order: "Sales Order",
  custom_contract: "Contract",
};

// axovend (Task #8): Filter Vertrags-Dropdown auf den Ticket-Kunden.
// HD Ticket.customer → HD Customer → custom_erpnext_customer → Contract.party_name.
// Wir injizieren das Ticket, lösen den ERPNext-Kunden via whitelisted Method
// und geben den filter dict an die Link-Komponente weiter.
const ticket = inject(TicketSymbol, null as any);
const erpnextCustomer = ref<string | null>(null);

const erpnextCustomerResource = createResource({
  url: "axovend.api.get_erpnext_customer_for_hd_customer",
  makeParams: () => ({ hd_customer: ticket?.value?.doc?.customer || "" }),
  onSuccess: (data: string | null) => {
    erpnextCustomer.value = data || null;
  },
});

watch(
  () => ticket?.value?.doc?.customer,
  (hd_customer) => {
    if (props.field.fieldname !== "custom_contract") return;
    if (!hd_customer) {
      erpnextCustomer.value = null;
      return;
    }
    erpnextCustomerResource.fetch();
  },
  { immediate: true }
);

const linkFilters = computed(() => {
  if (props.field.fieldname !== "custom_contract") return null;
  // Wenn ein ERPNext-Kunde aufgelöst werden konnte: filtere Verträge auf ihn.
  // Sonst: leere Liste (Filter, der nichts matcht), damit der User nicht
  // versehentlich Verträge eines fremden Kunden auswählt.
  if (erpnextCustomer.value) {
    return { party_name: erpnextCustomer.value };
  }
  // Sentinelwert: leerer party_name liefert nichts (sauber leer statt alle).
  return { party_name: "__no_customer__" };
});

const erpnextOpenPath = computed(() => {
  const fieldname = props.field.fieldname;
  const targetDoctype = EXTERNAL_LINK_FIELDS[fieldname];
  if (!targetDoctype) return "";
  const value = props.field.value;
  if (value === null || value === undefined || value === "") return "";
  const kebab = targetDoctype.toLowerCase().replace(/\s+/g, "-");
  return `/app/${kebab}/${encodeURIComponent(String(value))}`;
});

function openInErpnext() {
  if (!erpnextOpenPath.value) return;
  window.open(erpnextOpenPath.value, "_blank", "noopener,noreferrer");
}
</script>
<style scoped>
:deep(.form-control input:not([type="checkbox"])),
:deep(.form-control select),
:deep(.form-control textarea),
:deep(.form-control button) {
  border-color: transparent;
  background: white;
}

:deep(.form-control button) {
  gap: 0;
}
:deep(.form-control [type="checkbox"]) {
  margin-left: 9px;
  cursor: pointer;
}

:deep(.form-control button > div) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:deep(.form-control button svg) {
  color: white;
  width: 0;
}
</style>
