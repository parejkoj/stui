#!/usr/bin/env python
"""Display status of APOGEE QuickLook Actor
"""
import Tkinter
import RO.Wdg
import QuickLookWdg

_HelpURL = None
WindowName = "Inst.APOGEE QuickLook"

def addWindow(tlSet, visible=False):
    """Create the window for TUI.
    """
    tlSet.createToplevel(
        name = WindowName,
        defGeom = "+434+22",
        visible = visible,
        resizable = False,
        wdgFunc = QuickLookWdg.QuickLookWdg,
    )


if __name__ == '__main__':
    import TUI.Base.TestDispatcher
    
    testDispatcher = TUI.Base.TestDispatcher.TestDispatcher("tcc")
    tuiModel = testDispatcher.tuiModel
    root = tuiModel.tkRoot

    addWindow(tuiModel.tlSet, visible=True)

    tuiModel.reactor.run()
