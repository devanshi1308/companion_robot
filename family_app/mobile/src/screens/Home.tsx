import React from "react";
import { ScrollView, Text, View, StyleSheet } from "react-native";
import { Card, Chip, RobotArt } from "../components/ui";
import { KIND } from "../useRobot";
import { C } from "../theme";

export default function Home({ name, state, events, online, go }: { name: string; state: any; events: any[]; online: boolean; go: (t: string) => void }) {
  const hour = new Date().getHours();
  const greet = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
  const live = state && !state.waiting;
  const lvl = live ? state.alert?.level ?? 0 : 0;
  const tone = lvl >= 2 ? "danger" : lvl === 1 ? "warn" : "ok";
  const history = events.filter((e) => e.type === "sent").slice(-6).reverse();
  const meds = (state?.doses || []).filter((d: any) => !d.welfare);
  return (
    <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 110 }}>
      <View style={s.row}>
        <View style={{ flex: 1 }}>
          <Text style={s.greet}>{greet}, {name}</Text>
          <Text style={s.sub}>{live ? `${state.patient} is ${state.person?.posture || "at home"}` : "Waiting for the robot"}</Text>
        </View>
        <Chip text={online ? (live ? "Live" : "Waiting") : "Offline"} tone={online ? (live ? "ok" : "warn") : "danger"} />
      </View>

      <Card style={{ marginTop: 18, borderColor: C[tone] }}>
        <View style={s.row}>
          <View style={{ flex: 1 }}>
            <Text style={[s.cardTitle, { color: C[tone] }]}>{live ? state.alert?.title : "No data yet"}</Text>
            <Text style={s.sub}>{live ? `Baymax is ${state.robot.state_label.toLowerCase()} in the ${state.robot.room.toLowerCase()}` : "Start the demo on the Mac"}</Text>
            {live && <Text style={[s.sub, { marginTop: 4 }]}>Feels {state.robot.feeling?.label}</Text>}
          </View>
          <RobotArt size={86} mood={state?.robot?.feeling?.label} />
        </View>
      </Card>

      <View style={[s.row, { gap: 12, marginTop: 14 }]}>
        <Card style={{ flex: 1, minHeight: 120 }} onPress={() => go("Live")}>
          <Text style={s.big}>See live</Text><Text style={s.sub}>Floor plan with Baymax and Asha</Text>
        </Card>
        <Card style={{ flex: 1, minHeight: 120 }} onPress={() => go("Talk")}>
          <Text style={s.big}>Talk</Text><Text style={s.sub}>Ask how she is, or tell her something</Text>
        </Card>
      </View>

      <Text style={s.section}>Medicine</Text>
      <Card>
        {meds.length === 0 ? <Text style={s.sub}>No reminder yet today.</Text> : meds.map((d: any, i: number) => (
          <View key={i} style={{ marginBottom: 6 }}>
            <Text style={s.cardTitle}>{d.label}</Text>
            <Chip text={d.status === "taken" ? `Taken, seen ${d.clock_taken}` : d.status === "missed" ? "Missed" : d.status === "acknowledged" ? "Said OK, not seen yet" : "Reminded"} tone={d.status === "taken" ? "ok" : d.status === "missed" ? "danger" : "warn"} />
          </View>
        ))}
      </Card>

      <Text style={s.section}>History</Text>
      {history.length === 0 ? <Card><Text style={s.sub}>Nothing has been sent to you yet.</Text></Card> : history.map((e, i) => (
        <Card key={i} style={{ marginBottom: 10 }}>
          <Text style={[s.cardTitle, { color: ["emergency", "ambulance_call", "siren_on"].includes(e.kind) ? C.danger : C.text }]}>{KIND[e.kind] || e.kind}</Text>
          <Text style={s.sub}>{e.text}</Text>
          <Text style={s.time}>{e.clock}</Text>
        </Card>
      ))}
    </ScrollView>
  );
}
const s = StyleSheet.create({
  row: { flexDirection: "row", alignItems: "center" },
  greet: { color: C.text, fontSize: 24, fontWeight: "800" },
  sub: { color: C.muted, fontSize: 14, lineHeight: 20 },
  big: { color: C.text, fontSize: 20, fontWeight: "800", marginBottom: 6 },
  cardTitle: { color: C.text, fontSize: 16, fontWeight: "700", marginBottom: 2 },
  section: { color: C.text, fontSize: 18, fontWeight: "800", marginTop: 24, marginBottom: 10 },
  time: { color: C.faint, fontSize: 12, marginTop: 6 },
});
