#!/usr/bin/env python3
"""
Xiaohongshu Poster - Smart version with UI element detection
Controls Android phone via ADB to post on Xiaohongshu (小红书)

This version uses UI Automator to find elements by text/properties,
making it work across different screen sizes and layouts.

Usage:
    python xhs_bot_smart.py test
    python xhs_bot_smart.py post --title "标题" --content "内容" --image photo.jpg
    python xhs_bot_smart.py screenshot
"""

import subprocess
import sys
import time
import os
import re
import base64
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple, Dict, Any


class ADBController:
    """Controller for Android device via ADB with UI element detection."""

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
                cmd, capture_output=True, text=True, timeout=timeout,
                encoding='utf-8', errors='replace'
            )
            return result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return ""
        except FileNotFoundError:
            print("ERROR: ADB not found. Install Android SDK Platform Tools.")
            sys.exit(1)

    def connect(self, device_serial: Optional[str] = None) -> bool:
        """Connect to device."""
        output = self._run_adb("devices")
        lines = output.strip().split("\n")[1:]

        devices = []
        for line in lines:
            if "\tdevice" in line:
                devices.append(line.split("\t")[0])

        if not devices:
            print("No devices found. Check USB debugging is enabled.")
            return False

        self._device_serial = device_serial or devices[0]
        print(f"Connected to: {self._device_serial}")

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
        return 1080, 2400

    @property
    def screen_size(self) -> Tuple[int, int]:
        return self._screen_size or (1080, 2400)

    def tap(self, x: int, y: int) -> None:
        """Tap at coordinates."""
        self._run_adb("shell", "input", "tap", str(x), str(y))

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
        """Swipe gesture."""
        self._run_adb("shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms))

    def input_text(self, text: str) -> None:
        """Input ASCII text."""
        escaped = text.replace(" ", "%s").replace("&", "\\&")
        escaped = escaped.replace("'", "\\'").replace('"', '\\"')
        self._run_adb("shell", "input", "text", escaped)

    def input_text_chinese(self, text: str) -> None:
        """Input Chinese text via ADBKeyboard."""
        encoded = base64.b64encode(text.encode("utf-8")).decode("utf-8")
        self._run_adb("shell", "am", "broadcast", "-a", "ADB_INPUT_B64", "--es", "msg", encoded)

    def key_event(self, keycode: str) -> None:
        """Send key event."""
        self._run_adb("shell", "input", "keyevent", keycode)

    def press_back(self) -> None:
        self.key_event("KEYCODE_BACK")

    def press_enter(self) -> None:
        self.key_event("KEYCODE_ENTER")

    def launch_app(self, package: str) -> None:
        """Launch app."""
        self._run_adb("shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1")

    def close_app(self, package: str) -> None:
        """Force close app."""
        self._run_adb("shell", "am", "force-stop", package)

    def is_app_installed(self, package: str) -> bool:
        """Check if app is installed."""
        output = self._run_adb("shell", "pm", "list", "packages", package)
        return package in output

    def screenshot(self, local_path: str) -> bool:
        """Take screenshot."""
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
        """Run shell command."""
        return self._run_adb("shell", command)

    def get_ui_dump(self) -> str:
        """Get UI hierarchy XML."""
        device_path = "/sdcard/ui_dump.xml"
        self._run_adb("shell", "uiautomator", "dump", device_path)
        output = self._run_adb("shell", "cat", device_path)
        self._run_adb("shell", "rm", device_path)
        return output

    def find_element(self, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Find UI element by properties.

        Args:
            text: Exact text match
            text_contains: Partial text match
            resource_id: Resource ID (e.g., "com.xingin.xhs:id/xxx")
            class_name: Class name (e.g., "android.widget.Button")
            content_desc: Content description

        Returns:
            Dict with 'bounds', 'center', 'text' etc. or None
        """
        xml_str = self.get_ui_dump()
        if not xml_str or "<?xml" not in xml_str:
            return None

        try:
            # Clean up XML string
            xml_start = xml_str.find("<?xml")
            xml_str = xml_str[xml_start:]
            root = ET.fromstring(xml_str)
        except ET.ParseError:
            return None

        for node in root.iter("node"):
            attribs = node.attrib

            # Check text
            if "text" in kwargs:
                if attribs.get("text") != kwargs["text"]:
                    continue

            # Check text_contains
            if "text_contains" in kwargs:
                if kwargs["text_contains"] not in attribs.get("text", ""):
                    continue

            # Check resource_id
            if "resource_id" in kwargs:
                if kwargs["resource_id"] not in attribs.get("resource-id", ""):
                    continue

            # Check class_name
            if "class_name" in kwargs:
                if attribs.get("class") != kwargs["class_name"]:
                    continue

            # Check content_desc
            if "content_desc" in kwargs:
                if kwargs["content_desc"] not in attribs.get("content-desc", ""):
                    continue

            # Parse bounds [x1,y1][x2,y2]
            bounds_str = attribs.get("bounds", "")
            match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
            if match:
                x1, y1, x2, y2 = map(int, match.groups())
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                return {
                    "bounds": (x1, y1, x2, y2),
                    "center": (center_x, center_y),
                    "text": attribs.get("text", ""),
                    "resource_id": attribs.get("resource-id", ""),
                    "class": attribs.get("class", ""),
                    "content_desc": attribs.get("content-desc", ""),
                }

        return None

    def find_elements(self, **kwargs) -> List[Dict[str, Any]]:
        """Find all matching UI elements."""
        xml_str = self.get_ui_dump()
        if not xml_str or "<?xml" not in xml_str:
            return []

        try:
            xml_start = xml_str.find("<?xml")
            xml_str = xml_str[xml_start:]
            root = ET.fromstring(xml_str)
        except ET.ParseError:
            return []

        results = []
        for node in root.iter("node"):
            attribs = node.attrib
            match = True

            if "text" in kwargs and attribs.get("text") != kwargs["text"]:
                match = False
            if "text_contains" in kwargs and kwargs["text_contains"] not in attribs.get("text", ""):
                match = False
            if "resource_id" in kwargs and kwargs["resource_id"] not in attribs.get("resource-id", ""):
                match = False
            if "class_name" in kwargs and attribs.get("class") != kwargs["class_name"]:
                match = False
            if "content_desc" in kwargs and kwargs["content_desc"] not in attribs.get("content-desc", ""):
                match = False

            if match:
                bounds_str = attribs.get("bounds", "")
                bounds_match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
                if bounds_match:
                    x1, y1, x2, y2 = map(int, bounds_match.groups())
                    results.append({
                        "bounds": (x1, y1, x2, y2),
                        "center": ((x1 + x2) // 2, (y1 + y2) // 2),
                        "text": attribs.get("text", ""),
                        "resource_id": attribs.get("resource-id", ""),
                        "class": attribs.get("class", ""),
                        "content_desc": attribs.get("content-desc", ""),
                    })

        return results

    def tap_element(self, **kwargs) -> bool:
        """Find element and tap it."""
        element = self.find_element(**kwargs)
        if element:
            self.tap(element["center"][0], element["center"][1])
            return True
        return False

    def wait_for_element(self, timeout: int = 10, **kwargs) -> Optional[Dict[str, Any]]:
        """Wait for element to appear."""
        start = time.time()
        while time.time() - start < timeout:
            element = self.find_element(**kwargs)
            if element:
                return element
            time.sleep(0.5)
        return None


class XiaohongshuBot:
    """Smart bot that finds UI elements dynamically."""

    PACKAGE = "com.xingin.xhs"

    def __init__(self):
        self.adb = ADBController()
        self._connected = False

    def connect(self) -> bool:
        if not self.adb.connect():
            return False
        self._connected = True
        return True

    def test_connection(self) -> bool:
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

        if self.adb.is_app_installed("com.android.adbkeyboard"):
            print("  [OK] ADBKeyboard installed")
        else:
            print("  [WARN] ADBKeyboard not installed (Chinese may not work)")

        print("\nConnection test passed!")
        return True

    def launch_app(self) -> None:
        print("Launching Xiaohongshu...")
        self.adb.close_app(self.PACKAGE)
        time.sleep(1)
        self.adb.launch_app(self.PACKAGE)
        time.sleep(4)
        print("App launched")

    def close_app(self) -> None:
        self.adb.close_app(self.PACKAGE)
        print("App closed")

    def _input_text(self, text: str) -> None:
        """Input text (handles Chinese)."""
        if any('\u4e00' <= c <= '\u9fff' for c in text):
            self.adb.input_text_chinese(text)
        else:
            self.adb.input_text(text)
        time.sleep(0.5)

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
                self.adb.shell(f"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://{device_path}")

        time.sleep(2)
        return device_paths

    def _find_and_tap(self, description: str, timeout: int = 10, **kwargs) -> bool:
        """Find element and tap, with logging."""
        print(f"  Looking for: {description}...")
        element = self.adb.wait_for_element(timeout=timeout, **kwargs)
        if element:
            print(f"  Found at {element['center']}")
            self.adb.tap(element["center"][0], element["center"][1])
            time.sleep(1.5)
            return True
        print(f"  [!] Not found: {description}")
        return False

    def _tap_center_bottom(self) -> None:
        """Tap the center bottom area (where + button usually is)."""
        w, h = self.adb.screen_size
        # The + button is typically at bottom center
        self.adb.tap(w // 2, h - 120)
        time.sleep(1.5)

    def _select_images_from_gallery(self, count: int) -> None:
        """Select images from gallery."""
        print(f"  Selecting {count} image(s) from gallery...")
        time.sleep(1)

        # Find clickable image items in the gallery
        # Usually they have checkboxes or are ImageView elements
        images = self.adb.find_elements(class_name="android.widget.ImageView")

        # Filter to likely gallery thumbnails (skip small icons)
        gallery_images = []
        for img in images:
            x1, y1, x2, y2 = img["bounds"]
            width = x2 - x1
            height = y2 - y1
            # Gallery thumbnails are usually decent sized squares
            if width > 100 and height > 100 and abs(width - height) < 50:
                gallery_images.append(img)

        # Sort by position (top-left first)
        gallery_images.sort(key=lambda e: (e["bounds"][1], e["bounds"][0]))

        # Tap first N images
        for i, img in enumerate(gallery_images[:count]):
            print(f"    Tapping image {i+1} at {img['center']}")
            self.adb.tap(img["center"][0], img["center"][1])
            time.sleep(0.5)

    def create_post(
        self,
        title: str,
        content: str,
        media_paths: List[str],
        hashtags: Optional[List[str]] = None,
    ) -> bool:
        """Create a post using smart UI detection."""

        if not self._connected:
            print("Error: Not connected")
            return False

        for path in media_paths:
            if not os.path.exists(path):
                print(f"Error: File not found: {path}")
                return False

        try:
            self.launch_app()

            # Push media
            print("Uploading media to device...")
            device_paths = self._push_media(media_paths)
            if not device_paths:
                print("Error: Failed to push media")
                return False

            # Look for the + (create post) button
            print("Looking for post creation button...")

            # Try multiple ways to find it
            found = (
                self._find_and_tap("Post button", content_desc="发布") or
                self._find_and_tap("Post button (+)", text="+") or
                self._find_and_tap("Post button (发笔记)", text_contains="发笔记") or
                self._find_and_tap("Post button (拍摄)", text_contains="拍摄")
            )

            if not found:
                print("  Trying center bottom tap...")
                self._tap_center_bottom()

            time.sleep(2)

            # Look for image/photo option
            print("Selecting image post type...")
            found = (
                self._find_and_tap("Image option", text="相册") or
                self._find_and_tap("Image option", text_contains="图片") or
                self._find_and_tap("Image option", text_contains="照片") or
                self._find_and_tap("Image option", text="图文")
            )

            if not found:
                # Try tapping first option area
                w, h = self.adb.screen_size
                self.adb.tap(w // 4, h // 2)
                time.sleep(1.5)

            # Select images
            time.sleep(1)
            self._select_images_from_gallery(len(media_paths))

            # Look for Next/Continue button
            print("Looking for Next button...")
            found = (
                self._find_and_tap("Next", text="下一步") or
                self._find_and_tap("Next", text_contains="下一步") or
                self._find_and_tap("Next", text="继续") or
                self._find_and_tap("Next", text="确定") or
                self._find_and_tap("Next", text="完成")
            )

            if not found:
                # Try top right corner
                w, h = self.adb.screen_size
                self.adb.tap(w - 100, 100)
                time.sleep(1.5)

            time.sleep(2)

            # Input title - find the title input field
            print("Entering title...")
            title_field = (
                self.adb.find_element(text_contains="标题") or
                self.adb.find_element(text_contains="添加标题") or
                self.adb.find_element(resource_id="title")
            )
            if title_field:
                self.adb.tap(title_field["center"][0], title_field["center"][1])
            else:
                # Tap upper area where title usually is
                w, h = self.adb.screen_size
                self.adb.tap(w // 2, h // 4)

            time.sleep(0.5)
            self._input_text(title)
            time.sleep(1)

            # Input content - find content field
            print("Entering content...")
            content_field = (
                self.adb.find_element(text_contains="正文") or
                self.adb.find_element(text_contains="添加正文") or
                self.adb.find_element(text_contains="分享") or
                self.adb.find_element(resource_id="content")
            )
            if content_field:
                self.adb.tap(content_field["center"][0], content_field["center"][1])
            else:
                # Tap middle area
                w, h = self.adb.screen_size
                self.adb.tap(w // 2, h // 2)

            time.sleep(0.5)
            full_content = content
            if hashtags:
                full_content += " " + " ".join(f"#{tag}" for tag in hashtags)
            self._input_text(full_content)

            # Hide keyboard
            self.adb.press_back()
            time.sleep(1)

            # Find and tap publish button
            print("Publishing...")
            found = (
                self._find_and_tap("Publish", text="发布笔记") or
                self._find_and_tap("Publish", text="发布") or
                self._find_and_tap("Publish", text_contains="发布") or
                self._find_and_tap("Publish", text="发表")
            )

            if not found:
                # Try top right
                w, h = self.adb.screen_size
                self.adb.tap(w - 80, 100)

            print("Waiting for upload...")
            time.sleep(10)

            print("\nPost created successfully!")
            return True

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def screenshot(self, output_path: str = "screenshot.png") -> bool:
        if self.adb.screenshot(output_path):
            print(f"Screenshot saved: {output_path}")
            return True
        return False

    def dump_ui(self) -> None:
        """Dump current UI elements for debugging."""
        print("\nDumping UI elements...")
        xml_str = self.adb.get_ui_dump()

        # Save raw XML
        with open("ui_dump.xml", "w", encoding="utf-8") as f:
            f.write(xml_str)
        print("Raw XML saved to: ui_dump.xml")

        # Parse and show clickable elements
        try:
            xml_start = xml_str.find("<?xml")
            if xml_start >= 0:
                xml_str = xml_str[xml_start:]
            root = ET.fromstring(xml_str)

            print("\nClickable elements:")
            print("-" * 60)
            for node in root.iter("node"):
                attribs = node.attrib
                if attribs.get("clickable") == "true":
                    text = attribs.get("text", "")
                    desc = attribs.get("content-desc", "")
                    res_id = attribs.get("resource-id", "")
                    bounds = attribs.get("bounds", "")

                    info = []
                    if text:
                        info.append(f'text="{text}"')
                    if desc:
                        info.append(f'desc="{desc}"')
                    if res_id:
                        info.append(f'id="{res_id.split("/")[-1]}"')

                    if info:
                        print(f"  {bounds} {' '.join(info)}")

        except ET.ParseError as e:
            print(f"XML parse error: {e}")


def print_usage():
    print("""
Xiaohongshu Smart Bot (with UI detection)

Usage:
    python xhs_bot_smart.py test              Test device connection
    python xhs_bot_smart.py screenshot        Take a screenshot
    python xhs_bot_smart.py dump              Dump UI elements (for debugging)
    python xhs_bot_smart.py launch            Launch Xiaohongshu
    python xhs_bot_smart.py close             Close Xiaohongshu
    python xhs_bot_smart.py post [options]    Create a post

Post options:
    --title, -t TEXT       Post title (required)
    --content, -c TEXT     Post description (required)
    --image, -i PATH       Image file (can use multiple)
    --hashtag, -h TAG      Hashtag without # (can use multiple)

Examples:
    python xhs_bot_smart.py test
    python xhs_bot_smart.py dump
    python xhs_bot_smart.py post -t "Hello" -c "My post" -i photo.jpg
""")


def parse_args(args: List[str]) -> Dict[str, Any]:
    result = {
        "command": None,
        "title": None,
        "content": None,
        "images": [],
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

    elif command == "dump":
        if bot.connect():
            bot.dump_ui()

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
        if not args["images"]:
            print("Error: --image is required")
            return

        if bot.connect():
            bot.create_post(
                title=args["title"],
                content=args["content"],
                media_paths=args["images"],
                hashtags=args["hashtags"] or None,
            )
    else:
        print(f"Unknown command: {command}")
        print_usage()


if __name__ == "__main__":
    main()
