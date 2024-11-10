# pypeto
PyQt-based tabular user interface for designing and implementing control screens for EPICS and LiteServer devices.

Supported:
 - control of EPICS PVs and liteServer PVs,
 - automatic page generation,
 - merged cells, adjustable size of rows and columns, fonts and colors,
 - horizontal and vertical slider widgets,
 - configuration using python,
 - macro substitution from command line: single configuration file can be used for many similar devices,
 - embedding displays of other programs to a range of cells,
 - plotting of selected cells using pvplot,
 - content-driven cell coloring,
 - snapshots: full page can be saved and the selected cells could be restored from the saved snapshots,
 - slicing of vector parameters.

## Tests:

### Control of the litePeakSimulator
The testing requires sattellite modules **litePeakSimulator and pypeto**. They could be installed using pip:

    python3 -m pip install liteserver,pypeto

Start the litePeakSimulator liteserver on localhost if it is not running yet.

    python3 -m liteserver.device.litePeakSimulator -ilo -p9710

Connect to litePeakSimulator from pypeto:

    python3 -m pypeto -aLITE localhost;9710:dev1&

Using pypeto configuration file peakSimulator_pp.py:

    cd github/pypeto
    python3 -m pypeto -f peakSimulator
