import asyncio
import logging
import math
from asyncio import Task
from enum import Enum
from queue import SimpleQueue, Queue
from random import random, randrange
import time


import RunSM
from BSP import Signal
from Payload import Payload

logger = logging.getLogger(__name__)

class CmdState(Enum) :
    FREERUN = 0,
    STARTFLAG = 1,
    ENDFLAG = 2


class Instrument(asyncio.Protocol):

    def __init__(self, qlog = None):
        super().__init__()
        self.runsm : RunSM

        self.instrutask:Task = None

        self.cmds_queue = Queue(128)
        self.cmdstate = CmdState.FREERUN
        self.cmdbuf = bytes()
        self.cmdbufptr = 0
        self.cmdslice = bytes()
        self.trantab = bytes.maketrans(b'\xff\xfe\xf0', b'   ')
        self.cmdtimeout = 20

        self.configLogger(qlog)

        # ================== Data ==========================
        self.setra : int = 0
        self.setrap = 64000
        self.setrai = 10000
        self.setradumpthrs = (((1000000 - self.setrap) / 100) * 12) + self.setrap
        self.setradumpgain = 0.88
        self.setrarsd = 0.1
        self.setraup = False
        self.setracnt = 0.0
        self.setraspeed = 1.0
        self.setralock = True
        self.setrabumpflag = True

        self.setrainitts = 0
        self.setraendts = 0


    def setRunSM(self, rsm):
        self.runsm = rsm
        # self.sm_startInstru("")

    def configLogger(self, qlog):

        logger.setLevel(logging.DEBUG)
        if qlog is None:
            ch = logging.StreamHandler()
        else:
            ch = logging.StreamHandler(qlog)

        formatter = logging.Formatter('%(msecs).2f - %(levelno)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    def sendCallback(self, payload):
        sig = Signal(self, verb='TCPCALLBACK', payload = payload)
        self.runsm.registerSignal(sig)


    def calcSetra (self, mode = None):

        if self.setralock : return

        self.setra = self.setrap + (self.setrai * self.setracnt)
        lvar = randrange(int((self.setra / 100) * self.setrarsd))

        self.setra = int((self.setra - (lvar / 2)) + lvar)



    async def ILoop(self):

        while True:

            if self.cmdtimeout is not -1:
                self.cmdtimeout -= 1
                if self.cmdtimeout == 0:
                    print ('CMD timeout...')
                    self.cmdstate = CmdState.FREERUN
                    self.cmdtimeout = -1
                    self.cmdbuf = bytes()

            # Command on wire interceptor
            while not self.cmds_queue.empty() :
                pload = self.cmds_queue.get()
                ts = time.time()
                # print (f'Cmd : {pload} - {ts}')
                self.cmdbuf += pload

            if len(self.cmdbuf) > 0:
                if self.cmdstate is CmdState.FREERUN :
                    if b'\xff\xfe' in self.cmdbuf:
                        # print ('delim')
                        self.cmdstate = CmdState.STARTFLAG
                        self.cmdtimeout = 10

                elif self.cmdstate is CmdState.STARTFLAG :
                    lidx = self.cmdbuf.find(b'\xff\xf0')
                    if lidx is not -1:
                        self.cmdslice = self.cmdbuf[0:lidx+1]
                        self.cmdbuf = self.cmdbuf[lidx+1:]
                        self.cmdslice = self.cmdslice.translate(self.trantab)
                        self.cmdslice = self.cmdslice.rstrip().lstrip()
                        # print (f'End flag -> cmd = {self.cmdslice}')
                        cmdstr = self.cmdslice.decode('UTF-8', 'ignore')
                        self.cmdParser(cmdstr)
                        self.cmdstate = CmdState.FREERUN
                        self.cmdtimeout = -1

            # Sensor data machine
            if not self.setralock :
                if self.setraup  :
                    # Setra is going UP
                    self.setracnt += self.setraspeed
                    if self.setra >= 1000000 :
                        # if self.setrabumpflag :
                        #     self.setraendts = time.time()
                        #     print ("Rise time = {0:.3f}".format(self.setraendts - self.setrainitts))
                        #     self.setrabumpflag = False
                        self.setracnt -= self.setraspeed
                        self.calcSetra()
                        # print (self.setra)
                    else:
                        self.calcSetra()
                        # print (self.setra)

                else:
                    # Setra DOWN
                    if self.setracnt >= 0.00001 :
                        self.setracnt -= self.setraspeed
                        if self.setra <= self.setradumpthrs :
                            # Is below thrs restore previous cnt value
                            self.setracnt += self.setraspeed

                            self.setraspeed = 1 - (self.setradumpgain**self.setracnt)

                            if (self.setraspeed < 0.0005):
                                self.setracnt= 1
                                self.setraspeed = 1
                                print ("speed < limit")

                            self.setracnt -= self.setraspeed
                            print (f'Dump : {self.setracnt} - {self.setraspeed}')
                            self.calcSetra()
                            # print (self.setra)
                        else:
                            self.setraspeed = 1
                            self.calcSetra()
                            # print (self.setra)
                    else:
                        self.calcSetra()

            await asyncio.sleep(0.1)


    def cmdParser(self, incmd):

        if ' ' in incmd :
            cmds = incmd.split(b' ')
        else :
            cmds = [incmd]

        for cmd in cmds :
            if "=" in cmd:
                tokens = cmd.split('=')
                sig = Signal(self, verb=tokens[0], payload=tokens[1])
            else:
                sig = Signal(self, verb=cmd, payload="")
            self.runsm.registerSignal(sig)


    # INSTRU:SETSETRADUMPGAIN
    def sm_setSetraDumpGain(self, payload):

        value = '0.80'

        if isinstance(payload, str):
            value = payload
        else:
            if len(payload) > 1:
                value = payload[1]

        try:
            self.setradumpgain = float(value)
            self.sendCallback("Setra Dumpgain was set to " + value)
            sig = Signal(self, verb='SENDACK', payload='SETRADUMPGAIN='+value)
            self.runsm.registerSignal(sig)
        except Exception as e :
            self.sendCallback("Can't convert parameter due: {}".format(e.__repr__()))
            sig = Signal(self, verb='SENDACK', payload='SETRADUMPGAIN=ERROR')
            self.runsm.registerSignal(sig)



    # INSTRU:SETSETRADUMPTHRS
    def sm_setSetraDumpThrs(self, payload):

        value = payload[0]
        if len(payload) > 1:
            value = payload[1]

        try:
            self.setradumpthrs = float(value)
            self.sendCallback("Setra Dumpthreshold was set to " + value)
            sig = Signal(self, verb='SENDACK', payload='SETRADUMPTHRS='+value)
            self.runsm.registerSignal(sig)
        except Exception as e :
            self.sendCallback("Can't convert parameter due: {}".format(e.__repr__()))
            sig = Signal(self, verb='SENDACK', payload='SETRADUMPTHRS=ERROR')
            self.runsm.registerSignal(sig)

    # INSTRU:SETVALVES
    def sm_setValves(self, payload):

        ack = 'INVALID'
        if 'BUILDP' in payload :
            self.sm_setInstru('UP')
            self.sendCallback("Valves set to UP")
            ack = "BUILDPACK"
        elif 'PUMP' in payload :
            self.sm_setInstru('DOWN')
            self.sendCallback("Valves set to down")
            ack = "PUMP"
        else:
            logger.info(f'Setvalves(other)')

        sig = Signal(self, verb='SENDACK', payload=ack)
        self.runsm.registerSignal(sig)


    # INSTRU:SETINSTRU
    def sm_setInstru(self, payload):

        lockflag = self.setralock
        self.setralock = True

        if not len(payload) == 1 :

            if "UP" in payload :
                self.setraup = True
                self.setraspeed=1
                self.setrabumpflag = True
                self.sendCallback("Setra is going up")
            elif "DOWN" in payload:
                self.setraup = False
                self.setraspeed=1
                self.setrabumpflag = True
                self.sendCallback("Setra is going down")
            else:
                try :
                    self.setrap = int(payload[0])
                    self.setrai = int((1000000 - self.setrap) / (float(payload[1]) * 10))
                    self.setra = self.setrap
                    self.setracnt = -1
                    self.setrabumpflag = True
                except Exception as e :
                    self.sendCallback("Can't convert parameter due: {}".format(e.__repr__()))
                    return
        else:
            self.setra = self.setrap
            self.setracnt = -1
            self.setrabumpflag = True

        self.setrainitts = time.time()
        self.setralock = lockflag


    # INSTRU:BEACONLOCK
    def sm_beaconLock(self, payload):

        if "ON" in payload :
            sig = Signal(self, verb="STARTBC", payload="")
            self.runsm.registerSignal(sig)
            # self.sendCallback('Beacon is locked')
            return
        elif "OFF" in payload:
            sig = Signal(self, verb="STOPBC", payload="")
            self.runsm.registerSignal(sig)
            # self.sendCallback('Beacon is running')
            return
        else:
            self.sendCallback('Beacon Lock mode must be "ON" or "OFF"')


    # INSTRU:SENSORSLOCK
    def sm_sensorsLock(self, payload):

        if "ON" in payload :
            self.setralock = True
            self.sendCallback('Sensors are locked')
            return
        elif "OFF" in payload:
            self.setralock = False
            self.sendCallback('Sensors unlocked')
            return
        else:
            self.sendCallback('Lock mode must be "ON or "OFF')


    # INSTRU:RESTARTINSTRU
    def sm_restartInstru(self, payload):

        self.sm_stopInstru("")

        self.cmdstate = CmdState.FREERUN
        self.cmds_queue = Queue(128)
        self.cmdbuf = bytes()

        loop = self.runsm.getEventLoop()
        self.setralock = False
        self.setraup = False
        self.setra = self.setrap
        self.setraspeed = 1
        self.setracnt = 1
        self.instrutask = loop.create_task(self.ILoop())

        self.setradumpgain = 0.88

        sig = Signal(self, verb='SENDACK', payload='RESTARTINSTRU')
        self.runsm.registerSignal(sig)

        self.sendCallback('Instrument task was enabled - Sensors unlocked - Beacon is inactive')
        self.sendCallback(f'Dumping Threshold is {self.setradumpthrs}')

    # INSTRU:STOPINSTRU
    def sm_stopInstru(self, payload):
        if self.instrutask is not None :
            sig = Signal(self, verb="STOPBC", payload="")
            self.runsm.registerSignal(sig)
            self.instrutask.cancel()
            self.instrutask = None
            self.setralock = True
            self.sendCallback('Instrument task stopped - sensors are locked - Beacon was cancelled')









# if self.setrabumpflag:
#     self.setraendts = time.time()
#     print ("Fall time = {0:.3f}".format(self.setraendts - self.setrainitts))
#     self.setrabumpflag = False




# else:
# # Setra DOWN
# if self.setracnt >= 0.001 :
#     self.setracnt -= self.setraspeed
#     if self.setra <= self.setradumpthrs :
#         self.setracnt += self.setraspeed
#         self.setraspeed = self.setraspeed / 2
#         if (self.setraspeed < 0.001):
#             self.setracnt= 1
#             self.setraspeed = 1
#         self.setracnt -= self.setraspeed
#         print (self.setracnt)
#         self.calcSetra()
#         # print (self.setra)
#     else:
#         self.setraspeed = 1
#         self.calcSetra()
#         # print (self.setra)
# else:
#     self.calcSetra()
#
# await asyncio.sleep(0.1)


