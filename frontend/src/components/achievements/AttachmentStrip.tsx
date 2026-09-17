import { ExternalLink, ImageOff, Link2 } from "lucide-react";
import { useState } from "react";

import type { Attachment } from "@/api/types";
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet";
import { t } from "@/i18n/ru";
import { hostOf, isSafeUrl } from "@/lib/image";

function Thumb({ photo, onOpen }: { photo: Attachment; onOpen: () => void }) {
  const [broken, setBroken] = useState(false);
  if (!photo.url || broken) {
    return (
      <span title={t.attachments.photoUnavailable} className="flex h-14 w-14 items-center justify-center rounded-md border bg-muted text-muted-foreground">
        <ImageOff className="h-4 w-4" aria-label={t.attachments.photoUnavailable} />
      </span>
    );
  }
  return (
    <button type="button" onClick={onOpen} aria-label={t.attachments.open} className="h-14 w-14 overflow-hidden rounded-md border bg-muted">
      <img src={photo.url} alt={photo.title ?? t.attachments.photo} loading="lazy" onError={() => setBroken(true)} className="h-full w-full object-cover" />
    </button>
  );
}

/** Read-only photos and links of an achievement, with a full-size photo viewer. */
export function AttachmentStrip({ attachments }: { attachments: Attachment[] | undefined }) {
  const [open, setOpen] = useState<Attachment | null>(null);
  if (!attachments?.length) return null;
  const photos = attachments.filter((a) => a.kind === "photo");
  const links = attachments.filter((a) => a.kind === "link" && isSafeUrl(a.url));

  return (
    <div className="mt-2 space-y-2">
      {photos.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {photos.map((p) => (
            <Thumb key={p.id} photo={p} onOpen={() => setOpen(p)} />
          ))}
        </div>
      )}
      {links.length > 0 && (
        <ul className="flex flex-wrap gap-1.5">
          {links.map((l) => (
            <li key={l.id}>
              <a
                href={l.url!}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex max-w-[16rem] items-center gap-1.5 rounded-full border bg-card px-2.5 py-1 text-xs font-semibold text-primary hover:bg-muted"
              >
                <Link2 className="h-3.5 w-3.5 shrink-0" />
                <span className="truncate">{l.title || hostOf(l.url!)}</span>
                <ExternalLink className="h-3 w-3 shrink-0" />
              </a>
            </li>
          ))}
        </ul>
      )}

      <Sheet open={!!open} onOpenChange={(o) => !o && setOpen(null)}>
        <SheetContent>
          <SheetTitle>{open?.title || t.attachments.photo}</SheetTitle>
          <SheetDescription className="sr-only">{t.attachments.open}</SheetDescription>
          {open?.url && <img src={open.url} alt={open.title ?? t.attachments.photo} className="max-h-[70dvh] w-full rounded-md object-contain" />}
        </SheetContent>
      </Sheet>
    </div>
  );
}
