import { useEffect, useRef, useState } from "react";
import { client, Session } from "./api";
import { alertNow } from "./notify";

export const KIND: Record<string, string> = {
  heads_up: "Possible fall", emergency: "URGENT: emergency", ambulance_call: "Ambulance call (simulated)", update: "Update",
  all_clear: "All clear", reminder_missed: "Reminder missed", welfare_missed: "She did not answer", medicine_taken: "Tablet taken",
  medicine_acknowledged: "Said OK, not seen", siren_on: "Siren sounding",
};
const URGENT = ["emergency", "ambulance_call", "siren_on"];

export function useRobot(session: Session, onSignedOut: () => void) {
  const api = useRef(client(session)).current;
  const [state, setState] = useState<any>(null);
  const [layout, setLayout] = useState<any>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [online, setOnline] = useState(true);
  const next = useRef(0);
  const first = useRef(true);

  useEffect(() => {
    let dead = false;
    api.layout().then(setLayout).catch(() => {});
    const tick = async () => {
      try {
        const [st, ev] = await Promise.all([api.state(), api.events(next.current)]);
        if (dead) return;
        setOnline(true); setState(st);
        if (ev.events?.length) {
          setEvents((old) => [...old, ...ev.events].slice(-300));
          if (!first.current) for (const e of ev.events) {
            if (e.type === "sent") alertNow(KIND[e.kind] || "Baymax", e.text, URGENT.includes(e.kind));
          }
        }
        next.current = ev.next ?? next.current; first.current = false;
      } catch (e: any) {
        if (e.message === "signed-out") onSignedOut(); else setOnline(false);
      }
    };
    tick(); const id = setInterval(tick, 1000);
    return () => { dead = true; clearInterval(id); };
  }, [api, onSignedOut]);

  return { api, state, layout, events, online };
}
