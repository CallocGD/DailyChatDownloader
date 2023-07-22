
# https://ipinfo.io/192.42.116.209/geo

class MinusOne(Exception):
    """Robtop's server's didn't like your request or the level data wasn't found..."""

class RateLimit(Exception):
    """Your Client was rate-limited"""
    def __init__(self,timeout:int,msg:str,*args) -> None:
        self.timeout = timeout
        super().__init__(msg,*args)

class ServerMisbehaved(Exception):
    """Client failed to download comments Section of Geometry Dash Level because of this reason..."""
    def __init__(self,msg:str, *args: object) -> None:
        self.msg = msg 
        super().__init__(*args)