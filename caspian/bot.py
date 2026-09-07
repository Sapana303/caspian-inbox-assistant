"""Caspian communications layer. Run with: python caspian/bot.py"""

import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from caspian import Caspian
load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env")

from agent import ask

cx = Caspian(
    api_key=os.environ["CASPIAN_API_KEY"],
    base_url=os.environ.get("CASPIAN_BASE_URL", "https://api.trycaspianai.com"),
)

# Add the hosted email address after choosing its username during setup.
if os.environ.get("CASPIAN_EMAIL_USERNAME"):
    cx.channels.add("email", username=os.environ["CASPIAN_EMAIL_USERNAME"])

_ALLOWED = {
    sender.strip()
    for sender in os.environ.get("CASPIAN_ALLOWED_SENDERS", "").split(",")
    if sender.strip()
}


@cx.on_message({"overlap": "queue", "ack": "On it, I am checking the inbox..."})
def handle(thread, msg, ctx):
    if _ALLOWED and msg.sender not in _ALLOWED:
        return
    thread.post(ask(msg.text))


if __name__ == "__main__":
    print("Caspian is polling for inbound messages.")
    cx.run()
