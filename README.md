# Vision-Guided UAV Autonomy (PX4 SITL)

A vision-guided autonomy stack for a simulated multirotor, built on PX4 and Gazebo.
The aircraft uses a downward-facing camera to detect a target, hold position over it,
and land on it.

All work is developed and validated in PX4 Software-In-The-Loop (SITL) with Gazebo.
No hardware flight testing has been performed.

## Running it

See [COMMANDS.md](COMMANDS.md) for setup and the startup sequence.

## Why this exists

PX4 is the production flight stack that runs on real Pixhawk hardware. The offboard
control interface, the MAVLink protocol, the EKF2 estimator, and its external vision
inputs are the same code paths used in the field. Developing against them in simulation
is how autonomy work is actually done, because flight time is scarce and crashes are
expensive.

## Architecture

```
  Gazebo (camera sensor)
        |
        v
  Perception  ......  ArUco detection, pixel error, error in meters
        |
        v
  Controller  ......  error -> velocity setpoint (offboard)
        |
        v
  PX4 SITL    ......  EKF2 state estimation, attitude control
        |
        v
  CSV log     ......  one file per run, plotted offline
```

Perception and control run on the "companion computer" side in Python. PX4 handles
hard real-time stabilization and state estimation. The two communicate over MAVLink
via MAVSDK. Camera frames reach Python over ROS 2 through the `ros_gz_image` bridge.

## Milestones

Each milestone is complete only when it works on unrehearsed runs and has measured
numbers attached. "It worked once" does not count.

### M0: Environment (done)

PX4 SITL and Gazebo running with hardware-accelerated rendering. A MAVSDK script that
connects, arms, takes off, hovers, and lands.

**Done when:** renderer reports real GPU acceleration (not llvmpipe), sim runs near
real time, takeoff-and-land script succeeds three consecutive times.

### M1: Perception

Camera frames from Gazebo into Python. ArUco detection. Pixel error computed and
converted to ground distance in meters using altitude and the camera's field of view.

**Done when:** per-frame detection latency measured, and detection confirmed working
at 3m, 5m, and 10m.

### M2: Closed-loop position hold

Offboard velocity control driven by image error. The aircraft acquires the marker and
holds above it. Detection runs on a background thread; the control loop reads the
latest error and streams velocity setpoints.

**Done when:** holds 60s over the marker from 5 different starting offsets, with an
error-vs-time plot in this README and the steady-state error written down.

*This is the first milestone worth putting on a resume.*

### M3: Precision landing

Descend onto the static marker, but only while centered. If the marker is lost, stop
descending and hold.

**Done when:** lands within a stated distance of marker center across 5 to 10 attempts,
with a demo video recorded.

## Known limitations

Simulation does not reproduce the conditions that make vision-based control hard on
real aircraft:

- **Vibration.** Simulated IMU data is clean. Real IMUs sit on an airframe with four
  motors spinning, and vibration is a primary cause of vision-based estimation failure
  in practice.
- **Rolling shutter.** Simulated cameras have global shutter. Real rolling-shutter
  sensors smear geometry during fast motion.
- **Lighting and motion blur.** Simulated exposure is ideal.
- **Texture.** Real environments include blank concrete and featureless grass where
  there is nothing to track.

Two limitations in the current implementation specifically:

- **Altitude is ground truth**, read from Gazebo's pose topic rather than estimated.
  A real aircraft has no such source and would use the flight controller's own estimate.
- **Camera attitude is ignored.** The pixel-to-meter conversion assumes the camera
  points straight down, so a tilted airframe reports displacement that is not there.
  This is correct at hover and optimistic during acceleration.

## Results

| Milestone | Metric | Value |
|---|---|---|
| M1 | Detection latency | 1.4 to 3.1 ms per frame at 1280x960 |
| M1 | Detection at 3m / 5m / 10m | works at all three, 99% rate at 9.4 m |
| M2 | Steady-state hold error | |
| M2 | Control loop rate | |
| M2 | Perception-to-actuation latency | |
| M3 | Landing accuracy | |

## Future work

Out of scope for now, listed because they are the natural continuations:

- **Moving target tracking.** A pure proportional controller trails a constant-velocity
  target by a fixed offset forever. Fixing that with an integral term or velocity
  feedforward is the lesson.
- **Optical flow position hold.** First GPS-denied flight, using downward optical flow
  for velocity and a rangefinder for scale.
- **VIO waypoint navigation.** Off-the-shelf visual-inertial odometry publishing pose,
  PX4 fusing it, a multi-waypoint route flown with GPS disabled.
- **Replay tooling.** Reconstructing a run into plots and ground tracks without the
  simulator.

## Log

Running record of what was tried, what the numbers were, and what broke. Kept current
per milestone rather than reconstructed at the end.

### M1, 2026-10-01

ArUco detection runs in 1.4 to 3.1 ms per frame at 1280x960, and that cost is
independent of altitude, since the detector scans the whole image regardless of how
large the marker turns out to be. Detection confirmed at 3 m, 5 m and 10 m, with a 99%
rate at 9.4 m where the marker is only about 29 pixels across. The camera stream ran at
a fifth of its expected rate until the kernel UDP socket buffers, net.core.rmem_max and
wmem_max, were raised from their 208 KB default, because each 3.5 MB frame fragments
across thousands of UDP packets that all have to pass through them. Pixel error is
converted to ground distance with px * altitude / focal, where focal is 539 pixels for
this camera.
