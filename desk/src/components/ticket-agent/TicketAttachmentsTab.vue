<template>
  <div class="flex flex-col flex-1 overflow-y-auto px-5 py-4 gap-5">
    <!-- Upload-Bereich -->
    <div
      class="rounded-lg border border-dashed border-outline-gray-2 p-4 flex items-center justify-between flex-shrink-0 gap-4"
    >
      <div class="flex flex-col">
        <span class="text-sm font-medium text-ink-gray-8">Datei hochladen</span>
        <span class="text-xs text-ink-gray-5">Wird direkt am Ticket angehängt.</span>
      </div>
      <div class="flex items-center gap-3">
        <label v-if="!isPartner" class="flex items-center gap-2 text-xs text-ink-gray-7">
          <input type="checkbox" v-model="uploadPartnerVisible" />
          Für Servicepartner freigeben
        </label>
        <input ref="fileInputRef" type="file" class="hidden" @change="onFileSelected" />
        <Button label="Datei auswählen" variant="solid" :loading="uploading" @click="fileInputRef?.click()" />
      </div>
    </div>

    <div v-if="attachments.loading && !attachments.data" class="flex items-center justify-center flex-col py-10">
      <Button :loading="true" variant="ghost" size="2xl" />
    </div>

    <template v-else>
      <!-- Intern (nur interne Rollen) -->
      <section v-if="!isPartner">
        <div class="flex items-center gap-2 mb-2">
          <span class="text-sm font-semibold text-ink-gray-8">🔒 intern</span>
          <span class="text-xs text-ink-gray-5">({{ internalFiles.length }}) — nur Innendienst/Leitung</span>
        </div>
        <div v-if="!internalFiles.length" class="text-sm text-ink-gray-5 py-3">Keine internen Anlagen.</div>
        <table v-else class="w-full text-sm">
          <tbody>
            <tr v-for="row in internalFiles" :key="row.name" class="border-b border-outline-gray-1 align-top">
              <td class="py-2 pr-3">
                <a :href="row.file_url" target="_blank" rel="noopener" :title="row.file_name"
                   class="text-ink-gray-9 hover:underline flex items-center gap-2">
                  <span class="text-base">{{ fileEmoji(row.file_name) }}</span>
                  <span class="truncate max-w-[280px]">{{ row.file_name }}</span>
                </a>
              </td>
              <td class="py-2 pr-3 text-right text-ink-gray-7 whitespace-nowrap">{{ formatSize(row.file_size) }}</td>
              <td class="py-2 pr-3 text-ink-gray-7 whitespace-nowrap">{{ formatDate(row.source_date || row.creation) }}</td>
              <td class="py-2 pr-3"><Badge :theme="row.source === 'ticket' ? 'blue' : 'gray'" :label="row.source === 'communication' ? 'aus Mail' : 'hochgeladen'" size="sm" /></td>
              <td class="py-2 text-right">
                <Button variant="ghost" size="sm" label="→ Für Servicepartner freigeben" @click="setVisible(row, true)" />
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- Partner-sichtbar -->
      <section>
        <div class="flex items-center gap-2 mb-2">
          <span class="text-sm font-semibold text-ink-gray-8">👥 Für Servicepartner sichtbar</span>
          <span class="text-xs text-ink-gray-5">({{ partnerFiles.length }})</span>
        </div>
        <div v-if="!partnerFiles.length" class="text-sm text-ink-gray-5 py-3">Keine für Servicepartner sichtbaren Anlagen.</div>
        <table v-else class="w-full text-sm">
          <tbody>
            <tr v-for="row in partnerFiles" :key="row.name" class="border-b border-outline-gray-1 align-top">
              <td class="py-2 pr-3">
                <a :href="row.file_url" target="_blank" rel="noopener" :title="row.file_name"
                   class="text-ink-gray-9 hover:underline flex items-center gap-2">
                  <span class="text-base">{{ fileEmoji(row.file_name) }}</span>
                  <span class="truncate max-w-[280px]">{{ row.file_name }}</span>
                </a>
              </td>
              <td class="py-2 pr-3 text-right text-ink-gray-7 whitespace-nowrap">{{ formatSize(row.file_size) }}</td>
              <td class="py-2 pr-3 text-ink-gray-7 whitespace-nowrap">{{ formatDate(row.source_date || row.creation) }}</td>
              <td class="py-2 pr-3"><Badge :theme="row.source === 'ticket' ? 'blue' : 'gray'" :label="row.source === 'communication' ? 'aus Mail' : 'hochgeladen'" size="sm" /></td>
              <td class="py-2 text-right">
                <Button v-if="!isPartner" variant="ghost" size="sm" label="← auf intern setzen" @click="setVisible(row, false)" />
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { Badge, Button, createResource, toast } from "frappe-ui";
import { computed, ref, watch } from "vue";

