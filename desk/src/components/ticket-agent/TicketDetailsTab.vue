<template>
  <div class="flex h-full flex-col">
    <div class="shrink-0 px-4 pb-4 flex flex-col">
      <!-- User avatar with buttons -->
      <TicketContact />
      <!-- Core Fields -->
      <div class="mt-4">
        <div
          v-for="(section, index) in coreFields"
          :key="index"
          :class="
            section.group ? 'flex gap-2 items-start max-w-full mb-3' : 'mb-3'
          "
        >
          <template v-for="field in section.fields">
            <!-- Three-step UI for ticket_type (Axovend Hierarchie: Art → Kategorie → Unterkategorie) -->
            <template v-if="field.fieldname === 'ticket_type' && field.visible">
              <div
                :key="'ticket_type_picker'"
                class="flex flex-col gap-2"
                :class="section.group ? 'flex-1 min-w-0' : 'w-full'"
              >
                <FormControl
                  id="ticket_art"
                  type="select"
                  class="form-control-core form-control-core-select w-full"
                  :label="__('Ticket-Art')"
                  :options="ticketArtOptions"
                  :modelValue="ticketArt"
                  @update:model-value="(val:string) => onTicketArtChange(val)"
                />
                <Link
                  class="form-control-core w-full"
                  id="ticket_type_top"
                  :page-length="20"
                  :label="__('Kategorie')"
                  :placeholder="ticketArt ? __('Kategorie wählen') : __('Erst Ticket-Art wählen')"
                  doctype="HD Ticket Type"
                  :filters="topLevelFilters"
                  :modelValue="topLevelTicketType"
                  :disabled="!ticketArt"
                  @update:model-value="onTopLevelChange"
                />
                <Link
                  :ref="(el) => setFieldRef(field.fieldname, el)"
                  class="form-control-core w-full"
                  :id="field.fieldname"
                  :page-length="20"
                  :label="__('Unter-Kategorie')"
                  :placeholder="topLevelTicketType ? __('Unter-Kategorie wählen') : __('Erst Kategorie wählen')"
                  doctype="HD Ticket Type"
                  :filters="subTypeFilters"
                  :modelValue="subTypeValue"
                  :required="field.required"
                  :disabled="!topLevelTicketType"
                  @update:model-value="(val:string) => handleSubTypeChange(val)"
                />
              </div>
            </template>
            <Link
              v-else-if="field.visible"
              :key="field.fieldname"
              :ref="(el) => setFieldRef(field.fieldname, el)"
              class="form-control-core"
              :id="field.fieldname"
              :class="section.group ? 'flex-1 min-w-0' : 'w-full'"
              :page-length="10"
              :label="field.label"
              :placeholder="field.placeholder"
              :doctype="field.doctype"
              :modelValue="field.value"
              :required="field.required"
              @update:model-value="
              (val:string) => handleFieldUpdate(field.fieldname, val,true)
            "
            />
          </template>
        </div>

        <!-- Assignee component -->
        <AssignTo />
      </div>
    </div>

    <!-- Scrollable sections: Ticket Info + Recent / Similar Tickets -->
    <div
      class="border-t flex-1 min-h-0 overflow-y-auto divide-y-[1px]"
      v-if="Boolean(customFields.length) || showRecentSimilarTickets"
    >
      <!-- Ticket Info (custom fields) -->
      <div v-if="Boolean(customFields.length)">
        <Section label="Ticket Info" :opened="true">
          <template #header="{ opened, toggle }">
            <div
              class="flex gap-2.5 items-center justify-between sticky top-0 bg-surface-white z-10 px-4 py-4 cursor-pointer"
              @click="toggle"
            >
              <span class="text-ink-gray-8 font-semibold text-base select-none">
                {{ __("Ticket Info") }}
              </span>
              <LucideChevronRight
                class="size-4 text-ink-gray-6"
                :class="{ 'rotate-90': opened }"
              />
            </div>
          </template>
          <div
            class="space-y-1.5 px-4 last:mb-2"
            v-if="Boolean(customFields.length)"
          >
            <template v-for="field in customFields">
              <TicketField
                v-if="field.visible"
                :key="field.fieldname"
                :field="field"
                :value="field.value"
                @change="
                  ({ fieldname, value }) => handleFieldUpdate(fieldname, value)
                "
              />
            </template>
          </div>
        </Section>
      </div>

      <!-- Recent / Similar Tickets -->
      <template v-if="showRecentSimilarTickets">
        <div v-for="section in sections" :key="section.label">
          <Section
            :label="section.label"
            :hideLabel="section.hideLabel"
            :opened="section.opened"
          >
            <template #header="{ opened, toggle }">
              <div
                class="flex gap-2.5 items-center justify-between sticky top-0 bg-surface-white z-10 px-4 py-4 cursor-pointer"
                @click="toggle"
              >
                <Tooltip :text="section.tooltipMessage">
                  <span
                    class="text-ink-gray-8 font-semibold text-base select-none"
                  >
                    {{ __(section.label) }}
                  </span>
                </Tooltip>
                <LucideChevronRight
                  class="size-4 text-ink-gray-6"
                  :class="{ 'rotate-90': opened }"
                />
              </div>
            </template>
            <ul class="pt-0 px-5 divide-y divide-outline-gray-1 pb-4">
              <li
                v-for="t in section.tickets"
                :key="t.name"
                @click="openTicket(t.name)"
              >
                <div
                  class="-mx-2 px-2 py-3 cursor-pointer rounded hover:bg-surface-gray-2 transition-colors"
                >
                  <p class="text-sm font-base text-ink-gray-9 truncate mb-2">
                    {{ t.subject }}
                  </p>
                  <div class="flex items-center justify-between gap-2">
                    <p class="text-sm text-ink-gray-5 shrink-0">
                      {{ formatDate(t.creation as string) + " · " }}
                      <span class="">{{ "#" + t.name }}</span>
                    </p>
                    <span
                      class="text-xs px-2 py-0.5 font-base shrink-0 rounded-sm"
                      :class="getStatusColor(t.status as string)"
                    >
                      {{ t.status }}
                    </span>
                  </div>
                </div>
              </li>
            </ul>
          </Section>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Link } from "@/components";
