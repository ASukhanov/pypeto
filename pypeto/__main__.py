#!/usr/bin/env python3
"""Spreadsheet view of process variables from EPICS or liteServer infrastructure"""
__version__= 'v0.8.0 2025-01-03'# 
import argparse
from . import pypet

pypet.AppName = 'pypeto'
pypet.DefaultNamespace = 'EPICS'

def main():
    parser = argparse.ArgumentParser(description = __doc__
    ,formatter_class=argparse.ArgumentDefaultsHelpFormatter
    ,epilog=f'{pypet.AppName}: {__version__}')
    parser.add_argument('-a','--access', default=pypet.DefaultNamespace, help=\
     'Infrastructure', choices=['EPICS', 'PVA', 'LITE'])
    parser.add_argument('-c','--configDir',
     default = '/operations/app_store/pypet/pages/', help=\
     f'Config directory')
    parser.add_argument('-e','--dont_embed', action='store_true', help=\
     'Do not embed other applications') 
    parser.add_argument('-f','--file', help='Spreadsheet description page (python file with suffix _pp.py')
    parser.add_argument('-g','--geometry', help=\
    'Relative position (x,y) of the window on the screen, e.g. -g0.2,0.5')
    parser.add_argument('-H','--hidemenubar',  action='store_true',  help=\
    'Hide menuBar and statusBar')
    parser.add_argument('-i','--instance', default='', help=\
    'This argument will be available to target pypage as "builtins.pypage_INSTANCE"')
    parser.add_argument('-r','--restore', action='store_true', help=\
    'Restore the parameter setting from a snapshot')
    parser.add_argument('-R','--readonly', action='store_true', help=\
    'Read only mode: modification of parameters is prohibited')
    parser.add_argument('-s','--server', action='store_true', help=\
    'show server variables')
    parser.add_argument('-v', '--verbose', action='count', default=0, help=\
      'Show more log messages (-vv: show even more).')
    parser.add_argument('device', nargs='?', help=\
     ('device (e.g. simple.test), if specified, then a '\
     'temporary configuration will be build'))
    parser.add_argument('-z', '--zoomin', help=\
      'Zoom the application window by a factor, factor must be >= 1')
    pargs = parser.parse_args()
    if pargs.file is not None and pargs.device is not None:
        printe('--file option is not allowed when a device argument is supplied.')
        sys.exit(0)
    pypet.pargs = pargs

    pypet.run()

    print('Application exit')

if __name__ == "__main__":
    main()

