# pypeto
PyQt-based tabular user interface for designing and implementing control screens for EPICS (CA and PVA) and LiteServer devices.

Features:
 - control of EPICS PVs and LiteServer PVs,
 - tabs: several control pages can be managed from one window,
 - automatic page generation for LiteServer devices,
 - single configuration file can be used for many similar devices,
 - configuration files are python scripts,
 - snapshots: control page can be saved and selectively restored from the saved snapshots,
 - embedding os displays from other programs to a range of cells,
 - plotting of selected cells using pvplot,
 - merged cells, adjustable size of rows and columns, fonts and colors,
 - horizontal and vertical slider widgets,
 - content-driven cell coloring,
 - slicing of vector parameters.

![simScope](./docs/pypeto_simScopePVA.png)

## Examples:
Control of a simulated oscilloscope from EPICS PVAccess infrastructure [link](https://github.com/ASukhanov/p4pex):<br>
`python -m pypeto -c test -f simScopePVA -e`

Control of a peak simulators from LiteServer infrastructure,
for more detalis see ![simScope](./test/README.md):<br>
`python -m pypeto -c test -f peakSimPlot -e`

Several control pages in tabs:<br>
`python -m pypeto -c test -f peakSimLocal peakSimGlobal`

Control of a simulated oscilloscope from EPICS Channel Access infrastructure 
[link](https://epics.anl.gov/modules/soft/asyn/R4-38/asynDriver.html#testAsynPortDriverApp):<br>
`python -m pypeto -c test -fsimScope -e`

See more examples in test directory.

