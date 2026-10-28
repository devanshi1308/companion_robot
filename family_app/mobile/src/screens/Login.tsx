import React, { useState } from "react";
import { Text, TextInput, View, SafeAreaView, StyleSheet, KeyboardAvoidingView, Platform, ActivityIndicator } from "react-native";
import { Screen, Button, Card } from "../components/ui";
import { login, Session } from "../api";
import { C } from "../theme";

export default function Login({ initialUrl, onDone, onBack }: { initialUrl: string; onDone: (s: Session) => void; onBack: () => void }) {
  const [url, setUrl] = useState(initialUrl || "http://192.168.1.6:8765");
  const [user, setUser] = useState("");
  const [pw, setPw] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const go = async () => {
    setBusy(true); setErr("");
    try { onDone(await login(url, user.trim().toLowerCase(), pw)); }
    catch (e: any) { setErr(e.message?.includes("Network") ? "Cannot reach the server. Same Wi-Fi? Is run_app.sh --lan running?" : e.message); }
    setBusy(false);
  };
  return (
    <Screen><SafeAreaView style={{ flex: 1 }}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1, padding: 24, justifyContent: "center" }}>
        <Text style={s.h1}>Sign in</Text>
        <Text style={s.sub}>Family members only. Each person sees only their own messages.</Text>
        <Card style={{ marginTop: 20, gap: 10 }}>
          <Text style={s.label}>Server address</Text>
          <TextInput value={url} onChangeText={setUrl} autoCapitalize="none" autoCorrect={false} keyboardType="url" style={s.input} placeholderTextColor={C.faint} />
          <Text style={s.label}>Username</Text>
          <TextInput value={user} onChangeText={setUser} autoCapitalize="none" autoCorrect={false} style={s.input} placeholder="rohan" placeholderTextColor={C.faint} />
          <Text style={s.label}>Password</Text>
          <TextInput value={pw} onChangeText={setPw} secureTextEntry style={s.input} placeholder="demo password" placeholderTextColor={C.faint} onSubmitEditing={go} />
          {!!err && <Text style={s.err}>{err}</Text>}
        </Card>
        <View style={{ height: 18 }} />
        {busy ? <ActivityIndicator color={C.accentSoft} /> : <Button label="Sign in" onPress={go} disabled={!user || !pw} />}
        <View style={{ height: 10 }} />
        <Button label="Back" kind="ghost" onPress={onBack} />
      </KeyboardAvoidingView>
    </SafeAreaView></Screen>
  );
}
const s = StyleSheet.create({
  h1: { color: C.text, fontSize: 32, fontWeight: "800" },
  sub: { color: C.muted, marginTop: 6, lineHeight: 20 },
  label: { color: C.muted, fontSize: 12, fontWeight: "600", marginTop: 4 },
  input: { color: C.text, backgroundColor: "rgba(255,255,255,0.08)", borderRadius: 14, paddingHorizontal: 14, paddingVertical: 12, fontSize: 16, borderWidth: 1, borderColor: C.cardBorder },
  err: { color: C.danger, marginTop: 4 },
});
