"""
Display interesting information as a log

Version history:
01/25/2012  change motor position description to resovle a conflict of data types ??
02/12/2013 EM: calculate TAI time for new stui version
04/15/2013 EM:
    * updates self.updateFunSos[1,2] functions: no compare with previous values
    * set callNow=False for these sps functions;
    * boss.motorPosition forced to update after sos update;
    * added mcp.gang position changes
08/22/2013 EM:  updated for mcp.gang position changes in new actorkeys
2013-08-23 RO: updated to use mcpModel.apogeeGangLabelDict
2013-08-26 RO: standardized indentation
2014-09-26 EM: sos actor replace with hartmann actor; added test for hartmann
2014-10-01 EM: survey != eBOSS and boss exposure started, add  mangaDither 
2014-11-17 EM:  Added  cart number to the head of hartmann output using cmds callback; 
       added calculated offset of hartmann;  make clear names of output fields.   
2014-01-15 EM:  type survey type when load cart; refinement of the display of manga dither;
       minor refinement;          
2014-02-14 EM:  fixed bug: display survey info separate from loadCart info (different keywords); 
       clearing previous hartmann output. 
"""
import RO.Wdg
import TUI.Models
import time
import RO.Astro.Tm

encl="";  loadCart=""; gtfState=""; gtfStages=""
gStat="";  gexpTime=""; guiderCorr=""
calState=""; sciState=""

