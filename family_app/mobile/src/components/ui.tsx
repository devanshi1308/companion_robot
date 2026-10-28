import React, { useEffect, useRef } from "react";
import { Animated, Easing, Pressable, StyleSheet, Text, View, ViewStyle } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import Svg, { Circle, Ellipse, Path, Rect, Line, Polygon, G, Defs, RadialGradient, Stop } from "react-native-svg";
import { C, R } from "../theme";

export function Screen({ children }: { children: React.ReactNode }) {
  return <LinearGradient colors={[C.bgTop, C.bgMid, C.bgBottom]} style={{ flex: 1 }}>{children}</LinearGradient>;
}

export function Card({ children, style, onPress }: { children: React.ReactNode; style?: ViewStyle; onPress?: () => void }) {
  const body = <View style={[s.card, style]}>{children}</View>;
  return onPress ? <Pressable onPress={onPress} style={({ pressed }) => ({ opacity: pressed ? 0.8 : 1 })}>{body}</Pressable> : body;
}

export function Button({ label, onPress, kind = "primary", disabled }: { label: string; onPress: () => void; kind?: "primary" | "ghost" | "danger"; disabled?: boolean }) {
  const bg = kind === "primary" ? C.accent : kind === "danger" ? C.danger : "transparent";
  return (
    <Pressable onPress={onPress} disabled={disabled} accessibilityRole="button" accessibilityLabel={label}
      style={({ pressed }) => [s.btn, { backgroundColor: bg, borderColor: kind === "ghost" ? C.cardBorder : bg, opacity: disabled ? 0.45 : pressed ? 0.85 : 1 }]}>
      <Text style={s.btnText}>{label}</Text>
    </Pressable>
  );
}

export function Chip({ text, tone = "info" }: { text: string; tone?: "ok" | "warn" | "danger" | "info" }) {
  const col = C[tone];
  return <View style={[s.chip, { borderColor: col }]}><View style={[s.dot, { backgroundColor: col }]} /><Text style={[s.chipText, { color: col }]}>{text}</Text></View>;
}

/** Baymax-style robot: white egg head, two eyes joined by a line, teal body. */
export function RobotArt({ size = 160, mood = "calm" }: { size?: number; mood?: string }) {
  const bob = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    const a = Animated.loop(Animated.sequence([
      Animated.timing(bob, { toValue: 1, duration: 1600, easing: Easing.inOut(Easing.sin), useNativeDriver: true }),
      Animated.timing(bob, { toValue: 0, duration: 1600, easing: Easing.inOut(Easing.sin), useNativeDriver: true })]));
    a.start(); return () => a.stop();
  }, [bob]);
  const eye = mood === "alarmed" ? C.danger : mood === "worried" || mood === "concerned" ? C.warn : "#1b1033";
  return (
    <Animated.View style={{ transform: [{ translateY: bob.interpolate({ inputRange: [0, 1], outputRange: [0, -8] }) }] }}>
      <Svg width={size} height={size * 1.15} viewBox="0 0 160 184">
        <Defs><RadialGradient id="g" cx="50%" cy="35%" r="70%"><Stop offset="0" stopColor="#ffffff" /><Stop offset="1" stopColor="#d9d2f5" /></RadialGradient></Defs>
        <Ellipse cx="80" cy="170" rx="46" ry="8" fill="#000" opacity={0.25} />
        <Path d="M40 168 Q30 108 80 96 Q130 108 120 168 Z" fill="url(#g)" />
        <Ellipse cx="80" cy="62" rx="40" ry="32" fill="url(#g)" />
        <Circle cx="62" cy="62" r="5.5" fill={eye} /><Circle cx="98" cy="62" r="5.5" fill={eye} />
        <Line x1="62" y1="62" x2="98" y2="62" stroke={eye} strokeWidth={2.5} />
        <Circle cx="80" cy="128" r="10" fill={C.accentSoft} opacity={0.8} />
        <Path d="M42 118 Q22 132 30 152" stroke={C.accentSoft} strokeWidth={9} strokeLinecap="round" fill="none" />
        <Path d="M118 118 Q138 132 130 152" stroke={C.accentSoft} strokeWidth={9} strokeLinecap="round" fill="none" />
      </Svg>
    </Animated.View>
  );
}

