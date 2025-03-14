# whatsapp_bot.py
from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import logging
from database import Database
from hate_speech_model import HateSpeechDetector
import config

app = Flask(__name__)

# Twilio configuration
TWILIO_ACCOUNT_SID = config.TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN = config.TWILIO_AUTH_TOKEN
TWILIO_WHATSAPP_NUMBER = config.TWILIO_WHATSAPP_NUMBER

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Initialize shared modules
detector = HateSpeechDetector()
db = Database()

# Define monitoring numbers (in E.164 format, e.g., "+1234567890")
monitoring_numbers = ["+1234567890"]  # Replace with your WhatsApp admin numbers


@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    sender = request.values.get("From", "")
    message_text = request.values.get("Body", "")

    app.logger.info(f"Received message from {sender}: {message_text}")

    resp = MessagingResponse()
    reply = ""

    if message_text and detector.detect(message_text):
        # For WhatsApp we record the violation (using sender’s number as the user ID)
        violation_count = db.add_violation(sender, sender)
        # Notify each monitoring number via WhatsApp message
        for admin in monitoring_numbers:
            client.messages.create(
                from_=f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",
                to=f"whatsapp:{admin}",
                body=f"⚠️ Alert: Sender {sender} sent hate speech:\n{message_text}",
            )
        reply += "Your message was flagged as hate speech and recorded. "
        if violation_count == 6:
            reply += "You are restricted from sending messages for 7 days."
        elif violation_count > 6:
            reply += "You have been banned from the group due to repeated violations."
        else:
            reply += f"Violation count: {violation_count}."
    else:
        reply += "Message received."

    resp.message(reply)
    return Response(str(resp), mimetype="application/xml")


@app.route("/stats", methods=["GET"])
def stats():
    # Simple endpoint to view some stats (can be extended)
    return {"message": "Stats endpoint not fully implemented."}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True, port=5000)
