import mujoco
import mujoco.viewer

XML_FILE = "scenes/living_room.xml"

with open(XML_FILE, "r") as f:
    xml_string = f.read()

model = mujoco.MjModel.from_xml_string(xml_string)
data = mujoco.MjData(model)

print("MuJoCo scene loaded successfully!")
print("Launching viewer...")

with mujoco.viewer.launch_passive(model, data) as viewer:
    while viewer.is_running():
        mujoco.mj_step(model, data)
        viewer.sync()
