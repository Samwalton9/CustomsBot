# CustomsBot

This is a bot intended for use on /r/PUBATTLEGROUNDS primarily aimed at reducing the number of repetitive tasks hosters are required to carry out.

## Local hosting

You can use `pip install -r requirements.txt` to install necessary Python packages. This bot uses async discord.py and will switch to rewrite when it is stable.

### Server

To function in the same way as on /r/PUBATTLEGROUNDS, your server will need four channels: a moderator channel, a subscriber channel, a custom games channel where the information is posted and a custom hosters channel where commands are sent. Your server will also need a Custom games role.

You will need to create custom games voice channel(s) with names starting with the "\U0001F6E0" emoji. You will also need to add a number of emojis, as described in `config.json.in`.

### Config

Rename `config.json.in` to `config.json` and fill out the required fields before running. Every field (including IDs) should be a string.

### Permissions

You should give the following permissions to your bot for it to run properly:

* Manage Roles
* Manage Channels
* Read Text Channels & See Voice Channels
* Send Messages
* Manage Messages
* Embed Links
* Read Message History
* Mention Everyone
* Add Reactions
