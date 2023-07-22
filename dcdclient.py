import httpx 
import random 


# This is the same functionality as in the terminal version so 
# no need to change anything from that...
# from reporter import Reporter

from flags import ObfuscationLevel
import math 

import typing 
from time import perf_counter, sleep
from errors import RateLimit, MinusOne, ServerMisbehaved
from models import Level, parse_data
import socket 

from httpx_socks import SyncProxyTransport
from downloader import STRFormatter, ProgressFormatter



gameVersion = 21
"""The version currently being used"""
binaryVersion = 34
"""The version of the game in binary form"""

def make_decoy():
    """Makes a random IP address to use in the x-real-ip"""
    # RFC 1918 http://www.faqs.org/rfcs/rfc1918.html
    # 192.168.x.x, 172.16.0.0 to 172.31.255.255, 10.x.x.x are all bad IPs including 127.x.x.x
    # Reporter.Loading("Creating Decoy Alias for X-Real-IP")
    ip : list[int] = []
    ip.append(random.randint(1,255))
    ip.extend([random.randint(0,255) for _ in range(3)])
    
    if ip[0] in [10,127]:
        if ip[1] % 2 == 0:
            ip[0] -= 1
        else:
            ip[0] += 1
    elif ip[0] == 172 and ip[1] >= 16 and ip[1] <= 31:
        # NOTE This is a smarter mixing pattern than just simply adding or subtracting 1 as any number bewtween 15 and 31 and all be randomized 
        if ip[1] % 2 == 0:
            ip[1] -= 16 
        else:
            ip[1] += 16
    elif ip[0] == 192 and ip[1] == 168:
        if ip[2] % 2 == 0:
            ip[1] -= 1
        else:
            ip[1] += 1
    decoy = "%i.%i.%i.%i" % (ip[0],ip[1],ip[2],ip[3])
    # Reporter.Success("Fake Alias Will Be: %s" % decoy)
    return decoy

SECRET = "Wmfd2893gb7"
"""This doesn't need to be hidden however if it is altered in a future update 
to robtop's servers we can easily modify it from here - Calloc"""

# Chunks of code are from youtube-dl since it's under the unlicense license  
# which means I'm free to use it with dcd.... 
def float_or_none(v, scale=1, invscale=1, default=None):
    if v is None:
        return default
    try:
        return float(v) * invscale / scale
    except (ValueError, TypeError):
        return default

def format_decimal_suffix(num, fmt='%d%s', *, factor=1000):
    """ Formats numbers with decimal sufixes like K, M, etc """
    num, factor = float_or_none(num), float(factor)
    if num is None or num < 0:
        return None
    POSSIBLE_SUFFIXES = 'kMGTPEZY'
    exponent = 0 if num == 0 else min(int(math.log(num, factor)), len(POSSIBLE_SUFFIXES))
    suffix = ['', *POSSIBLE_SUFFIXES][exponent]
    if factor == 1024:
        suffix = {'k': 'Ki', '': ''}.get(suffix, f'{suffix}i')
    converted = num / (factor ** exponent)
    return fmt % (converted, suffix)


def format_bytes(_bytes:float):
    return format_decimal_suffix(_bytes, '%.2f%sB', factor=1000) or 'N/A'

def format_speed(speed):
    return ' Unknown B/s' if speed is None else f'{format_bytes(speed):>10s}/s'

def calc_speed(start:float, now:float, _bytes:int):
    dif = now - start
    # if _bytes == 0 or dif < 0.001:  # One millisecond
    if _bytes == 0:
        return None
    return float(_bytes) / dif

# def on_request(request:httpx.Request):  
#     print(request)


