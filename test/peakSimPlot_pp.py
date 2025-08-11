"""Pypet for liteServer peak simulator with embedded plot
"""
__version__='v3.0.0 2025-05-09'# 

#```````````````````Definitions```````````````````````````````````````````````
# Python expressions and functions, used in the PyPage.
_=' '
def span(x,y): return {'span':[x,y]}
def color(*v): return {'color':v[0]} if len(v)==1 else {'color':list(v)}

#``````````````````PyPage Object``````````````````````````````````````````````
class PyPage():
    def __init__(self, instance="localhost;9701", title=None):
        """instance: unique name of the page.
        For single-device page it is commonly device name or host;port.
        title: is used for name of the tab in the GUI. 
        """
        print(f'Instantiating Page {instance,title}')
        hostPort = instance
        dev = f"{hostPort}:dev1:"
        localDev = 'localhost;9701:dev1:'
        print(f'Controlling device {dev}')
        server = f"{hostPort}:server:"
        pvplot = f"python3 -m pvplot -a L:{dev} x,y"

        #``````````Mandatory class members starts here````````````````````````
        self.namespace = 'LITE'
        self.title = f'PeakSim@{hostPort}' if title is None else title

        #``````````Page attributes, optional`````````````````````````
        self.page = {**color(240,240,240)}
        #self.page['editable'] = False

        #``````````Definition of columns`````````````````````````````
        self.columns = {
          1: {"justify": "center"},
          2: {"width": 100},
          3: {"justify": "right"},
          5: {"width": 400},
        }

        #``````````Definition of rows````````````````````````````````
        self.rows = [
['Performance:', {server+'perf':span(3,1)},_,_,{_:{'embed':pvplot,**span(1,10)}}],
["run", dev+"run", 'debug:', server+'debug'],
["status", {dev+"status":span(3,1)}],
["frequency", dev+"frequency", "nPoints:", dev+"nPoints"],
["background", {dev+"background":span(3,1)}],
["noise", dev+"noise", "swing:", dev+"swing"],
["peakPars", {dev+"peakPars":span(3,1)}],
#["x", {dev+"x":span(3,1)}],
#["y", {dev+"y":span(3,1)}],
['yMin:', dev+'yMin', 'yMax:', dev+'yMax'],
["rps", dev+"rps", "cycle:", dev+"cycle"],
['cycle:',dev+"cycle", 'cycleLocal:',localDev+"cycle"],
[_,dev+"clear",_,localDev+"clear"],
]