class ScriptClass(object):
    def __init__(self, sr):
        # if True, run in debug-only mode 
        # if False, real time run
        sr.debug = False
        self.name="logFun: "

        self.sr = sr
        sr.master.winfo_toplevel().wm_resizable(True, True)

        width=45
        self.redWarn=RO.Constants.sevError
        self.logWdg = RO.Wdg.LogWdg(master=sr.master,width=width, height =22,)
        self.logWdg.grid(row=0, column=0, sticky="news")
        sr.master.rowconfigure(0, weight=1)
        sr.master.columnconfigure(0, weight=1)
        self.logWdg.text.tag_config("v", foreground="darkviolet")
        self.logWdg.text.tag_config("a", foreground="darkgreen")
        self.logWdg.text.tag_config("c", foreground="Brown")
        
        self.guiderModel = TUI.Models.getModel("guider")
        self.sopModel = TUI.Models.getModel("sop")
        self.hartmannModel = TUI.Models.getModel("hartmann")
        self.apoModel = TUI.Models.getModel("apo")
        self.bossModel = TUI.Models.getModel("boss")
        self.mcpModel = TUI.Models.getModel("mcp")
        self.apogeeModel = TUI.Models.getModel("apogee")
        self.cmdsModel = TUI.Models.getModel("cmds")

        ss="-- Init -- "
        self.logWdg.addMsg(ss)
        
        #enclosure
        self.apoModel.encl25m.addCallback(self.updateEncl,callNow=True)
        
        #guider
        self.guiderModel.cartridgeLoaded.addCallback(self.updateLoadCart,callNow=True)
        self.guiderModel.guideState.addCallback(self.updateGstate, callNow=True)
        self.guiderModel.expTime.addCallback(self.updateGexptime,callNow=True)
        self.guiderModel.guideEnable.addCallback(self.guideCorrFun,callNow=True)
        self.survey0=None; self.survey1=None  
        self.guiderModel.survey.addCallback(self.guideSurveyFun,callNow=True)

        #sop
        self.sopModel.gotoFieldState.addCallback(self.updateGtfStateFun,callNow=False)
      #  self.sopModel.gotoFieldStages.addCallback(self.updateGtfStagesFun,callNow=True)
      #  self.sopModel.doCalibsState.addCallback(self.updateCalStateFun,callNow=True)
      #  self.sopModel.doScienceState.addCallback(self.updateSciStateFun,callNow=True)
        
        #boss exposure
        self.expState=""
        self.bossModel.exposureState.addCallback(self.updateBossState,callNow=True)
        
        #motor position
        self.motPos= [sr.getKeyVar(self.bossModel.motorPosition, ind=i,  defVal=None) 
            for i in range(0,6)]       
        self.bossModel.motorPosition.addCallback(self.motorPosition,callNow=True)
                
        #hartmann:  call for end of hartmann command
        self.startHartmannCollimate=0
        self.cmdsModel.CmdQueued.addCallback(self.hartStart,callNow=False)
        self.cmdsModel.CmdDone.addCallback(self.hartEnd,callNow=False)

        #mcp
        self.FFs=[""]*6   #  self.FFs=self.mcpModel.ffsStatus[:]
        self.FFlamp=self.mcpModel.ffLamp[:]
        self.hgCdLamp=self.mcpModel.hgCdLamp[:]
        self.neLamp=self.mcpModel.neLamp[:]
        self.mcpModel.ffsStatus.addCallback(self.updateFFS,callNow=True)
        self.mcpModel.ffLamp.addCallback(self.updateFFlamp,callNow=True)
        self.mcpModel.hgCdLamp.addCallback(self.updateHgCdLamp,callNow=True)
        self.mcpModel.neLamp.addCallback(self.updateNeLamp,callNow=True)

        #self.apogeeState=self.apogeeModel.exposureWroteSummary[0]
        self.apogeeState=""
        self.apogeeModel.exposureWroteSummary.addCallback(self.updateApogeeExpos, callNow=True)

        self.ngang=""
        self.mcpModel.apogeeGang.addCallback(self.updateMCPGang, callNow=True)
 
        ss= "---- Monitoring ---"
        self.logWdg.addMsg(ss)
        
    def hartStart(self, keyVar):
        if not keyVar.isGenuine: 
            return
        if keyVar[4]=="hartmann" and keyVar[6]=="collimate": 
            self.startHartmannCollimate=keyVar[0]
        elif keyVar[4]=="sop" and  keyVar[6]=="collimateBoss":
            self.startHartmannCollimate=keyVar[0]
        elif keyVar[4]=="hartmann" and  keyVar[6]=="version":
            self.startHartmannCollimate=keyVar[0]
        else:
            pass
                                
    def hartEnd(self, keyVar):
        if not keyVar.isGenuine: 
            return
        if keyVar[0]==self.startHartmannCollimate:
            self.startHartmannCollimate=0
            cart=self.guiderModel.cartridgeLoaded[0]
            ssTime="%s" % (self.getTAITimeStr())
            ss="%s Hartmann collimate output on cart #%s" % (ssTime,cart)
            self.logWdg.addMsg("%s" % (ss), tags="c")
            sr=self.sr
            
            def pprint(ss):
                self.logWdg.addMsg("   %s" % (ss),tags="c")

            #sp1                
            rPiston=self.hartmannModel.r1PistonMove[0]
            rStr=self.hartmannModel.r1MeanOffset[1]            
            bRing=self.hartmannModel.b1RingMove[0]
            bStr=self.hartmannModel.b1MeanOffset[1]
            pprint("%s: offset: r= %s (%s);  b= %s (%s) " % ("sp1", rPiston, rStr, bRing, bStr)) 
            #sp2
            rPiston=self.hartmannModel.r2PistonMove[0]
            rStr=self.hartmannModel.r2MeanOffset[1]            
            bRing=self.hartmannModel.b2RingMove[0]
            bStr=self.hartmannModel.b2MeanOffset[1]
            pprint("%s: offset: r= %s (%s);  b= %s (%s) " % ("sp2", rPiston, rStr, bRing, bStr)) 

            #sp1
            spAvMove=self.hartmannModel.sp1AverageMove[0]
            pprint("%s: pred. move: spAverageMove= %s" % ("sp1",spAvMove))
            #sp2
            spAvMove=self.hartmannModel.sp2AverageMove[0]
            pprint("%s: pred. move: spAverageMove= %s" % ("sp2",spAvMove))

            #sp1
            spRes=self.hartmannModel.sp1Residuals[0:3] 
            spTemp=self.bossModel.sp1Temp[0]
            ss="pred. spResiduals: r= %s, b= %s, txt= %s, spTemp = %s" % (spRes[0],spRes[1],spRes[2], spTemp)
            pprint("%s: %s" %  ("sp1", ss))
            #sp2
            spRes=self.hartmannModel.sp2Residuals[0:3] 
            spTemp=self.bossModel.sp2Temp[0]
            ss="pred. spResiduals: r= %s, b= %s, txt= %s, spTemp = %s" % (spRes[0],spRes[1],spRes[2], spTemp)
            pprint("%s: %s" %  ("sp2", ss))
            
    def updateMCPGang(self, keyVar):
        if keyVar[0] != self.ngang:
            self.ngang=keyVar[0]
            timeStr = self.getTAITimeStr()

            hlp=self.mcpModel.apogeeGangLabelDict.get(self.ngang, "?")
            ss="%s  mcp.gang=%s  (%s)" % (timeStr, self.ngang, hlp)
            self.logWdg.addMsg("%s" % (ss))

    def updateApogeeExpos(self, keyVar):
        if not keyVar.isGenuine: return
        if keyVar[0] != self.apogeeState:
            timeStr = self.getTAITimeStr()
            self.apogeeState=keyVar[0]
            dd0=self.apogeeModel.utrReadState[0]
            dd3=self.apogeeModel.utrReadState[3]
            dth=self.apogeeModel.ditherPosition[1]
            exptp=self.apogeeModel.exposureState[1]
            ss="%s  apogee.expose=%s, %s, %s, %s" % (timeStr, dd0,dd3, dth, exptp)
            self.logWdg.addMsg("%s" % (ss),tags="a")

    def motorPosition(self,keyVar):
        if not keyVar.isGenuine: 
            return
        if keyVar == self.motPos:
            return
        sr=self.sr
        timeStr = self.getTAITimeStr()
        sname="%s,  %s" %  (self.name, timeStr)

        mv=[0]*6
        for i in range(0,6):
            try:
                mv[i] = keyVar[i] - self.motPos[i]
            except: 
                mv[i]=None
        if mv[0:3] != [0]*3:
                ss="%s  sp1.motor.move= %s, %s, %s" %  (timeStr, mv[0], mv[1], mv[2])
                self.logWdg.addMsg("%s" % ss,tags="v")
        if mv[3:6] != [0]*3:
                ss="%s  sp2.motor.move= %s, %s, %s" %  (timeStr, mv[3], mv[4], mv[5])
                self.logWdg.addMsg("%s" % ss,tags="v")                
        self.motPos= list(self.bossModel.motorPosition[0:6])        
