"""
Dual-path deployment helper for Rubik Pi projects.

Supports both:
1) .ino firmware generation (for external microcontroller flow)
2) No-.ino native Rubik Pi Python runtime generation (GPIO-first flow)
"""

import argparse
from pathlib import Path

from deploy_to_robot import build_rubik_pi_firmware


def build_native_rubik_pi_runtime(default_sensor_mode: str = "ultrasonic") -> str:
    """Generate a starter native Rubik Pi runtime script (no .ino needed)."""
    sensor_mode = "analog" if default_sensor_mode == "analog" else "ultrasonic"

    return f'''#!/usr/bin/env python3
"""
Rubik Pi Native Runtime (NO .ino)

This script is intended to run directly on Rubik Pi and control motors/sensors
through Python GPIO libraries + motor driver logic.

⚠️ Update GPIO pin mappings and motor/sensor code to match your hardware.
"""

import time

DEFAULT_SENSOR_MODE = "{sensor_mode}"

# ----------------------------------------------------------------------------
# Hardware mapping (EDIT for your board/wiring)
# ----------------------------------------------------------------------------
MOTOR_LEFT_FWD = 5
MOTOR_LEFT_BWD = 6
MOTOR_RIGHT_FWD = 9
MOTOR_RIGHT_BWD = 10

GROUND_TRIG_PIN = 2
GROUND_ECHO_PIN = 3
TOP_TRIG_PIN = 4
TOP_ECHO_PIN = 7

ANALOG_FRONT_PIN = 0
ANALOG_LEFT_PIN = 1
ANALOG_RIGHT_PIN = 2

TOP_FRONT_STOP_CM = 25
GROUND_MIN_SAFE_CM = 5


class RubikPiRobot:
    def __init__(self, sensor_mode=DEFAULT_SENSOR_MODE, dry_run=True):
        self.sensor_mode = sensor_mode
        self.auto_mode = False
        self.dry_run = dry_run

    # ---------------------------
    # Motor control stubs
    # ---------------------------
    def move_forward(self):
        self._log("FORWARD")

    def move_backward(self):
        self._log("BACKWARD")

    def turn_left(self):
        self._log("LEFT")

    def turn_right(self):
        self._log("RIGHT")

    def stop(self):
        self._log("STOP")

    # ---------------------------
    # Sensor stubs
    # ---------------------------
    def read_ultrasonic_cm(self, trig_pin, echo_pin):
        # TODO: replace with real GPIO trigger/echo timing logic
        _ = (trig_pin, echo_pin)
        return 100

    def read_analog(self, channel):
        # TODO: replace with ADC read implementation for your hardware
        _ = channel
        return 500

    def read_sensors(self):
        if self.sensor_mode == "analog":
            return {{
                "mode": "analog",
                "front": self.read_analog(ANALOG_FRONT_PIN),
                "left": self.read_analog(ANALOG_LEFT_PIN),
                "right": self.read_analog(ANALOG_RIGHT_PIN),
            }}

        return {{
            "mode": "ultrasonic",
            "ground_cm": self.read_ultrasonic_cm(GROUND_TRIG_PIN, GROUND_ECHO_PIN),
            "top_front_cm": self.read_ultrasonic_cm(TOP_TRIG_PIN, TOP_ECHO_PIN),
            # Add top-left/top-right logic if using servo scan
            "top_left_cm": 100,
            "top_right_cm": 100,
        }}

    def autonomous_step(self):
        s = self.read_sensors()

        if s["mode"] == "analog":
            obstacle_ahead = s["front"] < 300
            prefer_left = s["left"] > s["right"]
        else:
            if s["ground_cm"] < GROUND_MIN_SAFE_CM:
                self.move_backward()
                time.sleep(0.12)
                self.turn_left()
                return
            obstacle_ahead = s["top_front_cm"] < TOP_FRONT_STOP_CM
            prefer_left = s["top_left_cm"] > s["top_right_cm"]

        if obstacle_ahead:
            self.turn_left() if prefer_left else self.turn_right()
        else:
            self.move_forward()

    def _log(self, action):
        if self.dry_run:
            print(f"[DRY-RUN] {{action}}")


def main():
    robot = RubikPiRobot(sensor_mode=DEFAULT_SENSOR_MODE, dry_run=True)
    print("🤖 Rubik Pi native runtime started (no .ino)")
    print(f"Sensor mode: {{robot.sensor_mode}}")
    print("Press Ctrl+C to stop")

    try:
        while True:
            robot.autonomous_step()
            time.sleep(0.05)
    except KeyboardInterrupt:
        robot.stop()
        print("\n👋 Stopped")


if __name__ == "__main__":
    main()
'''


def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate deployment artifacts for Rubik Pi: .ino and/or native Python runtime"
    )
    parser.add_argument(
        "--mode",
        choices=["ino", "native", "both"],
        default="both",
        help="Which deployment artifact(s) to generate",
    )
    parser.add_argument(
        "--sensor-mode",
        choices=["analog", "ultrasonic"],
        default="ultrasonic",
        help="Default sensor mode embedded into generated artifacts",
    )
    parser.add_argument(
        "--ino-output",
        default="rubik_pi_firmware.ino",
        help="Output path for generated .ino firmware",
    )
    parser.add_argument(
        "--native-output",
        default="rubik_pi_runtime.py",
        help="Output path for generated native Rubik Pi runtime",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    generated = []

    if args.mode in ("ino", "both"):
        ino_path = Path(args.ino_output)
        ino_code = build_rubik_pi_firmware(args.sensor_mode)
        write_file(ino_path, ino_code)
        generated.append(str(ino_path))
        print(f"📝 Generated .ino firmware: {ino_path}")

    if args.mode in ("native", "both"):
        native_path = Path(args.native_output)
        native_code = build_native_rubik_pi_runtime(args.sensor_mode)
        write_file(native_path, native_code)
        generated.append(str(native_path))
        print(f"📝 Generated native runtime: {native_path}")

    if generated:
        print("\n✅ Done. Generated artifact(s):")
        for item in generated:
            print(f"   - {item}")


if __name__ == "__main__":
    main()
