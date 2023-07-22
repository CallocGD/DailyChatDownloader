import dearpygui.dearpygui as dpg
import datetime 

from contextlib import contextmanager
from typing import Callable, TypeVar, NamedTuple, Optional, Union
from dcdclient import DCDClient
from flags import ObfuscationLevel
from pathlib import Path
import time  , random  , json
from downloader import STRFormatter, ProgressFormatter

from utils import coded_partial


from config import (
    ProxyConfig, 
    DecoyConfig, 
    DelayConfig, 
    LevelConfig, 
    SearchConfig, 
    OutputConfig,
    # new in version 0.0.5
    BandwithConfig,
    SleepSettings,
    load_settings,
    dump_settings,
    DiscordConfig,
    # Version Moved to config so that it can be used to debug settings 
    # or whenever users need help with issue diagnosing...
    __version__
)

from external_parsing import (
    robtop_string_to_json,
    robtop_string_to_text,
    robtop_string_to_html
)

import pyperclip


import os
try:
    import sys
except ImportError:
    pass

if getattr(sys, 'frozen', False):
    image = os.path.join(sys._MEIPASS, Path("icos","dcd.ico"))
else:
    image = Path("icos","dcd.ico")



SOCKS5TOOLTIP = "These are intended for \nsocks5 only! Ignore\nuser and pass if\n your proxy doesn't\nneed a username and\n password!"

MONERO_WALLET = "84QtScDcuiwMkdbSzWsou7XGQbfwfnMztJa51z2XDAHLVeHDAj9pg7PY2HdfjB9hxQWQm8DBvKYw4QFuzPJ5vAM91iz2HvF"


class Backoff:
    def __init__(self,times:tuple[float]) -> None:
        self.min = min(times)
        self.max = max(times)
        self.current:float = 0

    def sleep(self, formatter:STRFormatter):
        """Sleeps for a random amount of seconds to prevent servers from refusing to serve us up content..."""
        t = round(random.uniform(self.min,self.max), 3)
        self.current = t 
        formatter % f"Sleeping for {self.current} seconds..."
        time.sleep(t)





class RGB(NamedTuple):
    r:int
    g:int
    b:int
    a:int = 255

    def create_color_theme(self):
        with dpg.theme() as theme:
            with dpg.theme_component(0):
                dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, value=self, category=dpg.mvThemeCat_Core)
        return theme

    def set_theme(self,i:int):
        dpg.set_item_theme(i, self.create_color_theme())

    def create_progress_theme(self):
        with dpg.theme() as t:
            with dpg.theme_component(0):
                dpg.add_theme_color(dpg.mvThemeCol_PlotHistogram,value=self,category=dpg.mvThemeCat_Core)
        return t


IMPERIAL_RED = RGB(135,15,15)
YELLOW = RGB(230,230,0)

T = TypeVar("T")


def main_program(func:Callable[...,T]):
    """Used to wrap the keyword run to the main program"""
    def decorator(*args,**kwargs):
        ret = func(*args,**kwargs)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.start_dearpygui()
        return ret 
    return decorator


