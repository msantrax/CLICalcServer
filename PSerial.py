import asyncio
import logging
import math
from asyncio import Task
from queue import SimpleQueue

import numpy as np

import serial_asyncio
import time

import RunSM
from BSP import Signal
import Instrument
from Payload import Payload

logger = logging.getLogger(__name__)



class PSerial(asyncio.Protocol):

    def __init__(self, qlog = None):
        super().__init__()
        self._transport = None
        self.runsm : RunSM
        self.instrument : Instrument

        self.beacon_task:Task = None
        self.beacon_tick = 0.25
        self.beacon_singlerun = True
        self.beacon_queue = SimpleQueue()

        self.payload = Payload()

        # self.x1 = list(range(-20, 21))
        # self.y1 = [(xx**2)+200 for xx in self.x]

        x2 = np.arange(0, 1, 0.025)
        self.y2 = (np.sin(2*np.pi*x2)+2)*10000
        self.y3 = self.y2.astype(int)
        self.bflen = len(self.y3)-2

        self.configLogger(qlog)


    def connection_made(self, transport):
        self.transport = transport
        print('Port opened')
        transport.serial.rts = False  # You can manipulate Serial object via transport
        # transport.write(b'Hello, World!\r\n')  # Write serial data via transport


    def setRunSM(self, rsm):
        self.runsm = rsm

    def setInstrument(self, instru):
        self.instrument = instru


    def sendRawData(self, data):
        # print ('data to send : ', data)
        if isinstance(data, str):
            data = bytes(data, 'utf8')
        self.transport.write(data)


    def data_received(self, data):

        # print('data received : ', repr(data), time.time())
        self.instrument.cmds_queue.put(data)

    def connection_lost(self, exc):
        print('port closed')
        self.transport.loop.stop()

    def pause_writing(self):
        print('pause writing')
        print(self.transport.get_write_buffer_size())

    def resume_writing(self):
        print(self.transport.get_write_buffer_size())
        print('resume writing')


    def configLogger(self, qlog):

        logger.setLevel(logging.DEBUG)
        if qlog is None:
            ch = logging.StreamHandler()
        else:
            ch = logging.StreamHandler(qlog)

        formatter = logging.Formatter('%(msecs).2f - %(levelno)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)


    async def SerialGate(self):

        while True :
            pload = ''
            if not self.beacon_queue.empty() :
                pload = self.beacon_queue.get()
                print ('Sending :', pload )

            s = self.payload.getBytes(None, self.instrument.setra, pload)
            self.sendRawData(s)

            await asyncio.sleep(self.beacon_tick)


    def sendCallback(self, payload):
        sig = Signal(self, verb='TCPCALLBACK', payload = payload)
        self.runsm.registerSignal(sig)


    # STATES ===========================================================================================================

    # SERIAL:SERIALINIT
    def sm_init(self, payload):
        logger.debug("Em Init State")

    # SERIAL:SERIALCONFIG
    def sm_config(self, payload):
        logger.debug("Serial config called")
        self.sendRawData(payload)

    # SERIAL:SERIALWRITE
    def sm_swrite(self, payload):
        logger.info("Serial write called")
        self.sendRawData(payload)

    # ================================================= APP Interface
    # SERIAL:STARTBC
    def sm_enableBeacon(self, payload):

        if self.beacon_task is None:
            # #  First send command do reset measurements buffers
            # s = self.payload.getBytes(None, -1, 'RESETMEAS')
            # self.sendRawData(s)

            loop = self.runsm.getEventLoop()
            self.beacon_task = loop.create_task(self.SerialGate())

            self.sm_sendACK("STARTBC")
            self.sendCallback('Beacon was enabled.')


    # SERIAL:STOPBC
    def sm_disableBeacon(self, payload):
        if self.beacon_task is not None :
            self.beacon_task.cancel()
            self.beacon_task = None

            # sig = Signal(self, verb='SENDACK', payload="STOPBC")
            # self.runsm.registerSignal(sig)
            self.sm_sendACK("STOPBC")

            self.sendCallback('Beacon was stopped.')



    # SERIAL:SENDACK
    def sm_sendACK(self, payload):
        sout = "AUTOACKCALLBACK="+payload

        # if self.beacon_task is not None :
        #     self.sendCallback('Sending ack via queue : '+ sout)
        #     self.beacon_queue.put_nowait(sout)
        # else:
        self.sendCallback('Sending ack via raw : '+ sout)
        s = self.payload.getBytes(None, -1, sout)
        self.sendRawData(s)




    # ======================================= Serial Beacon Internal tests

    # SERIAL:SENDBLOCK
    def sm_sendBlock(self, payload : list):

        # if self.beacon_task is not None :
            #  First send command do reset measurements buffers
            self.beacon_queue.put(self.payload.getBytes(None, -1, 'RESETMEAS'))

            #  Now send the package
            if len(payload) == 2 :
                try :
                    ticknum = int(payload[1])
                except Exception as e:
                    self.sendCallback("Can't convert parameter due: {}".format(e.__repr__()))
                    return
                pkg = self.y3[:ticknum]
            else:
                pkg = self.y3

            for data in pkg :
                pload = self.payload.getBytes(None, data)
                self.beacon_queue.put(pload)

            self.beacon_queue.put(self.payload.getBytes(None, -1, 'ENDMEAS'))
            self.sendCallback("Block Sent ...")
        # else:
        #     self.sendCallback("Can't do it -> Beacon is not enabled")


    # SERIAL:BCTICK
    def sm_setBeaconTick(self, payload):

        if self.beacon_task is not None :
            try :
                btick = float(payload[1])
            except Exception as e :
                self.sendCallback("Can't convert parameter due: {}".format(e.__repr__()))
                return
            self.beacon_tick = btick
            self.sendCallback('Beacon tick was set to {}'.format(btick))
        else:
            self.sendCallback("Can't do it -> Beacon is not enabled")


    # SERIAL:SENDBEACON
    def sm_sendBeacon(self, payload):

        s = self.payload.getBytes()
        self.sendRawData(s)
        # logger.info("Tick was sent...")
        self.sendCallback("Beacon was sent...")


    # SERIAL:SENDTICK
    def sm_sendTick(self, sm_payload : list):

        if len(sm_payload) == 1 :
            s = self.payload.getBytes(None, -1, '')
        else:
            sm_payload.pop(0)
            scmd = ':'.join(sm_payload)
            s = self.payload.getBytes(None, -2, scmd)

        self.sendRawData(s)
        self.sendCallback("TICK was sent...")










    # # SERIAL:RUNT1
    # def sm_runT1(self, sm_payload : list):
    #
    #     if len(sm_payload) == 1 :
    #         s = self.payload.getBytes(None, -1, 'DUMMY1')
    #     else:
    #         sm_payload.pop(0)
    #         scmd = ':'.join(sm_payload)
    #         s = self.payload.getBytes(None, -2, scmd)
    #
    #     self.sendRawData(s)
    #     self.sm_enableBeacon("")
    #
    #     self.sendCallback("RunT1 was sent...")


# async def SLoop(self):
#
#     counter = 0;
#     while True:
#
#         if counter > self.bflen :
#             if self.beacon_singlerun :
#                 self.beacon_task.cancel()
#                 self.beacon_task = None
#                 self.sendCallback('Singlerun Beacon ended')
#             else:
#                 counter = 0
#         else:
#             counter +=1
#
#         s = self.payload.getBytes(None, self.y3[counter])
#         # s = self.payload.getBytes(None, counter )
#         self.sendRawData(s)
#
#         await asyncio.sleep(self.beacon_tick)
