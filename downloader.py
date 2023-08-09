import dearpygui.dearpygui as dpg
from typing import Union, Any
import threading
from queue import Queue, Empty
import time 

class STRFormatter:
    def __init__(self,tag:Union[str,int], s:str) -> None:
        self.s = s
        self.tag = tag
        self.q = Queue()
        self.thread = threading.Thread(target=self.run_thread)
        self.thread.daemon = True
        self.not_dead = True
        self.thread.start()

    def run_thread(self):
        while self.not_dead:
            try:
                value = self.q.get_nowait()
                dpg.set_value(self.tag, value=value)
            except Empty:
                if not self.not_dead:
                    return
                time.sleep(0.05)
    
    def __mod__(self, value:Union[tuple[Any,...], Any]):
        v = self.s % value
        self.q.put(v)

    def exit(self):
        """Kills running thread..."""
        self.not_dead = False 
        self.thread.join()
    

class ProgressFormatter:
    def __init__(self,tag:Union[str,int],start:int=0, end:int=0) -> None:
        self.tag = tag
        self.start = start
        self.end = end

    def add(self):
        if self.start < self.end:
            self.start += 1 
            dpg.set_value(self.tag , self.start / self.end )

