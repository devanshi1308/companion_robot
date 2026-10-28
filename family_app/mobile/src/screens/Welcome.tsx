import React from "react";
import { Text, View, SafeAreaView, StyleSheet } from "react-native";
import { Screen, RobotArt, Button } from "../components/ui";
import { C } from "../theme";

export default function Welcome({ onStart }: { onStart: () => void }) {
  return (
    <Screen><SafeAreaView style={{ flex: 1, padding: 24, justifyContent: "space-between" }}>
      <View style={{ alignItems: "center", marginTop: 40 }}>
        <View style={s.bubble}><Text style={s.bubbleText}>Need help?</Text></View>
        <RobotArt size={190} />
      </View>
      <View>
        <Text style={s.title}>Baymax is looking after Asha</Text>
        <Text style={s.sub}>See where she is, hear what Baymax says, and get told straight away if something is wrong. Simulation only: no real calls are made.</Text>
        <View style={{ height: 22 }} />
        <Button label="Get started" onPress={onStart} />
      </View>
    </SafeAreaView></Screen>
  );
}
const s = StyleSheet.create({
  bubble: { backgroundColor: "rgba(255,255,255,0.12)", borderColor: C.cardBorder, borderWidth: 1, borderRadius: 18, paddingHorizontal: 16, paddingVertical: 8, marginBottom: 14 },
  bubbleText: { color: C.text, fontWeight: "600" },
  title: { color: C.text, fontSize: 30, fontWeight: "800", lineHeight: 36 },
  sub: { color: C.muted, fontSize: 15, marginTop: 10, lineHeight: 22 },
});
