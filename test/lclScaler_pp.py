"""Control of a liteScaler, test liteServer app.
"""
__version__='v3.0.0 2025-05-08'#
_Namespace = 'LITE'

#``````````````````Definitions````````````````````````````````````````````````
# Python expressions and functions, used in the spreadsheet.
def span(x,y): return {'span':[x,y]}
def color(*v): return {'color':v[0]} if len(v)==1 else {'color':list(v)}
def font(size): return {'font':['Arial',size]}
def just(i): return {'justify':{0:'left',1:'center',2:'right'}[i]}

#``````````````````Object Page````````````````````````````````````````````````
class PyPage():
    def __init__(self, instance="localhost;9702", title=None):
        print(f'Intantiating Page {instance,title}')
        hostPort = instance
        dev = f"{hostPort}:dev1:"
        localDev = 'localhost;9701:dev1:'
        print(f'Controlling device {dev}')
        server = f"{hostPort}:server:"
        pvplot = f"python3 -m pvplot -a L:{dev} x,y"

        #``````````Mandatory class members starts here````````````````````````
        self.namespace = 'LITE'
        self.title = f'liteScaler@{hostPort}' if title is None else title

        #``````````Page attributes, optional`````````````````````````
        self.page = {**color(252,252,237)}#'editable':False,

        #``````````Definition of columns`````````````````````````````
        self.columns = {
          1: {**just(2), **color(220,220,220)},
          2: {'width': 90},
          3: {'width': 80, **just(2)},
          4: {'width': 60},
          5: {'width': 50, **just(2)},
          6: {'width': 60},
        }

        #``````````Definition of rows````````````````````````````````
        self.rows = [
[{'Server':font(14)}, server+'run','debug', server+'debug', 'version:', server+'version'],
['status:', {server+'status':span(4,1)}],
['host:', server+'host', 'clients:', server+'statistics', server+'clientsInfo', server+'lastPID'],
['performance:', {server+'perf':span(3,1)},'',''],
[],
[{'Scaler':font(14)}, 'frequency', dev+'frequency', 'cycle',dev+'cycle', dev+'rps'],
['status:', {dev+'status':span(5,1)}],
['image:', dev+'image', 'shape:', {dev+'shape':span(2,1)},''],
#['subscribe', dev+'subscribe', 'sleep:', dev+'sleep'],
['counters', {dev+'counters':span(5,1)}],
['reset', dev+'reset','dataSize:',dev+'dataSize', dev+'chunks'],#'increments', dev+'increments'],# 'image', dev+'image'],
['publishingSpeed', dev+'publishingSpeed', dev+'udpSpeed', 'time', {dev+'time':span(2,1)},],
['coordinate', dev+'coordinate', 'number', dev+'number', 'text', dev+'text'],
]

# The following line is mandatory

