import React, { useState } from "react";
import { ScrollView, Text, View, Image, StyleSheet, useWindowDimensions } from "react-native";
import { Card, FloorPlan, Button, Chip } from "../components/ui";
import { C } from "../theme";

export default function Live({ api, state, layout }: { api: any; state: any; layout: any }) {
  const { width } = useWindowDimensions();
  const [note, setNote] = useState("");
  const [pic, setPic] = useState<string | null>(null);
  const live = state && !state.waiting;
  const act = async (cmd: string, args?: any, msg?: string) => { try { await api.command(cmd, args); setNote(msg || "Sent to Baymax"); } catch { setNote("Could not reach the server"); } };
  return (
    <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 110 }}>
      <Text style={s.h1}>Live view</Text>
      <Text style={s.sub}>A floor plan of the flat, updated every second. No camera video is streamed.</Text>
      <Card style={{ marginTop: 14, alignItems: "center", padding: 8 }}>
        {layout ? <FloorPlan layout={layout} state={state} width={width - 56} /> : <Text style={s.sub}>Loading plan...</Text>}
      </Card>
      <View style={{ flexDirection: "row", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
        <Chip text="Baymax" tone="info" /><Chip text="Asha" tone="ok" /><Chip text="Asha on the floor" tone="danger" />
      </View>
      {live && (
        <Card style={{ marginTop: 14 }}>
          <Text style={s.sub}>Baymax: {state.robot.state_label} in the {state.robot.room}</Text>
          <Text style={s.sub}>Asha: {state.person?.posture || "not in view"}{state.person?.seen_now ? "" : " (last known)"}</Text>
          {state.siren?.on && <Text style={[s.sub, { color: C.danger, marginTop: 6 }]}>Siren is sounding</Text>}
        </Card>
      )}
      <Text style={s.h2}>Ask Baymax</Text>
      <View style={{ gap: 10 }}>
        <Button label="Check on her now" kind="ghost" onPress={() => act("check", undefined, "Baymax is checking in")} />
        <Button label="Remind her about her tablet" kind="ghost" onPress={() => act("remind", undefined, "Reminder started")} />
        <Button label="Look up and down (picture)" kind="ghost" onPress={async () => { await act("snapshot", { view: "both" }, "Picture requested (needs her consent setting)"); setTimeout(() => setPic(api.snapshotUri("above")), 4000); }} />
        {state?.siren?.on && <Button label="Silence the siren" kind="danger" onPress={() => act("siren_off", undefined, "Siren silenced")} />}
      </View>
      {!!note && <Text style={[s.sub, { marginTop: 10, color: C.accentSoft }]}>{note}</Text>}
      {pic && <Image source={{ uri: pic, headers: api.headers }} style={{ width: width - 40, height: 200, borderRadius: 16, marginTop: 12 }} resizeMode="cover" />}
    </ScrollView>
  );
}
const s = StyleSheet.create({
  h1: { color: C.text, fontSize: 26, fontWeight: "800" },
  h2: { color: C.text, fontSize: 18, fontWeight: "800", marginTop: 24, marginBottom: 10 },
  sub: { color: C.muted, fontSize: 14, lineHeight: 20 },
});