import { parseField } from "@/composables/formCustomisation";
import { useNotifyTicketUpdate } from "@/composables/realtime";
import { useShortcut } from "@/composables/shortcuts";
import { getMeta } from "@/stores/meta";
import { useTicketStatusStore } from "@/stores/ticketStatus";
import {
  ActivitiesSymbol,
  AssigneeSymbol,
  CustomizationSymbol,
  FieldValue,
  RecentSimilarTicketsSymbol,
  TicketSymbol,
} from "@/types";
import dayjs from "dayjs";
import { FormControl, Tooltip, createResource } from "frappe-ui";
import { computed, inject, ref, watch } from "vue";
import LucideChevronRight from "~icons/lucide/chevron-right";
import Section from "../Section.vue";
import TicketField from "../TicketField.vue";
import AssignTo from "./AssignTo.vue";
import TicketContact from "./TicketContact.vue";

const ticket = inject(TicketSymbol)!;
const assignees = inject(AssigneeSymbol)!;
const customizations = inject(CustomizationSymbol)!;
const activities = inject(ActivitiesSymbol)!;
const recentSimilarTickets = inject(RecentSimilarTicketsSymbol)!;
const { getFields, getField } = getMeta("HD Ticket");
const { notifyTicketUpdate } = useNotifyTicketUpdate(ticket.value?.name);

const dateFormat = window.date_format;
const { getStatus, colorMap } = useTicketStatusStore();

// ticket_type, priority, customer, agent_group
const coreFields = computed(() => {
  // TODO: to confirm whether customizations should apply to core fields as well
  const fieldsMeta = getFields();
  if (!fieldsMeta || fieldsMeta.length === 0) {
    return [];
  }
  const _coreFields = [
    { group: true, fields: [getField("ticket_type"), getField("priority")] },
    { group: false, fields: [getField("customer")] },
    { group: true, fields: [getField("agent_group")] },
  ];

  _coreFields.forEach((section) => {
    section.fields = section.fields.map((f) => {
      f = parseField(f, ticket.value.doc);

      // cant handle required depends on as we directly set the value in DB on change
      f["required"] = f.reqd;
      f["ref"] = f.fieldname;

      f = getFieldInFormat(f, f);
      f["visible"] = true;
      return f;
    });
  });
  return _coreFields;
});

const customFields = computed(() => {
  const fieldsMeta = getFields();
  if (!fieldsMeta || fieldsMeta.length === 0) {
    return [];
  }

  if (!customizations.value.data || customizations.value.loading) return [];
  let customFields = customizations.value.data?.custom_fields || [];
  const _coreFields = [
    "ticket_type",
    "priority",
    "customer",
    "agent_group",
    "subject",
    "status",
  ];
  customFields = customFields.filter((f) => !_coreFields.includes(f.fieldname));
  let _customFields = customFields
    .map((f) => {
      let fieldMeta = getField(f.fieldname);
      if (!fieldMeta) return null;

      fieldMeta = parseField(fieldMeta, ticket.value.doc);
      // cant handle required depends on as we directly set the value in DB
      fieldMeta["required"] = fieldMeta.reqd || f.required;

      return getFieldInFormat(f, fieldMeta);
    })
    .filter(Boolean);
  return _customFields;
});

