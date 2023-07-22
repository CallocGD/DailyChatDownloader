import dearpygui.dearpygui as dpg
from dataclasses import dataclass, field, asdict
from discordrp import * 
from json import load, dump

from typing import Union

__version__ = "0.0.8"

# F5Hcea36ze/DailyChatDownloader_exe
from wakepy import keep
from typing import Callable, TypeVar
from out import DiscordPresense

T = TypeVar("T")


@dataclass
class Config:
    """BasePlate for making settings..."""

    def set_item_event(self,name:str):
       """enforces dearpygui to pass configurations off to use elsewhere...
       this can also act as lazy bypass method..."""
       return lambda s, data : self.__setattr__(name, data)
    
    @classmethod
    def from_dict(cls,data:dict):
        return cls(**data)

    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def set_defaults(cls:type[T]) -> T:
        raise NotImplementedError

    # This is my new solution for all the new settings that we add here...
    @classmethod
    def from_get_key(self,data:dict[str,dict],key:str):
        return self.from_dict(data[key]) if data.get(key) else self.set_defaults()



@dataclass
class OutputConfig(Config):
    use_default_filename:bool = field(default_factory=bool)
    filetype:str = field(default_factory=str)


@dataclass
class DiscordConfig(Config):
    """Enables Discord Rich Presense in simple terms people will be able to see 
    that your harvesting level Comments..."""
    presense:DiscordPresense = field(default=None, compare=False, init=False)
    on:bool = field(default_factory=bool)

    def __post_init__(self):
        if self.on:
            try:
                self.presense = DiscordPresense()
                self.presense.update()
            except:
                self.on = False
            
    def update_config(self):
        if not self.on:
            self.on = True
            self.presense = DiscordPresense()
            self.presense.update()
        else:
            self.close()
            self.on = False
    
    def update(self,text:str):
        if self.on:
            self.presense.set_text(text)
            self.presense.update()
    
    def close(self):
        if self.on:
            self.presense.close()
            self.presense = None

    @classmethod
    def set_defaults(cls):
        return cls(on=False)

    @classmethod
    def from_get_key(cls,data:dict[str,dict[str,bool]],key:str):
        return cls(data[key]["on"]) if data.get(key) else cls.set_defaults()


@dataclass
class SearchConfig(Config):
    query:str = field(default_factory=str)


@dataclass
class LevelConfig(Config):
    id:int = field(default_factory=int)

    def set_id(self, id:int):
        """Used to set the levelID and the tag value associated with it..."""
        return lambda s, data: self.set_event_id(id)

    def set_event_id(self, data):
        dpg.set_value("level_id", data)
        self.__setattr__("id", data)
        dpg.set_value("level_result", f"Current LevelID: {self.id}")


@dataclass 
class DelayConfig(Config):
    min:float = field(default_factory=float)
    max:float = field(default_factory=float)
    cpr:int = field(default_factory=int)



    
    
    

@dataclass
class DecoyConfig(Config):
    """Used to help configure decoys"""
    # These are like nmap decoys and are made to simulate and shift blame to other causes...
    gdbrowser:bool = field(default_factory=bool)
    use_decoy:bool = field(default_factory=bool)

    # This is very simillar to an nmap deocy but it replaces a header 
    # instead of spoofing an Arp scan

    # TODO Add property to generate a random decoy based off of dcd version 4.0.2 if there's no decoy to go off of...
    ip_decoy:str = field(default_factory=str)





@dataclass
class BandwithConfig(Config):
    """Coming Soon in 0.0.5..."""
    bandwith:int = field(default_factory=int)
    use_gzip:bool = field(default_factory=bool)
    




@dataclass
class ProxyConfig(Config):
    use_proxy:bool = field(default_factory=bool)
    host:str = field(default_factory=str)
    port:int = field(default_factory=int)
    version:str = field(default_factory=str)
    username:str = field(default_factory=str)
    password:str = field(default_factory=str)

    @property
    def url(self):
        """used to setup proxy url for httpx to pass off"""
        
        name_and_pass = f"{self.username}:{self.password}@" if (self.username or self.password) and self.version == "socks5" else ""
        return f'{self.version}://{name_and_pass}{self.host}:{self.port}'

