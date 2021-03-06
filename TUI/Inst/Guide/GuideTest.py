#!/usr/bin/env python
"""Guide test code that crudely substitutes for the hub

To do:
- make the whole thing an object

History:
2005-01-31 ROwen
2005-02-08 ROwen    Updated for PyGuide 1.2.
2005-02-22 ROwen    Fixed centroid output (had not been updated to match new star format).
2005-03-25 ROwen    Updated for new keywords. Stopped using float("nan").
2005-03-28 ROwen    Updated again for improved files and star keywords.
2005-04-11 ROwen    Modified for GCamModel->GuideModel.
                    Adjusted for 2005-04-01 findStars.
2005-04-12 ROwen    Made safe to import even when not being used.
2005-04-18 ROwen    Improved test code to increment cmID and offered a separate
                    optional init function before run (renamed from start).
2005-05-20 ROwen    Modified for PyGuide 1.3.
                    Stopped outputting obsolete centroidPyGuideConfig keyword.
                    Added _Verbosity to set verbosity of PyGuide calls.
                    Modified to send thesh to PyGuide.centroid
                    Modified to output xxDefxx keywords at startup.
2005-05-25 ROwen    Added the requirement to specify actor.
2005-06-13 ROwen    Added runDownload for a more realistic way to get lots of images.
2005-06-16 ROwen    Modified to import (with warnings) if PyGuide missing.
2005-06-17 ROwen    Bug fix: init failed if no PyGuide.
2005-06-22 ROwen    Changed init argument doFTP to isLocal.
                    Modified to set GuideWdg._LocalMode and _HistLength.
2005-06-24 ROwen    Added nFiles argument to runLocalFiles.
2005-07-08 ROwen    Modified for http download: changed imageRoot to httpRoot.
2005-07-14 ROwen    Removed isLocal mode.
2006-04-13 ROwen    runDownload: added imPrefix and removed maskNum argument.
                    nextDownload: removed maskNum.
2006-05-24 ROwen    setParams: added mode, removed count.
2007-04-24 ROwen    Removed unused import of numarray.
2009-03-31 ROwen    Modified to use twisted timers.
2009-07-15 ROwen    Modified to work with sdss code.
2009-11-10 ROwen    Removed obsolete code (leaving almost nothing).
2010-01-25 ROwen    Added guideState and two gcamera keywords.
2010-08-25 ROwen    Added gprobes data.
2013-03-27 ROwen    Removed obsolete gprobes keyword and added enabled and above/below focus bits to gprobeBits
2014-10-23 ROwen    Added mangaDither and decenter
"""
import TUI.Base.TestDispatcher

testDispatcher = TUI.Base.TestDispatcher.TestDispatcher("guider")
tuiModel = testDispatcher.tuiModel

GuiderMainDataList = (
    "expTime = 5.0",
    "gprobeBits=0x4,0xC,0x4,0x14,0x4,0xC,0x4,0x14,0x4,0x4,0x4,0x4,0x4,0x4,0x14,0xC,0x2",
    "guideEnable=True, True, False",
    "guideState=on",
    "mangaDither=C",
    "decenter=124, enabled, 1.23, -0.24, 55.4, 25.3, 1.000007",
)

GCameraMainDataList = (
    "exposureState = integrating, 9, 10",
    "simulating = On, /foo/bar/images, 5",
    "cooler = -40.0, -40.2, 50.4, 76.5, 0, Correcting",
)

GuiderDataSet = (
    ("guideState=on", "mangaDither=N",),
    ("mangaDither=C", "decenter=125, enabled, 0.22, -2.45, 1.5, 2.3, 0.99999"),
    ("guideState=stopping", "decenter=126, disabled, -3.33, 0.24, 5.4, 25.3, 1.000009",),
    ("guideState=off",),
    ("guideState=failed",),
)

def start():
    testDispatcher.dispatch(GuiderMainDataList)
    testDispatcher.dispatch(GCameraMainDataList, actor="gcamera")
    testDispatcher.runDataSet(GuiderDataSet)

