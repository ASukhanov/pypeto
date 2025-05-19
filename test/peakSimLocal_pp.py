"""Pypet definition for local PeakSimulator"""
import peakSimPlot_pp as module

def PyPage(**_):
    return  module.PyPage(instance='localhost;9701', title='PeakSimLocal')