@dataclass
class BandwithConfig(Config):
    """This will allow users to try and control the internet speeds of dcd's downloading proceedures..."""
    bandwith:int = field(default_factory=int)
    gzip:bool = field(default_factory=bool)

    @classmethod
    def set_defaults(cls):
        return cls(8192, True)
    
@dataclass
class SleepSettings(Config):
    r"""Prevents the processes from killing
    themselves during level comment downloads.
    However it can drain your battery 
    if your not careful with this"""
    
    afk:bool = field(default_factory=bool)
    
    def invoke(self,func:Callable[..., T],*args,**kwargs):
        if self.afk:
            with keep.presenting():
                return func(*args,**kwargs)
        else:
            return func(*args,**kwargs)
    
    @classmethod
    def set_defaults(cls):
        return cls(False)



class Version:
    """Made for handling version details..."""
    rewrite:int
    major:int
    minor:int

    def __init__(self,a,b,c) -> None:
        self.rewrite = a
        self.major = b
        self.minor = c

    @classmethod
    def parse(cls,data:str):
        r, m1, m2 = list(map(int,data.split(".", 2)))
        return cls(r,m1,m2)
    
    @property
    def list(self):
        return [self.rewrite, self.major, self.minor]

    # Version Comparisons...

    def __lt__(self, ver:Union["Version",str,tuple[int,int,int]]) -> bool:
        if isinstance(ver,str):
            ver = Version.parse(ver)
        elif isinstance(ver,tuple):
            return all(a < b for a , b in zip(self.list, ver))
        return all(a < b for a , b in zip(self.list, ver.tuple))

    def __gt__(self,ver:Union["Version",str,tuple[int,int,int]]) -> bool:
        if isinstance(ver,str):
            ver = Version.parse(ver)
        elif isinstance(ver,tuple):
            return all(a < b for a , b in zip(self.list, ver))
        return all(a < b for a , b in zip(self.list, ver.tuple))

    def __eq__(self, ver:Union["Version",str, tuple[int,int,int]]) -> bool:
        if isinstance(ver,str):
            ver = Version.parse(ver)
        elif isinstance(ver,tuple):
            return all(a < b for a , b in zip(self.list, ver))
        return all(a == b for a , b in zip(self.list, ver.tuple))

    @property
    def str(self):
        return f"{self.rewrite}.{self.major}.{self.minor}"

    def __hash__(self) -> int:
        return hash(self.str)

def load_settings():
    data:dict[str,Union[dict,str]] = load(open("dcd_settings.json","rb"))

    # TODO This variable will be used in later updates for debugging problems 
    # and for updating the tools...
    version = Version.parse(data.get("version", __version__))

    output = OutputConfig.from_dict(data["output"])
    delays = DelayConfig.from_dict(data["delays"])
    decoy = DecoyConfig.from_dict(data["decoys"])
    proxy = ProxyConfig.from_dict(data["proxy"])
    
    
    # Implement / roll-out new bandwith features this is likely an update from 0.0.4 to 0.0.5...
    bandwith = BandwithConfig.from_get_key(data ,"bandwith")
    afk = SleepSettings.from_get_key(data, "sleep")
    discord_rp = DiscordConfig.from_get_key(data,"drp")

    return output, delays , proxy, decoy, bandwith, afk, discord_rp


def dump_settings(
        output:OutputConfig, 
        delays:DelayConfig,
        decoys:DecoyConfig,
        proxy:ProxyConfig, 
        bandwith:BandwithConfig,
        sleep:SleepSettings,
        drp:DiscordConfig,
    ):
    data = {}


    # For now on since 0.0.4, Always add the version as well so that updating is easier to adpt to so when 
    # new settings have been added they won't jack up with the current ones 
    # that are put into place...
    data["version"] = __version__
    
    # Always in alphabetical order...
    data["decoys"] = decoys.to_dict()
    data["delays"] = delays.to_dict()
    data["output"] = output.to_dict()
    data["proxy"] = proxy.to_dict()
    data["bandwith"] = bandwith.to_dict()
    data["sleep"] = sleep.to_dict()
    data["drp"] = drp.to_dict()
    with open("dcd_settings.json","w") as wb:
        # At least try to make it look semi clean/optimal...
        dump(data, wb, indent=4)
    


