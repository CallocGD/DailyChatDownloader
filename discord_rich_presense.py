import discordrp
import threading
import pybase64
import time


default = "In Menu..."

class DiscordPresense:
    def __init__(self) -> None:
        self.client_id = pybase64.b64decode(b"MTEzMDk3Njg5MTA3MTkwNTgxMg==").decode("utf-8")
        self.text = default
        self.presence = discordrp.Presence(self.client_id)

    def set_text(self,new_text:str):
        self.text = new_text

    def update(self):
        self.presence.set(
            {
                "state": "In Game",
                "details": self.text,
                "timestamps": {"start": int(time.time())},
            }
        )
    def close(self):
        self.presence.close()

