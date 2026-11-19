/** Opens a web page or mailto: link outside the app. */
export function openExternal(url: string) {
  if (window.tuttle?.openExternal) window.tuttle.openExternal(url);
  else window.open(url, "_blank");
}

/** Opens a new message to `address` in the default mail client. */
export function composeEmail(address: string) {
  openExternal(`mailto:${encodeURIComponent(address.trim()).replace(/%40/g, "@")}`);
}
