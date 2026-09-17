import { ImagePlus, ImageOff, Link2, Loader2, Plus, X } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/misc";
import { t } from "@/i18n/ru";
import { compressImage, hostOf, isSafeUrl, MAX_ATTACHMENTS, MAX_PHOTO_BYTES } from "@/lib/image";
import { cn } from "@/lib/utils";

export interface AttachmentItem {
  id: string;
  kind: "photo" | "link";
  url: string | null | undefined;
  title?: string | null;
  pending?: boolean;
}

const linkSchema = z
  .string()
  .trim()
  .url()
  .refine((v) => /^https?:\/\//i.test(v));

interface Props {
  items: AttachmentItem[];
  onAddPhoto: (file: Blob) => Promise<void> | void;
  onAddLink: (url: string, title: string) => Promise<void> | void;
  onRemove: (id: string) => Promise<void> | void;
  disabled?: boolean;
}

/** Photos and links for one achievement. Used both for a draft (new achievement) and a saved one. */
export function AttachmentsEditor({ items, onAddPhoto, onAddLink, onRemove, disabled }: Props) {
  const fileInput = useRef<HTMLInputElement>(null);
  const [linkOpen, setLinkOpen] = useState(false);
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [urlError, setUrlError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const full = items.length >= MAX_ATTACHMENTS;

  const pickPhoto = async (file: File | undefined) => {
    if (!file) return;
    if (full) return void toast.error(t.attachments.limit);
    setProcessing(true);
    try {
      const blob = await compressImage(file);
      if (blob.size > MAX_PHOTO_BYTES) return void toast.error(t.attachments.tooLarge);
      await onAddPhoto(blob);
    } finally {
      setProcessing(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  };

  const submitLink = async () => {
    const parsed = linkSchema.safeParse(url);
    if (!parsed.success) return setUrlError(t.attachments.invalidUrl);
    if (full) return void toast.error(t.attachments.limit);
    await onAddLink(parsed.data, title.trim());
    setUrl("");
    setTitle("");
    setUrlError(null);
    setLinkOpen(false);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-sm font-semibold">{t.attachments.title}</p>
        <span className="text-xs text-muted-foreground">{t.attachments.counter(items.length, MAX_ATTACHMENTS)}</span>
      </div>
      {items.length === 0 && <p className="text-xs text-muted-foreground">{t.attachments.hint}</p>}

      {items.length > 0 && (
        <ul className="flex flex-wrap gap-2">
          {items.map((item) => (
            <li key={item.id} className="relative">
              {item.kind === "photo" ? (
                <div className="flex h-16 w-16 items-center justify-center overflow-hidden rounded-md border bg-muted">
                  {item.url ? (
                    <img src={item.url} alt={item.title ?? t.attachments.photo} className="h-full w-full object-cover" />
                  ) : (
                    <ImageOff className="h-5 w-5 text-muted-foreground" aria-label={t.attachments.photoUnavailable} />
                  )}
                  {item.pending && (
                    <span className="absolute inset-0 flex items-center justify-center rounded-md bg-background/60">
                      <Loader2 className="h-5 w-5 animate-spin" />
                    </span>
                  )}
                </div>
              ) : (
                <span className="flex h-16 max-w-[12rem] items-center gap-1.5 rounded-md border bg-card px-3 text-xs font-semibold">
                  <Link2 className="h-4 w-4 shrink-0 text-primary" />
                  <span className="truncate">{item.title || (item.url ? hostOf(item.url) : "")}</span>
                </span>
              )}
              <button
                type="button"
                onClick={() => onRemove(item.id)}
                disabled={disabled || item.pending}
                aria-label={t.attachments.remove}
                className="absolute -right-1.5 -top-1.5 flex h-6 w-6 items-center justify-center rounded-full border bg-card shadow disabled:opacity-50"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="flex flex-wrap gap-2">
        <input
          ref={fileInput}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/heic,image/heif"
          className="hidden"
          onChange={(e) => void pickPhoto(e.target.files?.[0])}
        />
        <Button type="button" size="sm" variant="outline" disabled={disabled || full || processing} onClick={() => fileInput.current?.click()}>
          {processing ? <Loader2 className="animate-spin" /> : <ImagePlus />} {t.attachments.addPhoto}
        </Button>
        <Button type="button" size="sm" variant="outline" disabled={disabled || full} onClick={() => setLinkOpen((o) => !o)}>
          <Link2 /> {t.attachments.addLink}
        </Button>
      </div>

      {linkOpen && (
        <div className={cn("space-y-2 rounded-md border p-3")}>
          <Input
            type="url"
            inputMode="url"
            placeholder={t.attachments.linkUrl}
            value={url}
            onChange={(e) => {
              setUrl(e.target.value);
              setUrlError(null);
            }}
            aria-invalid={!!urlError}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void submitLink();
              }
            }}
          />
          <Input placeholder={t.attachments.linkTitle} value={title} maxLength={120} onChange={(e) => setTitle(e.target.value)} />
          {urlError && <p className="text-xs text-blocker">{urlError}</p>}
          <Button type="button" size="sm" onClick={() => void submitLink()} disabled={disabled}>
            <Plus /> {t.attachments.linkAdd}
          </Button>
        </div>
      )}
    </div>
  );
}

export { isSafeUrl };
