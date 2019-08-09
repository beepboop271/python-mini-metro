#########################################################################################
#
# TimeClass.py
# Class for various ways of keeping track of time
#
# Kevin Qiao - December 28th, 2018
#
#########################################################################################

import time
import math

FORMAT_TOTAL_SECONDS = 1
FORMAT_HH_MM_SS = 0

SECONDS_PER_DAY = 86400
SECONDS_PER_HOUR = 3600

MODE_CURRENT_TIME = 0
MODE_STOPWATCH = 1
MODE_TIMER = 2


class Time(object):
    def __init__(self,
                 timeMode=MODE_CURRENT_TIME,
                 displayFormat=FORMAT_HH_MM_SS,
                 startingTime=0):
        self._displayFormat = displayFormat
        self.timeMode = timeMode

        self._startTime = time.time()

        if self.timeMode == MODE_CURRENT_TIME:
            self.time = time.time()
        elif self.timeMode == MODE_STOPWATCH:
            self.isActive = True  # time is passing
            self._elapsed = startingTime  # necessary for being able to stop and resume times
            self.time = 0
        elif self.timeMode == MODE_TIMER:
            self.countdownAmount = startingTime
            self.isActive = True
            self._elapsed = 0
            self.time = startingTime

        self.hours = 0
        self.minutes = 0
        self.seconds = 0

    def __cmp__(self, other):
        # compare two times
        if int(self.time) > int(other.time):
            return 1
        elif int(self.time) == int(other.time):
            return 0
        else:
            return -1

    def __add__(self, other):
        # add time2's time to this time
        return self.time + other.time

    def multiply(self, factor):
        # multiply this time by a certain value
        return self.time*factor

    def switchToFormat(self, displayFormat):
        # update values for hours, minutes, and seconds
        # everything is already internally stored as total seconds,
        # so no need to do anything for that format
        if displayFormat == FORMAT_HH_MM_SS:
            self.hours = int(math.floor(self.time
                                        % SECONDS_PER_DAY
                                        / SECONDS_PER_HOUR))
            self.minutes = int(math.floor(self.time
                                          % SECONDS_PER_DAY
                                          % SECONDS_PER_HOUR
                                          / 60))
            self.seconds = int(math.floor(self.time
                                          % SECONDS_PER_DAY
                                          % SECONDS_PER_HOUR
                                          % 60))

    def _convertToString(self, value):
        # convert a single part of a time (e.g. hours) to a
        # string, adding a leading 0 if necessary
        if value < 10:
            return "0"+str(value)
        else:
            return str(value)

    def output(self):
        # return a string with the time in its specified format
        if self._displayFormat == FORMAT_TOTAL_SECONDS:
            return str(int(math.floor(self.time)))
        elif self._displayFormat == FORMAT_HH_MM_SS:
            return (self._convertToString(self.hours)+":"
                    + self._convertToString(self.minutes)+":"
                    + self._convertToString(self.seconds))

    def shift(self, direction, amount=1):
        # shift time by an amount positive or negative
        # direction is 1 or -1, increment or decrement
        self.time = self.time + amount*direction

    def tick(self):
        # update times with the real time
        if self.isActive:
            if self._displayFormat == FORMAT_HH_MM_SS:
                self.switchToFormat(FORMAT_HH_MM_SS)

            if self.timeMode == MODE_CURRENT_TIME:
                self.time = time.time()
            elif self.timeMode == MODE_STOPWATCH:
                self.time = self._elapsed + time.time()-self._startTime
            elif self.timeMode == MODE_TIMER:
                self.time = (self.countdownAmount
                             - (self._elapsed+(time.time()-self._startTime)))

    def checkTimer(self, shouldRestart, startTime=None):
        # see if a timer has reached 0, restart it if specified
        if self.timeMode == MODE_TIMER:
            if self.time <= 0:
                if shouldRestart:
                    self.restart(startTime)
                else:
                    self.restart(startTime)
                    if self.isActive:
                        self.toggleActive()
                return True
            else:
                return False

    def restart(self, startTime=None):
        # for timers, change the time back to the supplied startTime or
        # the time given to the timer when it was created
        # for stopwatches, change the time to the supplied startTime or
        # zero
        if self.timeMode == MODE_TIMER:
            if startTime is None:
                self._elapsed = 0
            else:
                self._elapsed = self.countdownAmount-startTime
            self._startTime = time.time()
            self.time = self.countdownAmount
        elif self.timeMode == MODE_STOPWATCH:
            if startTime is None:
                self._elapsed = 0
            else:
                self._elapsed = startTime
            self._startTime = time.time()
            self.time = 0

    def toggleActive(self):
        # pause or unpause the time
        if self.timeMode != MODE_CURRENT_TIME:
            if self.isActive:
                self.tick()
                self._elapsed = self._elapsed+(time.time()-self._startTime)
            else:
                self._startTime = time.time()
        self.isActive = not self.isActive
