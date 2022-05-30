import asyncio
import serial_asyncio
import time
import logging
from queue import Queue

from pydispatch import dispatcher
from BSP import SMStates, SIGNALS, ENTITIES
from Instrument import Instrument
from RunSM import RunSM


from PSerial import PSerial
from TCPServer import TCPServer

logger = logging.getLogger(__name__)


async def BLoop(ps1):

    counter = 0;
    while True:
        counter +=1
        print ("bloop = ",  counter)
        s = 'Data from BLoop @ {}\n\r'.format(counter)
        ps1.sendRawData(s)
        await asyncio.sleep(5)



def configLogger(qlog):

    logger.setLevel(logging.DEBUG)

    if qlog is None:
        ch = logging.StreamHandler()
    else:
        ch = logging.StreamHandler(qlog)

    formatter = logging.Formatter('%(msecs).2f - %(levelno)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)



class LogQueue:

    def __init__(self, q):
        self.q = q

    def write(self, t):
        t = t.strip('\n')
        self.q.put(t)

    def flush(self):
        pass


if __name__ == '__main__':

    configLogger(None)

    loop = asyncio.get_event_loop()

    tcps = TCPServer()
    server = loop.create_server(lambda: tcps, '127.0.0.1', 8888)
    loop.run_until_complete(server)

    pserial1 = PSerial()
    pserial = serial_asyncio.create_serial_connection(loop, lambda: pserial1, '/dev/ttyUSB1', baudrate=115200)
    loop.run_until_complete(pserial)

    instrument = Instrument()

    sm = RunSM(None, pserial1, tcps, instrument)
    pserial1.setRunSM(sm)
    tcps.setRunSM(sm)
    instrument.setRunSM(sm)
    pserial1.setInstrument(instrument)



    sm.go(loop)


    loop.run_forever()

#
# async def main(loop):
#     reader, writer = await serial_asyncio.open_serial_connection(url='/dev/ttyUSB1', baudrate=115200)
#     print('Streams created')
#     messages = [b'foo\n\r', b'bar\n\r', b'baz\n\r', b'qux\n\r']
#     sent = send(writer, messages)
#     received = recv(reader)
#     await asyncio.wait([sent,received])
#
#
# async def send(w, msgs):
#     for msg in msgs:
#         w.write(msg)
#         print(f'sent: {msg.decode().rstrip()}')
#         # await asyncio.sleep(0.5)
#     w.write(b'DONE\n\r')
#     print('Done sending')
#
#
# async def recv(r):
#     while True:
#         msg = await r.readuntil(b'\n')
#         if msg.rstrip() == b'DONE':
#             print('Done receiving')
#             break
#         print(f'received: {msg.rstrip().decode()}')
#
#

