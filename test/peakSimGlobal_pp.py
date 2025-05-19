"""Pypet definition for local PeakSimulator"""
import peakSimPlot_pp as module

# Get IP address of the host machine
from liteserver.liteserver import ip_address
ipAddr = ip_address()
print(f'ipAddr: {ipAddr}')

def PyPage(**_):
    return  module.PyPage(instance=f'{ipAddr};9701',title='PeakSimGlobal')