const props = defineProps<{ ticketId: string }>();

const fileInputRef = ref<HTMLInputElement | null>(null);
const uploading = ref(false);
const uploadPartnerVisible = ref(false);

const partnerCheck = createResource({ url: "axovend.api.is_service_partner", auto: true });
const isPartner = computed(() => !!partnerCheck.data);

const attachments = createResource({
  url: "axovend.api.get_ticket_attachments",
  params: { ticket: props.ticketId },
  auto: true,
});

watch(
  () => props.ticketId,
  (id) => {
    attachments.update({ params: { ticket: id } });
    attachments.reload();
  }
);

const internalFiles = computed(() => (attachments.data || []).filter((r: any) => !r.partner_visible));
const partnerFiles = computed(() => (attachments.data || []).filter((r: any) => r.partner_visible));

const visResource = createResource({ url: "axovend.api.set_attachment_partner_visible" });
function setVisible(row: any, visible: boolean) {
  visResource.submit(
    { file: row.name, visible: visible ? 1 : 0 },
    {
      onSuccess: () => {
        toast.success(visible ? "Für Servicepartner freigegeben." : "Auf intern gesetzt.");
        attachments.reload();
      },
      onError: (e: any) => toast.error(e?.message || "Aktion fehlgeschlagen."),
    }
  );
}

async function onFileSelected(e: Event) {
  const input = e.target as HTMLInputElement;
  const file = input.files && input.files[0];
  if (!file) return;
  uploading.value = true;
  try {
    const form = new FormData();
    form.append("file", file);
    form.append("doctype", "HD Ticket");
    form.append("docname", props.ticketId);
    form.append("is_private", "1");
    form.append("optimize", "0");
    const csrf = (window as any).csrf_token || "";
    const resp = await fetch("/api/method/upload_file", {
      method: "POST",
      headers: csrf ? { "X-Frappe-CSRF-Token": csrf } : undefined,
      body: form,
    });
    if (!resp.ok) throw new Error((await resp.text()) || `Upload fehlgeschlagen (${resp.status})`);
    const data = await resp.json();
    const fileName = data?.message?.name;
    // Partner-Upload bleibt für den Partner sichtbar; intern je nach Checkbox.
    if (fileName && (isPartner.value || uploadPartnerVisible.value)) {
      await visResource.submit({ file: fileName, visible: 1 });
    }
    toast.success("Datei hochgeladen.");
    attachments.reload();
  } catch (err: any) {
    toast.error(err?.message || "Upload fehlgeschlagen.");
  } finally {
    uploading.value = false;
    if (input) input.value = "";
  }
}

function formatSize(bytes: number): string {
  const b = Number(bytes) || 0;
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1024 / 1024).toFixed(2)} MB`;
}
function formatDate(dt: string): string {
  if (!dt) return "—";
  const d = String(dt).slice(0, 10).split("-");
  return d.length === 3 ? `${d[2]}.${d[1]}.${d[0]}` : String(dt);
}
function fileEmoji(name: string): string {
  const n = (name || "").toLowerCase();
  if (n.endsWith(".pdf")) return "📄";
  if (/\.(png|jpe?g|gif|webp|svg|bmp|tiff?)$/.test(n)) return "🖼️";
  if (/\.(docx?|odt|rtf)$/.test(n)) return "📝";
  if (/\.(xlsx?|ods|csv)$/.test(n)) return "📊";
  if (/\.(zip|tar|gz|7z|rar)$/.test(n)) return "🗜️";
  if (/\.(eml|msg)$/.test(n)) return "✉️";
  return "📎";
}
</script>
