"""
ADB Controller for Android device communication and control.
"""

import subprocess
import time
from pathlib import Path
from typing import List, Optional, Tuple

from ppadb.client import Client as AdbClient


class ADBController:
    """
    Controller for Android device via ADB (Android Debug Bridge).

    Provides methods for:
    - Device connection (USB/WiFi)
    - Screen interaction (tap, swipe, input text)
    - App management (launch, close)
    - File transfer (push/pull)
    - Screenshot capture
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5037,
        device_serial: Optional[str] = None,
    ):
        """
        Initialize ADB controller.

        Args:
            host: ADB server host
            port: ADB server port
            device_serial: Specific device serial to connect to (optional)
        """
        self.host = host
        self.port = port
        self.device_serial = device_serial
        self._client: Optional[AdbClient] = None
        self._device = None
        self._screen_size: Optional[Tuple[int, int]] = None

    def connect(self, device_ip: Optional[str] = None, device_port: int = 5555) -> bool:
        """
        Connect to ADB server and device.

        Args:
            device_ip: IP address for WiFi connection (optional)
            device_port: Port for WiFi connection (default: 5555)

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self._client = AdbClient(host=self.host, port=self.port)

            # If WiFi connection requested, connect to device over network
            if device_ip:
                self._connect_wifi(device_ip, device_port)

            devices = self._client.devices()

            if not devices:
                print("No devices found. Please check:")
                print("  1. USB debugging is enabled on your phone")
                print("  2. Your phone is connected via USB or WiFi ADB is enabled")
                print("  3. ADB server is running (run 'adb start-server')")
                return False

            # Select specific device or first available
            if self.device_serial:
                for device in devices:
                    if device.serial == self.device_serial:
                        self._device = device
                        break
                if not self._device:
                    print(f"Device {self.device_serial} not found")
                    return False
            else:
                self._device = devices[0]

            print(f"Connected to device: {self._device.serial}")
            self._screen_size = self._get_screen_size()
            print(f"Screen size: {self._screen_size[0]}x{self._screen_size[1]}")

            return True

        except Exception as e:
            print(f"Failed to connect to ADB: {e}")
            print("Try running 'adb start-server' first")
            return False

    def _connect_wifi(self, device_ip: str, device_port: int) -> None:
        """Connect to device over WiFi."""
        target = f"{device_ip}:{device_port}"
        try:
            # Use subprocess for WiFi connection as pure-python-adb may not support it
            subprocess.run(
                ["adb", "connect", target],
                capture_output=True,
                text=True,
                timeout=10,
            )
            time.sleep(1)  # Wait for connection to establish
        except subprocess.TimeoutExpired:
            print(f"WiFi connection to {target} timed out")
        except FileNotFoundError:
            print("ADB executable not found. Please install Android SDK Platform Tools")

    def disconnect(self) -> None:
        """Disconnect from the device."""
        self._device = None
        self._client = None
        self._screen_size = None

    def _get_screen_size(self) -> Tuple[int, int]:
        """Get device screen size."""
        if not self._device:
            raise RuntimeError("Device not connected")

        output = self._device.shell("wm size")
        # Output format: "Physical size: 1080x2400"
        for line in output.strip().split("\n"):
            if "Physical size" in line or "Override size" in line:
                size_str = line.split(":")[-1].strip()
                width, height = size_str.split("x")
                return int(width), int(height)

        # Fallback: try dumpsys
        output = self._device.shell("dumpsys window displays | grep 'init='")
        if output:
            # Parse "init=1080x2400" format
            import re

            match = re.search(r"init=(\d+)x(\d+)", output)
            if match:
                return int(match.group(1)), int(match.group(2))

        return 1080, 2400  # Default fallback

    @property
    def screen_size(self) -> Tuple[int, int]:
        """Get cached screen size (width, height)."""
        if not self._screen_size:
            raise RuntimeError("Device not connected")
        return self._screen_size

    @property
    def is_connected(self) -> bool:
        """Check if device is connected."""
        return self._device is not None

    def tap(self, x: int, y: int) -> None:
        """
        Tap at specified coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
        """
        if not self._device:
            raise RuntimeError("Device not connected")
        self._device.shell(f"input tap {x} {y}")

    def long_press(self, x: int, y: int, duration_ms: int = 1000) -> None:
        """
        Long press at specified coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
            duration_ms: Press duration in milliseconds
        """
        if not self._device:
            raise RuntimeError("Device not connected")
        self._device.shell(f"input swipe {x} {y} {x} {y} {duration_ms}")

    def swipe(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration_ms: int = 300,
    ) -> None:
        """
        Swipe from start to end coordinates.

        Args:
            start_x: Starting X coordinate
            start_y: Starting Y coordinate
            end_x: Ending X coordinate
            end_y: Ending Y coordinate
            duration_ms: Swipe duration in milliseconds
        """
        if not self._device:
            raise RuntimeError("Device not connected")
        self._device.shell(f"input swipe {start_x} {start_y} {end_x} {end_y} {duration_ms}")

    def scroll_up(self, amount: float = 0.5) -> None:
        """
        Scroll up on the screen.

        Args:
            amount: Scroll amount as fraction of screen height (0.0 to 1.0)
        """
        width, height = self.screen_size
        center_x = width // 2
        start_y = int(height * (0.5 + amount / 2))
        end_y = int(height * (0.5 - amount / 2))
        self.swipe(center_x, start_y, center_x, end_y)

    def scroll_down(self, amount: float = 0.5) -> None:
        """
        Scroll down on the screen.

        Args:
            amount: Scroll amount as fraction of screen height (0.0 to 1.0)
        """
        width, height = self.screen_size
        center_x = width // 2
        start_y = int(height * (0.5 - amount / 2))
        end_y = int(height * (0.5 + amount / 2))
        self.swipe(center_x, start_y, center_x, end_y)

    def input_text(self, text: str) -> None:
        """
        Input text (ASCII only, use input_text_chinese for Chinese).

        Args:
            text: Text to input (ASCII characters only)
        """
        if not self._device:
            raise RuntimeError("Device not connected")
        # Escape special characters for shell
        escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'")
        escaped = escaped.replace(" ", "%s").replace("&", "\\&")
        self._device.shell(f'input text "{escaped}"')

    def input_text_chinese(self, text: str) -> None:
        """
        Input Chinese text using ADB broadcast.

        This requires ADBKeyboard app to be installed on the device.
        Install from: https://github.com/nickmelo/ADBKeyBoard

        Args:
            text: Text to input (supports Chinese and other Unicode)
        """
        if not self._device:
            raise RuntimeError("Device not connected")

        # Use ADBKeyboard broadcast for Unicode text input
        # The text needs to be base64 encoded for Chinese characters
        import base64

        encoded = base64.b64encode(text.encode("utf-8")).decode("utf-8")
        self._device.shell(
            f"am broadcast -a ADB_INPUT_B64 --es msg '{encoded}'"
        )

    def input_text_via_clipboard(self, text: str) -> None:
        """
        Input text via clipboard (alternative method for Chinese).

        This method:
        1. Writes text to a temp file on device
        2. Uses service call to set clipboard
        3. Pastes from clipboard

        Args:
            text: Text to input
        """
        if not self._device:
            raise RuntimeError("Device not connected")

        # Write text to device temp file
        temp_path = "/data/local/tmp/xhs_input.txt"
        self._device.shell(f"echo '{text}' > {temp_path}")

        # Note: Direct clipboard access varies by Android version
        # This is a simplified approach - may need adjustment for your device
        self.key_event("KEYCODE_PASTE")

    def key_event(self, keycode: str) -> None:
        """
        Send a key event.

        Args:
            keycode: Android keycode (e.g., "KEYCODE_BACK", "KEYCODE_HOME", "KEYCODE_ENTER")
        """
        if not self._device:
            raise RuntimeError("Device not connected")
        self._device.shell(f"input keyevent {keycode}")

    def press_back(self) -> None:
        """Press the back button."""
        self.key_event("KEYCODE_BACK")

    def press_home(self) -> None:
        """Press the home button."""
        self.key_event("KEYCODE_HOME")

    def press_enter(self) -> None:
        """Press the enter key."""
        self.key_event("KEYCODE_ENTER")

    def launch_app(self, package_name: str, activity: Optional[str] = None) -> None:
        """
        Launch an application.

        Args:
            package_name: App package name
            activity: Specific activity to launch (optional)
        """
        if not self._device:
            raise RuntimeError("Device not connected")

        if activity:
            component = f"{package_name}/{activity}"
            self._device.shell(f"am start -n {component}")
        else:
            # Use monkey to launch main activity
            self._device.shell(
                f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1"
            )

    def close_app(self, package_name: str) -> None:
        """
        Force close an application.

        Args:
            package_name: App package name
        """
        if not self._device:
            raise RuntimeError("Device not connected")
        self._device.shell(f"am force-stop {package_name}")

    def is_app_running(self, package_name: str) -> bool:
        """
        Check if an app is currently running.

        Args:
            package_name: App package name

        Returns:
            True if app is running, False otherwise
        """
        if not self._device:
            raise RuntimeError("Device not connected")
        output = self._device.shell(f"pidof {package_name}")
        return bool(output.strip())

    def get_current_activity(self) -> str:
        """
        Get the current focused activity.

        Returns:
            Current activity name
        """
        if not self._device:
            raise RuntimeError("Device not connected")
        output = self._device.shell("dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'")
        return output.strip()

    def screenshot(self, local_path: str) -> bool:
        """
        Take a screenshot and save to local path.

        Args:
            local_path: Local path to save screenshot

        Returns:
            True if successful, False otherwise
        """
        if not self._device:
            raise RuntimeError("Device not connected")

        try:
            device_path = "/sdcard/screenshot_temp.png"
            self._device.shell(f"screencap -p {device_path}")
            self._device.pull(device_path, local_path)
            self._device.shell(f"rm {device_path}")
            return True
        except Exception as e:
            print(f"Screenshot failed: {e}")
            return False

    def push_file(self, local_path: str, device_path: str) -> bool:
        """
        Push a file to the device.

        Args:
            local_path: Local file path
            device_path: Destination path on device

        Returns:
            True if successful, False otherwise
        """
        if not self._device:
            raise RuntimeError("Device not connected")

        try:
            self._device.push(local_path, device_path)
            return True
        except Exception as e:
            print(f"Push failed: {e}")
            return False

    def pull_file(self, device_path: str, local_path: str) -> bool:
        """
        Pull a file from the device.

        Args:
            device_path: Source path on device
            local_path: Local destination path

        Returns:
            True if successful, False otherwise
        """
        if not self._device:
            raise RuntimeError("Device not connected")

        try:
            self._device.pull(device_path, local_path)
            return True
        except Exception as e:
            print(f"Pull failed: {e}")
            return False

    def list_files(self, device_path: str) -> List[str]:
        """
        List files in a directory on device.

        Args:
            device_path: Directory path on device

        Returns:
            List of file names
        """
        if not self._device:
            raise RuntimeError("Device not connected")

        output = self._device.shell(f"ls -1 {device_path}")
        return [f for f in output.strip().split("\n") if f]

    def file_exists(self, device_path: str) -> bool:
        """
        Check if a file exists on device.

        Args:
            device_path: File path on device

        Returns:
            True if file exists, False otherwise
        """
        if not self._device:
            raise RuntimeError("Device not connected")

        result = self._device.shell(f"[ -e {device_path} ] && echo 'exists'")
        return "exists" in result

    def wait(self, seconds: float) -> None:
        """
        Wait for specified seconds.

        Args:
            seconds: Number of seconds to wait
        """
        time.sleep(seconds)

    def get_ui_hierarchy(self) -> str:
        """
        Get the current UI hierarchy (XML dump).

        Returns:
            UI hierarchy XML string
        """
        if not self._device:
            raise RuntimeError("Device not connected")

        device_path = "/sdcard/ui_dump.xml"
        self._device.shell(f"uiautomator dump {device_path}")
        output = self._device.shell(f"cat {device_path}")
        self._device.shell(f"rm {device_path}")
        return output
