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
 - plotting of selected cells using pvploto,
 - content-driven cell coloring,
 - snapshots: full page can be saved and the selected cells could be restored from the saved snapshots,
 - slicing of vector parameters.

## Tests:

Using interactive selection of configurations:

    pypeto

Using pypet configuration file:

    pypet -f tst
