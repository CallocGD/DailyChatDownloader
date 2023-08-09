import dearpygui.dearpygui as dpg
from dataclasses import dataclass, field, asdict
from dataclasses_json import DataClassJsonMixin
from discordrp import * 

from typing import Union

__version__ = "0.0.9 Beta"

from wakepy import keep
from typing import Callable, TypeVar
from out import DiscordPresense

T = TypeVar("T")






@dataclass
class Config(DataClassJsonMixin):
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
    use_default_filename:bool = True
    filetype:str = "text"


@dataclass
class DiscordConfig(Config):
    """Enables Discord Rich Presense in simple terms people will be able to see 
    that your harvesting level Comments..."""
    presense:DiscordPresense = field(default=None, compare=False, init=False)
    on:bool = False

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
    min:float = 2
    max:float = 5
    cpr:int = 100



@dataclass
class DecoyConfig(Config):
    """Used to help configure decoys"""
    # These are like nmap decoys and are made to simulate and shift blame to other causes...
    gdbrowser:bool = False
    use_decoy:bool = False

    # This is very simillar to an nmap deocy but it replaces a header 
    # instead of spoofing an Arp scan

    # TODO Add property to generate a random decoy based off of dcd version 4.0.2 if there's no decoy to go off of...
    ip_decoy:str = field(default_factory=str)










@dataclass
class ProxyConfig(Config):
    use_proxy:bool = False
    host:str = ""
    port:int = 0
    version:str = ""
    username:str = ""
    password:str = ""

    @property
    def url(self):
        """used to setup proxy url for httpx to pass off"""
        name_and_pass = f"{self.username}:{self.password}@" if (self.username or self.password) and self.version == "socks5" else ""
        return f'{self.version}://{name_and_pass}{self.host}:{self.port}'

@dataclass
class BandwithConfig(Config):
    """This will allow users to try and control the internet speeds of dcd's downloading proceedures..."""
    bandwith:int = 8192
    gzip:bool = False


@dataclass
class SleepSettings(Config):
    r"""Prevents the processes from killing
    themselves during level comment downloads.
    However it can drain your battery 
    if your not careful with this"""
    
    afk:bool = False
    
    def invoke(self,func:Callable[..., T],*args,**kwargs):
        if self.afk:
            with keep.presenting():
                return func(*args,**kwargs)
        else:
            return func(*args,**kwargs)
    

# "Cleaned up Settings now it should load all without the bullshit involved!" - Calloc 

@dataclass
class AllSettings(DataClassJsonMixin):
    output: OutputConfig = OutputConfig()
    delays: DelayConfig = DelayConfig()
    decoy: DecoyConfig = DecoyConfig()
    proxy: ProxyConfig = ProxyConfig()
    bandwith: BandwithConfig = BandwithConfig()
    afk : SleepSettings = SleepSettings()
    discord_rp: DiscordConfig = DiscordConfig()

    @classmethod
    def load_settings(cls):
        try:
            return cls.from_json(open("dcd_settings.json","r").read())
        except:
            return cls()
        
    def dump_settings(self):
        open("dcd_settings.json","w").write(self.to_json(indent=4))

    def depack(self):
        return self.output, self.delays, self.proxy, self.decoy , self.bandwith, self.afk, self.discord_rp 

