import copy


class SIGNALS(list):
    GEN, \
    LOG, \
    QUIT, \
    TERM_WRITELINE, \
    TERM_SHOWTIMER, \
    TERM_CMD, \
    LOADSTATE, \
    SCRIPT \
    = range(8)


class ENTITIES(list):
    TERM, \
    ROOT, \
    TORNADO, \
    RUNSM \
    = range(4)


class Signal :

    def __init__(self, caller=None , type='LOADSTATE', verb="IDLE", payload=""):
        self.caller = caller
        self.type = type
        self.verb = verb
        self.payload = payload

    def setpayload(self, payload):
        self.payload = payload

    def getpayload(self):
        return self.payload



class SMState :

    def __init__(self, state_name , state_index, realm, func):
        self.sname = state_name
        self.sindex = state_index
        self.realm = realm
        self.func = func
        self.payloads = []

    def push_payload(self, payload):
        self.payloads.append(payload)

    def pop_payload(self):
        if self.payloads :
            return self.payloads.pop()
        else :
            return None

class SMStates:

    def __init__(self):
        self.states = list()
        self.realms = list()
        self.lastindex = 0

    def addState(self, name, index, realm, func ):

        if index == 0:
            self.states.append(SMState(name, self.lastindex, realm, func ))
            self.lastindex +=1
        else:
            self.states.append(SMState(name, index, realm, func ))
            self.lastindex = index

        if realm not in self.realms:
            self.realms.append(realm)

    def sindex (self, name):
        for tstate in self.states:
            if tstate.sname == name:
                return tstate.sindex
        return -1

    def findState(self, name) -> SMState:
        for rstate in self.states:
            if rstate.sname == name:
                return rstate
        return None

    def getNewState(self, name) -> SMState :
        for tstate in self.states:
            if tstate.sname == name:
                return copy.copy(tstate)

    def getPayload(self, index):

        st_payload = self.states[index].pop_payload()
        #self.states[index].payload = ''
        return st_payload



