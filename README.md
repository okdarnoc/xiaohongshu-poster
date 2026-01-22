# Xiaohongshu Poster

An Android bot to automate posting on Xiaohongshu (小红书 / Little Red Book) using ADB.

## Features

- **Automated posting**: Create image and video posts with title, description, and hashtags
- **Chinese text support**: Input Chinese characters via ADBKeyboard
- **Configurable**: Customize timing, coordinates, and default settings
- **CLI interface**: Easy-to-use command-line tools
- **USB & WiFi**: Connect via USB or WiFi ADB

## Prerequisites

### 1. Android SDK Platform Tools

Install ADB (Android Debug Bridge):

**macOS:**
```bash
brew install android-platform-tools
```

**Ubuntu/Debian:**
```bash
sudo apt install android-tools-adb
```

**Windows:**
Download from [Android SDK Platform Tools](https://developer.android.com/studio/releases/platform-tools)

### 2. Enable USB Debugging on Your Phone

1. Go to **Settings** > **About phone**
2. Tap **Build number** 7 times to enable Developer options
3. Go back to **Settings** > **Developer options**
4. Enable **USB debugging**
5. (Optional) Enable **Wireless debugging** for WiFi connection

### 3. Install ADBKeyboard (Recommended for Chinese Input)

For proper Chinese text input, install ADBKeyboard on your Android device:

1. Download APK from [ADBKeyBoard releases](https://github.com/nickmelo/ADBKeyBoard/releases)
2. Install: `adb install ADBKeyboard.apk`
3. Enable in Settings > Language & Input > Current Keyboard > ADBKeyboard

### 4. Xiaohongshu App

Ensure Xiaohongshu (小红书) is installed and you're logged in on your phone.

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/xiaohongshu-poster.git
cd xiaohongshu-poster

# Install the package
pip install -e .

# Or install dependencies only
pip install -r requirements.txt
```

## Quick Start

### 1. Test Connection

Connect your phone via USB and run:

```bash
xhs-bot test
```

This will verify:
- Device connection
- Screen resolution
- Xiaohongshu app installation
- ADBKeyboard availability

### 2. Initialize Configuration

```bash
xhs-bot init-config
```

This creates a `config.yaml` file with default settings.

### 3. Calibrate Coordinates

```bash
xhs-bot calibrate
```

This helps you find the correct tap coordinates for your device. Open the generated screenshot and identify UI element positions.

### 4. Create a Post

**Image post:**
```bash
xhs-bot post-image \
  --title "My awesome post" \
  --content "Check out this amazing photo!" \
  --image photo1.jpg \
  --image photo2.jpg \
  --hashtag travel \
  --hashtag photography
```

**Video post:**
```bash
xhs-bot post-video \
  --title "My video" \
  --content "Watch this!" \
  --video video.mp4 \
  --hashtag vlog
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `xhs-bot test` | Test device connection |
| `xhs-bot init-config` | Create sample config file |
| `xhs-bot calibrate` | Help calibrate screen coordinates |
| `xhs-bot screenshot` | Take a screenshot |
| `xhs-bot launch` | Launch Xiaohongshu app |
| `xhs-bot close` | Close Xiaohongshu app |
| `xhs-bot post-image` | Create an image post |
| `xhs-bot post-video` | Create a video post |

Use `--help` with any command for more options.

## Configuration

### config.yaml

```yaml
# ADB Connection
adb:
  connection_type: "usb"  # or "wifi"
  device_ip: "192.168.1.100"  # for WiFi
  device_port: 5555

# Timing (in seconds)
timing:
  app_launch_wait: 3
  action_wait: 1.5
  upload_wait: 10
  post_complete_wait: 5

# Screen coordinates (calibrate for your device)
coordinates:
  screen_width: 1080
  screen_height: 2400
  post_button:
    x: 540
    y: 2280
  # ... see config.example.yaml for all options

# Default hashtags for all posts
post:
  default_hashtags:
    - xiaohongshu
```

### Environment Variables

You can override config values with environment variables:

- `XHS_ADB_HOST` - ADB server host
- `XHS_ADB_PORT` - ADB server port
- `XHS_DEVICE_IP` - Device IP for WiFi
- `XHS_DEVICE_PORT` - Device port for WiFi
- `XHS_CONNECTION_TYPE` - "usb" or "wifi"

## Python API

```python
from xiaohongshu_poster import XiaohongshuBot, Config

# Initialize
config = Config("config.yaml")
bot = XiaohongshuBot(config=config)

# Connect
bot.connect()

# Test connection
bot.test_connection()

# Create image post
bot.create_image_post(
    title="Amazing sunset",
    content="Beautiful view from the beach",
    image_paths=["sunset1.jpg", "sunset2.jpg"],
    hashtags=["sunset", "beach", "travel"]
)

# Create video post
bot.create_video_post(
    title="Beach vibes",
    content="Relaxing day at the beach",
    video_path="beach.mp4",
    hashtags=["vlog", "beach"]
)

# Disconnect
bot.disconnect()
```

## Calibration Guide

Different phones have different screen resolutions and Xiaohongshu UI layouts. To calibrate:

1. Run `xhs-bot calibrate` to take a screenshot
2. Open Xiaohongshu on your phone
3. Use an image editor to find coordinates:
   - **post_button**: The "+" button at bottom center
   - **image_option**: "Image" option when creating post
   - **video_option**: "Video" option when creating post
   - **next_button**: "Next" button after selecting media
   - **title_input**: Where you type the title
   - **content_input**: Where you type the description
   - **publish_button**: "Publish" button

4. Update `config.yaml` with your coordinates

## Troubleshooting

### "No devices found"

1. Ensure USB debugging is enabled
2. Check USB cable connection
3. Run `adb devices` to verify device is listed
4. Try `adb kill-server && adb start-server`

### Chinese text not working

1. Install ADBKeyboard app
2. Enable it as input method in phone settings
3. Verify with: `adb shell pm list packages | grep adbkeyboard`

### WiFi connection not working

1. Ensure phone and computer are on same network
2. Enable Wireless debugging in Developer options
3. Run `adb tcpip 5555` while connected via USB
4. Update `config.yaml` with correct IP

### Posts not completing

1. Run `xhs-bot calibrate` and verify coordinates
2. Increase timing values in config
3. Take screenshots during the process to debug

## WiFi ADB Setup

To use WiFi connection:

1. Connect phone via USB
2. Run: `adb tcpip 5555`
3. Disconnect USB
4. Find your phone's IP in WiFi settings
5. Update config:
   ```yaml
   adb:
     connection_type: "wifi"
     device_ip: "192.168.1.100"
     device_port: 5555
   ```

## Limitations

- Requires phone screen to be on during operation
- UI coordinates may change with Xiaohongshu app updates
- Chinese input requires ADBKeyboard app
- Some actions may need manual intervention

## License

MIT License

## Disclaimer

This tool is for personal automation purposes only. Use responsibly and in accordance with Xiaohongshu's terms of service.
