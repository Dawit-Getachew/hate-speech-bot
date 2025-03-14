# telegram_bot.py
from telegram import Update, ChatPermissions
from telegram.ext import (
    Updater,
    MessageHandler,
    Filters,
    CommandHandler,
    CallbackContext,
)
from datetime import datetime, timedelta
import logging
import config
from database import Database
from hate_speech_model import HateSpeechDetector

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


db = Database()
detector = HateSpeechDetector()


def start(update: Update, context: CallbackContext):
    update.message.reply_text("Hello! I'm the Hate Speech Monitor Bot for Telegram.")


def stats(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    group_id = str(update.message.chat_id)

    # Get user violations
    user_violations = db.get_violation_count(user_id)

    # Get group stats
    total_msgs, hate_msgs = db.get_stats(group_id)

    stats_message = (
        f"📊 Group Statistics:\n"
        f"Total Messages: {total_msgs}\n"
        f"Hate Speech Messages: {hate_msgs}\n"
        f"Your Violations: {user_violations}"
    )
    update.message.reply_text(stats_message)


def add_admin(update: Update, context: CallbackContext):
    # Add debug message
    logger.info(f"add_admin called with args: {context.args}")
    update.message.reply_text("Processing admin request...")

    try:
        # Check if command sender is a group admin
        chat = update.effective_chat
        user = update.effective_user

        chat_member = context.bot.get_chat_member(chat.id, user.id)
        if chat_member.status not in ["administrator", "creator"]:
            update.message.reply_text(
                "❌ Only group administrators can add new admins."
            )
            return

        # Show usage if no arguments or incorrect format
        if not context.args:
            update.message.reply_text(
                "❌ Usage:\n"
                "1. By username: /addadmin @username\n"
                "2. By user ID: /addadmin 123456789 nickname\n"
                "3. By replying to a message: /addadmin"
            )
            return

        group_id = str(update.message.chat_id)

        # Check if command is used as a reply to someone's message
        if update.message.reply_to_message:
            target_user = update.message.reply_to_message.from_user
            admin_id = str(target_user.id)
            display_name = target_user.username or target_user.first_name
            logger.info(f"Adding admin from reply: {admin_id}, {display_name}")
        # Handle case where user is mentioned with @
        elif context.args[0].startswith("@"):
            username = context.args[0][1:]  # Remove @ symbol
            logger.info(f"Trying to add admin with username: {username}")

            # Try three different methods to find the user:
            # Method 1: Try direct lookup via username (might work for some bots/users)
            # Method 2: Check all admins in the group
            # Method 3: Check if user recently posted a message we can find

            try:
                # Just use the username directly - we'll store it in DB and
                # send notifications to this user if they're in the group
                user_found = False
                admin_id = username
                display_name = username

                # Method 1: Try to get direct chat info
                try:
                    # This might work in some cases but often fails
                    user_chat = context.bot.get_chat("@" + username)
                    if user_chat:
                        admin_id = str(user_chat.id)
                        display_name = username
                        user_found = True
                        logger.info(f"Found user via direct chat lookup: {admin_id}")
                except Exception as e:
                    logger.info(f"Direct chat lookup failed: {e}")

                # Method 2: Check among administrators
                if not user_found:
                    try:
                        admins = context.bot.get_chat_administrators(chat.id)
                        for admin in admins:
                            if (
                                admin.user.username
                                and admin.user.username.lower() == username.lower()
                            ):
                                admin_id = str(admin.user.id)
                                display_name = username
                                user_found = True
                                logger.info(f"Found user in admins list: {admin_id}")
                                break
                    except Exception as e:
                        logger.info(f"Admin search failed: {e}")

                # Method 3: For regular members, we'll add them anyway
                # The bot can't easily search all chat members, but we'll accept the username

                # Add anyway with a message explaining the situation
                if not user_found:
                    logger.info(f"Using username directly as ID: {username}")
                    update.message.reply_text(
                        f"Adding @{username} as an admin. "
                        "Note: Notifications will only work if this user is in the group."
                    )
            except Exception as e:
                logger.error(f"Failed to search for username: {e}")
                admin_id = username  # Fallback: use username as ID
                display_name = username
        else:
            # Handle direct user ID input
            admin_id = context.args[0]
            display_name = context.args[1] if len(context.args) > 1 else admin_id

            # Try to verify if this ID exists in the group
            try:
                member = context.bot.get_chat_member(group_id, admin_id)
                display_name = member.user.username or member.user.first_name
            except Exception:
                update.message.reply_text(
                    f"⚠️ Could not verify user ID {admin_id}, but adding anyway."
                )

        # Add to database regardless of verification
        if db.add_admin(admin_id, group_id, display_name):
            update.message.reply_text(
                f"✅ Admin {display_name} (ID: {admin_id}) added successfully."
            )
            logger.info(f"New admin added - Group: {group_id}, Admin: {admin_id}")
        else:
            update.message.reply_text("❌ Failed to add admin. Please try again.")

    except Exception as e:
        logger.error(f"Error adding admin: {e}")
        update.message.reply_text("❌ Failed to add admin. Please try again.")


def remove_admin(update: Update, context: CallbackContext):
    try:
        admin_id = context.args[0]
        group_id = str(update.message.chat_id)
        db.remove_admin(admin_id, group_id)
        update.message.reply_text(f"Admin {admin_id} removed from this group.")
    except Exception as e:
        update.message.reply_text("Usage: /removeadmin <admin_id>")
        logger.error(e)


def list_admins(update: Update, context: CallbackContext):
    try:
        group_id = str(update.message.chat_id)
        admins = db.get_group_admins(group_id)

        if not admins:
            update.message.reply_text("📋 No registered admins found for this group.")
            return

        admin_list = "📋 Registered Group Admins:\n"
        for admin_id in admins:
            cursor = db.conn.cursor()
            cursor.execute(
                "SELECT username FROM admins WHERE admin_id = ? AND group_id = ?",
                (admin_id, group_id),
            )
            result = cursor.fetchone()
            username = result[0] if result and result[0] else "Unknown"

            # Get Telegram user info if possible
            try:
                user = context.bot.get_chat_member(group_id, admin_id).user
                actual_username = (
                    f"@{user.username}" if user.username else user.first_name
                )
                admin_list += f"• {actual_username} ({username}) - ID: {admin_id}\n"
            except:
                admin_list += f"• {username} - ID: {admin_id}\n"

        update.message.reply_text(admin_list)

    except Exception as e:
        logger.error(f"Error listing admins: {e}")
        update.message.reply_text("❌ Failed to fetch admin list.")


def handle_message(update: Update, context: CallbackContext):
    message = update.message
    text = message.text
    group_id = str(message.chat_id)
    user_id = str(message.from_user.id)
    username = message.from_user.username or message.from_user.first_name

    # Track total messages
    db.increment_message_stats(group_id)

    if text and detector.detect(text):
        # Increment hate speech counter
        db.increment_message_stats(group_id, is_hate_speech=True)
        # Record violation in the database
        violation_count = db.add_violation(user_id, username)
        # Attempt to delete the offending message (bot must be admin)
        try:
            context.bot.delete_message(chat_id=group_id, message_id=message.message_id)
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
        # Notify group admins (from the database)
        admins = db.get_group_admins(group_id)
        for admin in admins:
            context.bot.send_message(
                chat_id=admin,
                text=f"⚠️ Alert: User @{username} sent hate speech:\n{text}",
            )
        # Apply penalties based on violation count
        if violation_count == 25:
            until_date = datetime.now() + timedelta(days=7)
            context.bot.restrict_chat_member(
                chat_id=group_id,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until_date,
            )
            context.bot.send_message(
                chat_id=group_id, text=f"User @{username} is restricted for 7 days."
            )
        elif violation_count > 6:
            context.bot.kick_chat_member(chat_id=group_id, user_id=user_id)
            context.bot.send_message(
                chat_id=group_id,
                text=f"User @{username} has been banned due to repeated violations.",
            )


def error_handler(update: Update, context: CallbackContext):
    logger.error(f"Update {update} caused error {context.error}")
    if update.message:
        update.message.reply_text(
            "Sorry, an error occurred while processing your request."
        )


def main():
    updater = Updater(token=config.TELEGRAM_API_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Add all handlers - include both versions of commands (with and without underscores)
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("stats", stats))

    # Admin commands - both versions (with and without underscores)
    dp.add_handler(CommandHandler("addadmin", add_admin))
    dp.add_handler(CommandHandler("add_admin", add_admin))

    dp.add_handler(CommandHandler("removeadmin", remove_admin))
    dp.add_handler(CommandHandler("remove_admin", remove_admin))

    dp.add_handler(CommandHandler("listadmins", list_admins))
    dp.add_handler(CommandHandler("list_admins", list_admins))

    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    # Add error handler
    dp.add_error_handler(error_handler)

    # Start the bot
    updater.start_polling()
    logger.info("Telegram bot started.")
    updater.idle()


if __name__ == "__main__":
    main()
