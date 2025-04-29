"""Pypet for liteServer peak simulator with embedded plot
"""
__version__='v0.0.3 2025-04-27'# handle instance

_Namespace = "LITE"

# handle program option instance = 'host;port'
from builtins import pypage_INSTANCE as hostPort
if hostPort == '':
    hostPort = "localhost;9701"
print(f'hostPort: `{hostPort}`')

dev = f"{hostPort}:dev1:"
server = f"{hostPort}:server:"
#```````````````````Definitions````````````````````````````````````````````````
# Python expressions and functions, used in the spreadsheet.
_=' '
def span(x,y): return {'span':[x,y]}
def color(*v): return {'color':v[0]} if len(v)==1 else {'color':list(v)}
pvplot = f"python3 -m pvplot -a L:{dev} x,y"

#``````````````````Page attributes, optional``````````````````````````````````
#_Page = {'editable':False, **color(252,252,237)}
_Page = {**color(240,240,240)}

#```````````````````Configure columns and rows````````````````````````````````` 
_Columns = {
  1: {"justify": "center"},
  2: {"width": 100},
  3: {"justify": "right"},
  5: {"width": 400},
}

_Rows = [
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
[],
]
