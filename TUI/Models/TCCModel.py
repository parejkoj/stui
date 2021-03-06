#!/usr/bin/env python
"""An object that models the current state of the TCC.

It contains instance variables that are KeyVariables
or sets of KeyVariables. Most of these are directly associated
with status keywords and a few are ones that I generate.

Thus it is relatively easy to get the current value of a parameter
and it is trivial to register callbacks for when values change
or register ROWdg widgets to automatically display updating values.

2003-03-26 ROwen
2003-04-02 ROwen    Added axis limits and iimScale.
2003-04-04 ROwen    Added all offsets and axis limits.
2003-04-07 ROwen    Bug fix: iimScale was not being dispatched.
2003-04-14 ROwen    Removed unused imports.
2003-04-29 ROwen    Bug fix: RotExists was int, not bool;
    this caused failure in Python 2.3b1.
2003-05-08 ROwen    Modified to use RO.CnvUtil.
2003-05-28 ROwen    Added slewDuration and slewEnd;
                    changed coordSys and rotType to expand the short names
                    used by the TCC to the longer names used internally in TUI.
2003-06-09 ROwen    Modified to get the dispatcher from TUI.Models.TUIModel.
2003-06-11 ROwen    Renamed coordSys -> objSys;
                    modified objSys to use RO.CoordSys constants instead of names;
                    made keyword Inst uppercase.
2003-10-30 ROwen    Added tccPos.
2003-12-03 ROwen    Added guidePrep, guideStart
2004-01-06 ROwen    Modified to use KeyVarFactory.
2004-08-11 ROwen    Modified to allow NaN for the axis status word
                    in ctrlStatusSet (this shows up as "None" as isCurrent=True).
                    Bug fix: was not refreshing rotator status in ctrlStatusSet;
                    modified to optionally refresh it (since it may be missing)
                    using new refreshOptional argument in RO.KeyVariable.KeyVarFactory.
2005-06-03 ROwen    Improved indentation uniformity.
2006-02-21 ROwen    Modified to use new correctly spelled keyword SlewSuperseded.
2006-03-06 ROwen    Added axisCmdState (which supersedes tccStatus).
                    Modified to set rotExists from axisCmdState (instead of tccStatus)
                    and to only set it when the state (or isCurrent) changes.
2007-01-29 ROwen    Added instPos, gimCtr, gimLim, gimScale.
2007-07-25 ROwen    Added tai and utcMinusTAI.
2007-09-28 ROwen    Modified _cnvRotType to raise ValueError instead of KeyError for bad values
                    (because keyword conversion functions should always do that).
                    Modified _cnvObjSys to raise ValueError instead of returning None for bad values.
2008-02-01 ROwen    Fixed rotType; it was always set to None due to an error in _cnvRotType.
2008-03-25 ROwen    Removed obsolete gcFocus; get gmech focus from the gmech actor.
2009-03-27 ROwen    Modified to use new actor dictionary.
2009-04-01 ROwen    Modified to use new opscore.actor.model.Model.
2009-09-11 ROwen    Modified to make test code work.
2010-06-28 ROwen    Removed two unused imports and unused _RotTypeDict (thanks to pychecker).
                    Removed _CoordSysDict and switched to using _cnvObjSys (which was not being used).
                    Removed utc_TAI callback that wasn't doing anything useful.
2015-05-07 ROwen    Added gProbeDict attribute.
2015-06-02 ROwen    Removed a diagnostic print statement.
"""
__all__ = ["Model"]

import sys
from collections import OrderedDict
import opscore.protocols.keys as protoKeys
import opscore.protocols.types as protoTypes
import opscore.actor.keyvar as actorKeyvar
import opscore.actor.model as actorModel
import RO.CoordSys

_theModel = None

