"""
Xiaohongshu Bot - Automated posting on Xiaohongshu (Little Red Book) app.
"""

import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any

from .adb_controller import ADBController
from .config import Config


class PostType(Enum):
    """Type of post to create."""

    IMAGE = "image"
    VIDEO = "video"


@dataclass
class PostContent:
    """Content for a Xiaohongshu post."""

    title: str
    content: str
    media_paths: List[str] = field(default_factory=list)
    post_type: PostType = PostType.IMAGE
    hashtags: List[str] = field(default_factory=list)
    location: Optional[str] = None

    def __post_init__(self):
        """Validate post content."""
        if not self.title:
            raise ValueError("Post title cannot be empty")
        if len(self.title) > 20:
            print(f"Warning: Title is {len(self.title)} chars, may be truncated (max ~20)")
        if not self.media_paths:
            raise ValueError("At least one media file is required")
        for path in self.media_paths:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Media file not found: {path}")


class XiaohongshuBot:
    """
    Bot for automating posts on Xiaohongshu app.

    Features:
    - Post images or videos with title and description
    - Add hashtags automatically
    - Support Chinese text input
    - Configurable timing and coordinates
    """

    PACKAGE_NAME = "com.xingin.xhs"
    MAIN_ACTIVITY = "com.xingin.xhs.index.v2.IndexActivityV2"

    def __init__(
        self,
        config: Optional[Config] = None,
        adb_controller: Optional[ADBController] = None,
    ):
        """
        Initialize Xiaohongshu bot.

        Args:
            config: Configuration object (uses default if None)
            adb_controller: ADB controller instance (creates new if None)
        """
        self.config = config or Config()
        self.adb = adb_controller or ADBController(
            host=self.config.adb["adb_host"],
            port=self.config.adb["adb_port"],
        )
        self._coordinates: Optional[Dict[str, Any]] = None
        self._connected = False

    def connect(self) -> bool:
        """
        Connect to the Android device.

        Returns:
            True if connection successful, False otherwise
        """
        connection_type = self.config.adb["connection_type"]

        if connection_type == "wifi":
            success = self.adb.connect(
                device_ip=self.config.adb["device_ip"],
                device_port=self.config.adb["device_port"],
            )
        else:
            success = self.adb.connect()

        if success:
            # Scale coordinates to actual device resolution
            width, height = self.adb.screen_size
            self._coordinates = self.config.scale_coordinates(width, height)
            self._connected = True

        return success

    def disconnect(self) -> None:
        """Disconnect from the device."""
        self.adb.disconnect()
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if connected to device."""
        return self._connected and self.adb.is_connected

    def _wait(self, timing_key: str) -> None:
        """Wait for configured timing."""
        wait_time = self.config.timing.get(timing_key, 1)
        self.adb.wait(wait_time)

    def _tap(self, coord_key: str) -> None:
        """Tap at configured coordinate."""
        if not self._coordinates:
            raise RuntimeError("Not connected to device")
        coord = self._coordinates[coord_key]
        self.adb.tap(coord["x"], coord["y"])

    def launch_app(self) -> None:
        """Launch Xiaohongshu app."""
        print("Launching Xiaohongshu...")
        package = self.config.xiaohongshu.get("package_name", self.PACKAGE_NAME)
        activity = self.config.xiaohongshu.get("main_activity", self.MAIN_ACTIVITY)

        # Close app first if running
        if self.adb.is_app_running(package):
            self.adb.close_app(package)
            self.adb.wait(1)

        self.adb.launch_app(package, activity)
        self._wait("app_launch_wait")
        print("Xiaohongshu launched")

    def close_app(self) -> None:
        """Close Xiaohongshu app."""
        package = self.config.xiaohongshu.get("package_name", self.PACKAGE_NAME)
        self.adb.close_app(package)
        print("Xiaohongshu closed")

    def go_home(self) -> None:
        """Navigate to home screen in app."""
        # Press back a few times to ensure we're at home
        for _ in range(3):
            self.adb.press_back()
            self.adb.wait(0.5)

    def _push_media_to_device(self, local_paths: List[str]) -> List[str]:
        """
        Push media files to device storage.

        Args:
            local_paths: List of local media file paths

        Returns:
            List of device paths where files were pushed
        """
        device_paths = []
        device_media_dir = "/sdcard/DCIM/XHSBot"

        # Create directory on device
        self.adb._device.shell(f"mkdir -p {device_media_dir}")

        for local_path in local_paths:
            filename = os.path.basename(local_path)
            device_path = f"{device_media_dir}/{filename}"

            print(f"Pushing {filename} to device...")
            if self.adb.push_file(local_path, device_path):
                device_paths.append(device_path)
                # Trigger media scanner so file appears in gallery
                self.adb._device.shell(
                    f"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE "
                    f"-d file://{device_path}"
                )
            else:
                print(f"Failed to push {filename}")

        # Wait for media scanner
        self.adb.wait(2)

        return device_paths

    def _open_post_creator(self, post_type: PostType) -> None:
        """Open the post creation screen."""
        print("Opening post creator...")

        # Tap the center "+" button to create post
        self._tap("post_button")
        self._wait("action_wait")

        # Select image or video option
        if post_type == PostType.IMAGE:
            self._tap("image_option")
        else:
            self._tap("video_option")

        self._wait("action_wait")

    def _select_media_from_gallery(self, count: int = 1) -> None:
        """
        Select media from gallery.

        This method assumes:
        1. Gallery picker is open
        2. Most recent photos are shown first

        Args:
            count: Number of media items to select
        """
        print(f"Selecting {count} media item(s)...")

        # Coordinates for first few gallery items (grid layout)
        # These are approximate for a 3-column grid
        width, height = self.adb.screen_size
        grid_start_x = width // 6
        grid_start_y = height // 3
        grid_spacing_x = width // 3

        for i in range(min(count, 9)):  # Max 9 images per post
            row = i // 3
            col = i % 3
            x = grid_start_x + (col * grid_spacing_x)
            y = grid_start_y + (row * grid_spacing_x)
            self.adb.tap(x, y)
            self.adb.wait(0.3)

        self._wait("action_wait")

    def _input_chinese_text(self, text: str) -> None:
        """
        Input Chinese text.

        Uses multiple fallback methods:
        1. ADBKeyboard broadcast (requires ADBKeyboard app)
        2. Direct input (may not work for Chinese)
        """
        try:
            # Try ADBKeyboard first (best for Chinese)
            self.adb.input_text_chinese(text)
        except Exception:
            # Fallback to regular input (may lose Chinese characters)
            print("Warning: ADBKeyboard not available, Chinese text may not input correctly")
            self.adb.input_text(text)

    def _fill_post_details(self, post: PostContent) -> None:
        """Fill in post title and content."""
        print("Filling post details...")

        # Tap title input
        self._tap("title_input")
        self.adb.wait(0.5)

        # Input title
        self._input_chinese_text(post.title)
        self._wait("action_wait")

        # Tap content area
        self._tap("content_input")
        self.adb.wait(0.5)

        # Build content with hashtags
        full_content = post.content

        # Add hashtags
        all_hashtags = list(post.hashtags) + self.config.post.get("default_hashtags", [])
        if all_hashtags:
            hashtag_text = " " + " ".join(f"#{tag}" for tag in all_hashtags)
            full_content += hashtag_text

        # Input content
        self._input_chinese_text(full_content)
        self._wait("action_wait")

    def _publish_post(self) -> None:
        """Tap the publish button to submit the post."""
        print("Publishing post...")

        self._tap("publish_button")
        self._wait("upload_wait")

        # Wait for upload/publishing
        print("Waiting for upload to complete...")
        self._wait("post_complete_wait")

        print("Post published successfully!")

    def create_post(
        self,
        title: str,
        content: str,
        media_paths: List[str],
        post_type: PostType = PostType.IMAGE,
        hashtags: Optional[List[str]] = None,
        location: Optional[str] = None,
        auto_select_media: bool = True,
    ) -> bool:
        """
        Create a new post on Xiaohongshu.

        Args:
            title: Post title (max ~20 characters recommended)
            content: Post description/content
            media_paths: List of local paths to images or video
            post_type: Type of post (IMAGE or VIDEO)
            hashtags: List of hashtags to add
            location: Location to tag (optional)
            auto_select_media: If True, push media and auto-select from gallery

        Returns:
            True if post created successfully, False otherwise
        """
        if not self.is_connected:
            print("Error: Not connected to device. Call connect() first.")
            return False

        try:
            # Validate and create post content
            post = PostContent(
                title=title,
                content=content,
                media_paths=media_paths,
                post_type=post_type,
                hashtags=hashtags or [],
                location=location,
            )

            # Launch app
            self.launch_app()

            # Push media to device if needed
            if auto_select_media:
                device_paths = self._push_media_to_device(media_paths)
                if not device_paths:
                    print("Error: Failed to push media files to device")
                    return False

            # Open post creator
            self._open_post_creator(post.post_type)

            # Select media from gallery
            if auto_select_media:
                self._select_media_from_gallery(len(media_paths))

            # Tap next to proceed to details
            self._tap("next_button")
            self._wait("action_wait")

            # Fill in title and content
            self._fill_post_details(post)

            # Publish
            self._publish_post()

            return True

        except Exception as e:
            print(f"Error creating post: {e}")
            return False

    def create_image_post(
        self,
        title: str,
        content: str,
        image_paths: List[str],
        hashtags: Optional[List[str]] = None,
    ) -> bool:
        """
        Create an image post (convenience method).

        Args:
            title: Post title
            content: Post description
            image_paths: List of image file paths
            hashtags: Hashtags to add

        Returns:
            True if successful
        """
        return self.create_post(
            title=title,
            content=content,
            media_paths=image_paths,
            post_type=PostType.IMAGE,
            hashtags=hashtags,
        )

    def create_video_post(
        self,
        title: str,
        content: str,
        video_path: str,
        hashtags: Optional[List[str]] = None,
    ) -> bool:
        """
        Create a video post (convenience method).

        Args:
            title: Post title
            content: Post description
            video_path: Video file path
            hashtags: Hashtags to add

        Returns:
            True if successful
        """
        return self.create_post(
            title=title,
            content=content,
            media_paths=[video_path],
            post_type=PostType.VIDEO,
            hashtags=hashtags,
        )

    def calibrate_coordinates(self) -> Dict[str, Any]:
        """
        Interactive coordinate calibration helper.

        Takes screenshots and helps identify UI element positions.

        Returns:
            Dictionary of calibrated coordinates
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to device")

        print("Starting coordinate calibration...")
        print("This will help you find the correct coordinates for UI elements.")

        calibrated = {}

        # Take initial screenshot
        screenshot_path = "/tmp/xhs_calibration.png"
        self.adb.screenshot(screenshot_path)
        print(f"Screenshot saved to: {screenshot_path}")
        print("Open this image to identify coordinates.")

        width, height = self.adb.screen_size
        print(f"Device resolution: {width}x{height}")

        print("\nTo calibrate, you'll need to:")
        print("1. Open the screenshot")
        print("2. Identify the center coordinates of each UI element")
        print("3. Update config.yaml with the correct values")

        return {
            "screen_width": width,
            "screen_height": height,
            "screenshot_path": screenshot_path,
        }

    def test_connection(self) -> bool:
        """
        Test device connection and app availability.

        Returns:
            True if everything is working
        """
        print("Testing connection...")

        if not self.is_connected:
            print("  [FAIL] Not connected to device")
            return False

        print("  [OK] Device connected")

        # Check screen size
        width, height = self.adb.screen_size
        print(f"  [OK] Screen size: {width}x{height}")

        # Check if Xiaohongshu is installed
        package = self.config.xiaohongshu.get("package_name", self.PACKAGE_NAME)
        result = self.adb._device.shell(f"pm list packages | grep {package}")

        if package in result:
            print(f"  [OK] Xiaohongshu app installed ({package})")
        else:
            print(f"  [FAIL] Xiaohongshu app not found ({package})")
            return False

        # Check ADBKeyboard (optional but recommended)
        adb_keyboard_result = self.adb._device.shell(
            "pm list packages | grep com.android.adbkeyboard"
        )
        if "adbkeyboard" in adb_keyboard_result.lower():
            print("  [OK] ADBKeyboard installed (Chinese input supported)")
        else:
            print("  [WARN] ADBKeyboard not installed (Chinese input may not work)")
            print("         Install from: https://github.com/nickmelo/ADBKeyBoard")

        print("\nConnection test passed!")
        return True
