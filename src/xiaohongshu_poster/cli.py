"""
Command-line interface for Xiaohongshu Poster bot.
"""

import sys
from pathlib import Path
from typing import List, Optional

import click

from . import __version__
from .config import Config
from .xiaohongshu_bot import XiaohongshuBot, PostType


@click.group()
@click.version_option(version=__version__)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to config file",
)
@click.pass_context
def main(ctx, config: Optional[str]):
    """
    Xiaohongshu Poster - Android bot for automating posts on Xiaohongshu.

    Use 'xhs-bot COMMAND --help' for more information on each command.
    """
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config


@main.command()
@click.pass_context
def test(ctx):
    """Test connection to Android device."""
    config_path = ctx.obj.get("config_path")
    config = Config(config_path) if config_path else Config()

    bot = XiaohongshuBot(config=config)

    click.echo("Connecting to device...")
    if not bot.connect():
        click.echo("Failed to connect to device", err=True)
        sys.exit(1)

    if bot.test_connection():
        click.echo("\nAll tests passed! Ready to post.")
    else:
        click.echo("\nSome tests failed. Please check the issues above.", err=True)
        sys.exit(1)

    bot.disconnect()


@main.command()
@click.option("--title", "-t", required=True, help="Post title")
@click.option("--content", "-d", required=True, help="Post description/content")
@click.option(
    "--image",
    "-i",
    multiple=True,
    type=click.Path(exists=True),
    help="Image file(s) to post (can specify multiple)",
)
@click.option(
    "--hashtag",
    "-h",
    multiple=True,
    help="Hashtag(s) to add (without #, can specify multiple)",
)
@click.pass_context
def post_image(
    ctx,
    title: str,
    content: str,
    image: tuple,
    hashtag: tuple,
):
    """Create an image post on Xiaohongshu."""
    if not image:
        click.echo("Error: At least one image is required", err=True)
        sys.exit(1)

    config_path = ctx.obj.get("config_path")
    config = Config(config_path) if config_path else Config()

    bot = XiaohongshuBot(config=config)

    click.echo("Connecting to device...")
    if not bot.connect():
        click.echo("Failed to connect to device", err=True)
        sys.exit(1)

    click.echo(f"Creating image post: {title}")
    click.echo(f"  Images: {len(image)}")
    click.echo(f"  Hashtags: {list(hashtag)}")

    success = bot.create_image_post(
        title=title,
        content=content,
        image_paths=list(image),
        hashtags=list(hashtag) if hashtag else None,
    )

    bot.disconnect()

    if success:
        click.echo("\nPost created successfully!")
    else:
        click.echo("\nFailed to create post", err=True)
        sys.exit(1)


@main.command()
@click.option("--title", "-t", required=True, help="Post title")
@click.option("--content", "-d", required=True, help="Post description/content")
@click.option(
    "--video",
    "-v",
    required=True,
    type=click.Path(exists=True),
    help="Video file to post",
)
@click.option(
    "--hashtag",
    "-h",
    multiple=True,
    help="Hashtag(s) to add (without #, can specify multiple)",
)
@click.pass_context
def post_video(
    ctx,
    title: str,
    content: str,
    video: str,
    hashtag: tuple,
):
    """Create a video post on Xiaohongshu."""
    config_path = ctx.obj.get("config_path")
    config = Config(config_path) if config_path else Config()

    bot = XiaohongshuBot(config=config)

    click.echo("Connecting to device...")
    if not bot.connect():
        click.echo("Failed to connect to device", err=True)
        sys.exit(1)

    click.echo(f"Creating video post: {title}")
    click.echo(f"  Video: {video}")
    click.echo(f"  Hashtags: {list(hashtag)}")

    success = bot.create_video_post(
        title=title,
        content=content,
        video_path=video,
        hashtags=list(hashtag) if hashtag else None,
    )

    bot.disconnect()

    if success:
        click.echo("\nPost created successfully!")
    else:
        click.echo("\nFailed to create post", err=True)
        sys.exit(1)


@main.command()
@click.pass_context
def calibrate(ctx):
    """Calibrate screen coordinates for your device."""
    config_path = ctx.obj.get("config_path")
    config = Config(config_path) if config_path else Config()

    bot = XiaohongshuBot(config=config)

    click.echo("Connecting to device...")
    if not bot.connect():
        click.echo("Failed to connect to device", err=True)
        sys.exit(1)

    result = bot.calibrate_coordinates()

    click.echo("\n" + "=" * 50)
    click.echo("CALIBRATION GUIDE")
    click.echo("=" * 50)
    click.echo(f"\nDevice resolution: {result['screen_width']}x{result['screen_height']}")
    click.echo(f"Screenshot saved to: {result['screenshot_path']}")
    click.echo("\nTo calibrate your device:")
    click.echo("1. Open the screenshot in an image viewer")
    click.echo("2. Launch Xiaohongshu on your phone")
    click.echo("3. Identify the coordinates for each UI element:")
    click.echo("   - post_button: The '+' button to create new post")
    click.echo("   - image_option: The 'Image' option in post type selector")
    click.echo("   - video_option: The 'Video' option in post type selector")
    click.echo("   - next_button: The 'Next' button after selecting media")
    click.echo("   - title_input: The title input field")
    click.echo("   - content_input: The content/description input field")
    click.echo("   - publish_button: The 'Publish' button")
    click.echo("\n4. Update config.yaml with your coordinates")
    click.echo("\nExample config.yaml coordinates section:")
    click.echo("""
coordinates:
  screen_width: {width}
  screen_height: {height}
  post_button:
    x: 540
    y: 2280
  # ... etc
""".format(width=result['screen_width'], height=result['screen_height']))

    bot.disconnect()