def _cnvObjSys(tccName):
    """Converts a coordinate system name from the names used in the TCC keyword ObjSys
    to the RO.CoordSys constants used locally. Case-insensitive.

    Raise KeyError or ValueError if tccName not a valid TCC ObjSys.
    """
    #print "_cnvObjSys(%r)" % tccName
    tuiName = dict(
        icrs = 'ICRS',
        fk5 = 'FK5',
        fk4 = 'FK4',
        gal = 'Galactic',
        geo = 'Geocentric',
        topo = 'Topocentric',
        obs = 'Observed',
        phys = 'Physical',
        mount = 'Mount',
        none = 'None',
    )[tccName.lower()]
    return RO.CoordSys.getSysConst(tuiName)

def _cnvRotType(tccName):
    """Converts a rotation type name from the names used in the TCC keyword RotType
    to the (longer) names used locally. Case-insensitive.

    Raise ValueError if tccName not a valid TCC RotType.
    """
    #print "_cnvRotType(%r)" % (tccName,)
    try:
        return dict(
            obj = 'Object',
            horiz = 'Horizon',
            phys = 'Physical',
            mount = 'Mount',
            none ='None',
        )[tccName.lower()]
    except KeyError:
        raise ValueError()

def Model():
    global _theModel
    if not _theModel:
        _theModel = _Model()
    return _theModel

class _Model (actorModel.Model):
    def __init__(self):
        actorModel.Model.__init__(self, "tcc")
        
        self.axisNames = ("Az", "Alt", "Rot")
        
        # synthetic keywords
        self.rotExists = actorKeyvar.KeyVar(
            self.actor,
            protoKeys.Key("RotExists", protoTypes.Bool("F", "T"), descr="Does this instrument have a rotator?")
        )
        self.ipConfig.addCallback(self._updRotExists)
        
        # csysObj is an RO.CoordSys coordinate system constant
        self.csysObj = None
        self.objSys.addCallback(self._updCSysObj, callNow=True)

        self.gProbeDict = OrderedDict() # dict of guide probe number: GuideProbe object; based on GProbeInfo keyword
        self.gProbeInfo.addCallback(self._updGProbeDict)

    def _updRotExists(self, keyVar):
        isCurrent = keyVar.isCurrent
        ipConfig = keyVar.valueList[0]
        if ipConfig == None:
            rotExists = True
            isCurrent = False
        else:
            rotExists = ipConfig[0].lower() == "t"

        if (rotExists, isCurrent) != (self.rotExists[0], self.rotExists.isCurrent):
            self.rotExists.set((rotExists,), isCurrent=isCurrent)
#         print "%s._updRotExists(%s): rotExists=%s, isCurrent=%s" % \
#             (self.__class__.__name__, keyVar, self.rotExists[0], self.rotExists.isCurrent)

    def _updCSysObj(self, keyVar):
#        print "%s._updCSysObj(%s)" % (self.__class__.__name__, keyVar)
        if keyVar[0] == None:
            self.csysObj = RO.CoordSys.getSysConst(RO.CoordSys.Unknown)
            return

        tccCSysName = str(keyVar[0])
        try:
            self.csysObj = _cnvObjSys(tccCSysName)
        except Exception:
            sys.stderr.write("Unknown coordinate system %r\n" % (tccCSysName,))
            self.csysObj = RO.CoordSys.getSysConst(RO.CoordSys.Unknown)

    def _updGProbeDict(self, keyVar):
        """Call when the TCC outputs gProbeInfo and use to update self.gProbeDict
        """
        if keyVar[0] == None:
            return
        guideProbe = GuideProbe(keyVar[:])
        if guideProbe.number == 1:
            # reset gProbeDict, since the TCC outputs probe information in order
            self.gProbeDict = OrderedDict()
        self.gProbeDict[guideProbe.number] = guideProbe


class GuideProbe(object):
    """Information about one guide probe
    """
    def __init__(self, valueList):
        self.number = valueList[0]
        self.exists = valueList[1]
        self.ctrXY = (valueList[2], valueList[3])
        self.minXY = (valueList[4], valueList[5])
        self.maxXY = (valueList[6], valueList[7])
        self.gp_rot_xy = (valueList[8], valueList[9])
        self.rot_gim_ang = valueList[10]



if __name__ == "__main__":
    import TUI.Base.TestDispatcher
    
    testDispatcher = TUI.Base.TestDispatcher.TestDispatcher("tcc")
    Model()