#    boss mechStatus  -- Parse the status of each conected mech and report it in keyword form.
#    boss moveColl <spec> [<a>] [<b>] [<c>] -- Adjust the position of the colimator motors.
#    boss moveColl spec=sp1 piston=5

    def getTAITimeStr(self,):
        currPythonSeconds = RO.Astro.Tm.getCurrPySec()
        currTAITuple= time.gmtime(currPythonSeconds - RO.Astro.Tm.getUTCMinusTAI())
        self.taiTimeStr = time.strftime("%H:%M:%S", currTAITuple)
        return self.taiTimeStr

    def getTAITimeStrDate(self,):
        currPythonSeconds = RO.Astro.Tm.getCurrPySec()
        currTAITuple= time.gmtime(currPythonSeconds - RO.Astro.Tm.getUTCMinusTAI())
        self.taiTimeStr = time.strftime("%M:%D:%Y,  %H:%M:%S", currTAITuple)
        return self.taiTimeStr

    def updateBossState(self,keyVar):
        if not keyVar.isGenuine: return
        timeStr = self.getTAITimeStr()
     #   global expState
        if keyVar[0] != self.expState:
            self.expState=keyVar[0]
            expState=self.expState
            expTime =keyVar[1]
            expId=int(self.bossModel.exposureId[0])+2
            self.logWdg.text.tag_config("b", foreground="darkblue")
            self.logWdg.text.tag_config("l", foreground="blue")
            self.logWdg.text.tag_config("br", foreground="brown")
            if expState == "IDLE":
                self.logWdg.addMsg("%s  boss Idle" % (timeStr), tags="b")
            elif expState == "INTEGRATING":
                ss="%s  boss exposure %6.1f, file=%i" % (timeStr, expTime, expId)
                survey= self.guiderModel.survey[0]
                if  "manga"  in survey.lower():
                    dither=self.guiderModel.mangaDither[0]
                    self.logWdg.addMsg("%s, %s" % (ss,dither), tags="l")                    
                else:  
                    self.logWdg.addMsg("%s " % (ss), tags="b")
                ss1="%s  boss.expState= %s,%7.2f, file=%i" % (timeStr, expState, expTime, expId)
            else:
                ss1="%s  boss.expState= %s,%7.2f, file=%i " % (timeStr, expState, expTime, expId)

    def updateEncl(self,keyVar):
        if not keyVar.isGenuine: return
        timeStr = self.getTAITimeStr()
        global encl;
        if keyVar[0] != encl:
            if keyVar[0] > 0: enclM="open"
            else : enclM="closed"
            self.logWdg.addMsg("%s  encl25m : %s;  " % (timeStr,enclM))
            ss="%s  encl25m : %s;  " % (timeStr,enclM)
            encl=keyVar[0]
        else: pass

    def updateLoadCart(self,keyVar):
        if not keyVar.isGenuine: return
        global loadCart
        ct=keyVar[0]; pl=keyVar[1]; sd=keyVar[2]
        if [ct,pl,sd] != loadCart:
            self.updateLoadCartOutput()
            loadCart=[ct,pl,sd]
            self.survey0=None;  self.survey1=None;
        else: pass
    def updateLoadCartOutput(self):
        ll=self.guiderModel.cartridgeLoaded
        ct=ll[0]; pl=ll[1]; sd=ll[2]
        timeStr = self.getTAITimeStr()
        self.logWdg.addMsg("%s"% (40*"-"))
        ss="%s  loadCart: ct=%s, pl=%s;" % (timeStr,str(ct),str(pl))
        self.logWdg.addMsg("%s"% ss)
        
    def guideSurveyFun(self,keyVar):
        if not keyVar.isGenuine: return
        if (self.survey0 != keyVar[0]) or (self.survey1 != keyVar[1]):
            self.survey0=keyVar[0];  self.survey1=keyVar[1]
            self.guideSurveyPrint()
        else: 
            pass
    def guideSurveyPrint(self): 
        timeStr = self.getTAITimeStr()
        ss="%s survey: %s;  lead: %s" % (timeStr, \
                   self.guiderModel.survey[0], self.guiderModel.survey[1])
        self.logWdg.addMsg("%s"% ss)
        
    def updateGstate(self,keyVar):
      if not keyVar.isGenuine:return
      global gStat
      timeStr = self.getTAITimeStr()
      if keyVar[0] != gStat:
        s1=str(keyVar[0])
        if (str(keyVar[0]) == "stopping") or (str(keyVar[0]) == "failed") :
            self.logWdg.addMsg("%s  guider = %s;  " % (timeStr, s1), severity=self.redWarn)
            ss="%s  guider = %s;  " % (timeStr, s1)
        else:
            self.logWdg.addMsg("%s  guider = %s;  " % (timeStr, s1))
            ss="%s  guider = %s;  " % (timeStr, s1)
        gStat=keyVar[0]

    def updateGexptime(self,keyVar):
        if not keyVar.isGenuine: return
        global gexpTime
        if keyVar[0] != gexpTime:
            timeStr = self.getTAITimeStr()
            self.logWdg.addMsg("%s  guider.expTime = %s;  " % (timeStr, str(keyVar[0])))
            ss="%s  guider.expTime = %s;  " % (timeStr, str(keyVar[0]))
            gexpTime=keyVar[0]

    def guideCorrFun(self,keyVar):
        if not keyVar.isGenuine: return
        global guiderCorr
        def sw(v):
            if str(v) == "True":
                s="y"
            else:
                s="n"
            return s
        ax=keyVar[0];  foc=keyVar[1]; sc=keyVar[2]
        if [ax,foc,sc] != guiderCorr:
            timeStr = self.getTAITimeStr()
            self.logWdg.text.tag_config("g", foreground="DarkGrey")
            self.logWdg.addMsg("%s  guider.Corr:  %s %s %s  (ax foc sc);  "
                  % (timeStr, sw(ax),sw(foc),sw(sc)), tags="g")
            ss="%s  guider.Corr:  %s %s %s  (ax foc sc);  " % (timeStr, sw(ax),sw(foc),sw(sc))
            guiderCorr=[ax,foc,sc]

    def updateGtfStateFun(self,keyVar):    # gotoField
        if not keyVar.isGenuine:  return
        global gtfState
        if keyVar[0] != gtfState:
            timeStr = self.getTAITimeStr()
            self.logWdg.addMsg("%s  sop.gotoField = %s;  " % (timeStr,keyVar[0]))
            ss="%s  sop.gotoField = %s;  " % (timeStr,keyVar[0])
            gtfState=keyVar[0]
    def updateGtfStagesFun(self,keyVar):
        if not keyVar.isGenuine:
            return
        global gtfStages
        if keyVar[0] != gtfStages:
            timeStr = self.getTAITimeStr()
            self.logWdg.addMsg("%s  sop.gotoField.stages = %s;  " % (timeStr,keyVar[0]))
            ss="%s  sop.gotoField.stages = %s;  " % (timeStr,keyVar[0])
            gtfStages=keyVar[0]

    def updateCalStateFun(self,keyVar):   # doCalibs
        if not keyVar.isGenuine: return
        global calState
        if keyVar[0] != calState:
            timeStr = self.getTAITimeStr()
            self.logWdg.addMsg("%s  sop.doCalibs = %s;  " % (timeStr,keyVar[0]))
            ss="%s  sop.doCalibs = %s;  " % (timeStr,keyVar[0])
            calState=keyVar[0]

    def updateSciStateFun(self,keyVar):     # doScience
        if not keyVar.isGenuine:  return
        global sciState
        if keyVar[0] != sciState:
            timeStr = self.getTAITimeStr()
            self.logWdg.addMsg("%s  sop.doScience = %s;  " % (timeStr,keyVar[0]))
            ss="%s  sop.doScience = %s;  " % (timeStr,keyVar[0])
            sciState=keyVar[0]

    def updateNeLamp(self,keyVar):
        if not keyVar.isGenuine: return
        ll=[keyVar[0],keyVar[1],keyVar[2],keyVar[3]]
        if ll !=self.neLamp:
            timeStr = self.getTAITimeStr()
            ss="%s  mcp.neLamp = %s%s%s%s"% (timeStr,str(ll[0]),str(ll[1]),str(ll[2]),str(ll[3]))
        #    self.logWdg.addMsg("%s %s" % (self.name,ss))
            self.neLamp=ll

    def updateHgCdLamp(self,keyVar):
        if not keyVar.isGenuine: return
        ll=[keyVar[0],keyVar[1],keyVar[2],keyVar[3]]
        if ll != self.hgCdLamp:
            timeStr = self.getTAITimeStr()
            ss="%s  mcp.hgCdLamp = %s%s%s%s" % (timeStr,str(ll[0]),str(ll[1]),str(ll[2]),str(ll[3]))
         #  self.logWdg.addMsg("%s %s" % (self.name, ss))
            self.hgCdLamp=ll

    def updateFFlamp(self,keyVar):
        if not keyVar.isGenuine: return
        ff=[keyVar[0],keyVar[1],keyVar[2],keyVar[3]]
        if ff != self.FFlamp:
            timeStr = self.getTAITimeStr()
            ss="%s  mcp.FFlamp=%s%s%s%s " % (timeStr,str(ff[0]),str(ff[1]),str(ff[2]),str(ff[3]))
         #   self.logWdg.addMsg("%s %s" % (self.name, ss))
            self.FFlamp=ff

    def updateFFS(self,keyVar):
        if not keyVar.isGenuine:
          return
        ssp=""
        for i in range(0,8):
           p0=str(keyVar[i])[0];  p1=str(keyVar[i])[1]
           if p0=="0" and p1=="0":  sp="?"
           elif p0=="0" and p1=="1": sp="0"
           elif p0=="1" and p1=="0": sp="1"
           else: sp="?"
           ssp=ssp+sp
        timeStr = self.getTAITimeStr()
        if ssp != self.FFs:
             ss="%s  mcp.FFs= %s " % (timeStr,ssp)
            # self.logWdg.addMsg("%s " % (ss))
             self.FFs=ssp

    def stopCalls(self,): 
        self.apoModel.encl25m.removeCallback(self.updateEncl)
        self.guiderModel.cartridgeLoaded.removeCallback(self.updateLoadCart)
        self.sopModel.gotoFieldState.removeCallback(self.updateGtfStateFun)
        self.guiderModel.guideState.removeCallback(self.updateGstate)
        self.guiderModel.expTime.removeCallback(self.updateGexptime)
        self.guiderModel.guideEnable.removeCallback(self.guideCorrFun)
        self.hartmannModel.sp1Residuals.removeCallback(self.updateFunSos1)
        self.hartmannModel.sp2Residuals.removeCallback(self.updateFunSos2)
        self.logWdg.addMsg("-----------")
        self.logWdg.addMsg("      stopped")

    def run(self, sr):
        self.updateLoadCartOutput()
        self.guideSurveyPrint()
        
    def end(self, sr):
        pass
        # self.stopCalls()


if __name__ == "__main__":
    import TUI.Base.TestDispatcher
    pass
