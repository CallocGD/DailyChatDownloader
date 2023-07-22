from dataclasses import dataclass, field
try:
    # Optional import or inclusion but it is included by default in the executable file...
    from pybase64 import urlsafe_b64decode
except ModuleNotFoundError:
    from base64 import urlsafe_b64decode

@dataclass
class Creator:
    """A dataclass of a gd user in the simplest possible format..."""
    PlayerID:int = field(default_factory=int)
    name:str = field(default_factory=str)
    AccountID:int = field(default_factory=int)

    @classmethod
    def from_bytes(cls,data:bytes):
        try:
            playerid , name , accountid = data.split(b":",2)
            return cls(
                PlayerID = int(playerid),
                name = name.decode("utf-8","surrogateescape"),
                AccountID = int(accountid))
        except:
            return cls(0,"Unknown",0)

@dataclass
class Level:
    id:int = field(default_factory=int) 
    name:str = field(default_factory=str)
    description:bytes = field(default_factory=bytes)
    creator:Creator = field(default_factory=Creator)

    @classmethod 
    def from_bytes(cls,data:bytes):
        hashes = data.split(b"#")
        raw:dict[bytes,bytes] = dict(zip(*(iter(hashes[0].split(b":")),) * 2))

        return cls(
            id=int(raw[b"1"]),
            name=raw[b"2"].decode(errors="surrogateescape"),
            description=urlsafe_b64decode(raw[b"3"]),
            creator=Creator.from_bytes(hashes[-1])
        )
    
    @classmethod
    def from_search_result(cls, level:dict[bytes,bytes],udict:dict[bytes,list[bytes]]):
        playerid = level[b"6"]
        
        try:
            user = udict[playerid]
        
            return cls(
                id=int(level[b"1"]),
                name=level[b"2"].decode(errors="surrogateescape"),
                description=urlsafe_b64decode(level[b"3"]),
                creator=Creator(int(user[0]),user[1].decode(errors="surrogateescape"),int(user[2]))
            )
        except:
            return cls(
                id=int(level[b"1"]),
                name=level[b"2"].decode(errors="surrogateescape"),
                description=urlsafe_b64decode(level[b"3"]),
                creator=Creator(0,"Unknown User",0)

            )

# TODO Add Comment parser so that the outputs can all be parsed at the end of eatch download if and whenever chosen...






def parse_data(data:bytes):
    levels , users , songs,_ = (data.split(b"#",3))
    ldict = [dict(zip(*(iter(l.split(b":")),) * 2)) for l in levels.split(b"|")]
    udict = {a[0]:a for a in [l.split(b":") for l in users.split(b"|")]}
    
    return [Level.from_search_result(l,udict) for l in ldict]


if __name__ == "__main__":
    parse_data(open("test.txt","rb").read())