const sections = computed(() => {
  if (recentSimilarTickets.value.loading || !recentSimilarTickets.value.data) {
    return [];
  }
  const recentTickets = recentSimilarTickets.value?.data?.recent_tickets || [];
  const similarTickets =
    recentSimilarTickets.value?.data?.similar_tickets || [];
  const _sections = [];
  if (recentTickets.length) {
    _sections.push({
      label: "Recent Tickets",
      tooltipMessage: "Tickets recently raised by this contact/customer",
      hideLabel: false,
      opened: true,
      tickets: recentTickets,
    });
  }
  if (similarTickets.length) {
    _sections.push({
      label: "Similar Tickets",
      tooltipMessage: "Tickets with similar queries",
      hideLabel: false,
      opened: true,
      tickets: similarTickets,
    });
  }
  return _sections;
});

function getStatusColor(status: string) {
  let { color } = getStatus(status);
  return colorMap[color] ?? colorMap["Default"];
}

function formatDate(date: string) {
  return dayjs(date).format(dateFormat.toUpperCase());
}

function openTicket(name: string | number) {
  let url = window.location.origin + "/helpdesk/tickets/" + name;
  window.open(url, "_blank");
}

function getFieldInFormat(fieldTemplate, fieldMeta) {
  return {
    label: fieldMeta?.label || fieldTemplate.fieldname,
    value: ticket.value.doc[fieldTemplate.fieldname],
    fieldtype: fieldMeta?.fieldtype,
    doctype: fieldMeta?.options || "",
    options: fieldMeta?.options || "",
    placeholder:
      fieldTemplate.placeholder ||
      `Enter ${fieldMeta?.label || fieldTemplate.fieldname}`,
    readonly: Boolean(fieldMeta.read_only),
    disabled: Boolean(fieldMeta.read_only),
    url_method: fieldTemplate.url_method || "",
    fieldname: fieldTemplate.fieldname,
    required: fieldTemplate.required || fieldMeta?.required || false,
    visible:
      fieldMeta.display_via_depends_on &&
      !fieldMeta.hidden &&
      (!!ticket.value.doc[fieldTemplate.fieldname] || !fieldMeta.read_only),
  };
}

const normalize = (v: string | FieldValue) =>
  v === null || v === undefined ? "" : v;

function handleFieldUpdate(
  fieldname: string,
  value: FieldValue,
  isCoreFieldUpdated = false
) {
  if (normalize(ticket.value.doc[fieldname]) == normalize(value)) return;
  if (isCoreFieldUpdated) {
    const label = getField(fieldname)?.label || fieldname;
    notifyTicketUpdate(label, value as string);
  }
  ticket.value.setValue.submit(
    { [fieldname]: value },
    {
      onSuccess: () => {
        // TODO: emit the event for notification to listeners
        if (fieldname === "agent_group") {
          assignees.value.reload();
        }
        activities.value.reload();
      },
    }

    //show error toast
  );
}

// --- Three-step ticket_type (Axovend: Art → Kategorie → Unter-Kategorie) ---
const ticketArt = ref<string>("");
const topLevelTicketType = ref<string>("");
// Cache: ticket_type name -> { parent: string, ticket_art: string }
type TypeInfo = { parent: string; ticket_art: string };
const typeInfoCache = ref<Record<string, TypeInfo>>({});

const ticketArtOptions = [
  { label: "", value: "" },
  { label: "Intern", value: "Intern" },
  { label: "Extern", value: "Extern" },
];

const subTypeValue = computed(() => {
  const v = ticket.value?.doc?.ticket_type || "";
  // If ticket_type equals the chosen top, the sub field should display empty.
  if (v && v === topLevelTicketType.value) return "";
  return v;
});

const topLevelFilters = computed(() => {
  if (!ticketArt.value) {
    // No art selected: show nothing (impossible filter)
    return { parent_ticket_type: ["is", "not set"], ticket_art: ["=", "__none__"] };
  }
  return {
    parent_ticket_type: ["is", "not set"],
    ticket_art: ticketArt.value,
  };
});

