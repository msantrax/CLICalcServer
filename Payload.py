
from struct import *
from array import array
from collections import namedtuple
import time

class Payload (object):


    beacon_payload_lenght = 120
    tick_payload_lenght = 50


    beacon_payload = array('B', bytes(beacon_payload_lenght))


    # BEACON CONFIG
    ofs_id = 8
    ofs_xducers = ofs_id + 16
    xducers = {  'setra'    : 120856,
                 'manta1'   : -4,
                 'manta2'   : 256,
                 'systemp'  : 1024,
                 'dewar'    : -1
               }

    ofs_dewar = ofs_xducers + 48
    dewar = {
                'pos'       : -2,
                'swup'      : True,
                'swbottom'  : True
            }

    # TICK CONFIG

    def initBeacon(self):

        psensors = array('q',self.xducers.values()).tobytes()

        pack_into( '2s', self.beacon_payload, 0, b'\xff\xfc')
        pack_into( 'q', self.beacon_payload, self.ofs_id, self.getID())

        pack_into( 'c', self.beacon_payload, self.ofs_xducers - 1, b'\xAA')
        pack_into( '40s', self.beacon_payload, self.ofs_xducers, psensors)

        pack_into( 'c', self.beacon_payload, self.ofs_dewar - 1, b'\xAA')
        pack_into( 'q', self.beacon_payload, self.ofs_dewar, self.dewar['pos'])
        pack_into( '?', self.beacon_payload, self.ofs_dewar + 8, self.dewar['swup'])
        pack_into( '?', self.beacon_payload, self.ofs_dewar + 9, self.dewar['swbottom'])

        pack_into( '2s', self.beacon_payload, self.beacon_payload_lenght - 2, b'\xff\xf0')


    def __init__(self):

        self.initBeacon()


    def getBytes(self, id = None, usetick = None, cmd=''):

        if usetick is None :
            if id is None : id = self.getID()
            pack_into( 'q', self.beacon_payload, self.ofs_id, id)
            return self.beacon_payload.tobytes()
        else:
            ldata = len(cmd)
            if (ldata == 0):
                tick_payload = array('B', bytes(13))
                pack_into( '2s', tick_payload, 0, b'\xff\xfa')
                pack_into( 'q', tick_payload, 2, usetick)
                pack_into( 'c', tick_payload, 10, b'\x00')
                pack_into( '2s', tick_payload, 11, b'\xff\xf0')
            else:
                data = bytes(cmd, 'utf8')
                prefix = '{}s'.format(ldata)
                tick_payload = array('B', bytes(13 + ldata))
                pack_into( '2s', tick_payload, 0, b'\xff\xfa')
                pack_into( 'q', tick_payload, 2, usetick)
                pack_into( prefix, tick_payload, 10, data)
                pack_into( '2s', tick_payload, len(tick_payload)-2, b'\xff\xf0')

            return tick_payload.tobytes()

        pass



    def setSensor (self, name='setra', value=-1):
        self.xducers[name] = value
        pack_into( '40s', self.beacon_payload, self.ofs_xducers,
                   array('q', self.xducers.values()).tobytes())
        pack_into( 'c', self.beacon_payload, self.ofs_xducers - 1, b'\xAA')


    def setDewar (self, name='setra', value=1):

        self.dewar[name] = value
        pack_into( 'c', self.beacon_payload, self.ofs_dewar - 1, b'\xAA')
        pack_into( 'q', self.beacon_payload, self.ofs_dewar, self.dewar['pos'])
        pack_into( '?', self.beacon_payload, self.ofs_dewar + 8, self.dewar['swup'])
        pack_into( '?', self.beacon_payload, self.ofs_dewar + 9, self.dewar['swbottom'])


    def getID(self) -> int:

        p1 = int(time.time()*1000)
        while (int(time.time()*1000) == p1):
            pass
        return int(time.time()*1000)
