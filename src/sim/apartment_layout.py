"""
Single source of truth for the one-bedroom flat (metres; MuJoCo world, REP-103 style:
X east/forward, Y north/left, Z up).  Used by build_apartment.py (geometry),
walk_and_fall.py (her walking path and trip point) and dynamic_obstacles.py.

Plan view (not to scale):

  y=+3.0 +-------------------------------+---------------------+
         |  kitchen counter (north wall) |  BEDROOM  (carpet)  |
         |  DINING: table + 4 chairs     |  bed, wardrobe,     |
         |  vacuum loop (west of table)  |  nightstands        |
         |  LIVING (hardwood):           |                     |
         |  sofa, coffee table, rug, TV  |                     |
  y=-1.9 +--------[0.90 m door]----------+------[0.85 m door]--+   <- hallway wall
         |  HALLWAY (laminate), front door at the west end      |
  y=-3.0 +-------------------------------+---------------------+
       x=-3.5                         x=0.6 (partition)       x=3.5
"""
import numpy as np

# --- shell ------------------------------------------------------------------------------
X0, X1 = -3.5, 3.5            # 7.0 m
Y0, Y1 = -3.0, 3.0            # 6.0 m
WALL_T = 0.12
WALL_H = 2.40
DOOR_H = 2.05
CUTAWAY_H = 0.80              # visual height of the cut-away walls (collision height stays WALL_H)

HALL_Y = -1.9                 # dividing wall between hallway and the rooms
PART_X = 0.6                  # partition between living-dining and bedroom
DOOR_LIVING = (-2.2, 0.90)    # (centre x, clear width) in the hallway wall
DOOR_BEDROOM = (2.0, 0.85)

# Floor zones: name, (x0, x1, y0, y1), sliding friction, texture tile size (m).
# Friction values are the guide's: hardwood 0.42, laminate 0.50, low-pile carpet 0.68.
FLOORS = [
    ("hardwood", (X0, PART_X, HALL_Y, Y1), 0.42, 1.2),
    ("laminate", (X0, X1, Y0, HALL_Y), 0.50, 0.9),
    ("carpet", (PART_X, X1, HALL_Y, Y1), 0.68, 0.6),
]

# --- her walk -----------------------------------------------------------------------------
# Gets up beside the bed, leaves the bedroom, walks the hallway, enters the living room and
# trips on the curled edge of the rug (slippers left on the floor next to it).
WALK_PATH = np.array([[2.0, 0.5], [2.0, -2.45], [-2.2, -2.45], [-2.2, 0.3]])
TRIP_AFTER_LAST_CORNER = 1.2          # m after the turn into the living room = the rug's south edge
RUG_CENTER = (-1.5, -0.3)
RUG_HALF = (1.3, 0.95)                # south edge at y = -1.25

# Routes she can walk (polylines through the doorways) for the experiment set. Events (falls, daily activities) happen along or at the end of them.
ROUTES = {
    "bed_to_living": WALK_PATH,
    "living_to_bed": WALK_PATH[::-1],
    "bed_to_front_door": np.array([[2.0, 0.5], [2.0, -2.45], [-2.8, -2.45]]),
    "hall_to_bedroom": np.array([[-2.2, -2.45], [2.0, -2.45], [2.0, 0.5], [2.5, 0.5]]),
    "living_to_dining": np.array([[-2.2, -0.9], [-2.2, 0.9]]),
    "living_south_to_north": np.array([[-2.3, -1.3], [-2.3, 0.7]]),
    "bedroom_local": np.array([[2.0, -1.3], [2.0, 0.3], [2.7, 0.3]]),
}

# --- moving obstacle (robot vacuum, driven kinematically) -----------------------------------------
VACUUM_LOOP = np.array([[-3.0, 1.6], [-1.7, 1.6], [-1.7, 2.2], [-3.0, 2.2]])   # closed loop
VACUUM_SPEED = 0.25                   # m/s

# --- robot dock (charging pad); the robot starts here: x, y, yaw in degrees (0 = facing +x) ---------------
ROBOT_DOCK = (-1.05, -1.10, 180.0)            # 'watch' scenario: waits here and sees the fall side-on
ROBOT_START_FOLLOW = (2.9, 0.0, 160.0)       # 'follow' scenario: starts in the bedroom with her and follows her through the flat

# --- named places (sites in the model; the robot's patrol and the fall scenarios use them) ------
WAYPOINTS = {
    "wp_hall_west": (-2.2, -2.45),
    "wp_hall_east": (2.0, -2.45),
    "wp_living": (-2.2, -0.6),
    "wp_dining": (-2.2, 0.95),
    "wp_bedroom": (2.0, -0.5),
}
FALL_ZONES = {
    "fall_zone_living": (-2.2, 0.2),
    "fall_zone_dining": (-1.3, 1.5),
    "fall_zone_bedroom": (2.2, -0.3),
    "fall_zone_hallway": (0.0, -2.45),
}


def path_arclengths(path=WALK_PATH):
    seg = np.diff(path, axis=0)
    return np.concatenate([[0.0], np.cumsum(np.hypot(seg[:, 0], seg[:, 1]))])


def path_xy(path, s):
    """Point at arc length s along a polyline."""
    cum = path_arclengths(path)
    s = float(np.clip(s, 0, cum[-1]))
    i = min(int(np.searchsorted(cum, s, side="right") - 1), len(path) - 2)
    u = (s - cum[i]) / max(cum[i + 1] - cum[i], 1e-9)
    return np.asarray(path[i], float) + u * (np.asarray(path[i + 1], float) - np.asarray(path[i], float))


def trip_arclength(path=WALK_PATH):
    """Arc length (m) along the path at which she trips."""
    return path_arclengths(path)[-2] + TRIP_AFTER_LAST_CORNER


def lookat_xyaxes(pos, target, up=(0.0, 0.0, 1.0)):
    """MuJoCo camera xyaxes (camera looks along its -z) for a camera at pos aimed at target."""
    f = np.asarray(target, float) - np.asarray(pos, float)
    f /= np.linalg.norm(f)
    right = np.cross(f, up)
    right /= np.linalg.norm(right)
    upv = np.cross(right, f)
    return np.concatenate([right, upv])


def room_of(x, y):
    """Name of the room a point is in (used in alert messages)."""
    if y < HALL_Y:
        return "hallway"
    if x > PART_X:
        return "bedroom"
    return "dining area" if y > 0.9 else "living room"


def zone_of(x, y):
    """Coarse zone for balancing events: hallway, bedroom or the open-plan living-dining area."""
    return {"hallway": "hallway", "bedroom": "bedroom"}.get(room_of(x, y), "living")
