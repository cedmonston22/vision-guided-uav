# Commands

Repo at `~/vision-guided-uav`, PX4 at `~/PX4-Autopilot`.

## Setup (one time)

```bash
sudo apt install ros-jazzy-ros-base ros-jazzy-ros-gz-bridge ros-jazzy-ros-gz-image ros-jazzy-rqt-image-view
```

UDP socket buffers, send and receive. Frames are 3.5 MB and the 208 KB
defaults drop most of them. Measured 6 Hz with only the receive side
raised, 24 Hz with both.

```bash
sudo tee /etc/sysctl.d/99-ros2.conf <<'CONF'
net.core.rmem_max=16777216
net.core.rmem_default=16777216
net.core.wmem_max=16777216
net.core.wmem_default=16777216
CONF
```

```bash
cd ~/vision-guided-uav && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

## Startup

### All at once

Brings up SITL, marker, bridge, and `detect_marker.py` in one tmux session, with a free shell in the last pane.

```bash
~/vision-guided-uav/scripts/start_sim.sh
```

```bash
tmux attach -t uav
```

```bash
tmux kill-session -t uav
```

### 1. SITL

```bash
deactivate 2>/dev/null; cd ~/PX4-Autopilot && HEADLESS=1 make px4_sitl gz_x500_mono_cam_down
```

### 2. Marker, then bridge

Marker is lost on every SITL restart.

```bash
gz service -s /world/default/create --reqtype gz.msgs.EntityFactory --reptype gz.msgs.Boolean --timeout 5000 --req 'sdf_filename: "arucotag", name: "aruco_0", pose: {position: {x: 0, y: 0, z: 0.01}}'
```

```bash
source /opt/ros/jazzy/setup.bash && ros2 run ros_gz_image image_bridge /world/default/model/x500_mono_cam_down_0/link/camera_link/sensor/camera/image
```

### 3. Viewer, Detector, or Hold

```bash
source /opt/ros/jazzy/setup.bash && source ~/vision-guided-uav/.venv/bin/activate && python ~/vision-guided-uav/scripts/view_camera.py
```

```bash
source /opt/ros/jazzy/setup.bash && source ~/vision-guided-uav/.venv/bin/activate && python ~/vision-guided-uav/scripts/detect_marker.py
```

Run one detector at a time. Stop `detect_marker.py` before starting `hold_marker.py`.

```bash
source /opt/ros/jazzy/setup.bash && source ~/vision-guided-uav/.venv/bin/activate && python ~/vision-guided-uav/scripts/hold_marker.py
```

### 4. Flight

```bash
source ~/vision-guided-uav/.venv/bin/activate && python ~/vision-guided-uav/scripts/takeoff_land.py
```

## Inspection

```bash
gz topic -l
```

```bash
gz model --list
```

```bash
source /opt/ros/jazzy/setup.bash && ros2 topic list
```

`ros2 topic hz` understates the rate on this topic. A subscriber with depth 1 reads the full 30 Hz.

## Reference

| Item | Value |
|---|---|
| Camera topic | `/world/default/model/x500_mono_cam_down_0/link/camera_link/sensor/camera/image` |
| Image | 1280x960, rgb8, 30 Hz, step 3840, 3.5 MB |
| Horizontal FOV | 1.74 rad (99.7 deg) |
| Marker | DICT_4X4_50, id 0, 0.5 m square |
| Airframe | `gz_x500_mono_cam_down` (4014) |
| QoS | RELIABLE, KEEP_LAST, depth 1 |

The topic contains the model instance name, set from `PX4_SIM_MODEL`. Change airframes and it changes.