const subTypeFilters = computed(() => {
  if (!topLevelTicketType.value) {
    // No top selected: show nothing (impossible filter)
    return { parent_ticket_type: ["=", "__none__"] };
  }
  return { parent_ticket_type: topLevelTicketType.value };
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
    // frappe.client.get_value returns the dict directly or wrapped in {message}.
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

async function resolveParent(typeName: string): Promise<string> {
  return (await resolveTypeInfo(typeName)).parent;
}

// Initialise / sync ticketArt + topLevel from current ticket_type
async function syncFromTicketType(typeName: string) {
  if (!typeName) {
    // Keep ticketArt as-is if doc has custom_ticket_art set (allows user to start fresh)
    const docArt = (ticket.value?.doc as any)?.custom_ticket_art || "";
    ticketArt.value = docArt || "";
    topLevelTicketType.value = "";
    return;
  }
  const info = await resolveTypeInfo(typeName);
  // If type has a parent, that parent is the top. Otherwise the type itself is top.
  const top = info.parent || typeName;
  topLevelTicketType.value = top;
  // ticket_art: prefer the type's value; fall back to doc.custom_ticket_art.
  let art = info.ticket_art;
  if (!art && info.parent) {
    const parentInfo = await resolveTypeInfo(info.parent);
    art = parentInfo.ticket_art;
  }
  if (!art) art = (ticket.value?.doc as any)?.custom_ticket_art || "";
  ticketArt.value = art || "";
}

watch(
  () => ticket.value?.doc?.ticket_type,
  (val) => {
    syncFromTicketType(val || "");
  },
  { immediate: true }
);

function onTicketArtChange(val: string) {
  if (val === ticketArt.value) return;
  ticketArt.value = val || "";
  const currentSub = ticket.value?.doc?.ticket_type;
  if (!val) {
    // Art cleared → clear top + ticket_type.
    topLevelTicketType.value = "";
    if (currentSub) handleFieldUpdate("ticket_type", "", true);
    return;
  }
  // If existing ticket_type does not belong to the new art, clear top + ticket_type.
  if (currentSub) {
    resolveTypeInfo(currentSub).then((info) => {
      const effectiveTop = info.parent || currentSub;
      resolveTypeInfo(effectiveTop).then((topInfo) => {
        if (topInfo.ticket_art && topInfo.ticket_art !== val) {
          topLevelTicketType.value = "";
          handleFieldUpdate("ticket_type", "", true);
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
  const currentSub = ticket.value?.doc?.ticket_type;
  if (!val) {
    // Top cleared → clear ticket_type
    if (currentSub) handleFieldUpdate("ticket_type", "", true);
    return;
  }
  // Determine whether the new top has any sub-types. If not, set ticket_type=top.
  // Either way, if the current sub-type does not belong to this top, replace it
  // with the top itself (acts as default; user can pick a sub afterwards).
  if (!currentSub) {
    handleFieldUpdate("ticket_type", val, true);
    typeInfoCache.value[val] = { parent: "", ticket_art: ticketArt.value };
    return;
  }
  resolveParent(currentSub).then((parent) => {
    const effectiveTop = parent || currentSub;
    if (effectiveTop !== val) {
      // Sub-type no longer matches → fall back to top as default value.
      handleFieldUpdate("ticket_type", val, true);
      typeInfoCache.value[val] = { parent: "", ticket_art: ticketArt.value };
    }
  });
}

function handleSubTypeChange(val: string) {
  // Cache parent + art for new value
  if (val) {
    typeInfoCache.value[val] = {
      parent: topLevelTicketType.value || "",
      ticket_art: ticketArt.value || "",
    };
  }
  handleFieldUpdate("ticket_type", val, true);
}
// --- end three-step ticket_type ---

const fieldRefs = ref<Record<string, any>>({});

const setFieldRef = (fieldname: string, el: any) => {
  if (el) {
    fieldRefs.value[fieldname] = el;
  }
};

const showRecentSimilarTickets = computed(() => {
  return (
    !recentSimilarTickets.value.loading &&
    (recentSimilarTickets.value?.data?.recent_tickets?.length ||
      recentSimilarTickets.value?.data?.similar_tickets?.length)
  );
});

useShortcut("t", () => {
  fieldRefs.value?.ticket_type?.$el?.querySelector("button")?.click();
});

useShortcut("p", () => {
  fieldRefs.value?.priority?.$el?.querySelector("button")?.click();
});

useShortcut({ key: "t", shift: true }, () => {
  fieldRefs.value?.agent_group?.$el?.querySelector("button")?.click();
});
</script>

<style scoped>
:deep(.form-control-core button) {
  @apply text-base rounded h-7 py-1.5 border border-outline-gray-2 bg-surface-white placeholder-ink-gray-4 hover:border-outline-gray-3 hover:shadow-sm focus:bg-surface-white focus:border-outline-gray-4 focus:shadow-sm focus:ring-0 focus-visible:ring-0 text-ink-gray-8 transition-colors w-full dark:[color-scheme:dark];
}
:deep(.form-control-core button > div) {
  @apply truncate;
}

:deep(.form-control-core div) {
  width: 100%;
  display: flex;
}

:deep(.form-control-core-select select) {
  @apply text-base rounded h-7 py-1.5 border border-outline-gray-2 bg-surface-white placeholder-ink-gray-4 hover:border-outline-gray-3 hover:shadow-sm focus:bg-surface-white focus:border-outline-gray-4 focus:shadow-sm focus:ring-0 focus-visible:ring-0 text-ink-gray-8 transition-colors w-full dark:[color-scheme:dark];
}
</style>
