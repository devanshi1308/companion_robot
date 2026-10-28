import React, { useEffect, useRef, useState } from "react";
import { FlatList, KeyboardAvoidingView, Platform, Text, TextInput, View, Pressable, StyleSheet } from "react-native";
import * as Speech from "expo-speech";
import { Orb } from "../components/ui";
import { C } from "../theme";

export default function Talk({ api, events }: { api: any; events: any[] }) {
  const [text, setText] = useState("");
  const [speak, setSpeak] = useState(true);
  const [busy, setBusy] = useState(false);
  const list = useRef<FlatList>(null);
  const spoken = useRef(new Set<string>());
  const msgs = events.filter((e) => e.type === "chat" || e.type === "sent");
  useEffect(() => {
    const last = msgs[msgs.length - 1];
    if (!last) return;
    const k = last.type + last.kind + last.t + last.text;
    if (spoken.current.has(k)) return;
    spoken.current.add(k);
    if (speak && last.who !== "user" && spoken.current.size > 1) Speech.speak(last.text, { rate: 0.92, pitch: 0.9 });
    setBusy(false);
    setTimeout(() => list.current?.scrollToEnd({ animated: true }), 50);
  }, [msgs.length]);
  const send = async () => {
    const t = text.trim(); if (!t) return;
    setText(""); setBusy(true);
    try { await api.chat(t); } catch { setBusy(false); }
  };
  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1 }} keyboardVerticalOffset={90}>
      <View style={{ alignItems: "center", marginTop: -20, height: 170, justifyContent: "center" }}><Orb active={busy} size={110} /></View>
      <View style={s.head}><Text style={s.h1}>Talk to Baymax</Text>
        <Pressable onPress={() => { setSpeak(!speak); Speech.stop(); }} accessibilityLabel="Toggle voice"><Text style={s.toggle}>{speak ? "Voice on" : "Voice off"}</Text></Pressable></View>
      <FlatList ref={list} data={msgs} keyExtractor={(_, i) => String(i)} contentContainerStyle={{ padding: 16, paddingBottom: 12 }}
        ListEmptyComponent={<Text style={s.empty}>Try: "Did she take her tablet?" or "Where is she?"</Text>}
        renderItem={({ item }) => {
          const me = item.type === "chat" && item.who === "user";
          const urgent = item.type === "sent" && ["emergency", "siren_on"].includes(item.kind);
          return (
            <View style={[s.bub, me ? s.me : s.them, urgent && { borderColor: C.danger, borderWidth: 1 }]}>
              {!me && <Text style={s.who}>Baymax</Text>}
              <Text style={s.msg}>{item.text}</Text>
              <Text style={s.time}>{item.clock}</Text>
            </View>
          );
        }} />
      <View style={s.bar}>
        <TextInput value={text} onChangeText={setText} placeholder="Message Baymax" placeholderTextColor={C.faint} style={s.input} onSubmitEditing={send} returnKeyType="send" />
        <Pressable onPress={send} style={s.send} accessibilityLabel="Send"><Text style={{ color: "#fff", fontWeight: "800" }}>Send</Text></Pressable>
      </View>
      <View style={{ height: 90 }} />
    </KeyboardAvoidingView>
  );
}
const s = StyleSheet.create({
  head: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: 20 },
  h1: { color: C.text, fontSize: 22, fontWeight: "800" },
  toggle: { color: C.accentSoft, fontWeight: "700" },
  empty: { color: C.faint, textAlign: "center", marginTop: 30 },
  bub: { maxWidth: "82%", padding: 12, borderRadius: 18, marginBottom: 10 },
  me: { alignSelf: "flex-end", backgroundColor: C.accent },
  them: { alignSelf: "flex-start", backgroundColor: "rgba(255,255,255,0.1)" },
  who: { color: C.accentSoft, fontSize: 12, fontWeight: "700", marginBottom: 2 },
  msg: { color: C.text, fontSize: 15, lineHeight: 21 },
  time: { color: C.muted, fontSize: 11, marginTop: 4, alignSelf: "flex-end" },
  bar: { flexDirection: "row", gap: 8, paddingHorizontal: 16 },
  input: { flex: 1, color: C.text, backgroundColor: "rgba(255,255,255,0.1)", borderRadius: 24, paddingHorizontal: 16, paddingVertical: 12, borderColor: C.cardBorder, borderWidth: 1 },
  send: { backgroundColor: C.accent, borderRadius: 24, paddingHorizontal: 18, justifyContent: "center" },
});
