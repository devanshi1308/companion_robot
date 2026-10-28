import AsyncStorage from "@react-native-async-storage/async-storage";

export type Session = { url: string; token: string; user: { id: string; display: string } };
const KEY = "baymax_session_v1";

export async function loadSession(): Promise<Session | null> {
  try { const s = await AsyncStorage.getItem(KEY); return s ? JSON.parse(s) : null; } catch { return null; }
}
export async function saveSession(s: Session | null) {
  try { if (s) await AsyncStorage.setItem(KEY, JSON.stringify(s)); else await AsyncStorage.removeItem(KEY); } catch {}
}
export function clean(url: string) {
  let u = url.trim().replace(/\/+$/, "");
  if (!/^https?:\/\//.test(u)) u = "http://" + u;
  return u;
}
export async function login(url: string, user: string, password: string): Promise<Session> {
  const base = clean(url);
  const r = await fetch(base + "/api/login", {
    method: "POST", headers: { "Content-Type": "application/json", "X-Client": "mobile" }, body: JSON.stringify({ user, password }),
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok || !j.token) throw new Error(j.error || "Could not sign in");
  return { url: base, token: j.token, user: j.user };
}
export function client(s: Session) {
  const h = { Authorization: "Bearer " + s.token, "Content-Type": "application/json" };
  const get = async (p: string) => {
    const r = await fetch(s.url + p, { headers: h });
    if (r.status === 401) throw new Error("signed-out");
    return r.json();
  };
  const post = async (p: string, body: any) => {
    const r = await fetch(s.url + p, { method: "POST", headers: h, body: JSON.stringify(body) });
    if (r.status === 401) throw new Error("signed-out");
    return r.json();
  };
  return {
    state: () => get("/api/state"), layout: () => get("/api/layout"), events: (since: number) => get("/api/events?since=" + since),
    chat: (text: string) => post("/api/chat", { text }), command: (cmd: string, args?: any) => post("/api/command", { cmd, args }),
    snapshotUri: (view?: string) => s.url + "/api/snapshot" + (view ? "?view=" + view + "&" : "?") + "t=" + Date.now(),
    headers: { Authorization: "Bearer " + s.token },
  };
}
