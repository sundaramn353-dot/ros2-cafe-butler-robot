#!/usr/bin/env python3
import os
import shutil

src_dir = "/home/sundar/french_cafe"
media_dir = os.path.join(src_dir, "media")
os.makedirs(media_dir, exist_ok=True)

# Copy banner
banner_src = "/home/sundar/.gemini/antigravity/brain/7767e940-f566-4a9a-9de4-c9f79ff5b5ae/cafe_robot_banner_1780995764265.png"
if os.path.exists(banner_src):
    shutil.copy(banner_src, os.path.join(media_dir, "cafe_robot_banner.png"))
    print("Copied banner image.")
else:
    print("Banner image not found in cache.")

# Copy screenshot
image_src = os.path.join(src_dir, "image.png")
if os.path.exists(image_src):
    shutil.copy(image_src, os.path.join(media_dir, "simulation_screenshot.png"))
    print("Copied screenshot image.")
else:
    print("image.png not found in French Café directory.")

# Copy videos
video1_src = os.path.join(src_dir, "demo video1.webm")
if os.path.exists(video1_src):
    shutil.copy(video1_src, os.path.join(media_dir, "demo_video1.webm"))
    print("Copied video 1.")
else:
    print("demo video1.webm not found in French Café directory.")

video2_src = os.path.join(src_dir, "demo video2.webm")
if os.path.exists(video2_src):
    shutil.copy(video2_src, os.path.join(media_dir, "demo_video2.webm"))
    print("Copied video 2.")
else:
    print("demo video2.webm not found in French Café directory.")

print("Asset copying complete!")
