import os
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
import time

# Enable logging
logging.basicConfig(level=logging.INFO)

# Set up API credentials
API_ID = 22141398  # Replace with your API_ID
API_HASH = "0c8f8bd171e05e42d6f6e5a6f4305389"  # Replace with your API_HASH
BOT_TOKEN = "7779271859:AAGJSSwbzyhP5tU-EP45w4fbKP6C_KKhWHA"  # Replace with your BOT_TOKEN

# Initialize bot
bot = Client("rename_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Dictionary to store temporary user data
user_data = {}

# Progress bar function
async def progress_bar(current, total, message, action="Processing"):
    percent = (current / total) * 100
    progress = f"{action}: {percent:.2f}% ({current / 1024 / 1024:.2f} MB / {total / 1024 / 1024:.2f} MB)"
    
    try:
        await message.edit_text(progress)
    except:
        pass  # Ignore edit errors to avoid rate limits

# Handle video or file upload
@bot.on_message((filters.video | filters.document) & filters.private)
async def video_handler(client, message: Message):
    user_id = message.from_user.id
    file = message.video or message.document  # Supports both videos & files

    if not file:
        await message.reply_text("❌ Unsupported file format. Please send a video or document.")
        return

    # Save file details
    user_data[user_id] = {
        "file_id": file.file_id,
        "file_name": file.file_name
    }

    await message.reply_text(
        f"✅ Received your file: `{file.file_name}`\n\n"
        "📌 Now send me the **new name** for this file (including extension, e.g., `new_movie.mkv`)."
    )

# Handle new filename
@bot.on_message(filters.text & filters.private)
async def rename_handler(client, message: Message):
    user_id = message.from_user.id
    new_name = message.text.strip()

    if user_id not in user_data or "file_id" not in user_data[user_id]:
        await message.reply_text("⚠ Please send me a file first.")
        return

    user_data[user_id]["new_name"] = new_name
    await message.reply_text(
        "📌 Now send me a **new thumbnail image** (or type 'skip' to keep the original thumbnail)."
    )

# Handle thumbnail image
@bot.on_message(filters.photo & filters.private)
async def thumbnail_handler(client, message: Message):
    user_id = message.from_user.id
    photo = message.photo

    if user_id not in user_data or "file_id" not in user_data[user_id]:
        await message.reply_text("⚠ Please send me a file first.")
        return

    # Save thumbnail file ID
    user_data[user_id]["thumb_id"] = photo.file_id

    await process_video(client, message, user_id)

# Handle "skip" message for thumbnail
@bot.on_message(filters.text & filters.private & filters.regex(r"(?i)skip"))
async def skip_thumbnail(client, message: Message):
    user_id = message.from_user.id

    if user_id not in user_data or "file_id" not in user_data[user_id]:
        await message.reply_text("⚠ Please send me a file first.")
        return

    user_data[user_id]["thumb_id"] = None  # No new thumbnail
    await process_video(client, message, user_id)

# Process and send the renamed video
async def process_video(client, message, user_id):
    file_id = user_data[user_id]["file_id"]
    new_name = user_data[user_id]["new_name"]
    thumb_id = user_data[user_id].get("thumb_id")

    # Send processing message
    processing_msg = await message.reply_text("🔄 **Downloading your file, please wait...**")

    # Download the video with progress bar
    file_path = await client.download_media(
        file_id,
        progress=progress_bar,
        progress_args=(processing_msg, "Downloading")
    )

    new_path = os.path.join(os.path.dirname(file_path), new_name)
    os.rename(file_path, new_path)  # Rename file

    # Download thumbnail if provided
    thumb_path = None
    if thumb_id:
        thumb_path = await client.download_media(thumb_id)

    # Update user that upload is starting
    await processing_msg.edit_text("✅ **File processed! Uploading now...**")

    # Send the renamed file with the new thumbnail and show progress
    await client.send_document(
        chat_id=user_id,
        document=new_path,
        caption=f"🎬 Here is your renamed file: `{new_name}`",
        thumb=thumb_path,
        progress=progress_bar,
        progress_args=(processing_msg, "Uploading")
    )

    # Clean up
    os.remove(new_path)
    if thumb_path:
        os.remove(thumb_path)

    del user_data[user_id]  # Clear user data

    # Update message to show completion
    await processing_msg.edit_text("✅ **File uploaded successfully!**")

# Start the bot
bot.run()
