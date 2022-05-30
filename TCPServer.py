import asyncio
import logging

import serial_asyncio
import time

import RunSM
from BSP import Signal

logger = logging.getLogger(__name__)

class TCPServer(asyncio.Protocol):


    def __init__(self, qlog = None):
        super().__init__()
        self._transport = None
        self.runsm :RunSM

        self.prompt = "opus@virna5:"

        self.configLogger(qlog)


    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        print('Connection from {}'.format(peername))
        self.transport = transport
        self.transport.write(b'\x1b[2J')

        self.sm_showCallback('Welcome to Virna Python  V5.0 @ {}'.format(peername))
        self.runsm.registerSignal(Signal(self, verb='RESTARTINSTRU'))



    def setRunSM(self, rsm):
        self.runsm = rsm


    def data_received(self, data):

        try :
            message = data.decode()
        except Exception as e :
            logger.info("Failed to decode message {} from peer due: {} ".format(data, e.__repr__()))
            return

        # print('Data received: {!r}'.format(message))

        if b'\x1b[A' in data:
            # print('History called')
            self.sm_showCallback("History is {}".format("hist"))

        else:
            message = message.replace(self.prompt, "").replace("\n", "").replace("\r", "")
            message = message.upper().strip()
            tokens = message.split()
            if message == '':
                self.sm_showCallback("\n\r")
            elif self.runsm.hasState(tokens[0]):
                # tokens = tokens[1:]
                sig = Signal(self, verb=tokens[0], payload = tokens)
                self.runsm.registerSignal(sig)
            else:
                self.sm_showCallback("Syntax Error @ {}".format(message))


    def sendRawData(self, data):
        # print ('data to send : ', data)
        if isinstance(data, str):
            data = bytes(data, 'utf8')
        self.transport.write(data)


    def configLogger(self, qlog):

        logger.setLevel(logging.DEBUG)
        if qlog is None:
            ch = logging.StreamHandler()
        else:
            ch = logging.StreamHandler(qlog)

        formatter = logging.Formatter('%(msecs).2f - %(levelno)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    # STATES ===========================================================================================================

    # TCPSV:TCPCALLBACK
    def sm_showCallback(self, payload):

        self.sendRawData(payload)
        if not '\n' in payload:
            self.sendRawData('\n\r')
        self.sendRawData(self.prompt)

