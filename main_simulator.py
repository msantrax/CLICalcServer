
from TestFrame1 import TestFrame1
import cmd, sys
import logging, re

logger = logging.getLogger(__name__)


class Repl(cmd.Cmd):

    intro = 'Welcome to the DataGen.   Type help or ? to list commands.\n'
    prompt = '(Dgen) '
    file = None

    tframe1 : TestFrame1

    def __init__(self, qlog=None):
        cmd.Cmd.__init__(self)
        self.configLogger(qlog)
        self.tframe1 = TestFrame1(None)
        self.tframe1.showStatus()
        #self.tframe1.bokeh2()


        logger.info("Repl started...")

    def do_undo(self, arg):
        'Undo (repeatedly) the last turtle action(s):  UNDO'
    def do_reset(self, arg):
        'Clear the screen and return turtle to center:  RESET'
        # reset()
    def do_bye(self, arg):
        'Stop recording, close the turtle window, and exit:  BYE'
        print('Thank you for using DGen')
        self.close()
        # bye()
        return True

    def do_initcv(self, arg):
        # logger.info("init_cv called ")
        self.tframe1.showStatus()




    # ----- record and playback -----
    def do_record(self, arg):
        'Save future commands to filename:  RECORD rose.cmd'
        self.file = open(arg, 'w')
    def do_playback(self, arg):
        'Playback commands from a file:  PLAYBACK rose.cmd'
        self.close()
        with open(arg) as f:
            self.cmdqueue.extend(f.read().splitlines())
    def precmd(self, line):
        line = line.lower()
        if self.file and 'playback' not in line:
            print(line, file=self.file)
        return line
    def close(self):
        if self.file:
            self.file.close()
            self.file = None


    def configLogger(self, qlog=None):

        logger.setLevel(logging.DEBUG)

        if qlog is None:
            ch = logging.StreamHandler()
        else:
            ch = logging.StreamHandler(qlog)

        formatter = logging.Formatter('%(msecs).2f - %(levelno)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)


def parse(arg):
    'Convert a series of zero or more numbers to an argument tuple'
    return tuple(map(int, arg.split()))






if __name__ == '__main__':
    # tframe1 = TestFrame1(None)
    Repl().cmdloop()







