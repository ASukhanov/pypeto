"""Basic EPICS access API using caproto threading.
The API is similar to cad_io.
The devPar argument is tuple (deviceName,parameterName).
The EPICS PV name is concatenation of the deviceName and parameterName

For example: epics.get(('testAPD:scope1:','MaxValue_RBV')) returns 
{('testAPD:scope1:', 'MaxValue_RBV'): {'value': 1.5620877339306638, 'timestamp': 1681488886.923712, 'alarm': 0}}
"""
__version__ = 'v0.0.2 2023-04-14'# No colon separation when splitting PV name to (device,parameter) tuple.

#from time import perf_counter as timer

from caproto.threading.client import Context
_Ctx = Context()

_PVCache = {}# cache of PVs
# the key is EPICS PV name, the fields are as follows:
_PVC_PV = 0# EPICS PV object
_PVC_CB = 1# callback
_PVC_Props = 2# PV properties
_PVC_DevPar = 3# (deviceName, ParameterName)

_Subscriptions = []# list of EPICS PV subscriptions

_CA_data_type_STRING = 14

_dbg = False
def _printd(msg):
    if _dbg:
        print(f'CPAccess:{msg}')

def init():
    return

def _get_pv(devPar:tuple):
    pvName = ''.join(devPar)
    r = _PVCache.get(pvName)
    if r is None:
        _printd(f'register pv {pvName} {devPar}')
        pv,*_ = _Ctx.get_pvs(''.join(pvName), timeout=2)
        _PVCache[pvName] = [pv, None, None, devPar]
        _fill_PVCacheProps(pv)
    else:
        pv,*_ = r
    return pv

def _fill_PVCacheProps(pv):
    pvName = pv.name
    pvData = pv.read(data_type='time')
    val = pvData.data
    if len(val) == 1:
        try:
            # treat it as numpy
            val = pvData.data[0].item()
        except:
            # data is not numpy
            val = pvData.data[0]
    
    # get properties
    #ISSUE: the caproto reports timestamp as float, the precision for float64 
    #presentation is ~300ns
    featureBit2Letter = {1:'R', 2:'WE'}
    featureCode = pv.access_rights
    features = ''
    for bit, letter in featureBit2Letter.items():
        if bit & featureCode:
            features += letter
    pvControl = pv.read(data_type='control')
    #_printd(f'pvcontrol {pvName}: {pvControl}')
    datatype = pvControl.data_type
    #_printd(f'data_type:{datatype}')
    if datatype == _CA_data_type_STRING:# convert text bytearray to str
        val = val.decode()
    props = {'value':val}
    props['timestamp'] = pvData.metadata.timestamp
    props['count'] = len(pvData.data)
    props['features'] = features
    try:    
        props['units'] = pvControl.metadata.units.decode()
        if props['units'] == '':   props['units'] = None
    except: pass

    try:    props['engLow'] = pvControl.metadata.lower_ctrl_limit
    except: pass

    try:    
        props['engHigh'] = pvControl.metadata.upper_ctrl_limit
        if props['engHigh'] == 0.0 and props['engHigh'] == 0.0:
            props['engHigh'], props['engLow'] = None, None
    except: pass

    try:
        props['alarm'] = pvControl.metadata.severity 
        #_printd(f'status {pvControl.metadata.severity}')
        if props['alarm'] == 17:# UDF
            props['alarm'] = None
    except: pass

    try:    # legalValues
        enum_strings = pvControl.metadata.enum_strings
        props['legalValues'] = [i.decode() for i in enum_strings]
        props['value'] = props['legalValues'][val]
    except:
        #props['legalValues'] = None
        if 'legalValues' in props:
            del props['legalValues']
    #_printd(f'_props {props}')
    _PVCache[pvName][_PVC_Props] = props

def info(devPar:tuple):
    """Abridged PV info"""
    pvName = ''.join(devPar)
    pv = _get_pv(devPar)
    return {devPar:_PVCache[pvName][_PVC_Props]}

def get(devPar:tuple, *args, **kwargs):
    '''Returns devPar-keyed map of PV properties: {'value','timestamp'...}'''
    pvName = ''.join(devPar)
    pv = _get_pv(devPar)
    pvData = pv.read(data_type='time')
    rDict = _unpack_ReadNotifyResponse(pvName, pvData)
    return rDict

def set(devParValue:tuple):
    '''Sets the PV value. The devParValue is (deviceName, ParameterName, value)
    '''
    dev, par, value = devParValue
    #print(f'epicsAccess.set({dev,par,value})')
    pvName = ''.join((dev,par))
    pv = _get_pv((dev,par))
    try: # if PV has legalValues then the value should be index of legalValues
        value = _PVCache[pvName][_PVC_Props]['legalValues'].index(value)
    except Exception as e:
        #print(f'in epicsAccess.set. Value not in legalValues: {e}')
        pass
    pv.write(value)
    return 1

def _unpack_ReadNotifyResponse(pvName:str, pvData):
    val = pvData.data
    if len(val) == 1:
        try:    #it as numpy
            val = pvData.data[0].item()
        except: # it is not numpy
            val = pvData.data[0]
    #_printd(f'pvData:{pvData}')
    #_printd(f'val:{val}, {pvData.data_type}')
    if pvData.data_type == _CA_data_type_STRING:
        val = val.decode()

    legalValues = _PVCache[pvName][_PVC_Props].get('legalValues')
    if legalValues is not None:
        #rDict['value'] = legalValues[int(val)]
        val = legalValues[int(val)]
    alarm = pvData.metadata.severity
    key = _PVCache[pvName][_PVC_DevPar]
    rDict = {key: {'value':val\
    , 'timestamp':pvData.metadata.timestamp, 'alarm': alarm}}
    return rDict

def _callback(subscription, pvData):
    #tMark = [timer(), 0., 0.]
    pvName = subscription.pv.name
    _printd(f'>epicsAccess._callback: {pvName}')#{pvData})')
    rDict = _unpack_ReadNotifyResponse(pvName, pvData)
    #tMark[1] = timer()
    cache = _PVCache.get(pvName)
    cb = cache[_PVC_CB]
    if cb:
        cb(rDict)
    #tMark[2] = timer() - tMark[1]
    #tMark[1] -= tMark[0]
    ##_printd(f'caproto cb times {tMark}')# 20-30 uS
    
def subscribe(callback:callable, devPar:tuple):
    '''Subscribe callback method to changes of PVs, defined by devPar'''
    pvName = ''.join(devPar)
    pv = _get_pv(devPar)
    subscription = pv.subscribe(data_type='time')
    _PVCache[pvName][_PVC_CB] = callback
    subscription.add_callback(_callback)
    _Subscriptions.append(subscription)

def unsubscribe():
    '''Unsubscribe all subscriptions'''
    global _Subscriptions
    for subscription in _Subscriptions:
        #print(f'>epicsAccess clear subs: {subscription}')
        subscription.clear()
    _Subscriptions = []
    
