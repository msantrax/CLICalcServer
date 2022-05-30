import asyncio
import inspect
import logging, re
import os
import time
from threading import Thread, Timer
# from pydispatch import dispatcher
from queue import Queue
# from itertools import izip

from BSP import SMStates, SIGNALS, ENTITIES, Signal

import Instrument
from PSerial import PSerial
from TCPServer import TCPServer

logger = logging.getLogger(__name__)


class RunSM:

    def __init__(self, qlog, ps, tcps, instru):

        self.configLogger(qlog)


        self.__running = True

        self.pserial:PSerial = ps
        self.tcpserver:TCPServer = tcps
        self.instrument:Instrument = instru

        self.eventloop:asyncio.EventLoop

        self.timerflag = False
        self.timer_reload = 0
        self.timer_counter = 0

        self.smstates = SMStates()
        self._states_stack1 = list()
        self.signal_queue = Queue()

        self.registerStates(self)
        self.registerStates(self.pserial)
        self.registerStates(self.tcpserver)
        self.registerStates(self.instrument)

        self.callState("IDLE")
        # self.callState("SERIALCONFIG", "Teste do Serial -  VINDO DO INIT\r\n")
        self.callState("CONFIG", b'\x1b[2J')
        self.callState("INIT")


        # logger.info('RunSM configured.')


    def registerStates(self, service):
        members = inspect.getmembers(service)
        for member in members :
            if member[0].startswith('sm_'):
                func = member[1]
                anot = inspect.getcomments(func)
                anot = anot.replace("#", "").replace(" ", "").replace("\n", "")
                trealm, tstate = anot.split(':')
                # logger.info('Found state {}'.format(anot))
                self.smstates.addState(tstate, 0, trealm, func)


    def callState (self, name, payload = None):
        newstate = self.smstates.getNewState(name)
        newstate.push_payload(payload)
        self._states_stack1.append(newstate)

    def hasState(self, name):
        return self.smstates.findState(name)


    def registerSignal(self, signal):
        sig1 = Signal()
        self.signal_queue.put(signal)


    def setEventLoop (self, eloop):
        self.eventloop = eloop

    def getEventLoop (self):
        return self.eventloop


    def go(self, eloop):

        logger.debug("This is the State Machine Manager - > Starting services...")
        self.eventloop = eloop
        t = Thread(target=self.runsm, args=())
        t.start();

    def runsm(self):
        # -
        payload = ''

        while self.__running:
            time.sleep(0.1)
            if self.timer_counter > 0:
                self.timer_counter -= 1
                # if self.timer_counter % 10000 == 0:
                #     dispatcher.send(message=" ", signal=SIGNALS.TERM_SHOWTIMER, sender=ENTITIES.RUNSM)
            else:
                # Execute @ states stack top
                if (self._states_stack1.__len__()) == 0:
                    self.__running = False
                else:
                    # Do signal housekeeping
                    if not self.signal_queue.empty():
                        signal = self.signal_queue.get()
                        if 'LOADSTATE' in signal.type :
                            self.callState ( signal.verb, signal.getpayload())

                    current_state = self._states_stack1.pop()
                    payload = current_state.pop_payload()
                    states_to_load = current_state.func(payload)

                    if states_to_load != None:
                        for lstate in states_to_load:
                            statereturn = self.smstates.getNewState(lstate)
                            # if statereturn != 2 :
                            #     print ('State returned {}'.format(statereturn))
                            self._states_stack1.append(statereturn)

                if self.timer_reload != 0:
                    self.timer_counter = self.timer_reload


    def runsm_dispatcher_script(self, message):
        logger.debug('Signal Script with payload : {}'.format(message))
        self.execute_script(message)

    def runsm_dispatcher_receive(self, message):
        # logger.debug('Signal Received with payload : {}'.format(message))
        self.__signal_queue.put_nowait(message)

    def runsm_dispatcher_quit(self):
        self.__running = False

    def runsm_dispatcher_event(self, message):
        logger.debug('Event Received on RunSM with payload : {}'.format(message))




    def set_timer(self, payload):

        iterpl = iter(payload)
        cmds = dict(zip(iterpl, iterpl));
        # cmds = dict(map(None, *[iterpl] * 2))

        timer_clear = cmds.get("clear")
        timer_value = cmds.get("set")

        if timer_clear is not None:
            self.timer_reload = 0

        elif timer_value is not None:
            self.timer_reload = int(timer_value) * 1000
            self.do_timer();

    def do_timer(self):

        self.tmr = Timer(5.0, self.do_timer)
        self.tmr.start()
        logger.debug("Timer callback !")

    def get_signal_cmd(self, local_signal):

        vb_tokens = re.findall('\'\S*\'', local_signal)
        for token0 in vb_tokens:
            token1 = token0.replace('\'', '')
            token1 = token1.replace(' ', '|')
            token1 = token1.replace('=', '^')
            local_signal = local_signal.replace(token0, token1)

        tokens = re.split(r'[=\s]\s*', local_signal)

        for i in range(0, tokens.__len__()):
            tokens[i] = tokens[i].replace('|', ' ')
            tokens[i] = tokens[i].replace('^', '=')

        payload = tokens[1:]

        return tokens[0].upper(), payload


    def push_cmd(self, signal):
        cmd, payload = self.get_signal_cmd(signal)
        if self.smstates.sindex(cmd) in self._states_lookup:
            pstate = self.smstates.findState(cmd)
            if pstate != None:
                pstate.push_payload(payload)
            self._states_stack.append(self.smstates.sindex(cmd))
            # logger.debug("Valid Signal received : {}".format(cmd))
        else:
            logger.warn("Syntax Error : {}".format(cmd))


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

    # ROOT:INIT
    def sm_init(self, payload):
        pass
        # logger.debug("Em Init State")

    # ROOT:CONFIG
    def sm_config(self, payload):
        logger.debug("Em Config State")
        # self.pserial.sendRawData(payload)

    # ROOT:IDLE
    def sm_idle(self, payload):
        # self._states_stack.append(self.smstates.sindex("IDLE"))
        return ['IDLE']

    # ROOT:EXIT
    def sm_exit(self, payload):
        os._exit(0)









    # def execute_script(self, script_list, rv=True):
    #     #
    #     if rv == True:
    #         for line in reversed(script_list):
    #             self.push_cmd(line)
    #     else:
    #         for line in script_list:
    #             self.push_cmd(line)
    #
    # def load_script(self, payload):
    #     #
    #     cmds = list()
    #     if payload.__len__() == 0:
    #         logger.warning("Load from nothing ?")
    #     else:
    #         scriptpath = payload[0]
    #         logger.info("Loading script from file %s", scriptpath)
    #         file_obj = open(scriptpath, 'r')
    #         # script= ''.join(file_obj.readlines())
    #         lines = (line.strip() for line in file_obj)
    #         for line in lines:
    #             if line != "" and line[0] != "#":
    #                 logger.debug("Pushing cmd : {}".format(line))
    #                 cmds.append(line)
    #
    #         if cmds:
    #             self.execute_script(cmds)
    #         file_obj.close()


    # def eval_test(self, payload):
    #
    #     iterpl = iter(payload)
    #     cmds = dict(zip(iterpl, iterpl));
    #     # cmds = dict(map(None, *[iterpl] * 2))
    #
    #     slst = []
    #     slst.append("Evaluating command : \n\r")
    #     slst.append("=================================================================\n\r")
    #     for key, value in cmds.items():
    #         slst.append("\tKey {:<15} = {}\n\r".format(key, value))
    #
    #     slst.append("=================================================================\n\r")
    #     logger.debug(''.join(slst))





        # self.smstates.addState("LOAD_SCRIPT", 0, "ROOT")
        # self._states_lookup[self.smstates.sindex("LOAD_SCRIPT")] = self.load_script
        #
        # self.smstates.addState("EVAL", 0, "ROOT")
        # self._states_lookup[self.smstates.sindex("EVAL")] = self.eval_test
        #
        # self.smstates.addState("TIMER", 0, "ROOT")
        # self._states_lookup[self.smstates.sindex("TIMER")] = self.set_timer



        # dispatcher.connect(self.runsm_dispatcher_receive, signal=SIGNALS.TERM_CMD, sender=dispatcher.Any)
        # dispatcher.connect(self.runsm_dispatcher_quit, signal=SIGNALS.QUIT, sender=dispatcher.Any)
        # dispatcher.connect(self.runsm_dispatcher_script, signal=SIGNALS.SCRIPT, sender=dispatcher.Any)

        # sitecode.addStates(self.smstates, self._states_lookup)
        # self.tornado.addStates(self.smstates, self._states_lookup)
        # self.topo.addStates(self.smstates, self._states_lookup)
        # self.do_timer()


        # self._states_lookup = {}
        # self._states_lookup[self.smstates.sindex("INIT")] = self.sm_init
        # self._states_lookup[self.smstates.sindex("CONFIG")] = self.sm_config
        # self._states_lookup[self.smstates.sindex("IDLE")] = self.sm_idle

