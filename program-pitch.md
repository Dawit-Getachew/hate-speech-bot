# Hate Speech Monitor Bot

## Overview
The Hate Speech Monitor Bot is a Telegram and WhatsApp bot designed to detect and moderate hate speech in group chats. It uses Natural Language Processing (NLP) techniques to analyze messages and take appropriate actions, such as deleting offensive content, notifying admins, and applying penalties to violators.

---

## Tools and Libraries
1. **Python**: Core programming language.
2. **python-telegram-bot**: For Telegram bot integration.
3. **Flask**: For WhatsApp webhook and REST API.
4. **Twilio API**: For WhatsApp messaging.
5. **SQLite**: Lightweight database for storing user violations, admin data, and message statistics.
6. **Transformers (Hugging Face)**: For NLP model integration.
7. **Torch**: Backend for running the NLP model.
8. **dotenv**: For managing environment variables securely.

---

## Model and NLP
1. **Model**: `unitary/toxic-bert` (Hugging Face Transformers)
   - A pre-trained BERT-based model fine-tuned for detecting toxic and hate speech content.
2. **NLP Techniques**:
   - **Text Classification**: The model classifies messages into categories like "toxic" or "hate" with confidence scores.
   - **Threshold-Based Detection**: Messages are flagged as hate speech if the model's confidence exceeds a configurable threshold.

---

## Key Features
1. **Telegram Bot**:
   - Automatically deletes hate speech messages.
   - Notifies group admins about violations.
   - Progressive penalties: warnings, restrictions, and bans.
   - Admin management commands: `/addadmin`, `/removeadmin`, `/listadmins`.
2. **WhatsApp Bot**:
   - Detects hate speech via Twilio webhook.
   - Sends alerts to monitoring numbers.
3. **Database**:
   - Tracks user violations and group statistics.

---

This project leverages **NLP** and **pre-trained transformer models** to provide real-time hate speech detection and moderation in group chats.