@main.command()
@click.pass_context
def screenshot(ctx):
    """Take a screenshot of the connected device."""
    config_path = ctx.obj.get("config_path")
    config = Config(config_path) if config_path else Config()

    from .adb_controller import ADBController

    adb = ADBController(
        host=config.adb["adb_host"],
        port=config.adb["adb_port"],
    )

    click.echo("Connecting to device...")
    if not adb.connect():
        click.echo("Failed to connect to device", err=True)
        sys.exit(1)

    output_path = "screenshot.png"
    click.echo(f"Taking screenshot...")

    if adb.screenshot(output_path):
        click.echo(f"Screenshot saved to: {output_path}")
    else:
        click.echo("Failed to take screenshot", err=True)
        sys.exit(1)

    adb.disconnect()


@main.command()
@click.pass_context
def launch(ctx):
    """Launch Xiaohongshu app on device."""
    config_path = ctx.obj.get("config_path")
    config = Config(config_path) if config_path else Config()

    bot = XiaohongshuBot(config=config)

    click.echo("Connecting to device...")
    if not bot.connect():
        click.echo("Failed to connect to device", err=True)
        sys.exit(1)

    bot.launch_app()
    click.echo("Xiaohongshu launched")

    bot.disconnect()


@main.command()
@click.pass_context
def close(ctx):
    """Close Xiaohongshu app on device."""
    config_path = ctx.obj.get("config_path")
    config = Config(config_path) if config_path else Config()

    bot = XiaohongshuBot(config=config)

    click.echo("Connecting to device...")
    if not bot.connect():
        click.echo("Failed to connect to device", err=True)
        sys.exit(1)

    bot.close_app()
    click.echo("Xiaohongshu closed")

    bot.disconnect()


@main.command()
def init_config():
    """Create a sample config file in the current directory."""
    config_content = """# Xiaohongshu Poster Configuration

# ADB Connection Settings
adb:
  # Device connection method: "usb" or "wifi"
  connection_type: "usb"
  # For WiFi connection, specify device IP and port
  device_ip: "192.168.1.100"
  device_port: 5555
  # ADB server host (usually localhost)
  adb_host: "127.0.0.1"
  adb_port: 5037

# Xiaohongshu App Settings
xiaohongshu:
  # Package name of the Xiaohongshu app
  package_name: "com.xingin.xhs"
  # Main activity to launch
  main_activity: "com.xingin.xhs.index.v2.IndexActivityV2"

# Timing Settings (in seconds)
timing:
  # Wait time after launching app
  app_launch_wait: 3
  # Wait time after each UI interaction
  action_wait: 1.5
  # Wait time for media to upload
  upload_wait: 10
  # Wait time after posting
  post_complete_wait: 5

# Screen Coordinates (adjust based on your device resolution)
# Run 'xhs-bot calibrate' to help determine your coordinates
coordinates:
  # Resolution of your device
  screen_width: 1080
  screen_height: 2400

  # Post button (usually center bottom + icon)
  post_button:
    x: 540
    y: 2280

  # Select image/video option
  image_option:
    x: 270
    y: 1800
  video_option:
    x: 810
    y: 1800

  # Next button after selecting media
  next_button:
    x: 980
    y: 150

  # Title input area
  title_input:
    x: 540
    y: 400

  # Content/description input area
  content_input:
    x: 540
    y: 700

  # Publish button
  publish_button:
    x: 980
    y: 150

# Post Settings
post:
  # Default hashtags to add to all posts
  default_hashtags: []
  # Add location to posts
  add_location: false
"""

    output_path = Path("config.yaml")
    if output_path.exists():
        if not click.confirm("config.yaml already exists. Overwrite?"):
            click.echo("Aborted")
            return

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(config_content)

    click.echo(f"Config file created: {output_path}")
    click.echo("\nNext steps:")
    click.echo("1. Run 'xhs-bot test' to verify device connection")
    click.echo("2. Run 'xhs-bot calibrate' to find correct coordinates")
    click.echo("3. Edit config.yaml with your coordinates")
    click.echo("4. Run 'xhs-bot post-image' to create a post")


if __name__ == "__main__":
    main()
