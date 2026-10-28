import * as Notifications from "expo-notifications";
import * as Haptics from "expo-haptics";
import { Platform } from "react-native";

Notifications.setNotificationHandler({
  handleNotification: async () => ({ shouldShowBanner: true, shouldShowList: true, shouldPlaySound: true, shouldSetBadge: false }),
});

export async function askPermission() {
  try { if (Platform.OS === "web") return; await Notifications.requestPermissionsAsync(); } catch {}
}
export async function alertNow(title: string, body: string, urgent: boolean) {
  try {
    if (urgent) await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
    else await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
  } catch {}
  try { if (Platform.OS !== "web") await Notifications.scheduleNotificationAsync({ content: { title, body }, trigger: null }); } catch {}
}
