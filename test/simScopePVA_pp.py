"""Pypet configuration of the EPICS-PVA simulated oscilloscope
""" 
__version__ = 'v3.0.3 2025-05-14'# for pypet v3+

#``````````````````Definitions````````````````````````````````````````````````
# python expressions and functions, used in the spreadsheet

def slider(minValue,maxValue):
    """Definition of the GUI element: horizontal slider with flexible range"""
    return {'widget':'hslider','opLimits':[minValue,maxValue]}

MediumFont = {'color':3*[220], 'font': ['Arial',12]}
_ = ''

#``````````````````PyPage Object``````````````````````````````````````````````
class PyPage():
    def __init__(self, instance="simScope1", title="simScope1"):
        """instance: unique name of the page.
        For EPICS it is usually device prefix 
        """
        print(f'Instantiating Page {instance,title}')

        #``````````Mandatory class members starts here````````````````````````
        self.namespace = 'PVA'
        self.title = title

        #``````````Page attributes, optional`````````````````````````
        #self.page = {**color(240,240,240)}
        #self.page['editable'] = False

        #``````````Definition of columns`````````````````````````````
        self.columns = {
            1:{'width':140,'justify':'right'},
            2:{'width':80},
            3:{'width':70},
            4:{'width':30},
            5:{'width':480},
        }
        #``````````Definition of rows````````````````````````````````
        D = instance+':'
        self.rows = [
#[{'ATTRIBUTES':MediumFont},
#  {f'Parameters of {D}':{'span':[3,1],'justify':'center'}},_,_,
#  {D+'VoltOffset':{'span':[1,16],'widget':'vslider','opLimits':[-10,10]}},
#  {_:{'embed':f'pvplotx P:{D}Waveform_RBV','span':[1,16]}}],
['Run:',{D+'Run':{'attr':'WE'}}, {D+'threads':{'attr':'R'}}],
['MeanValue:',{D+'MeanValue_RBV':{'attr':'R'}}],
]

'''
['VoltsPerDivSelect:',{D+'VoltsPerDivSelect':{'attr':'WE'}}],
['TimePerDivSelect:',{D+'TimePerDivSelect':{'attr':'WE','span':[2,1]}},''],
['VertGainSelect:',{D+'VertGainSelect':{'attr':'WE'}}],
['VoltOffset:',{D+'VoltOffset':{'attr':'WE'}}],
['TriggerDelay:',{D+'TriggerDelay':{'attr':'WE',**slider(0,10)}},
    D+'TriggerDelay'],
['NoiseAmplitude:',{D+'NoiseAmplitude':{'attr':'WE',**slider(0,10)}},
    D+'NoiseAmplitude'],
['UpdateTime:',{D+'UpdateTime':{'attr':'WE',**slider(0.1,10)}},D+'UpdateTime'],
['Waveform:',{D+'Waveform_RBV':{'attr':'R'}}],
['TimeBase:',{D+'TimeBase_RBV':{'attr':'R'}}],
['MaxPoints:',{D+'MaxPoints_RBV':{'attr':'R'}}],
['MinValue:',{D+'MinValue_RBV':{'attr':'R'}}],
['MaxValue:',{D+'MaxValue_RBV':{'attr':'R'}}],
'''

