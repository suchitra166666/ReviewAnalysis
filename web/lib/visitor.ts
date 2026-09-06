const KEY = "rap_vid";

export function visitorId(): string {
  if (typeof window === "undefined") return "";
  let id = window.localStorage.getItem(KEY);
  if (!id) {
    id = window.crypto.randomUUID();
    window.localStorage.setItem(KEY, id);
  }
  return id;
}

export function visitorHeaders(): HeadersInit {
  const id = visitorId();
  return id ? { "X-Visitor-Id": id } : {};
}
