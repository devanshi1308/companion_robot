import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Pressable, SafeAreaView, Text, View, StyleSheet } from "react-native";
import { StatusBar } from "expo-status-bar";
import { Screen } from "./src/components/ui";
import Welcome from "./src/screens/Welcome";
import Login from "./src/screens/Login";
import Home from "./src/screens/Home";
import Live from "./src/screens/Live";
import Talk from "./src/screens/Talk";
import { loadSession, saveSession, Session } from "./src/api";
import { useRobot } from "./src/useRobot";
import { askPermission } from "./src/notify";
import { C } from "./src/theme";

const TABS = ["Home", "Live", "Talk"];

function Main({ session, onOut }: { session: Session; onOut: () => void }) {
  const [tab, setTab] = useState("Home");
  const { api, state, layout, events, online } = useRobot(session, onOut);
  useEffect(() => { askPermission(); }, []);
  const urgent = state?.alert?.level >= 2;
  return (
    <Screen><SafeAreaView style={{ flex: 1 }}>
      {urgent && <View style={s.banner}><Text style={s.bannerText}>{state.alert.title}</Text></View>}
      <View style={{ flex: 1 }}>
        {tab === "Home" && <Home name={session.user.display} state={state} events={events} online={online} go={setTab} />}
        {tab === "Live" && <Live api={api} state={state} layout={layout} />}
        {tab === "Talk" && <Talk api={api} events={events} />}
      </View>
      <View style={s.tabs}>
        {TABS.map((t) => (
          <Pressable key={t} onPress={() => setTab(t)} style={[s.tab, tab === t && s.tabOn]} accessibilityRole="tab" accessibilityLabel={t}>
            <Text style={[s.tabText, tab === t && { color: "#fff" }]}>{t}</Text>
          </Pressable>
        ))}
        <Pressable onPress={onOut} style={s.tab} accessibilityLabel="Sign out"><Text style={s.tabText}>Sign out</Text></Pressable>
      </View>
    </SafeAreaView></Screen>
  );
}

export default function App() {
  const [boot, setBoot] = useState(true);
  const [stage, setStage] = useState<"welcome" | "login" | "main">("welcome");
  const [session, setSession] = useState<Session | null>(null);
  const [lastUrl, setLastUrl] = useState("");
  useEffect(() => { loadSession().then((s) => { if (s) { setSession(s); setLastUrl(s.url); setStage("main"); } setBoot(false); }); }, []);
  const out = useCallback(() => { saveSession(null); setSession(null); setStage("login"); }, []);
  if (boot) return <Screen><View style={{ flex: 1, justifyContent: "center" }}><ActivityIndicator color={C.accentSoft} /></View></Screen>;
  return (
    <>
      <StatusBar style="light" />
      {stage === "welcome" && <Welcome onStart={() => setStage("login")} />}
      {stage === "login" && <Login initialUrl={lastUrl} onBack={() => setStage("welcome")} onDone={(s) => { saveSession(s); setSession(s); setStage("main"); }} />}
      {stage === "main" && session && <Main session={session} onOut={out} />}
    </>
  );
}
const s = StyleSheet.create({
  banner: { backgroundColor: C.danger, padding: 12 },
  bannerText: { color: "#fff", fontWeight: "800", textAlign: "center" },
  tabs: { position: "absolute", left: 16, right: 16, bottom: 18, flexDirection: "row", backgroundColor: "rgba(20,8,48,0.92)", borderRadius: 28, borderWidth: 1, borderColor: C.cardBorder, padding: 6, gap: 4 },
  tab: { flex: 1, paddingVertical: 12, borderRadius: 22, alignItems: "center" },
  tabOn: { backgroundColor: C.accent },
  tabText: { color: C.muted, fontWeight: "700", fontSize: 13 },
});
