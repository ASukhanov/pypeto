"""Pypet for liteServer peak simulator with embedded plot
"""
__version__='v3.0.1 2025-08-13'# localDev removed 

#```````````````````Definitions```````````````````````````````````````````````
# Python expressions and functions, used in the PyPage.
_=' '
def span(x,y): return {'span':[x,y]}
def color(*v): return {'color':v[0]} if len(v)==1 else {'color':list(v)}
def font(size): return {'font':['Arial',size]}
CyanRow = {'ATTRIBUTES':{'color':'light cyan', **font(12)}}

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
          1: {"justify": "right"},
          2: {"width": 100},
          3: {"justify": "right"},
          5: {"width": 100},
        }

        #``````````Definition of rows````````````````````````````````
        self.rows = [
[CyanRow,'Control of', {dev:span(3,1)}],
['Performance:', {server+'perf':span(3,1)},_,_,{_:{'embed':pvplot,**span(1,10)}}],
["run is ", dev+"run", 'debug:', server+'debug'],
[{dev+"status":span(4,1)}],
["frequency:", dev+"frequency", "nPoints:", dev+"nPoints"],
["background:", {dev+"background":span(3,1)}],
["noise:", dev+"noise", "swing:", dev+"swing"],
["peakPars:", {dev+"peakPars":span(3,1)}],
#["x", {dev+"x":span(3,1)}],
#["y", {dev+"y":span(3,1)}],
['yMin:', dev+'yMin', 'yMax:', dev+'yMax'],
["rps:", dev+"rps", "cycle:", dev+"cycle"],
['cycle:',dev+"cycle"],
[_,dev+"clear"],
]