class DCDClient:
    def __init__(
            self,
            obfuscation:ObfuscationLevel = ObfuscationLevel.NONE, 
            proxy:typing.Optional[str]=None,
            bandwith:int=8192,
            decoy:str=None,
            gzip:bool=True) -> None:
        
        self.speed = STRFormatter("speed", "Download Speed:     %s")
    

        self.client = httpx.Client(
            transport=SyncProxyTransport.from_url(proxy) if proxy else None, 
            # event_hooks={"request":[on_request]},
            base_url="http://www.boomlings.com",
            # gzip is faster to handle, I found out we can even forward this because I've seen robtop's mysql Admin Portal / Settings
            headers={"Accept-Encoding":"gzip"} if gzip else {})
        
        # we cannot forward a user-agent because it will trigger boomlings's firewall 
        # and it not let us through giving us a 403 http response...
        del self.client.headers["user-agent"]
        del self.client.headers["accept"]

        self.default_parameters = {}
        
        self.bandwith = bandwith
        """used to configure download speeds"""

        if obfuscation >= ObfuscationLevel.GDBROWSER:
            # Reporter.Success("Setting up fake instance of gdbrowser")
            self.default_parameters["gdbrowser"] = 1

        # Below is a Vulnerability/Exploit technique that goes way back ,
        # the reason why this works is because gdbrowser forwards 
        # IP addresses it connects to along to robtop to prevent ddosing (More Likely For Telemetry)
        # So what's to stop us if we forward a non-existant client as long as we have 
        # a legitimate IP address to be forwarded?

        # By passing along fake X-Real-IP headers we can hide ourselves by shifting the blame 
        # over the decoy rather than ourselves incase we fuck up.

        # This vulnerability is apparently unpatachable which makes it perfect for us to use...
        # This is simillar to what Nmap does 

        if obfuscation >= ObfuscationLevel.XFAKEIP and not decoy:
            self.client.headers["X-Real-IP"] = make_decoy()
            
        elif decoy:
            # Reporter.Loading(f"setting X-Real-IP header as {decoy}")
            self.client.headers["X-Real-IP"] = decoy 

    def test(self):
        response = self.client.get(url="/")
        print(response.read())
    
    def set_targetID(self,id:int):
        self.targetID = id 

    def getGJComments(self,page:int,mode:int=0,count:int=20,total:int=0):
        params = {
            "levelID":self.targetID, 
            "secret":SECRET,
            "page":page,
            "mode":mode,
            "count":count,
            "total":total,
            "gameVersion":gameVersion,
            "binaryVersion":binaryVersion,
        }
        return self.force_post("/database/getGJComments21.php",params=params)
    
    def post(self,endpoint:str,params:dict):

        # paramters should be updated here which is why we 
        # have a post function of our own to begin with......
        for k , v in self.default_parameters.items():
            params[k] = v
        with self.client.stream("POST",endpoint,data=params,timeout=300) as response:
            if response.status_code == 429:
                raise RateLimit(response.headers.get("Retry-After",3600), "(429 Too Many Requests) Got RateLimited")
            
            elif response.status_code != 200:
                # -- New Issue that's server realted was triggered --
                # Can be caused/invoked by one of 3 things...
                # 1. WAF Fucked up (Aka Firewall Misbehaved)
                # 2. Robtop swapped/chanaged Wafs...
                # 3. WAF Finds our proxy's ip address to be unfavorable & 
                # likely because ip address used to or has a low reputation 
                # on a dnsblacklist (which is bad) I know because I have an 
                # api key for project honeypot myself...
                raise ServerMisbehaved(f"Misbehavior was given by the server <Status:{response.status_code} Reason:{response.reason_phrase} ")
            
            # Download response...
            data = self.handle_response(response)
            
            if data == b"-1":
                raise MinusOne(f"Level:{params['levelID']} is not avalible" if params.get('levelID') else "Server F'd up")
            
            elif data.startswith(b"<"):
                # We've likely landed on html which is a captcha page which is bad! :(
                # If you landed here god I hope you at least had the 
                # balls to use a proxy of some kind. 
                # Otherwise ask your isp for different IP address
                # This Commonly will arise if your using tor or are hosting 
                # a tor exit node from your home internet or your IP had a Bad reputation on Project Honeypot...
                raise ServerMisbehaved("An Unsolvable Captcha Was Invoked by Geometry Dash's Server Firewall even though server told us <200:OK>")
            
            return data 
    
    def force_post(self,endpoint:str,params:dict):
        """same as post but handles all exceptions raised right here..."""
        while True:
            try:
                return self.post(endpoint,params)
            
            except ServerMisbehaved as sm:
                # Reporter.Critical("Server Misbehaved",sm.msg)
                # Reporter.Critical("Exiting","Preparing to do an Emergency Shutdown")
                self.client.close()
                raise sm

            except MinusOne as m:
                # Reporter.Error(f"-1 was obtained because {m.args[0]}")
                self.client.close()
                raise m

            except RateLimit as rl:
                # Reporter.Critical("Rate Limited","Your Requests were Rate Limted")
                # if not Reporter.Question("Would you like to wait out the timeout given?"):
                    # self.client.close()
                    # sys.exit(1)
                # Reporter.Timer("Waiting out Server's instrcuted Timeout...",rl.timeout,"Timeout has been statisfied.")
                # Reporter.Loading("Redoing the original request")
                # go back to the while true portion
                raise rl 
            
            except socket.timeout as e:
                sleep(0.3)
                # Reporter.Error("Socket Timed out likely because the response fucked itself up")
                # Reporter.Loading("Redoing the same request...")
                continue

    def handle_response(self,response:httpx.Response):
        download = response.iter_bytes(self.bandwith) 
        read = b""  

        while True:
            start = perf_counter()
            chunk = next(download,None)
            now = perf_counter()
            if not chunk:
                # TODO add to dearpygui reports or logfiles...
                return read
            # TODO Add to dearpygui...
            self.speed % format_speed( calc_speed(start,now,self.bandwith))

            read += chunk
            


    def downloadGJLevel(self,levelID:int):
        return Level.from_bytes(self.force_post("/database/downloadGJLevel22.php", {"levelID":levelID,"secret":SECRET}))
    
    def search_level(self,query:str,page:int=0):
        params = {
            "secret":SECRET,
            "page":f"{page}",
            "gdw":"0",
            "type":"0",
            "str": query,
            "gameVersion":gameVersion,
            "binaryVersion":binaryVersion,
        }

        return parse_data(self.force_post("/database/getGJLevels21.php",params=params))
    
    # TODO (Calloc) add User Harvesting in the future if the user gives permission to scrape thier data...
    
    def __enter__(self):
        return self 
    
    def __exit__(self,*args):
        self.speed.exit()
        return self.client.close()

# with DCDClient() as dcd:
#     print(dcd.downloadGJLevel(42069))

if __name__ == "__main__":
    with DCDClient(ObfuscationLevel.ALL) as dcd:
        print(dcd.search_level("Unzor",0))

