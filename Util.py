
import logging, re
from datetime import datetime
import time
import locale
import jsons, json


logger = logging.getLogger(__name__)


# mongolink : MongoLink

def getID() -> int:

    p1 = int(time.time()*1000)
    while (int(time.time()*1000) == p1):
        pass
    return int(time.time()*1000)



def configLogger(qlog=None):
    logger.setLevel(logging.DEBUG)

    if qlog is None:
        ch = logging.StreamHandler()
    else:
        ch = logging.StreamHandler(qlog)

    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(msecs).2f - %(levelno)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)




def SDate2JavaMillis (sdate, format='%B %d %H:%M:%S %Y', offset=3600):

    try:
        # dt1 = datetime.strptime(sdate, '%b %d %H:%M:%S %Y')
        locale.setlocale(locale.LC_ALL, 'en_US.UTF8')
        sdate = sdate.replace('\n', "").strip()

        dt1 = datetime.strptime(sdate, format)
    except Exception as e:
        logger.debug('Utils failed to converted sdate {} due {}'.format(sdate, e.__repr__()))
        return 0

    tstamp = int((dt1.timestamp()-offset)*1000)
    return tstamp


def LocatedDate2JavaMillis(sdata):

    # 'BuildPressure(23.802 780.000 751.697)mmHg [VOL Down] December 30 10:27:58 2020'
    mpat=re.compile (r'(January|February|March|April|May|June|July|August|September|October|November|December)(.{17})')
    m = re.search(mpat,sdata)
    if m is None:
        logger.debug('LocateDate unable to find any date in "{}"'.format(sdata))
        return 0
    else:
        joins = m.group()
        tstamp = SDate2JavaMillis(joins)
        return tstamp



def stripTail(sdata, slice):

    sout = sdata[len(sdata)-slice:]
    return sout


def Epoch2SDate(epoch, format='%B %d %H:%M:%S %Y'):

    dt1 = datetime.fromtimestamp(epoch)
    sdate = datetime.strftime(dt1, format)
    return sdate


def get_class( kls ):
    parts = kls.split('.')
    module = ".".join(parts[:-1])
    m = __import__( module )
    for comp in parts[1:]:
        m = getattr(m, comp)
    return m


def pprintJson (obj):

    jobj = json.loads(jsons.dumps(obj))
    dumped = json.dumps(jobj, indent=4)
    return dumped

def saveJson (obj, path):

    try:
        dumped = pprintJson(obj)
        with open(path, 'wt') as fhandle:
            fhandle.write(dumped)
            fhandle.close()
    except Exception as e:
        logger.debug('Failed to save JSON {} due {}'.format(path, e.__repr__()))

def loadJson (path, obj):

    try:
        with open(path, 'rt') as fhandle:
            data = fhandle.read()
            instance = jsons.loads(data, obj)
            fhandle.close()
            return instance
    except Exception as e :
        logger.debug('Failed to load JSON {} due {}'.format(path, e.__repr__()))
        return None



    def int_to_bytes(x: int) -> bytes:
        byt = x.to_bytes((x.bit_length() + 7) // 8, 'big')
        return byt


class StringBuilder(object):

    def __init__(self, val):
        self.store = [val]
        self.indent = '  '

    def __iadd__(self, value):
        self.store.append(value)
        return self

    def appendln(self, value):
        self.store.append(value + '\n\r')
        return self

    def appendind(self, value, indent):
        for _ in range(indent):
            self.store.append(self.indent)
        self.store.append(value)
        return self

    def __str__(self):
        return "".join(self.store)





