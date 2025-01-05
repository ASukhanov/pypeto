#Pypet page to control a Peak Simulator in LiteServer infrastructure.

#``````````````````Variables, used by pypet
_Namespace = "LITE"# Devices are from Liteserver infrastructure
_WindowTitle = 'LITE PeakSimulator'
_PageHelp = 'https://github.com/ASukhanov/liteServer/blob/master/liteserver/device/litePeakSimulator.py'

#``````````````````Definitions`````````````````````````````````````````````````

#hostPort = "acnlin23:"
hostPort = "localhost;9710:"
dev = hostPort+"dev1:"
server = hostPort+"server:"
bkgColor = {"color": (240,240,240)}# background color
_ = {'':bkgColor}# empty cell

# Python expressions and functions, used in the spreadsheet.
def span(x,y): return {'span':[x,y]}
def color(*v): return {'color':v[0]} if len(v)==1 else {'color':list(v)}
def font(size): return {'font':['Arial',size]}
def slider(minValue,maxValue):
    """Definition of the GUI element: horizontal slider with flexible range"""
    return {'widget':'hslider','opLimits':[minValue,maxValue]}

# Buttons
def Button(name, launch, fontSize=12, col='lightGreen'):
    return {name:{'launch':launch, 'font':['Open Sans Semibold',fontSize], 
    **color(col)}}
PlotXY = Button("Plot Y vs X",
  "python3 -m pvplot -s.01 -a'L:localhost;9710:dev1:' 'x,y'")
Stripchart = Button("Stripchart",
  "python3 -m pvplot -s.01 -a'L:localhost;9710:dev1:' 'yMin yMax'")
Correlation = Button("Min-Max Correlation",
  "python3 -m pvplot -s.01 -a'L:localhost;9710:dev1:' 'yMin,yMax'")

GrayRow = {'ATTRIBUTES':{'color':'lightGray', 'justify':'center', **font(12)}}
LargeRow = {'ATTRIBUTES':{**font(12)}}
FocusRow = {'ATTRIBUTES':{'color':'lightCyan', **font(12)}}
#,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
#``````````````````Page attributes, optional``````````````````````````````````
#_Page = {'editable':False, **color(252,252,237)}
_Page = {**bkgColor}

_Columns = {
  1: {"justify": "right"},#"center"},
  2: {"width": 100},
  3: {"width": 60, "justify": "right"},
}

#``````````````````Rows in the spreadsheet`````````````````````````````````````
_Rows = [
["Device is ", dev+"run", 'debug:', server+'debug'],
["Device status messages:", {dev+"status":span(3,1)}],
["Data update frequency:", dev+"frequency", "nPoints:", dev+"nPoints"],
[],
[GrayRow,{'Plots and data':span(4,1)}],
[Correlation,Stripchart,'',PlotXY,],
["X:", {dev+"x":span(3,1)}],
["Y:", {dev+"y":span(3,1)}],
['yMin:', dev+'yMin', 'yMax:', dev+'yMax'],
[],
[GrayRow,{'Peak Parameters':span(4,1)}],
["Noise level:", {dev+"noise":slider(0.,20.)}, dev+"noise",_],
["Swinging range of peaks:", {dev+"swing":slider(0.,2.)}, dev+"swing",_],
["Peaks parameters:", {dev+"peakPars":span(3,1)}],
["Quadratic baseline:", {dev+"background":span(3,1)}],
[],
[GrayRow,{'For experts, performance':span(4,1)}],
['Array of perf. counters:', {server+'perf':span(3,1)}],
['MBytes published:', server+'perf[1]', 'MB/s:', server+'perf[2]'],
['Packets lost,dropped:', server+'perf[4:6]',_,_],
["Cycles:", dev+"cycle", "Cycle/s", dev+"rps"],
]
