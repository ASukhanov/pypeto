"""Pypet definition for local PeakSimulator"""
import peakSimPlot_pp as module

def PyPage(**_):
    return  module.PyPage(instance='192.168.27.102;9701',title='PeakSimPi09')

