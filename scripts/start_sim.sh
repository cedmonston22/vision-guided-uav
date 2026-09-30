#!/usr/bin/env bash
set -u

SESSION=uav
REPO=~/vision-guided-uav
PX4=~/PX4-Autopilot
CAM_TOPIC=/world/default/model/x500_mono_cam_down_0/link/camera_link/sensor/camera/image

STRIP_VENV='unset VIRTUAL_ENV; PATH=$(echo "$PATH" | tr ":" "\n" | grep -v "\.venv/bin" | paste -sd ":" -)'

if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "session '$SESSION' already running, attaching"
    exec tmux attach -t "$SESSION"
fi

tmux new-session -d -s "$SESSION"
tmux split-window -t "$SESSION"
tmux split-window -t "$SESSION"
tmux split-window -t "$SESSION"
tmux select-layout -t "$SESSION" tiled

tmux send-keys -t "$SESSION:0.0" \
    "$STRIP_VENV; cd $PX4 && HEADLESS=1 make px4_sitl gz_x500_mono_cam_down" Enter

echo "waiting for gazebo to publish the camera topic"
READY=0
for i in $(seq 1 120); do
    if timeout 5 gz topic -l 2>/dev/null | grep -q camera_link; then
        READY=1
        echo "gazebo up after ${i}s"
        break
    fi
    sleep 1
done

if [ "$READY" -eq 0 ]; then
    echo "gazebo did not come up in 120s, attaching anyway so you can see pane 0"
    exec tmux attach -t "$SESSION"
fi

SPAWN="gz service -s /world/default/create --reqtype gz.msgs.EntityFactory --reptype gz.msgs.Boolean --timeout 5000 --req 'sdf_filename: \"arucotag\", name: \"aruco_0\", pose: {position: {x: 0, y: 0, z: 0.01}}'"
BRIDGE="source /opt/ros/jazzy/setup.bash && ros2 run ros_gz_image image_bridge $CAM_TOPIC"

tmux send-keys -t "$SESSION:0.1" "$SPAWN && $BRIDGE" Enter
tmux send-keys -t "$SESSION:0.2" \
    "source /opt/ros/jazzy/setup.bash && source $REPO/.venv/bin/activate && python $REPO/scripts/detect_marker.py" Enter
tmux send-keys -t "$SESSION:0.3" \
    "source $REPO/.venv/bin/activate && cd $REPO" Enter

tmux attach -t "$SESSION"
