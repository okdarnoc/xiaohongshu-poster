#!/usr/bin/env python3
"""
Xiaohongshu Poster - Standalone single-file version
Controls Android phone via ADB to post on Xiaohongshu (小红书)

Usage:
    python xhs_bot_standalone.py test
    python xhs_bot_standalone.py post --title "标题" --content "内容" --image photo.jpg
    python xhs_bot_standalone.py screenshot
"""

import subprocess
import sys
import time
import os
import re
import base64
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Dict, Any


# ============================================================================
# ADB Controller
# ============================================================================

class ADBController:
    """Controller for Android device via ADB."""

    def __init__(self):
        self._device_serial: Optional[str] = None
        self._screen_size: Optional[Tuple[int, int]] = None

    def _run_adb(self, *args, timeout: int = 30) -> str:
        """Run an ADB command and return output."""
        cmd = ["adb"]
        if self._device_serial:
            cmd.extend(["-s", self._device_serial])
        cmd.extend(args)

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout, encoding='utf-8', errors='replace'
            )
            return result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return ""
        except FileNotFoundError:
            print("ERROR: ADB not found. Please install Android SDK Platform Tools.")
            print("Download from: https://developer.android.com/studio/releases/platform-tools")
            sys.exit(1)

    def connect(self, device_serial: Optional[str] = None) -> bool:
        """Connect to device."""
        # Get list of devices
        output = self._run_adb("devices")
        lines = output.strip().split("\n")[1:]  # Skip header

        devices = []
        for line in lines:
            if "\tdevice" in line:
                devices.append(line.split("\t")[0])

        if not devices:
            print("No devices found. Please check:")
            print("  1. USB debugging is enabled on your phone")
            print("  2. Phone is connected via USB")
            print("  3. You tapped 'Allow' on the USB debugging prompt")
            return False

        self._device_serial = device_serial or devices[0]
        print(f"Connected to: {self._device_serial}")

        # Get screen size
        self._screen_size = self._get_screen_size()
        print(f"Screen size: {self._screen_size[0]}x{self._screen_size[1]}")

        return True

    def _get_screen_size(self) -> Tuple[int, int]:
        """Get device screen resolution."""
        output = self._run_adb("shell", "wm", "size")
        for line in output.strip().split("\n"):
            if "Physical size" in line or "Override size" in line:
                size_str = line.split(":")[-1].strip()
                width, height = size_str.split("x")
                return int(width), int(height)
        return 1080, 2400  # Default fallback

    @property
    def screen_size(self) -> Tuple[int, int]:
        return self._screen_size or (1080, 2400)

    def tap(self, x: int, y: int) -> None:
        """Tap at coordinates."""
        self._run_adb("shell", "input", "tap", str(x), str(y))

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
        """Swipe from (x1,y1) to (x2,y2)."""
        self._run_adb("shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms))

    def input_text(self, text: str) -> None:
        """Input ASCII text."""
        escaped = text.replace(" ", "%s").replace("&", "\\&").replace("<", "\\<").replace(">", "\\>")
        escaped = escaped.replace("'", "\\'").replace('"', '\\"')
        self._run_adb("shell", "input", "text", escaped)

    def input_text_chinese(self, text: str) -> None:
        """Input Chinese text via ADBKeyboard broadcast."""
        encoded = base64.b64encode(text.encode("utf-8")).decode("utf-8")
        self._run_adb("shell", "am", "broadcast", "-a", "ADB_INPUT_B64", "--es", "msg", encoded)

    def key_event(self, keycode: str) -> None:
        """Send key event."""
        self._run_adb("shell", "input", "keyevent", keycode)

    def press_back(self) -> None:
        self.key_event("KEYCODE_BACK")

    def press_home(self) -> None:
        self.key_event("KEYCODE_HOME")

    def press_enter(self) -> None:
        self.key_event("KEYCODE_ENTER")

    def launch_app(self, package: str) -> None:
        """Launch app by package name."""
        self._run_adb("shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1")

    def close_app(self, package: str) -> None:
        """Force close app."""
        self._run_adb("shell", "am", "force-stop", package)

    def is_app_installed(self, package: str) -> bool:
        """Check if app is installed."""
        output = self._run_adb("shell", "pm", "list", "packages", package)
        return package in output

    def screenshot(self, local_path: str) -> bool:
        """Take screenshot and save locally."""
        device_path = "/sdcard/screenshot_temp.png"
        self._run_adb("shell", "screencap", "-p", device_path)
        self._run_adb("pull", device_path, local_path)
        self._run_adb("shell", "rm", device_path)
        return os.path.exists(local_path)

    def push_file(self, local_path: str, device_path: str) -> bool:
        """Push file to device."""
        output = self._run_adb("push", local_path, device_path)
        return "error" not in output.lower()

    def shell(self, command: str) -> str:
        """Run shell command on device."""
        return self._run_adb("shell", command)


# ============================================================================
# Xiaohongshu Bot
# ============================================================================

class PostType(Enum):
    IMAGE = "image"
    VIDEO = "video"


@dataclass
class Coordinates:
    """Screen coordinates for UI elements (1080x2400 base resolution)."""
    screen_width: int = 1080
    screen_height: int = 2400
    post_button: Tuple[int, int] = (540, 2280)
    image_option: Tuple[int, int] = (270, 1800)
    video_option: Tuple[int, int] = (810, 1800)
    next_button: Tuple[int, int] = (980, 150)
    title_input: Tuple[int, int] = (540, 400)
    content_input: Tuple[int, int] = (540, 700)
    publish_button: Tuple[int, int] = (980, 150)

    def scale(self, actual_width: int, actual_height: int) -> 'Coordinates':
        """Scale coordinates to actual screen resolution."""
        sx = actual_width / self.screen_width
        sy = actual_height / self.screen_height
        return Coordinates(
            screen_width=actual_width,
            screen_height=actual_height,
            post_button=(int(self.post_button[0] * sx), int(self.post_button[1] * sy)),
            image_option=(int(self.image_option[0] * sx), int(self.image_option[1] * sy)),
            video_option=(int(self.video_option[0] * sx), int(self.video_option[1] * sy)),
            next_button=(int(self.next_button[0] * sx), int(self.next_button[1] * sy)),
            title_input=(int(self.title_input[0] * sx), int(self.title_input[1] * sy)),
            content_input=(int(self.content_input[0] * sx), int(self.content_input[1] * sy)),
            publish_button=(int(self.publish_button[0] * sx), int(self.publish_button[1] * sy)),
        )


class XiaohongshuBot:
    """Bot for automating Xiaohongshu posts."""

    PACKAGE = "com.xingin.xhs"

    def __init__(self):
        self.adb = ADBController()
        self.coords = Coordinates()
        self._connected = False

    def connect(self) -> bool:
        """Connect to Android device."""
        if not self.adb.connect():
            return False

        # Scale coordinates to actual screen size
        w, h = self.adb.screen_size
        self.coords = self.coords.scale(w, h)
        self._connected = True
        return True

    def test_connection(self) -> bool:
        """Test device connection and app installation."""
        print("\nRunning connection tests...")

        if not self._connected:
            print("  [FAIL] Not connected")
            return False
        print("  [OK] Device connected")

        w, h = self.adb.screen_size
        print(f"  [OK] Screen: {w}x{h}")

        if self.adb.is_app_installed(self.PACKAGE):
            print(f"  [OK] Xiaohongshu installed")
        else:
            print(f"  [FAIL] Xiaohongshu not installed")
            return False

        # Check ADBKeyboard
        if self.adb.is_app_installed("com.android.adbkeyboard"):
            print("  [OK] ADBKeyboard installed (Chinese input supported)")
        else:
            print("  [WARN] ADBKeyboard not installed")
            print("         Chinese input may not work correctly")
            print("         Install from: https://github.com/nickmelo/ADBKeyBoard")

        print("\nConnection test passed!")
        return True

    def launch_app(self) -> None:
        """Launch Xiaohongshu."""
        print("Launching Xiaohongshu...")
        self.adb.close_app(self.PACKAGE)
        time.sleep(1)
        self.adb.launch_app(self.PACKAGE)
        time.sleep(3)
        print("App launched")

    def close_app(self) -> None:
        """Close Xiaohongshu."""
        self.adb.close_app(self.PACKAGE)
        print("App closed")

    def _tap(self, coord: Tuple[int, int], wait: float = 1.5) -> None:
        """Tap and wait."""
        self.adb.tap(coord[0], coord[1])
        time.sleep(wait)

    def _push_media(self, local_paths: List[str]) -> List[str]:
        """Push media files to device."""
        device_dir = "/sdcard/DCIM/XHSBot"
        self.adb.shell(f"mkdir -p {device_dir}")

        device_paths = []
        for local_path in local_paths:
            filename = os.path.basename(local_path)
            device_path = f"{device_dir}/{filename}"
            print(f"  Pushing {filename}...")
            if self.adb.push_file(local_path, device_path):
                device_paths.append(device_path)
                # Trigger media scan
                self.adb.shell(f"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://{device_path}")

        time.sleep(2)  # Wait for media scanner
        return device_paths

    def _select_media(self, count: int) -> None:
        """Select media from gallery grid."""
        print(f"  Selecting {count} item(s)...")
        w, h = self.adb.screen_size
        grid_x = w // 6
        grid_y = h // 3
        spacing = w // 3

        for i in range(min(count, 9)):
            row, col = i // 3, i % 3
            x = grid_x + (col * spacing)
            y = grid_y + (row * spacing)
            self.adb.tap(x, y)
            time.sleep(0.3)

        time.sleep(1)

    def _input_text(self, text: str) -> None:
        """Input text (handles Chinese)."""
        # Try ADBKeyboard first for Chinese support
        if any('\u4e00' <= c <= '\u9fff' for c in text):
            self.adb.input_text_chinese(text)
        else:
            self.adb.input_text(text)
        time.sleep(0.5)

    def create_post(
        self,
        title: str,
        content: str,
        media_paths: List[str],
        post_type: PostType = PostType.IMAGE,
        hashtags: Optional[List[str]] = None,
    ) -> bool:
        """
        Create a post on Xiaohongshu.

        Args:
            title: Post title
            content: Post description
            media_paths: List of image/video file paths
            post_type: IMAGE or VIDEO
            hashtags: Optional list of hashtags
        """
        if not self._connected:
            print("Error: Not connected. Call connect() first.")
            return False

        # Validate media files
        for path in media_paths:
            if not os.path.exists(path):
                print(f"Error: File not found: {path}")
                return False

        try:
            # Launch app
            self.launch_app()

            # Push media to device
            print("Uploading media...")
            device_paths = self._push_media(media_paths)
            if not device_paths:
                print("Error: Failed to push media")
                return False

            # Tap post button (+)
            print("Opening post creator...")
            self._tap(self.coords.post_button)

            # Select image or video
            if post_type == PostType.IMAGE:
                self._tap(self.coords.image_option)
            else:
                self._tap(self.coords.video_option)

            # Select media from gallery
            self._select_media(len(media_paths))

            # Tap next
            print("Proceeding to details...")
            self._tap(self.coords.next_button)
            time.sleep(2)

            # Input title
            print("Entering title...")
            self._tap(self.coords.title_input, wait=0.5)
            self._input_text(title)

            # Input content
            print("Entering content...")
            self._tap(self.coords.content_input, wait=0.5)

            full_content = content
            if hashtags:
                full_content += " " + " ".join(f"#{tag}" for tag in hashtags)
            self._input_text(full_content)

            # Hide keyboard
            self.adb.press_back()
            time.sleep(1)

            # Publish
            print("Publishing...")
            self._tap(self.coords.publish_button)

            # Wait for upload
            print("Waiting for upload...")
            time.sleep(10)

            print("\nPost created successfully!")
            return True

        except Exception as e:
            print(f"Error: {e}")
            return False

    def screenshot(self, output_path: str = "screenshot.png") -> bool:
        """Take a screenshot."""
        if self.adb.screenshot(output_path):
            print(f"Screenshot saved: {output_path}")
            return True
        print("Screenshot failed")
        return False

    def calibrate(self) -> None:
        """Help calibrate coordinates."""
        print("\n" + "=" * 50)
        print("COORDINATE CALIBRATION")
        print("=" * 50)

        w, h = self.adb.screen_size
        print(f"\nYour screen resolution: {w}x{h}")

        # Take screenshot
        self.screenshot("calibration.png")

        print("\nTo calibrate for your device:")
        print("1. Open calibration.png")
        print("2. Open Xiaohongshu on your phone")
        print("3. Find pixel coordinates for each button:")
        print("   - post_button: The '+' at bottom center")
        print("   - image_option: 'Image' in post type menu")
        print("   - next_button: 'Next' after selecting media")
        print("   - title_input: Title text field")
        print("   - content_input: Description text field")
        print("   - publish_button: 'Publish' button")
        print("\n4. Edit this script and update the Coordinates class")


# ============================================================================
# CLI
# ============================================================================

def print_usage():
    print("""
Xiaohongshu Poster Bot

Usage:
    python xhs_bot_standalone.py test                    Test device connection
    python xhs_bot_standalone.py screenshot              Take a screenshot
    python xhs_bot_standalone.py calibrate               Help calibrate coordinates
    python xhs_bot_standalone.py launch                  Launch Xiaohongshu
    python xhs_bot_standalone.py close                   Close Xiaohongshu
    python xhs_bot_standalone.py post [options]          Create a post

Post options:
    --title, -t TEXT       Post title (required)
    --content, -c TEXT     Post description (required)
    --image, -i PATH       Image file (can use multiple times)
    --video, -v PATH       Video file
    --hashtag, -h TAG      Hashtag without # (can use multiple times)

Examples:
    python xhs_bot_standalone.py test
    python xhs_bot_standalone.py post -t "Hello" -c "My first post" -i photo.jpg
    python xhs_bot_standalone.py post -t "旅行" -c "美丽的风景" -i img1.jpg -i img2.jpg -h 旅行 -h 风景
""")


def parse_args(args: List[str]) -> Dict[str, Any]:
    """Simple argument parser."""
    result = {
        "command": None,
        "title": None,
        "content": None,
        "images": [],
        "video": None,
        "hashtags": [],
    }

    if not args:
        return result

    result["command"] = args[0]

    i = 1
    while i < len(args):
        arg = args[i]

        if arg in ("--title", "-t") and i + 1 < len(args):
            result["title"] = args[i + 1]
            i += 2
        elif arg in ("--content", "-c") and i + 1 < len(args):
            result["content"] = args[i + 1]
            i += 2
        elif arg in ("--image", "-i") and i + 1 < len(args):
            result["images"].append(args[i + 1])
            i += 2
        elif arg in ("--video", "-v") and i + 1 < len(args):
            result["video"] = args[i + 1]
            i += 2
        elif arg in ("--hashtag", "-h") and i + 1 < len(args):
            result["hashtags"].append(args[i + 1])
            i += 2
        else:
            i += 1

    return result


def main():
    args = parse_args(sys.argv[1:])
    command = args["command"]

    if not command or command in ("help", "--help", "-h"):
        print_usage()
        return

    bot = XiaohongshuBot()

    if command == "test":
        if bot.connect():
            bot.test_connection()

    elif command == "screenshot":
        if bot.connect():
            bot.screenshot()

    elif command == "calibrate":
        if bot.connect():
            bot.calibrate()

    elif command == "launch":
        if bot.connect():
            bot.launch_app()

    elif command == "close":
        if bot.connect():
            bot.close_app()

    elif command == "post":
        if not args["title"]:
            print("Error: --title is required")
            return
        if not args["content"]:
            print("Error: --content is required")
            return
        if not args["images"] and not args["video"]:
            print("Error: --image or --video is required")
            return

        if not bot.connect():
            return

        if args["video"]:
            bot.create_post(
                title=args["title"],
                content=args["content"],
                media_paths=[args["video"]],
                post_type=PostType.VIDEO,
                hashtags=args["hashtags"] or None,
            )
        else:
            bot.create_post(
                title=args["title"],
                content=args["content"],
                media_paths=args["images"],
                post_type=PostType.IMAGE,
                hashtags=args["hashtags"] or None,
            )

    else:
        print(f"Unknown command: {command}")
        print_usage()


if __name__ == "__main__":
    main()
