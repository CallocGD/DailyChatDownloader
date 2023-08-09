class coded_partial:
    """Used as a bypass method for getting around the `__code__` issue..."""
    def __init__(self,func,*args,**kwargs) -> None:
        self.func = func 
        self.args = args 
        self.kwargs = kwargs
    
    def method(self):
        return self.func(*self.args, **self.kwargs)