/** Glowing voice orb that breathes while active. */
export function Orb({ active, size = 220 }: { active: boolean; size?: number }) {
  const p = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    const a = Animated.loop(Animated.sequence([
      Animated.timing(p, { toValue: 1, duration: active ? 600 : 1800, easing: Easing.inOut(Easing.quad), useNativeDriver: true }),
      Animated.timing(p, { toValue: 0, duration: active ? 600 : 1800, easing: Easing.inOut(Easing.quad), useNativeDriver: true })]));
    a.start(); return () => a.stop();
  }, [active, p]);
  const sc = p.interpolate({ inputRange: [0, 1], outputRange: [0.94, active ? 1.12 : 1.04] });
  return (
    <View style={{ width: size * 1.5, height: size * 1.5, alignItems: "center", justifyContent: "center" }}>
      <Animated.View style={{ position: "absolute", width: size * 1.4, height: size * 1.4, borderRadius: size, backgroundColor: C.accent, opacity: 0.12, transform: [{ scale: sc }] }} />
      <Animated.View style={{ position: "absolute", width: size * 1.15, height: size * 1.15, borderRadius: size, backgroundColor: C.accentSoft, opacity: 0.2, transform: [{ scale: sc }] }} />
      <Animated.View style={{ transform: [{ scale: sc }] }}>
        <LinearGradient colors={["#c4b5fd", "#8b5cf6", "#5b21b6"]} style={{ width: size, height: size, borderRadius: size / 2 }} />
      </Animated.View>
    </View>
  );
}

type Layout = { bounds: number[]; rooms: any[]; doors: any[]; furniture: any[] };
export function FloorPlan({ layout, state, width }: { layout: Layout; state: any; width: number }) {
  const [x0, x1, y0, y1] = layout.bounds;
  const pad = 14, sc = (width - 2 * pad) / (x1 - x0), h = (y1 - y0) * sc + 2 * pad;
  const px = (u: number) => pad + (u - x0) * sc, py = (v: number) => h - pad - (v - y0) * sc;
  const rb = state?.robot, pe = state?.person;
  const lying = pe?.posture?.startsWith("lying");
  const sirenOn = state?.siren?.on;
  return (
    <Svg width={width} height={h}>
      {layout.rooms.map((r, i) => (
        <G key={i}>
          <Rect x={px(r.x0)} y={py(r.y1)} width={(r.x1 - r.x0) * sc} height={(r.y1 - r.y0) * sc} fill="rgba(255,255,255,0.05)" stroke="rgba(167,139,250,0.6)" strokeWidth={2} />
        </G>
      ))}
      {layout.doors.map((d, i) => <Line key={i} x1={px(d.x - d.w / 2)} x2={px(d.x + d.w / 2)} y1={py(d.y)} y2={py(d.y)} stroke={C.bgMid} strokeWidth={6} />)}
      {layout.furniture.map((f, i) => <Rect key={i} x={px(f.x0)} y={py(f.y1)} width={(f.x1 - f.x0) * sc} height={(f.y1 - f.y0) * sc} rx={4} fill="rgba(139,92,246,0.22)" stroke="rgba(167,139,250,0.35)" />)}
      {sirenOn && pe?.x != null && [14, 28, 42].map((r, i) => <Circle key={i} cx={px(pe.x)} cy={py(pe.y)} r={r} stroke={C.danger} strokeWidth={2} fill="none" opacity={0.7 - i * 0.2} />)}
      {pe?.x != null && <Circle cx={px(pe.x)} cy={py(pe.y)} r={lying ? 10 : 8} fill={lying ? C.danger : C.ok} opacity={pe.seen_now ? 1 : 0.5} />}
      {rb && (
        <G transform={`translate(${px(rb.x)},${py(rb.y)}) rotate(${(-rb.yaw * 180) / Math.PI})`}>
          <Circle r={9} fill={C.accentSoft} /><Polygon points="15,0 6,-6 6,6" fill="#fff" />
        </G>
      )}
    </Svg>
  );
}

const s = StyleSheet.create({
  card: { backgroundColor: C.card, borderColor: C.cardBorder, borderWidth: 1, borderRadius: R.card, padding: 16 },
  btn: { borderWidth: 1, borderRadius: R.pill, paddingVertical: 14, paddingHorizontal: 22, alignItems: "center", minHeight: 48, justifyContent: "center" },
  btnText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  chip: { flexDirection: "row", alignItems: "center", borderWidth: 1, borderRadius: R.pill, paddingHorizontal: 10, paddingVertical: 4, alignSelf: "flex-start" },
  dot: { width: 7, height: 7, borderRadius: 4, marginRight: 6 },
  chipText: { fontSize: 12, fontWeight: "600" },
});