def calc_pagesum(total:int,count:int):
    """Used to caculate how many pages should be harvested up from geometry dash back to us"""
    rem = 1 if (total % count) > 0 else 0
    ps = (total // count) + rem 
    return ps 




class GUIContext:
    """Used to help make the top windows of dearpygui"""
    def __init__(self,title:str,width:int,height:int,**kw) -> None:
        dpg.create_context()
        dpg.create_viewport(title=title,width=width,height=height,**kw)
        

    def __enter__(self):
        return self
        

    @contextmanager
    def main_window(self,label:str,**kw):
        """Automatically makes and sets up a main window to use..."""
        with dpg.window(label=label,**kw) as w:
            yield w
        dpg.set_primary_window(w,True)
    

    def tooltip(self,obj:Union[int,str],text:str,**kw):
        with dpg.tooltip(obj):
            dpg.add_text(text,**kw)
        return obj

    def __exit__(self,*args):
        dpg.destroy_context()


def copy_monero_wallet():
    pyperclip.copy(MONERO_WALLET)




class DCDApp(GUIContext):
    def __init__(self, title: str, width: int, height: int, **kw) -> None:
        super().__init__(title, width, height, **kw)

        if not Path("dcd_settings.json").exists():
            # New user... just downloaded tools...
            self.output = OutputConfig(True,"raw")
            self.delays = DelayConfig(2, 5, 100)
            self.proxy = ProxyConfig(use_proxy=False)
            self.decoy = DecoyConfig(gdbrowser=False,use_decoy=False,ip_decoy="")
            self.bandwith = BandwithConfig.set_defaults()
            self.drp = DiscordConfig.set_defaults()

        else:
            self.output, self.delays, self.proxy, self.decoy , self.bandwith, self.sleep, self.drp = load_settings()

        self.stop_download = False 

        self.search = SearchConfig()
        self.level = LevelConfig(-1)


    def save_settings(self):
        dump_settings(
            self.output, 
            self.delays, 
            self.decoy, 
            self.proxy, 
            self.bandwith, 
            self.sleep,
            self.drp
        )


    def debug(self,sender, app_data, user_data):
        print(f"sender is: {sender}")
        print(f"app_data is: {app_data}")
        print(f"user_data is: {user_data}")

    def bail_out(self):
        """Bails out of downloading the gd level..."""
        self.stop_download = True


    def client(self):
        """Creates an http client to setup and use..."""
        flag = ObfuscationLevel.NONE
        if self.decoy.gdbrowser:
            flag |= ObfuscationLevel.GDBROWSER
        if self.decoy.use_decoy:
            flag |= ObfuscationLevel.XFAKEIP
        
        # TODO in 0.0.2 add bandwith settings...
        return DCDClient(
            flag,
            proxy=self.proxy.url if self.proxy.use_proxy else None,
            # a fake decoy will be pass even if ip is not avalible as long as 
            # use_decoy's flag has been is set to true. 
            decoy=self.decoy.ip_decoy if self.decoy.ip_decoy else None,
            bandwith=self.bandwith.bandwith,
            gzip=self.bandwith.gzip)


    def search_level(self, page = 0, is_next:bool = False):
        # clamp page number ourselves...
        if page < 0:
            page = 0

        if is_next:
            dpg.delete_item("level_search_results", children_only=True)
            dpg.configure_item("level_search_results", show=False)


        dpg.add_text(source="level_result", parent="level_search_results")

        with self.client() as client:
            levels = client.search_level(self.search.query, page)
        

        # with dpg.window(label="Search Results",tag="level_search_results",modal=True,on_close=lambda:self.leave_search_tool()):
            # tag = "level-id-%i"

        for level in levels:
            # DO NOT OVERDO THE ITEMS!!!
            # with dpg.group():
            name = level.name[:10] + "..." if len(level.name) > 10 else level.name
            
            dpg.add_text(f"{name} - by {level.creator.name}",parent="level_search_results")
            # Special function...
            part = coded_partial(self.level.set_event_id, level.id)
            dpg.add_button(label=f"Set LevelID:{level.id}",callback=part.method, parent="level_search_results")
        
        with dpg.group(parent="level_search_results", horizontal=True):
            dpg.add_button(label="Exit",callback=lambda:self.leave_search_tool(),parent="level_search_results")
            if page > 0:
                dpg.add_button(label="prev",callback=lambda:self.search_level(page - 1, is_next=True),parent="level_search_results")
            dpg.add_button(label="next",callback=lambda:self.search_level(page + 1, is_next=True),parent="level_search_results")

        dpg.configure_item("level_search_results",show=True)


    def noop(self):
        """Do nothing, in programming noop stands for \"no-operation\" we use noop for a special dearpygui bypassing trick..."""
        return None

    def leave_search_tool(self):
        """exits search tool and destroys previously made items..."""
        dpg.delete_item("level_search_results", children_only=True)
        dpg.configure_item("level_search_results", show=False)

    def ask_for_file(self):
        """asks program to save a file as...
        uses a Future object to enable easy callback so that when we have the object we can use it..."""
        
        # Reminds me of an asyncio callback...
        def callback(sender, app_data):
            """Calls back to the future to get our data and continue..."""
            item = Path(app_data.get("current_path"),app_data.get("file_name"))
            # Now hide file dialog and go to downloading the level comments...
            dpg.configure_item("file_dialog",show=False)
            self.sleep.invoke(self.download_level_comments, item)


        # Wait for user's response on what filename they would like to save as...
        dpg.set_item_callback("file_dialog",callback=callback)
        dpg.configure_item("file_dialog",show=True)
        

    def do_download(self):
        if not self.output.use_default_filename:
            self.ask_for_file()
        else:
            # Skip to downloading comments using default name which is the timestamp...
            self.download_level_comments(Path(datetime.datetime.now().strftime("%Y-%m-%d-_%I-%M-%S_%p") + ".txt"))
        if self.stop_download:
            self.stop_download = False


    # TODO Before 0.0.9 or something sooner allow user to download the terminal version in the options
    # Menu to give another option for downloading level comments if he or she belives downloading comments is not optimal enough... 
    
    # TODO Before 0.0.5 add bandwith settings which will include download speeds and a checkbox for enabling gzip settings...

    # TODO Drop "Evasion Settings" block and move the childern to the Settings Block to be a little faster

    def download_level_comments(self,file:Path):
        
        backoff = Backoff((self.delays.min, self.delays.max))
        
        # Open Download window...
        dpg.configure_item("download_pending",show=True)
        status = STRFormatter("download_status","Status:      %s")
        level_name = STRFormatter("level_title","Level Name: %s")
        pages_left = STRFormatter("pages_left", "%.2f")

        
        with self.client() as client:
            status % "Resolving Level..."
            level = client.downloadGJLevel(self.level.id)
            client.set_targetID(level.id)
            level_name % (level.name + f" by {level.creator.name}")
            status % "Getting Pagesum..."

            self.drp.update("Downloading Level Comments Name: %s  ID: %i" % (level.name, level.id))
        

            if self.stop_download:
                status % "Used Bailed on input Exiting..."
                status.exit()
                level_name.exit()
                pages_left.exit()
                return False 
            
            with file.open("wb") as w:
                page = client.getGJComments(0,0,count=self.delays.cpr)

                # No Comments Avalibe this will raise an error saying that no comments were found...
                if page.startswith(b"#"):
                    return False
                
                w.write(page + b"\n")
                idx = page.find(b"#")
                total = int(page[idx + 1: page.find(b":",idx)])
                pagesum = calc_pagesum(total, self.delays.cpr)
                progress = ProgressFormatter("progress",1,pagesum)

                if self.stop_download:
                    status % "Used Bailed on input Exiting..."
                    status.exit()
                    level_name.exit()
                    pages_left.exit()
                    self.drp.update("In Menu...")
                    return False 

                for p in range(1,pagesum):
                    if self.stop_download:
                        status % "Used Bailed on input Exiting..."
                        status.exit()
                        level_name.exit()
                        pages_left.exit()
                        self.drp.update("In Menu...")
                        return False
                    
                    page = client.getGJComments(p,count=self.delays.cpr,total=total)
                    w.write(page + b"\n")
                    backoff.sleep(status)
                    status % f"Getting page {p}..."
                    pages_left % ((p / pagesum) * 100)
                    progress.add()
        
        progress.add()
        # print("debug: " + self.output.filetype)
        if self.output.filetype and self.output.filetype != "raw":
            status % "Parsing data..."
            if self.output.filetype == "json":
                robtop_string_to_json(str(file))
            elif self.output.filetype == "text":
                robtop_string_to_text(str(file))
            elif self.output.filetype == "html":
                robtop_string_to_html(str(file),str(file.name))

        status % "Done!" 
        time.sleep(2)
        # Exit all currently running threads...
        status.exit()
        level_name.exit()
        pages_left.exit()
        # Close Download window...
        dpg.configure_item("download_pending",show=False)
        self.drp.update("In Menu...")
        return True
    

        


    @main_program
    def main(self):
        with dpg.value_registry():
            dpg.add_int_value(default_value=self.level.id, tag="level_id")
            dpg.add_string_value(default_value=f"Current LevelID: {self.level.id}",tag="level_result")
            dpg.add_string_value(tag="download_status")
            dpg.add_string_value(tag="speed")
            dpg.add_float_value(tag="progress", default_value=0)
            dpg.add_string_value(tag="pages_left")
            dpg.add_string_value(tag="level_title")

        if sys.platform in ["win32","cygwin","cli"]:
            dpg.set_viewport_large_icon(image)

        # TODO Move Bandwith settings to it's own custom menu...
        # with dpg.window(label="Bandwith Settings",show=False, tag="bandwith_settings",modal=True, width=310, height=150):
            
        #     self.tooltip(
        #         dpg.add_checkbox(
        #         label="Use Gzip Protocols", 
        #         default_value=self.bandwith.gzip, 
        #         callback=self.bandwith.set_item_event("gzip")),
        #         "Asks the boomlings server to use gzip.\n"\
        #         "This can speedup request transfers immensly\n"
        #         "however it can be costly on some lower end devices...\n\n"
        #         "If you have an old computer that takes a long time to\n"
        #         "open. It might be a good idea to turn this off."
        #     )
        #     # We do not need more than 1 MB of speed since responses do not take long to load...
        #     self.tooltip(
        #         dpg.add_input_int(
        #             label="Bandwith",
        #             min_value=1024,
        #             min_clamped=True, 
        #             max_value=10240,
        #             max_clamped=True,
        #             default_value=self.bandwith.bandwith,
        #             callback=self.bandwith.set_item_event("bandwith")),
        #         "Simillar to QBitTorrent, You\n"\
        #         "can control the speeds of your\n"\
        #         "download here minimum value is set\n"\
        #         "to be at 1024 and the max is 10240\n"\
        #         "robtop's data chunks are not that large\n"\
        #         "to load at all..."
        #     )

        # For now please use noop...
        with dpg.file_dialog(directory_selector=False, show=False, tag="file_dialog", width=700 ,height=400):
            dpg.add_file_extension(".txt")

        with dpg.window(label="Downloading Level Comments",tag="download_pending",modal=True, show=False,width=310,height=150,on_close=self.bail_out):
            dpg.add_text(label="Level Name",source="level_title")
            dpg.add_text(label="Status",source="download_status")
            dpg.add_text(label="Speed",source="speed")
            with dpg.group(horizontal=True):
                bar = dpg.add_progress_bar(label="Progress",source="progress")
                dpg.add_text(label="Completed",source="pages_left")
            # DCD GUI Now has a built-in emergency exit function...
            dpg.add_button(label="Cancel Download",callback=self.bail_out)

        dpg.bind_item_theme(bar,YELLOW.create_progress_theme())

        with dpg.window(label="Search Results",tag="level_search_results",modal=True, on_close=lambda:self.leave_search_tool(), show=False):
            # noop it...
            self.noop()

        with dpg.window(label="Support",modal=True,show=False,tag="donations"):
            
            dpg.add_text(
                        "To continue bringing great\n"\
                        "services to people like you\n"\
                        "as well as keeping our applications\n"\
                        "tracker and ad-free.\n"
                        "Please consider donating to\n"\
                        "our Monero Wallet where your\n"\
                        "donations won't be tracked, stolen,\n"\
                        "viewed or modfied by any\n"\
                        "third parties or governments"
                    )
        
            dpg.add_button(label="Copy Monero Wallet", callback=lambda:copy_monero_wallet())

        with dpg.window(label="Credits",modal=True,tag="credits_display",show=False):
            dpg.add_text("Calloc - Developer of the Daily Chat Downloader")
            dpg.add_text("Inspired by the original DCD Commandline module")
            dpg.add_text("Note - The Developer or anyone who\n"\
                        "contributes to the software is not\n"\
                        "responsible for what you download\n"\
                        "Download Level Comments at your own risk,\n"\
                        "This is not legal advice...")
            dpg.add_text(f"Version - {__version__}")
            dpg.add_text("Licsense - MIT")
            dpg.add_button(label="Exit",callback=lambda:dpg.configure_item("credits_display", show=False))

        # with dpg.window(label="Delay Settings",modal=True,tag="delay_settings",show=False):
           

            

            # with dpg.group(horizontal=True):
            #     dpg.add_button(label="Save", callback=lambda: dpg.configure_item("delay_settings", show=False))
                # dpg.add_button(label="Preview",callback=lambda: print(self.delays))

        # TODO Move to Menu instead of here...
        # with dpg.window(label="Decoy Settings",modal=True,tag="decoy_settings",show=False):
        #     self.tooltip(dpg.add_checkbox(label="Mimic Gdbrowser Instance",default_value=self.decoy.gdbrowser,callback=self.decoy.set_item_event("gdbrowser")), 
        #                  "tricks the boomlings server\ninto thinking were hosting gdbrowser")
        #     self.tooltip(dpg.add_checkbox(label="Spoof Client IP Address",default_value=self.decoy.use_decoy,callback=self.decoy.set_item_event("use_decoy")),
        #     "Makes boomlings servers think\n"\
        #     "that were a server that is\n"\
        #     "trying to forward someone\n"\
        #     "else to their end..."
        #     )
        #     self.tooltip(dpg.add_input_text(label="fake-ip",default_value=self.decoy.ip_decoy,callback=self.decoy.set_item_event("ip_decoy")),
        #                 "this will use the fake ip you give\n"\
        #                 "however it is better to ignore this\n"\
        #                 "and use a random ip that dcd will\n"\
        #                 "generate for you if you have\n"\
        #                 "Spoof Client IP Address Enabled")
            
            # with dpg.group(horizontal=True):
            #     dpg.add_button(label="Save", callback=lambda: dpg.configure_item("decoy_settings", show=False))
            #     dpg.add_button(label="Preview",callback=lambda:print(self.decoy))


        # Proxy Settings Child window...
        with dpg.window(label="Proxy Settings",modal=True,tag="proxy_settings",show=False):
            dpg.add_checkbox(label="Enable Proxy Connections",tag="use_proxy", default_value=self.proxy.use_proxy ,callback=self.proxy.set_item_event("use_proxy"))

            dpg.add_input_text(label="host",default_value=self.proxy.host,callback=self.proxy.set_item_event("host"))
            dpg.add_input_int(label="port",min_value=0,default_value=self.proxy.port,min_clamped=True,max_value=65536,max_clamped=True,callback=self.proxy.set_item_event("port"))
            dpg.add_combo(["http","socks5","socks4"],default_value=self.proxy.version,label="Version",callback=self.proxy.set_item_event("version"))
            
            self.tooltip(dpg.add_input_text(label="user",default_value=self.proxy.username,callback=self.proxy.set_item_event("username")), SOCKS5TOOLTIP)
            self.tooltip(dpg.add_input_text(label="pass",default_value=self.proxy.password,password=True,callback=self.proxy.set_item_event("password")),SOCKS5TOOLTIP)

            with dpg.group(horizontal=True):
                dpg.add_button(label="Save", callback=lambda: dpg.configure_item("proxy_settings", show=False))
                dpg.add_button(label="Preview",callback=lambda:print(self.proxy.url))

        with self.main_window("MAIN WINDOW"):
            
            with dpg.menu_bar():
                with dpg.menu(label="Settings"):
                    # with dpg.menu(label="Evasion Settings") as ev:
                    self.tooltip(dpg.add_menu_item(label="Proxy Connections",callback=lambda: dpg.configure_item("proxy_settings", show=True)),
                                "Allows the use of hooking\n"\
                                "up Socks5, Socks4 and HTTP\n"\
                                "Proxies and It includes a\n"\
                                "test button to ensure that\n"\
                                "the proxy not only connects\n"\
                                "but also tests weather or not\n"\
                                "boomlings will accept and not\n"\
                                "kick the proxy during the\n"
                                "exchange")

                    with dpg.menu(label="Decoy Tools") as decoy_tools:

                        self.tooltip(dpg.add_checkbox(label="Mimic Gdbrowser Instance",default_value=self.decoy.gdbrowser,callback=self.decoy.set_item_event("gdbrowser")), 
                                     "tricks the boomlings server\ninto thinking were hosting gdbrowser")
                        self.tooltip(dpg.add_checkbox(label="Spoof Client IP Address",default_value=self.decoy.use_decoy,callback=self.decoy.set_item_event("use_decoy")),
                        "Makes boomlings servers think\n"\
                        "that were a server that is\n"\
                        "trying to forward someone\n"\
                        "else to their end..."
                        )
                        self.tooltip(dpg.add_input_text(label="fake-ip",default_value=self.decoy.ip_decoy,callback=self.decoy.set_item_event("ip_decoy")),
                                    "this will use the fake ip you give\n"\
                                    "however it is smarter to ignore this\n"\
                                    "dcd will automatically\n"\
                                    "generate random legimate\n"\
                                    "IP address to spoof\n"\
                                    "if you have Spoof Client\n"\
                                    "IP Address Enabled"
                        )

                    self.tooltip(decoy_tools,
                        "Sets up decoys to\n"\
                        "shift blame for where\n"\
                        "the http traffic is\n"\
                        "coming from. This will\n"\
                        "also allow us to protect\n"\
                        "ourselves from Cloudflare's\n"\
                        "Telemetry And other trackers..."
                    )
                    
                    # This will be eaiser than having a popupscreen which seems to have lag of it's own...
                    with dpg.menu(label="Delay Settings") as ds:
                        dpg.add_text("Delays Per Request")

                        dpg.add_input_double(
                            label="min",min_value=0,max_value=20,default_value=self.delays.min,
                            callback=self.delays.set_item_event("min")
                        )
            
                        dpg.add_input_double(
                            label="max",min_value=1,max_value=21,default_value=self.delays.max,
                            callback=self.delays.set_item_event("max")
                        )

                    self.tooltip(ds, "Controls random delays\n"\
                    "in comment downloads\n"\
                    "to prevent rate-limiting\n"\
                    "and prevent accidental\n"\
                    "ddos attacks")

                    with dpg.menu(label="Bandwith Settings"):
                        self.tooltip(
                            dpg.add_checkbox(
                            label="Use Gzip Protocols", 
                            default_value=self.bandwith.gzip, 
                            callback=self.bandwith.set_item_event("gzip")),
                            "Asks the boomlings server to use gzip.\n"\
                            "This can speedup request transfers immensly\n"
                            "however it can be costly on some lower end devices...\n\n"
                            "If you have an old computer that takes a long time to\n"
                            "open. It might be a good idea to turn this off."
                        )
                        # We do not need more than 1 MB of speed since responses do not take long to load...
                        self.tooltip(
                            dpg.add_input_int(
                                label="Bandwith",
                                min_value=1024,
                                min_clamped=True, 
                                max_value=10240,
                                max_clamped=True,
                                default_value=self.bandwith.bandwith,
                                callback=self.bandwith.set_item_event("bandwith")),
                            "Simillar to QBitTorrent, You\n"\
                            "can control the speeds of your\n"\
                            "download here. Minimum value is set\n"\
                            "to be at 1024 and the Maximum is set to 10240.\n"\
                            "Robtop's data chunks are not that large\n"\
                            "to load at all but use this when\n"\
                            "you're having lag."
                        )

                    with dpg.menu(label="Sleep Settings"):
                        self.tooltip(dpg.add_checkbox(label="Enable AFK Downloading", default_value=self.sleep.afk, callback=self.sleep.set_item_event("afk")), SleepSettings.__doc__)
                    with dpg.menu(label="Discord Settings"):
                        self.tooltip(dpg.add_checkbox(label="Enable Discord Rich Presense", default_value=self.drp.on, callback=self.drp.update_config), DiscordConfig.__doc__)
                    # self.tooltip(ev,"These settings help with\nevading ip bans\nand rate limiting\nWarning Evasion Block will be removed in 0.0.3....\nall blocks will be moved over here instead...")
                # TODO Add bandwith and Gzip settings to 0.0.4

                with dpg.menu(label="Other"):
                    dpg.add_menu_item(label="Credits",callback=lambda:dpg.configure_item("credits_display", show=True))
                    dpg.add_menu_item(label="Support",callback=lambda:dpg.configure_item("donations",show=True))

            dpg.add_text("The Geometry Dash Level Comment Downloader Tool - By Calloc")
        # Now work on the tabs...
            with dpg.tab_bar():
                with dpg.tab(label="Downloader"):
                    dpg.add_text("Level Comment Downloader")

                    dpg.add_input_int(
                        label="LevelID",
                        min_clamped=True, 
                        min_value=-2,
                        callback=self.level.set_item_event("id"),
                        source="level_id"
                    )
                    
                    dpg.add_checkbox(label="Use timestamp as filename",default_value=self.output.use_default_filename,callback=self.output.set_item_event("use_default_filename"))

                    dpg.add_input_int(
                        label="Comments Per Request",
                        default_value=self.delays.cpr,
                        min_value=10,min_clamped=True,
                        max_value=100,max_clamped=True,
                        callback=self.delays.set_item_event("cpr")
                    )

                    with dpg.group(horizontal=True):
                        dpg.add_button(label="Set To Daily",callback=lambda:self.level.set_event_id(-1))
                        dpg.add_button(label="Set To Weekly",callback=lambda:self.level.set_event_id(-2))

                    self.tooltip(dpg.add_combo(["text","json","raw","html"],label="Output Format",default_value=self.output.filetype,callback=self.output.set_item_event("filetype")),
                                "text: format in a normal forum style logging\n"\
                                "json: save all data in a textfile with json values this is lossless\n"
                                "raw: leave as is which is robtop string...\n"
                                "html: Renders data as html into a forum format.\n"\
                                    " It also includes links to all the comment author\n"\
                                        " accounts to be acessed in gdbrowser")

                    # Temporary callback for debugging dynamic variables...
                    # temp = lambda: dpg.configure_item("download_pending", show=True)
                    dpg.add_button(label="Download Level",callback=self.do_download)


                    # TODO Finish Downloader tab
                with dpg.tab(label="Level Search Tool"):
                    dpg.add_text("Level Search")
                    dpg.add_input_text(label="Level Name", callback=self.search.set_item_event("query"))
                    dpg.add_button(label="Search",callback=lambda:self.search_level())


        

if __name__ == "__main__":
    with DCDApp(f"DCD Version {__version__}",800,600) as app:
        app.main()
        # Save settings if we have any...
        app.drp.close()
        app.save_settings()

    

        