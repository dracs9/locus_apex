/** Lets non-component code (toasts in api/hooks.ts) navigate without importing the router. */
let navigator: ((path: string) => void) | null = null;

export function setNavigator(fn: (path: string) => void) {
  navigator = fn;
}

export function navigateTo(path: string) {
  if (navigator) navigator(path);
  else window.location.assign(path);
}
