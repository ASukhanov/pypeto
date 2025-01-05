"""litePet configuration of the EPICS simulated oscilloscope""" 
__version__ = 'v04 2024-04-14'# scope1::Waveform_RBV

_Namespace = 'EPICS'

# Local variables, they can be overridden in the command line (option --macro).
D = 'testAPD:scope1:'
#``````````````````Definitions````````````````````````````````````````````````
# python expressions and functions, used in the spreadsheet

def slider(minValue,maxValue):
    """Definition of the GUI element: horizontal slider with flexible range"""
    return {'widget':'hslider','opLimits':[minValue,maxValue]}

MediumFont = {'color':3*[220], 'font': ['Arial',12]}
_ = ''

#``````````````````Page attributes, optional``````````````````````````````````
#_Page = {'editable': False,}
#``````````````````Column attributes, optional````````````````````````````````
_Columns = {
1:{'width':140,'justify':'right'},
2:{'width':80},
3:{'width':30},
4:{'width':30},
5:{'width':480},
}
#``````````````````Configuration of rows``````````````````````````````````````
_Rows = [
[{'ATTRIBUTES':MediumFont},
  {f'Parameters of {D}':{'span':[3,1],'justify':'center'}},_,_,
  {D+'VoltOffset':{'span':[1,16],'widget':'vslider','opLimits':[-10,10]}},
  {_:{'embed':'python -m pvplot E:testAPD:scope1:Waveform_RBV','span':[1,16]}}],
['Run:',{D+'Run':{'attr':'WE'}}],
['VoltsPerDivSelect',{D+'VoltsPerDivSelect_RBV':{'attr':'R'}}],
['TimePerDivSelect',{D+'TimePerDivSelect':{'attr':'WE','span':[2,1]}},''],
['VertGainSelect',{D+'VertGainSelect':{'attr':'WE'}}],
['VoltsPerDivSelect',{D+'VoltsPerDivSelect':{'attr':'WE'}}],
['VoltOffset',D+'VoltOffset_RBV'],
['TriggerDelay',{D+'TriggerDelay':{'attr':'WE',**slider(0,10)}},
    D+'TriggerDelay'],
['NoiseAmplitude',{D+'NoiseAmplitude':{'attr':'WE',**slider(0,2)}},
    D+'NoiseAmplitude'],
['UpdateTime',{D+'UpdateTime':{'attr':'WE',**slider(0.1,10)}},D+'UpdateTime'],
['Waveform',{D+'Waveform_RBV':{'attr':'R'}}],
['TimeBase',{D+'TimeBase_RBV':{'attr':'R'}}],
['MaxPoints',{D+'MaxPoints_RBV':{'attr':'R'}}],
['MinValue',{D+'MinValue_RBV':{'attr':'R'}}],
['MaxValue',{D+'MaxValue_RBV':{'attr':'R'}}],
['MeanValue',{D+'MeanValue_RBV':{'attr':'R'}}],
]
