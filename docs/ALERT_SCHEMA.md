# Alert payload schema and privacy contract

What may leave the robot, and only AFTER the first alert. Before the first alert nothing leaves it: frames are processed on board and discarded, landmarks are kept only for the last few seconds in memory, and the logged counter `bytes_off_board` is 0 (measured: 0 in every one of the 120 test trials).

## Message record (src/control/dispatch.py, `Dispatcher._send`)
| field | type | meaning |
|---|---|---|
| t | number | simulation time of the send, s |
| clock | string | wall-clock style time shown to the family |
| to | string | recipient name from config/family_contacts.json (fictional) |
| channel | string | app_push, sms or phone (all simulated) |
| kind | string | heads_up, emergency, ambulance_call, update, all_clear, missed_reminder, medicine_report, siren |
| text | string | the message text (a fixed template, optionally re-worded by the agent, but never the ambulance script) |
| attachment | string or null | path of ONE face-blurred snapshot, only on an emergency (and only with her consent in the family platform) |
| telemetry | object (emergency only) | the structured payload below |

## Telemetry object (emergency)
| field | type | unit |
|---|---|---|
| event | string | "collapse_unresponsive" |
| witnessed | bool | whether the fall itself was seen |
| time_of_collapse | string | clock time |
| seconds_since_collapse | number | s |
| unresponsive_for_s | number | s of silence at the check-in |
| location.room | string | named room |
| location.x, location.y | number | m, map frame |
| posture.hip_height_m | number | m |
| posture.torso_angle_deg | number | degrees from vertical |
| posture.box_aspect_ratio | number | width / height of the landmark box |
| posture.still | bool | |
| robot.x, robot.y | number | m, map frame |
| robot.distance_to_person_m | number or null | m |
| evidence | string | short text of what the detector saw |

## What is never sent
Raw video frames, the stream of pose landmarks, audio recordings, or any image except the single face-blurred snapshot after a confirmed emergency. Tested in tests/test_alert_privacy.py.
