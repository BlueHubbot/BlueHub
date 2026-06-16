# Bot

Telegram bot for the BlueHub platform, built with python-telegram-bot.

## Structure

- **handlers/** - Conversation handlers for user interactions
  - `start.py` - Bot onboarding and welcome
  - `account.py` - User account management
  - `admin.py` - Admin panel via bot
  - `language_callback.py` - Language selection handling
- **keyboards/** - Inline and reply keyboards
  - `main_menu.py` - Main navigation keyboard
  - `language.py` - Language selection keyboard
- **middleware/** - Bot middleware
  - `auth.py` - User authentication and session
  - `i18n.py` - Internationalization for messages
- `main.py` - Bot entry point and configuration

## Features

- Multi-language support (Persian, English)
- User account linking with Telegram ID
- Service status checks and management
- Balance inquiries and payment links