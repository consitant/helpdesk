<template>
  <div class="flex flex-col flex-1 overflow-y-auto px-5 py-4 gap-5">
    <!-- Upload-Bereich -->
    <div
      class="rounded-lg border border-dashed border-outline-gray-2 p-4 flex items-center justify-between flex-shrink-0"
    >
      <div class="flex flex-col">
        <span class="text-sm font-medium text-ink-gray-8">Datei hochladen</span>
        <span class="text-xs text-ink-gray-5">
          Die Datei wird direkt am Ticket angehängt.
        </span>
      </div>
      <div>
        <input
          ref="fileInputRef"
          type="file"
          class="hidden"
          @change="onFileSelected"
        />
        <Button
          label="Datei auswählen"
          variant="solid"
          :loading="uploading"
          @click="fileInputRef?.click()"
        />
      </div>
    </div>

    <!-- Liste -->
    <div class="flex-1">
      <div
        v-if="attachments.loading && !attachments.data"
        class="flex items-center justify-center flex-col py-10"
      >
        <Button :loading="true" variant="ghost" size="2xl" />
      </div>
      <div
        v-else-if="!attachments.data?.length"
        class="text-sm text-ink-gray-5 py-10 text-center"
      >
        Keine Anlagen — laden Sie eine Datei hoch oder warten Sie auf den nächsten Mail-Eingang.
      </div>
      <table v-else class="w-full text-sm">
        <thead>
          <tr class="text-left text-ink-gray-5 border-b border-outline-gray-2">
            <th class="py-2 pr-3 font-medium">Datei</th>
            <th class="py-2 pr-3 font-medium text-right">Größe</th>
            <th class="py-2 pr-3 font-medium">Datum</th>
            <th class="py-2 font-medium">Quelle</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in attachments.data"
            :key="row.name"
            class="border-b border-outline-gray-1 align-top"
          >
            <td class="py-2 pr-3">
              <a
                :href="row.file_url"
                target="_blank"
                rel="noopener"
                class="text-ink-gray-9 hover:underline flex items-center gap-2"
                :title="row.file_name"
              >
                <span class="text-base">{{ fileEmoji(row.file_name) }}</span>
                <span class="truncate max-w-[320px]">{{ row.file_name }}</span>
              </a>
            </td>
            <td class="py-2 pr-3 text-right text-ink-gray-7">
              {{ formatSize(row.file_size) }}
            </td>
            <td class="py-2 pr-3 text-ink-gray-7">
              {{ formatDate(row.source_date || row.creation) }}
            </td>
            <td class="py-2 text-ink-gray-7">
              <Badge
                :theme="row.source === 'ticket' ? 'blue' : 'gray'"
                :label="sourceLabel(row)"
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
import { Badge, Button, createResource, toast } from "frappe-ui";
import { ref, watch } from "vue";

const props = defineProps<{ ticketId: string }>();

const fileInputRef = ref<HTMLInputElement | null>(null);
const uploading = ref(false);

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

function sourceLabel(row: any): string {
  const date = formatDate(row.source_date || row.creation);
  if (row.source === "communication") {
    return `aus Mail vom ${date}`;
  }
  return `direkt hochgeladen am ${date}`;
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
    // Frappe CSRF: aus window.csrf_token wenn vorhanden
    const csrf = (window as any).csrf_token || "";

    const resp = await fetch("/api/method/upload_file", {
      method: "POST",
      headers: csrf ? { "X-Frappe-CSRF-Token": csrf } : undefined,
      body: form,
    });
    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(text || `Upload fehlgeschlagen (${resp.status})`);
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
</script>
