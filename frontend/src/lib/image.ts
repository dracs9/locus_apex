export const MAX_PHOTO_BYTES = 5 * 1024 * 1024;
export const MAX_ATTACHMENTS = 5;
const MAX_SIDE = 1600;

/** Scales (width, height) down so the longer side is at most `max`; never scales up. */
export function fitSize(width: number, height: number, max = MAX_SIDE): { width: number; height: number } {
  const longer = Math.max(width, height);
  if (longer <= max || longer === 0) return { width, height };
  const k = max / longer;
  return { width: Math.round(width * k), height: Math.round(height * k) };
}

/**
 * Downscales a photo in the browser to ~1600px JPEG before upload.
 * If the browser can't decode it (e.g. HEIC outside Safari) the original file is returned.
 */
export async function compressImage(file: File): Promise<Blob> {
  try {
    const bitmap = await createImageBitmap(file);
    const { width, height } = fitSize(bitmap.width, bitmap.height);
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    canvas.getContext("2d")?.drawImage(bitmap, 0, 0, width, height);
    bitmap.close();
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
    return blob && blob.size < file.size ? blob : file;
  } catch {
    return file;
  }
}

export function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

/** Only http(s) links are ever rendered as clickable. */
export function isSafeUrl(url: string | null | undefined): url is string {
  return !!url && /^https?:\/\//i.test(url);
}
