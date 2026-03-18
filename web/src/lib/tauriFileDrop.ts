/**
 * Module-level singleton for Tauri file drop events.
 * Registers the OS-level listener exactly once for the lifetime of the app.
 * DropZone components register/unregister a callback to receive dropped files.
 */

type DropCallback = (files: File[], dragOver: boolean) => void;

let listenerRegistered = false;
let activeCallback: DropCallback | null = null;
const pendingPaths: string[] = [];
let batchTimer: ReturnType<typeof setTimeout> | null = null;

async function flushPaths() {
  const paths = [...pendingPaths];
  pendingPaths.length = 0;
  if (!activeCallback) return;

  const { readBinaryFile } = await import("@tauri-apps/api/fs");
  const files: File[] = [];
  for (const filePath of paths) {
    try {
      const bytes = await readBinaryFile(filePath);
      const name = filePath.replace(/\\/g, "/").split("/").pop() ?? "file";
      files.push(new File([bytes], name));
    } catch (err) {
      console.warn("Could not read dropped file:", filePath, err);
    }
  }
  if (files.length && activeCallback) activeCallback(files, false);
}

async function ensureListener() {
  if (listenerRegistered) return;
  listenerRegistered = true;

  const { appWindow } = await import("@tauri-apps/api/window");

  await appWindow.onFileDropEvent((event) => {
    if (event.payload.type === "hover") {
      activeCallback?.([], true);
      return;
    }
    if (event.payload.type === "cancel") {
      activeCallback?.([], false);
      return;
    }
    if (event.payload.type === "drop") {
      activeCallback?.([], false); // clear hover immediately
      pendingPaths.push(...(event.payload.paths as string[]));
      if (batchTimer) clearTimeout(batchTimer);
      batchTimer = setTimeout(flushPaths, 80);
    }
  });
}

export function registerDropZone(cb: DropCallback) {
  activeCallback = cb;
  ensureListener().catch(console.error);
}

export function unregisterDropZone() {
  activeCallback = null;
}
