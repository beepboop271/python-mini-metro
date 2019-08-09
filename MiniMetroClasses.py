###################################################################################################
#
# MiniMetroClasses.py
# Contains classes and some functions and constants for Mini Metro
#
# Kevin Qiao - January 20, 2019
#
###################################################################################################

import random
import copy
import math
import pygame
import pygame.gfxdraw
import TimeClass as Time
pygame.init()

COLOURS = {"background": (48, 48, 48),
           "river": (83, 124, 144),
           "blackInside": (45, 45, 45),
           "whiteOutline": (217, 217, 217),
           "lines": ((254, 201, 9),
                     (230, 80, 40),
                     (42, 96, 157),
                     (59, 161, 210),
                     (55, 135, 48),
                     (242, 145, 173),
                     (140, 84, 42))}

CIRCLE = 0
TRIANGLE = 1
SQUARE = 2
DIAMOND = 3
TRAPEZOID = 4
PARLLELOGRAM = 5
PENTAGON = 6
HEXAGON = 7
STAR = 8

CARRIAGE = 0
LINE = 1
TRAIN = 2
TUNNEL = 3

# units are in world pixels
STOP_REMOVAL_DISTANCE = 10  # distance mouse must be to a stop to remove it from a line
STOP_ADDITION_DISTANCE = 5  # distance mouse must be to a stop to add it to a line
ENDPOINT_SEGMENT_DISTANCE = 60  # distance mouse must be to grab an endpoint segment
STOP_DISTANCE = 100  # minimum spacing between any two given stops

LOSE_DURATION = 45  # amount of time stop has to overcrowd to cause the game to be over

RESOURCE_GAIN_DELAY = 90  # time between each resource gain event


def _isValidSpawn(x, y, stops, mapSurface):
    # Returns True or False depending on whether or not the given
    # point (x, y) is a valid stop location on the given map
    if tuple(mapSurface.get_at((x, y))[:3]) == COLOURS.get("river"):
        return False
    for stop in stops:
        if stop.withinRadius(x, y, STOP_DISTANCE):
            return False
    return True


def findDistance((x1, y1), (x2, y2)):
    """ ((num, num), (num, num)) -> float
        Returns the shortest distance between the two points
        (x1, y1) and (x2, y2).
    """
    return math.sqrt((x1-x2)**2 + (y1-y2)**2)


def getViewCoords(x, y, offset):
    """ (num, num, list) -> (num, num)
        Returns (x, y) the point in view space that corresponds to the
        given coordinates "x" and "y" in world space, using the offset
        provided.
        Offset is [[world scale x, world scale y],
                   [world translation x, world translation y]]
    """
    return [(x-offset[1][0])*offset[0][0], (y-offset[1][1])*offset[0][1]]


class World(object):
    def __init__(self, mapSurface, stopSize=30, passengerSize=10):
        self.stops = []
        self.lines = []
        self.trains = []
        self.carriages = []
        self.trainSpeed = 1
        self._map = mapSurface
        self.stopSize = stopSize
        self.passengerSize = passengerSize
        self.width = mapSurface.get_width()
        self.height = mapSurface.get_height()
        self.validStopDistanceX = 250
        self.validStopDistanceY = int(self.validStopDistanceX
                                      * (float(self.height)/self.width))
        # give the player some starting equipment
        self.resources = [1, 2, 3, 3]
        self.totalTunnels = self.resources[TUNNEL]
        self.iconHitboxes = [None]*4
        self.passengersMoved = 0

    def addRandomStop(self, shape, stopSurfaces):
        """ (int, list) -> bool, bool
            Creates a stop of the given shape at a random but valid
            location on the map.
            Returns two booleans: the first dictates if the map area
            was expanded, and the second tells whether or not the
            maximum map area has been reached.
        """
        # makes shape in random valid location
        count = 0
        x = random.randint(self.width/2-self.validStopDistanceX+self.passengerSize*6,
                           self.width/2+self.validStopDistanceX-self.passengerSize*6)
        y = random.randint(self.height/2-self.validStopDistanceY+self.stopSize*3,
                           self.height/2+self.validStopDistanceY-self.stopSize*3)
        # try 15 times to generate a valid stop
        while (not _isValidSpawn(x, y, self.stops, self._map)) and count < 15:
            x = random.randint(self.width/2-self.validStopDistanceX+self.passengerSize*6,
                               self.width/2+self.validStopDistanceX-self.passengerSize*6)
            y = random.randint(self.height/2-self.validStopDistanceY+self.stopSize*3,
                               self.height/2+self.validStopDistanceY-self.stopSize*3)
            count = count+1
        if count < 15:
            timer = Time.Time(Time.MODE_STOPWATCH, Time.FORMAT_TOTAL_SECONDS, 0)
            self.stops.append(Stop(x, y, shape, stopSurfaces, timer))
            return False, False
        # if a stop isn't generated within 15 tries,
        # try to expand the generation area
        else:
            self.validStopDistanceX = self.validStopDistanceX+50
            if self.validStopDistanceX >= self.width/2:
                self.validStopDistanceX = self.width/2
                self.validStopDistanceY = int(self.validStopDistanceX
                                              * (float(self.height)/self.width))
                return False, True
            else:
                self.validStopDistanceY = int(self.validStopDistanceX
                                              * (float(self.height)/self.width))
                return True, False

    def switchRandomStop(self, shapeRange, existingStops, worldSurface):
        """ (int) -> int
            Picks a random stop (circle, triangle, or square) and
            changes the shape of the stop to a special one.
            Returns -1 if no conversion was made or the shape the stop
            was converted to as an int.
        """
        # try 10 times to get a random shape that isn't used
        count = 0
        newShape = random.choice(shapeRange)
        while newShape in existingStops and count < 10:
            newShape = random.choice(shapeRange)
            count = count+1
        if count == 10:
            return -1
        # try 10 times to find a non-special stop to switch
        count = 0
        newStop = self.stops[random.randint(0, len(self.stops)-1)]
        while newStop.shape > SQUARE and count < 10:
            newStop = self.stops[random.randint(0, len(self.stops)-1)]
            count = count+1
        if count == 10:
            return -1
        else:
            newStop.shape = newShape
            for line in newStop.lines:
                line.update(worldSurface, False)
            return newShape

    def createNewLine(self, mouseObject, stop):
        """ (MousePosition, Stop) -> int
            Creates a new line with a starting mouse segment anchored
            at the provided stop and MousePosition object.
            Returns the index of the line.
        """
        availableLines = [0, 1, 2, 3, 4, 5, 6]
        for line in self.lines:
            availableLines.remove(line.LINE_NUMBER)
        if len(availableLines) == 0:
            return -1
        newLine = availableLines[0]
        line = Line(newLine)
        self.lines.insert(newLine, line)
        line.isMoving = True
        line.createMouseSegments(-1, mouseObject, None, stop)
        return newLine

    def getClickedLine(self, colour):
        """ (tuple) -> int
            "colour" is a tuple of length 3 (R, G, B).
            Returns the index of the line with the colour given, or
            -1 if no line has that colour.
        """
        # there must be a check to see if the colour is in the line list first because
        # the Tuple.index method throws an exception if it is not in it
        if colour in COLOURS.get("lines"):
            return COLOURS.get("lines").index(colour)
        else:
            return -1

    def getSegmentFromWorld(self, mouseObject, offset):
        # as opposed to getting a segment from a specific line
        clickedSegments = []
        for i in range(len(self.lines)):
            for j in range(len(self.lines[i].segments)):
                if self.lines[i].segments[j].rect.collidepoint(mouseObject.getView(offset)):
                    clickedSegments.append([i, j])
        if len(clickedSegments) > 1:
            lowestDistance = [1000000, [-1, -1]]
            for segment in clickedSegments:
                distanceScore = (self.lines[segment[0]].segments[segment[1]]
                                 .getDistanceScore(mouseObject.getWorld()))
                if distanceScore < lowestDistance[0]:
                    lowestDistance = [distanceScore, segment]
            return lowestDistance[1]
        elif len(clickedSegments) == 1:
            return clickedSegments[0]
        else:
            return -1

    def getLineByHitbox(self, mouseObject, offset):
        # as opposed to getting the clicked line by colour
        segment = self.getSegmentFromWorld(mouseObject, offset)
        if segment != -1:
            return segment[0]
        else:
            return -1

    def getClickedIcon(self, mouseView):
        for i in range(len(self.iconHitboxes)):
            if self.iconHitboxes[i].collidepoint(mouseView):
                return i
        return -1

    def getClickedTrainLine(self, colour):
        # get the line that the clicked train is on
        for i in range(len(self.lines)):
            if colour == self.lines[i].BRIGHTER_COLOUR:
                return i
        return -1

    def getClickedTrain(self, mouseView, line):
        # get a train or carriage on a line
        trains = self.lines[line].trains
        for train in trains:
            if train.rect.collidepoint(mouseView):
                return train, "train"
            for carriage in train.carriages:
                if carriage.rect.collidepoint(mouseView):
                    return carriage, "carriage"
        for abandonedLine in self.lines[line].abandonedChildren:
            for train in abandonedLine.trains:
                if train.rect.collidepoint(mouseView):
                    return train, "train"
                for carriage in train.carriages:
                    if carriage.rect.collidepoint(mouseView):
                        return carriage, "carriage"
        return -1

    def removeLine(self, index):
        # remove a line and everything on it
        childLines = self.lines[index].abandonedChildren
        for i in range(len(childLines)-1, -1, -1):
            for j in range(len(childLines[i].trains)-1, -1, -1):
                for carriage in childLines[i].trains[j].carriages:
                    self.resources[CARRIAGE] = self.resources[CARRIAGE]+1
                    self.carriages.remove(carriage)
                    childLines[i].trains[j].carriages.remove(carriage)
                    carriage.remove()
                self.trains.remove(childLines[i].trains[j])
                self.resources[TRAIN] = self.resources[TRAIN]+1
                childLines[i].trains[j].remove()
                childLines[i].trains.pop(j)
            self.lines[index].abandonedChildren.pop(i)
        self.lines.pop(index)
        self.resources[LINE] = self.resources[LINE]+1


class Stop(object):
    def __init__(self, x, y, shape, surfaces, timer):
        self._STOP_SURFACES = surfaces
        self.X = x
        self.Y = y
        self.shape = shape
        self.passengers = []
        self.timer = timer
        self.usingTimer = False
        self.timer.toggleActive()
        self.trains = []  # trains stopped at the stop
        self.lines = []  # lines that pass through this stop

    def __eq__(self, other):
        # overrided definition of Stop == Stop
        # if the coordinates of both stops are equal, the
        # stops are considered equal
        return self.X == other.X and self.Y == other.Y

    def withinRadius(self, x, y, radius):
        """ (int, int, int) -> bool
            Returns if the point at (x, y) is less than "radius" pixels
            away (in world space) from the stop "self"
        """
        return (x-self.X)**2 + (y-self.Y)**2 < radius**2

    def getPosition(self):
        """ (None) -> num, num
            Returns the world position of the stop as a tuple (x, y).
        """
        return self.X, self.Y

    def draw(self, targetSurface, size, passengerSize, offset):
        """ (pygame.Surface, int, int, list) -> None
            Draws the stop "self" onto "targetSurface", as well as any
            passengers at that stop.
            Offset is a list containing the scale for x and y as well
            as the translation for x and y required to transform world
            coordinates into view coordinates.
        """
        # convert the world coordinates of the stop to view coordinates
        stopView = getViewCoords(self.X, self.Y, offset)
        stopView[0] = stopView[0]-size/2
        stopView[1] = stopView[1]-size/2
        targetSurface.blit(self._STOP_SURFACES[self.shape], stopView)
        if self.usingTimer:
            self.timer.tick()
            width = self._STOP_SURFACES[self.shape].get_width()*2
            stop = pygame.Surface((width, width))
            stop.blit(self._STOP_SURFACES[self.shape], (width/2-size/2, width/2-size/2))
            # draw the red fill the changes the stop colour
            # the pygame.draw.arc() function leaves some pixels empty which causes it to look
            # bad, but there is no other (easy and simple) way to do this
            pie = pygame.Surface((width, width))
            pygame.draw.arc(pie,
                            (255, 45, 45),
                            pie.get_rect(),
                            math.pi/2.0,
                            math.pi/2.0+(2*math.pi*(max(self.timer.time, 0)/LOSE_DURATION)),
                            width/2)
            stop.blit(pie, (0, 0), None, pygame.BLEND_MIN)
            stop.set_colorkey((0, 0, 0))
            targetSurface.blit(stop, (stopView[0]-size/2, stopView[1]-size/2))
            # draw the outer ring
            pygame.gfxdraw.arc(targetSurface,
                               int(stopView[0]+size/2),
                               int(stopView[1]+size/2),
                               width/2,
                               max(int(-90-360*(max(self.timer.time, 0)/LOSE_DURATION)), -449),
                               -90,
                               (255, 0, 0))
        for i in range(len(self.passengers)):
            # draw the passenger to the side of the stop, in rows of 6
            # (so if a 7th passenger spawns, it'll appear in another row)
            self.passengers[i].draw(targetSurface,
                                    passengerSize,
                                    stopView[0] + size*1.4 + (i % 6)*passengerSize,
                                    stopView[1] + (i/6)*passengerSize)

    def addRandomPassenger(self, shapes, passengerSurfaces):
        """ (int, list) -> None
            Creates a passenger of the given shape (given by an
            integer 0-8) at this stop.
        """
        shapes = list(shapes)
        shapes.remove(self.shape)
        self.passengers.append(Passenger(random.choice(shapes), passengerSurfaces))

    def processTrain(self, train, trainsToMove):
        # load or unload passengers that can move
        for carriage in train.carriages:
            if carriage.movingClone in trainsToMove:
                return self.movePassenger(train, True)
        if train in trainsToMove or train.movingClone in trainsToMove:
            return self.movePassenger(train, True)
        else:
            return self.movePassenger(train, False)

    def isValidTransfer(self, path, transfer):
        # if the transfer's line has already been visited,
        # ignore it
        for step in path:
            if transfer[1] == step[1]:
                return False
        return True

    def findPath(self, currentLine, passenger, path):
        # recursively finds the first path to the target stop
        # not the fastest path but it doesn't matter
        # for a game like this
        if passenger.SHAPE in currentLine.stopNums:
            index = currentLine.stopNums.index(passenger.SHAPE)
            path.append([index, currentLine])
            return path
        else:
            for transfer in currentLine.transfers:
                if self.isValidTransfer(path, transfer):
                    newPath = list(path)
                    newPath.append(transfer)
                    foundPath = self.findPath(transfer[1], passenger, newPath)
                    if foundPath != -1:
                        return foundPath
        return -1

    def findValidPassenger(self, train):
        for i in range(len(self.passengers)):
            # first, see if the stop it wants to go to
            # is reachable by train without the train needing
            # to reverse direction
            foundPath = len(self.passengers[i].path) > 0
            if (train.direction == 1
                    and (self.passengers[i].SHAPE in train.line.stopNums[train.segmentNum:]
                         or (foundPath
                             and self.passengers[i].path[1][0] > train.segmentNum
                             and train in self.passengers[i].path[0][1].trains))):
                return i
            elif (train.direction == -1
                  and (self.passengers[i].SHAPE in train.line.stopNums[:train.segmentNum+1]
                       or (foundPath
                           and self.passengers[i].path[1][0] <= train.segmentNum
                           and train in self.passengers[i].path[0][1].trains))):
                return i
            # then, check all lines directly accessible to the passenger/stop
            if not foundPath:
                for line in self.lines:
                    if self.passengers[i].SHAPE in line.stopNums:
                        foundPath = True  # do nothing, wait until the right train comes
            # finally, if all else fails, find a path along the whole network
            if not foundPath:
                for line in self.lines:
                    path = [[-1, line]]
                    path = self.findPath(line, self.passengers[i], list(path))
                    if path != -1:
                        self.passengers[i].path = path
                        if (train.direction == 1
                                and self.passengers[i].path[1][0] > train.segmentNum):
                            return i
                        elif (train.direction == -1
                              and self.passengers[i].path[1][0] <= train.segmentNum):
                            return i
        return -1

    def movePassenger(self, train, shouldUnload):
        # move a single passenger
        index = -1
        for i in range(len(train.passengers)):
            if (self.shape == train.passengers[i].SHAPE
                    or (len(train.passengers[i].path) > 0
                        and train.passengers[i].path[1][1] in self.lines)):
                index = i
        if index > -1:
            # if a passenger was found that can be moved off the train, move it
            if len(train.passengers[index].path) > 0:
                train.passengers[index].path.pop(0)
                if train.passengers[index].path[-1][1] in self.lines:
                    train.passengers[index].path = []
                self.passengers.append(train.passengers.pop(index))
                return 0
            else:
                train.passengers.pop(index)
                return 1  # one passenger has been moved
        elif shouldUnload:
            # if the train or carriage should be moved to another line, it
            # can't have any passengers on it, so unload move them off
            self.passengers.append(train.passengers.pop())
            return 0
        index = self.findValidPassenger(train)
        # if a passenger was found that can be moved onto the train, move it
        if (index > -1
                and len(train.passengers) < (len(train.carriages)*6)+6):
            train.passengers.append(self.passengers.pop(index))
        else:
            # no passengers can be moved
            if train.setMoving(True):
                self.trains.remove(train)
        return 0


class Passenger(object):
    def __init__(self, shape, surfaces):
        self._PASSENGER_SURFACES = surfaces
        self.SHAPE = shape
        self.path = []

    def draw(self, targetSurface, size, x, y):
        centerX = x - size/2
        centerY = y - size/2
        targetSurface.blit(self._PASSENGER_SURFACES[self.SHAPE],
                           (centerX, centerY))


class Line(object):
    def __init__(self, lineNumber):
        # lineNumber is 0-6 (inclusive, for 7 lines maximum)
        self.LINE_NUMBER = lineNumber
        self._COLOUR = COLOURS.get("lines")[lineNumber]
        self.BRIGHTER_COLOUR = (min(self._COLOUR[0]+50, 255),
                                min(self._COLOUR[1]+50, 255),
                                min(self._COLOUR[2]+50, 255))
        self.DARKER_COLOUR = (max(self._COLOUR[0]-50, 0),
                              max(self._COLOUR[1]-50, 0),
                              max(self._COLOUR[2]-50, 0))

        # holds lines that were split from this parent line
        # and are considered "abandoned". all trains on a
        # segment that was split into a child line get
        # moved to the child line and the moment they leave,
        # the abandoned line is deleted
        self.abandonedChildren = []
        self.isAbandoned = False

        self.segments = []
        self.stopNums = []  # numeric values of the shape of stops on the line
        self.transfers = []  # for passenger pathfinding (along with stopNums)

        # temporary list used to edit the line before commiting changes
        self.tempSegments = []
        self._newStops = []
        self._removedStops = []
        self._abandonedSegments = []
        self.mouseSegments = []
        self.isMoving = False  # if the mouse is moving the line

        self.trains = []

    def draw(self, targetSurface, width, offset):
        for segment in self.tempSegments+self.segments:
            if segment.isAbandoned:
                segment.draw(targetSurface, self.DARKER_COLOUR, width, offset)
            else:
                segment.draw(targetSurface, self._COLOUR, width, offset)
        if self.isMoving:
            for mouseSegment in self.mouseSegments:
                mouseSegment.draw(targetSurface, self.BRIGHTER_COLOUR, offset)

    def _abandonSegment(self, segmentIndex):
        self.tempSegments[segmentIndex].isAbandoned = True
        self._abandonedSegments.append(self.tempSegments[segmentIndex])

    def getClickedSegment(self, mouseView, mouseObject):
        # determine which segment of the line is being clicked on
        intersectingSegments = []
        for i in range(len(self.segments)):
            if self.segments[i].rect.collidepoint(mouseView):
                intersectingSegments.append(i)
        # if only one approximate rectangle is clicked,
        # pick that segment. if multiple approximate rectangles
        # are clicked, use a more precise detection:
        if len(intersectingSegments) > 1:
            # holds the lowest score and the index of
            # the segment with that score
            lowestDistance = [10000000, -1]
            for i in range(len(intersectingSegments)):
                distanceScore = (self.segments[intersectingSegments[i]]
                                 .getDistanceScore(mouseObject.getWorld()))
                if distanceScore < lowestDistance[0]:
                    lowestDistance = [distanceScore, intersectingSegments[i]]
            intersectingSegments[0] = lowestDistance[1]
        if len(intersectingSegments) > 0:
            # sometimes the rectangles pygame returns do not cover
            # the full line, so make sure there is an intersection
            # in the list before returning
            return intersectingSegments[0]
        else:
            return -1

    def createMouseSegments(self, segment, mouseObject, stop1, stop2):
        self.tempSegments = list(self.segments)
        if (segment == 0
                and findDistance(mouseObject.getWorld(),
                                 stop1.getPosition()) < ENDPOINT_SEGMENT_DISTANCE):
            self.mouseSegments.append(MouseSegment(stop1,
                                                   mouseObject,
                                                   -len(self.segments),
                                                   "before"))
        elif (segment == len(self.segments)-1
              and findDistance(mouseObject.getWorld(),
                               stop2.getPosition()) < ENDPOINT_SEGMENT_DISTANCE):
            self.mouseSegments.append(MouseSegment(stop2,
                                                   mouseObject,
                                                   segment,
                                                   "after"))
        else:
            self._abandonSegment(segment)
            self.mouseSegments.append(MouseSegment(stop1,
                                                   mouseObject,
                                                   segment-1,
                                                   "after"))
            self.mouseSegments.append(MouseSegment(stop2,
                                                   mouseObject,
                                                   -len(self.segments)+segment+1,
                                                   "before"))

    def update(self, worldSurface, updateTransfers):
        # commit changes made during editing and fix values that changed
        # updateTransfers = True: update everything, and update the lines that
        # get marked as transfers from this line with updateTransfers = False
        # updateTransfers = False: only update the line, no trains, and
        # do not continue to call update on lines that get marked as transfers
        if len(self.segments) > 0:
            if self in self.segments[0].firstPoint.lines:
                self.segments[0].firstPoint.lines.remove(self)
        for i in range(len(self.segments)):
            if self in self.segments[i].lastPoint.lines:
                self.segments[i].lastPoint.lines.remove(self)
        self.transfers = []

        if updateTransfers:
            self.updateTrainIndices()
        for i in range(len(self._abandonedSegments)-1, -1, -1):
            self._abandonedSegments.pop(i)
        for i in range(len(self.tempSegments)-1, -1, -1):
            if self.tempSegments[i].isAbandoned:
                self.tempSegments.pop(i)
        self.segments = list(self.tempSegments)
        # fix indices and update the stop number list as well each stop
        if len(self.segments) > 0:
            self.stopNums = [self.segments[0].firstPoint.shape]
            if self not in self.segments[0].firstPoint.lines:
                self.segments[0].firstPoint.lines.append(self)
        for i in range(len(self.segments)):
            self.segments[i].index = i
            self.tempSegments[i].index = i
            self.segments[i].checkOverWater(worldSurface)
            self.stopNums.append(self.segments[i].lastPoint.shape)
            if self not in self.segments[i].lastPoint.lines:
                self.segments[i].lastPoint.lines.append(self)
        # update transfers
        if len(self.segments) > 0:
            for line in self.segments[0].firstPoint.lines:
                if line is not self and [0, line] not in self.transfers:
                    self.transfers.append([0, line])
                    if updateTransfers:
                        line.update(worldSurface, False)
        for i in range(len(self.segments)):
            for line in self.segments[i].lastPoint.lines:
                if line is not self and [i+1, line] not in self.transfers:
                    self.transfers.append([i+1, line])
                    if updateTransfers:
                        line.update(worldSurface, False)
        # clear new stops
        for i in range(len(self._newStops)-1, -1, -1):
            self._newStops.pop(i)
        # clear removed stops
        for i in range(len(self._removedStops)-1, -1, -1):
            self._removedStops.pop(i)
        # clear mouse segments
        for i in range(len(self.mouseSegments)-1, -1, -1):
            self.mouseSegments.pop(i)

    def contains(self, stop):
        # see if a stop is within a line
        inLine = False
        for segment in self.tempSegments:
            if stop == segment.firstPoint or stop == segment.lastPoint:
                inLine = True
        return inLine

    def find(self, stop, source):
        # see if a stop is within the list source
        segments = []
        for i in range(len(source)):
            if (source[i].firstPoint == stop
                    or source[i].lastPoint == stop):
                segments.append(i)
        return segments

    def processMouseSegments(self, stops, mouseObject, offset, worldSurface):
        for mouseSegment in self.mouseSegments:
            mouseSegment.update(mouseObject.getView(offset), offset)
            for stop in stops:
                mouseWorld = mouseObject.getWorld()
                if (not self.contains(stop)
                        and (stop not in self._removedStops)
                        # expand the result of mouseWorld into the
                        # function call. radius has to be assigned by
                        # name since we are expanding a tuple into
                        # the function call
                        and stop.withinRadius(*mouseWorld,
                                              radius=STOP_ADDITION_DISTANCE)):
                    # if the mouse segment meets the conditions for adding a stop, add one
                    self._insertSegment(mouseSegment, stop, worldSurface)
                elif (self.contains(stop)
                      and (stop not in self._newStops)
                      and (stop not in self._removedStops)
                      and stop.withinRadius(*mouseWorld,
                                            radius=STOP_REMOVAL_DISTANCE)):
                    # same as before but for removing
                    self._removeStop(stop)

    def _findNextActiveStop(self, stopsToSearch):
        # find the next non-abandoned stop in the given list
        for stop in stopsToSearch:
            if not self.tempSegments[stop].isAbandoned:
                return stop
        return

    def _removeStop(self, stop):
        matchedSegments = self.find(stop, self.tempSegments)
        validRemoval = False
        for mouseSegment in self.mouseSegments:
            if stop == mouseSegment.firstPoint:
                validRemoval = True
        if not validRemoval:
            return
        if len(matchedSegments) == 2 and len(self.mouseSegments) == 2:
            # removing middle stops

            if not self.tempSegments[matchedSegments[0]].isAbandoned:
                self._abandonSegment(matchedSegments[0])
            if not self.tempSegments[matchedSegments[1]].isAbandoned:
                self._abandonSegment(matchedSegments[1])

            # find the next active stop after the removed point
            self._updateMouseSegment("after", matchedSegments[1], 1)
            # find the next active stop before the removed point
            self._updateMouseSegment("before", matchedSegments[0], 0)

        elif (len(matchedSegments) == 1
              or (len(matchedSegments) == 2
                  and len(self.mouseSegments) == 1)):
            # removing end stops

            if (len(matchedSegments) == 2
                    and self.tempSegments[matchedSegments[0]].isAbandoned):
                matchedSegments.pop(0)
            if not self.tempSegments[matchedSegments[0]].isAbandoned:
                self._abandonSegment(matchedSegments[0])
            if len(self.mouseSegments) == 2:
                # remove the extra unwanted mouse segment
                if matchedSegments[0] == 0:
                    if (self.mouseSegments[0].direction == "before"
                            or self.mouseSegments[0].firstPoint != stop):
                        self.mouseSegments.pop(1)
                    else:
                        self.mouseSegments.pop(0)
                elif matchedSegments[0] == len(self.tempSegments)-1:
                    if self.mouseSegments[0].direction == "after":
                        self.mouseSegments.pop(1)
                    else:
                        self.mouseSegments.pop(0)

            if self.mouseSegments[0].direction == "before":
                self._updateMouseSegment("after", matchedSegments[0], 0)
            elif self.mouseSegments[0].direction == "after":
                self._updateMouseSegment("before", matchedSegments[0], 0)

        self._removedStops.append(stop)

    def _updateMouseSegment(self, direction, matchedSegment, mouseIndex):
        # corrects the mouse segment after removal of stops
        if direction == "after":
            nextStop = self._findNextActiveStop(range(-len(self.tempSegments)+matchedSegment, 0))
            if nextStop is None:
                self.mouseSegments[mouseIndex].firstPoint = self.tempSegments[-1].lastPoint
                self.mouseSegments[mouseIndex].index = 0
            else:
                self.mouseSegments[mouseIndex].firstPoint = self.tempSegments[nextStop].firstPoint
                self.mouseSegments[mouseIndex].index = nextStop
        elif direction == "before":
            nextStop = self._findNextActiveStop(range(matchedSegment, -1, -1))
            if nextStop is None:
                self.mouseSegments[mouseIndex].firstPoint = self.tempSegments[0].firstPoint
                self.mouseSegments[mouseIndex].index = -1
            else:
                self.mouseSegments[mouseIndex].firstPoint = self.tempSegments[nextStop].lastPoint
                self.mouseSegments[mouseIndex].index = nextStop

    def _insertSegment(self, mouseSegment, stop, worldSurface):
        if len(self.tempSegments) == 0:
            if stop != mouseSegment.firstPoint:
                segment = Segment(mouseSegment.firstPoint,
                                  stop,
                                  0)
                segment.checkOverWater(worldSurface)
                self.tempSegments.append(segment)
                mouseSegment.index = mouseSegment.index+1
        elif mouseSegment.direction == "before":
            if mouseSegment.index == 0:
                segment = Segment(stop,
                                  self.tempSegments[-1].lastPoint,
                                  -1)
                segment.checkOverWater(worldSurface)
                self.tempSegments.append(segment)
            else:
                segment = Segment(stop,
                                  self.tempSegments[mouseSegment.index].firstPoint,
                                  mouseSegment.index-1)
                segment.checkOverWater(worldSurface)
                self.tempSegments.insert(mouseSegment.index,
                                         segment)
            mouseSegment.index = mouseSegment.index-1
        elif mouseSegment.direction == "after":
            if mouseSegment.index == -1:
                segment = Segment(self.tempSegments[0].firstPoint,
                                  stop,
                                  0)
                segment.checkOverWater(worldSurface)
                self.tempSegments.insert(0,
                                         segment)
            else:
                segment = Segment(self.tempSegments[mouseSegment.index].lastPoint,
                                  stop,
                                  mouseSegment.index+1)
                segment.checkOverWater(worldSurface)
                self.tempSegments.insert(mouseSegment.index+1,
                                         segment)
            mouseSegment.index = mouseSegment.index+1
        mouseSegment.firstPoint = stop
        self._newStops.append(stop)

    def updateTrainIndices(self):
        abandonedIndices = []
        for abandonedSegment in self._abandonedSegments:
            abandonedIndices.append(abandonedSegment.index)
        if len(abandonedIndices) == 0:
            abandonedIndices.append(len(self.segments))  # to keep the list non-empty
        mouseIndices = []
        for mouseSegment in self.mouseSegments:
            if mouseSegment.index < 0:
                mouseIndices.append(len(self.segments)+mouseSegment.index)
            else:
                mouseIndices.append(mouseSegment.index)
        # change in number of stops
        deltaLength = len(self._newStops)-len(self._removedStops)
        for i in range(len(self.trains)-1, -1, -1):
            # [true if any part is on an abandoned segment,
            # true if train head is on an abandoned segment]
            isOnAbandonedSegment = [False, False]
            if (self.trains[i].segmentNum in abandonedIndices
                    and self.trains[i].line == self):
                isOnAbandonedSegment = [True, True]
            for carriage in self.trains[i].carriages:
                if carriage.segmentNum in abandonedIndices and carriage.line == self:
                    isOnAbandonedSegment[0] = True
            if isOnAbandonedSegment[0]:
                # if the segment the train was on got removed from
                # this line, switch the train onto the abandoned line
                self.createAbandonedChildren(self.trains[i], abandonedIndices)
            # if the changes were after this train,
            # nothing needs to be done to indices
            # if the changes were all before this train,
            # add the delta of stops to the index
            if (not isOnAbandonedSegment[1]
                    and (self.trains[i].segmentNum > max(mouseIndices)
                         or self.trains[i].segmentNum > max(abandonedIndices))):
                self.trains[i].segmentNum = self.trains[i].segmentNum+deltaLength
            for carriage in self.trains[i].carriages:
                if (carriage.segmentNum > max(mouseIndices)
                        or carriage.segmentNum > max(abandonedIndices)):
                    carriage.segmentNum = carriage.segmentNum+deltaLength
            if isOnAbandonedSegment[1]:
                self.trains.pop(i)

    def createAbandonedChildren(self, train, indices):
        abandonedLine = Line(self.LINE_NUMBER)
        abandonedLine.isAbandoned = True
        abandonedLine.parentLine = self
        # could use sorted() and somehow use lambdas to get a key
        # but i barely understand that so just sort with some kind
        # of insertion sort
        abandonedLine.segments.append(self._abandonedSegments[0])
        for i in range(1, len(self._abandonedSegments)):
            index = 0
            while (index < len(abandonedLine.segments)
                   and (abandonedLine.segments[index].index
                        < self._abandonedSegments[i].index)):
                index = index+1
            abandonedLine.segments.insert(index, self._abandonedSegments[i])
        self.abandonedChildren.append(abandonedLine)
        if train.segmentNum in indices:
            train.line = abandonedLine
            abandonedLine.trains.append(train)
            train.segmentNum = train.segmentNum-min(indices)
        for carriage in train.carriages:
            if carriage.segmentNum in indices:
                carriage.line = abandonedLine
                carriage.segmentNum = carriage.segmentNum-min(indices)


class Segment(object):
    def __init__(self, stop1, stop2, index):
        self.firstPoint = stop1
        self.lastPoint = stop2
        # bounding box (for collision detection)
        self.rect = None
        self.isAbandoned = False
        self.isTunnel = False
        self.index = index
        self.calculateData()

    def calculateData(self):
        self.length = findDistance(self.firstPoint.getPosition(),
                                   self.lastPoint.getPosition())
        self.angle = math.atan2(self.lastPoint.Y-self.firstPoint.Y,
                                self.lastPoint.X-self.firstPoint.X)
        self.reverseAngle = math.atan2(self.firstPoint.Y-self.lastPoint.Y,
                                       self.firstPoint.X-self.lastPoint.X)

    def getDistanceScore(self, point):
        # get a score calculated from a point to this segment that
        # roughly represents distance. not an exact value, but just
        # a score that will be lower when distance is lower and higher
        # when distance is higher. since we only care about relative
        # distance or approximate distance most of the time, this lazy
        # calculation works

        # calculation of score:
        # first, find the distance from an endpoint of the segment
        # to the point and add that to the distance from the other
        # endpoint to the point. then, from that, subtract the
        # length of the segment by itself to get the score
        return (findDistance((self.firstPoint.X,
                              self.firstPoint.Y),
                             point)
                + findDistance((self.lastPoint.X,
                                self.lastPoint.Y),
                               point)
                - findDistance((self.firstPoint.X,
                                self.firstPoint.Y),
                               (self.lastPoint.X,
                                self.lastPoint.Y)))

    def draw(self, targetSurface, colour, width, offset):
        firstView = getViewCoords(self.firstPoint.X, self.firstPoint.Y, offset)
        lastView = getViewCoords(self.lastPoint.X, self.lastPoint.Y, offset)
        self.rect = pygame.draw.line(targetSurface, colour, firstView, lastView, width)

    def checkOverWater(self, worldSurface):
        # check a few points on the segment to see if they are over water
        for step in self.getPointsAlongSegment(20):
            if worldSurface.get_at((int(step[0]), int(step[1]))) == COLOURS.get("river"):
                self.isTunnel = True
                return True
        self.isTunnel = False
        return False

    def getPointsAlongSegment(self, interval):
        stepX = interval*math.cos(self.angle)
        stepY = interval*math.sin(self.angle)
        steps = [[self.firstPoint.X, self.firstPoint.Y]]
        while findDistance(steps[0], steps[-1]) < self.length:
            steps.append([steps[-1][0]+stepX, steps[-1][1]+stepY])
        return steps[:-1]

    def getPointsOverWater(self, interval, worldSurface):
        # get points along  the segment with the given interval, then
        # return the ones over water
        points = self.getPointsAlongSegment(interval)
        for i in range(len(points)-1, -1, -1):
            if worldSurface.get_at((int(points[i][0]), int(points[i][1]))) != COLOURS.get("river"):
                points.pop(i)
        return points

    def drawTunnel(self, targetSurface, width, offset, worldSurface, interval):
        colour = COLOURS.get("river")
        steps = self.getPointsOverWater(interval, worldSurface)
        for step in steps:
            viewCoords = getViewCoords(step[0], step[1], offset)
            pygame.draw.circle(targetSurface,
                               colour,
                               (int(viewCoords[0]),
                                int(viewCoords[1])),
                               width)


class MousePosition(object):
    def __init__(self, viewCoords, offset):
        self.updateWithView(viewCoords, offset)

    def updateWithView(self, newViewCoords, offset):
        # update the mouse position given view coordinates and an offset
        self.x, self.y = newViewCoords
        self.x, self.y = self.toWorldCoords(offset)

    def updateWithWorld(self, newWorldCoords):
        # update the mouse position given world coordinates
        self.x, self.y = newWorldCoords

    def toWorldCoords(self, offset):
        # if self.x and self.y are in view space, tranform them to world space
        return [(self.x/float(offset[0][0]))+offset[1][0],
                (self.y/float(offset[0][1]))+offset[1][1]]

    def getWorld(self):
        return self.x, self.y

    def getView(self, offset):
        return getViewCoords(self.x, self.y, offset)


class MouseSegment(Segment):
    def __init__(self, stop1, mouse, index, direction):
        Segment.__init__(self, stop1, mouse, index)
        self.direction = direction

    def calculateData(self):
        self.length = findDistance(self.firstPoint.getPosition(),
                                   self.lastPoint.getWorld())
        self.angle = math.atan2(self.lastPoint.y-self.firstPoint.Y,
                                self.lastPoint.x-self.firstPoint.X)
        self.reverseAngle = math.atan2(self.firstPoint.Y-self.lastPoint.y,
                                       self.firstPoint.X-self.lastPoint.x)

    def draw(self, targetSurface, colour, offset):
        firstView = getViewCoords(self.firstPoint.X, self.firstPoint.Y, offset)
        mouseView = getViewCoords(self.lastPoint.x, self.lastPoint.y, offset)
        pygame.draw.aaline(targetSurface, colour, firstView, mouseView)

    def update(self, mouse, offset):
        self.lastPoint.updateWithView(mouse, offset)


class Train(object):
    def __init__(self, x, y, speed):
        self.passengers = []
        self.carriages = []
        self.head = None
        self._x = x
        self._y = y
        self.direction = 1  # -1 or 1
        self._colour = COLOURS.get("whiteOutline")
        self._angle = 0
        self._speed = speed
        self.canMove = False
        self.isOnSegment = False
        self.line = None
        self.stop = None
        self.rect = None
        self.movingClone = None

    def getPosition(self):
        return self._x, self._y

    def updateMouse(self, mouseObject):
        self.canMove = False
        self._x, self._y = mouseObject.getWorld()

    def startMouseMove(self):
        # when the train is already on a line and being moved
        self._colour = self.line.DARKER_COLOUR
        self.movingClone = copy.copy(self)
        self.movingClone.snapToLine(self.line, self.segmentNum)

    def moveLines(self, offset, passengerSize):
        # moves this train to the movingClone
        self.line.trains.remove(self)
        movingClone = self.movingClone
        self = copy.copy(movingClone)
        movingClone.line.trains.remove(movingClone)
        self.line.trains.append(self)
        self.placeOnLine()
        self.movingClone = None
        carriages = self.carriages
        self.carriages = []
        for i in range(len(carriages)-1, -1, -1):
            carriages[i].moveLines(self, i, offset, passengerSize)
        # copy.copy to make the clone and set self to the clone
        # causes self to point to a new memory address, but the
        # trains do not have any concept of the world, and the
        # for loop that controls the trains uses the trains in the
        # world. since the address the world knows is now
        # incorrect, return self so that the world can correct
        # the address
        return self

    def stopMouseMove(self):
        self._colour = self.line.BRIGHTER_COLOUR
        self.movingClone = None

    def snapToLine(self, line, segmentNum):
        if len(line.trains) > 3:
            self.unsnapFromLine()
            return
        self.isOnSegment = True
        self.line = line
        self.segmentNum = segmentNum
        self._angle = line.segments[segmentNum].angle
        self._colour = line.DARKER_COLOUR

        # visually snap the train to the line
        segment = self.line.segments[segmentNum]
        # clamp x coordinates to be within the domain of the segment
        if segment.firstPoint.X <= segment.lastPoint.X:
            self._x = max(segment.firstPoint.X, min(self._x, segment.lastPoint.X))
        else:
            self._x = max(segment.lastPoint.X, min(self._x, segment.firstPoint.X))
        # y = tan(theta)*(x-h)+k
        # eq-n of the line of the segment with a starting point of (h, k)
        # snap the y to be on the line at the correct coordinates
        self._y = (math.tan(self._angle)
                   * (self._x-segment.firstPoint.X)
                   + segment.firstPoint.Y)
        if self not in self.line.trains:
            self.line.trains.append(self)

    def unsnapFromLine(self):
        if self.line is not None and self in self.line.trains:
            self.line.trains.remove(self)
        self.isOnSegment = False
        self._angle = 0
        self._colour = COLOURS.get("whiteOutline")

    def remove(self):
        self.tail = None
        for i in range(len(self.carriages)-1, -1, -1):
            self.carriages[i].remove()
            self.carriages.pop(i)

    def placeOnLine(self):
        # places line on the segment it snapped to
        self.canMove = True
        self._colour = self.line.BRIGHTER_COLOUR
        distanceFromFirstPoint = findDistance((self.line.segments[self.segmentNum]
                                               .firstPoint.getPosition()),
                                              (self._x, self._y))
        distanceFromLastPoint = findDistance((self.line.segments[self.segmentNum]
                                              .lastPoint.getPosition()),
                                             (self._x, self._y))
        if (distanceFromFirstPoint <= distanceFromLastPoint):
            self.direction = -1
            self._segmentDistance = distanceFromLastPoint
            self._angle = self.line.segments[self.segmentNum].angle
        else:
            self.direction = 1
            self._segmentDistance = distanceFromFirstPoint
            self._angle = self.line.segments[self.segmentNum].reverseAngle

    def moveToParentLine(self):
        # move off abandoned child back onto main line
        if self.segmentNum < 0:
            segments = self.line.parentLine.find(self.line.segments[0].firstPoint,
                                                 self.line.parentLine.segments)
            if len(segments) > 1:
                self.segmentNum = min(segments)
            elif len(segments) == 1:
                self.segmentNum = segments[0]
                if (self.line.segments[0].firstPoint
                        == self.line.parentLine.segments[0].firstPoint):
                    # change the segment number so that the train will change direction
                    # if the beginning of the abandoned segment is the beginning of the
                    # parent line and the train is about to move off to the beginning
                    # of the line
                    self.segmentNum = self.segmentNum+self.direction
            else:
                return
        elif self.segmentNum > len(self.line.segments)-1:
            segments = self.line.parentLine.find(self.line.segments[-1].lastPoint,
                                                 self.line.parentLine.segments)
            if len(segments) > 1:
                self.segmentNum = max(segments)
            elif len(segments) == 1:
                self.segmentNum = segments[0]
                if (self.line.segments[-1].lastPoint
                        == self.line.parentLine.segments[-1].lastPoint):
                    # same idea as above just for the end of the line
                    self.segmentNum = self.segmentNum+self.direction
            else:
                return
        else:
            return
        self.line.trains.remove(self)
        self.line = self.line.parentLine
        self.line.trains.append(self)

    def move(self, offset, passengerSize):
        # if the train has moved past the segment, move it to the next segment or attach
        # it to the stop it is at
        if self._segmentDistance >= self.line.segments[self.segmentNum].length:
            self.segmentNum = self.segmentNum+self.direction
            self._segmentDistance = 0
            if self.line.isAbandoned:
                self.moveToParentLine()

            if self.segmentNum < 0:
                self.segmentNum = 0
                self.direction = 1
            elif self.segmentNum > len(self.line.segments)-1:
                self.segmentNum = len(self.line.segments)-1
                self.direction = -1

            if self.direction == 1:
                self._angle = self.line.segments[self.segmentNum].reverseAngle
                self.stop = self.line.segments[self.segmentNum].firstPoint
            else:
                self._angle = self.line.segments[self.segmentNum].angle
                self.stop = self.line.segments[self.segmentNum].lastPoint
            if len(self.stop.passengers) > 0 or len(self.passengers) > 0:
                self.stop.trains.append(self)
                self.setMoving(False)

        self._x = self._x + -self._speed*math.cos(self._angle)
        self._y = self._y + -self._speed*math.sin(self._angle)
        self._segmentDistance = self._segmentDistance+self._speed
        for carriage in self.carriages:
            if carriage.canMove:
                carriage.move(offset, passengerSize)

    def setMoving(self, state):
        if state:
            for train in self.line.trains:
                if (train is not self
                        and train.segmentNum == self.segmentNum
                        and train.direction == self.direction
                        and train.canMove):
                    # to prevent trains all moving in the same place,
                    # stop the train from moving if there is a train
                    # on the segment it is about to go on
                    return False  # the intended setMoving operation did not complete
        self.canMove = state
        for carriage in self.carriages:
            carriage.canMove = state
        return True

    def rotatePoint(self, point, angle):
        # rotate point around the origin
        return [point[0]*math.cos(angle) - point[1]*math.sin(angle),
                point[0]*math.sin(angle) + point[1]*math.cos(angle)]

    def findFirst(self):
        head = self
        while head.head is not None:
            head = head.head
        return head

    def findLast(self):
        tail = self
        while tail.tail is not None:
            tail = tail.tail
        return tail

    def drawAllPassengers(self, targetSurface, rect, passengerSize, offset):
        # rect[1] (from the draw() method) is a list of points that
        # passengers would be drawn at if the train was centered
        # around the origin, so rotate and translate the points
        viewRect = copy.deepcopy(rect[1])
        centerView = getViewCoords(self._x, self._y, offset)
        for i in range(len(viewRect)):
            viewRect[i] = self.rotatePoint(viewRect[i], self._angle)
            viewRect[i][0] = viewRect[i][0]+centerView[0]
            viewRect[i][1] = viewRect[i][1]+centerView[1]

        for i in range(len(self.passengers[:6])):
            self.passengers[i].draw(targetSurface, passengerSize, *viewRect[i])

        for i in range(len(self.carriages)):
            viewRect = copy.deepcopy(rect[1])
            centerView = getViewCoords(self.carriages[i]._x, self.carriages[i]._y, offset)
            for j in range(len(viewRect)):
                viewRect[j] = self.rotatePoint(viewRect[j], self.carriages[i]._angle)
                viewRect[j][0] = viewRect[j][0]+centerView[0]
                viewRect[j][1] = viewRect[j][1]+centerView[1]
            for j in range(len(self.passengers[(6*(i+1)):(6*(i+2))])):
                self.passengers[j].draw(targetSurface, passengerSize, *viewRect[j % 6])

    def draw(self, targetSurface, rect, passengerSize, offset):
        # since rect is a multi-dimensional list, list() is not enough
        # rect[0] is a list of points for a correctly shaped rectangle
        # centered around the origin, so rotate and translate it to the
        # orientation we want
        rect = copy.deepcopy(rect[0])
        centerView = getViewCoords(self._x, self._y, offset)
        for i in range(len(rect)):
            rect[i] = self.rotatePoint(rect[i], self._angle)
            rect[i][0] = rect[i][0]+centerView[0]
            rect[i][1] = rect[i][1]+centerView[1]
        pygame.gfxdraw.aapolygon(targetSurface, rect, self._colour)
        self.rect = pygame.draw.polygon(targetSurface,
                                        self._colour,
                                        rect)


class Carriage(Train):
    def __init__(self, x, y, speed):
        Train.__init__(self, x, y, speed)
        # carriage - follows a train/carriage and can be followed by a carriage
        # holds people, adds capacity to a parent train
        self.tail = None  # the carriage that follows this
        self._segmentDistance = 0

    def attachToNearestTrain(self):
        # find the closest train on the line the
        # carriage is on
        lowestDistance = [10000000, -1]
        for i in range(len(self.line.trains)):
            distance = findDistance(self.line.trains[i].getPosition(),
                                    self.getPosition())
            if distance < lowestDistance[0]:
                lowestDistance = [distance, i]
        if lowestDistance[1] != -1 and len(self.line.trains[lowestDistance[1]].carriages) < 4:
            self.head = self.line.trains[lowestDistance[1]]
            self._speed = self.head._speed
            self.isOnSegment = True
        else:
            self.isOnSegment = False
            self.unsnapFromLine()

    def startMouseMove(self):
        self._colour = self.line.DARKER_COLOUR
        self.movingClone = copy.copy(self)
        self.movingClone.snapToLine(self.line)

    def snapToLine(self, line):
        self.line = line
        self._colour = line.DARKER_COLOUR
        self.attachToNearestTrain()

    def moveLines(self, train, index, offset, passengerSize):
        # index is the position of the carriage in the train
        # e.g. first carriage, second carriage
        # remove element from linked list
        self.findFirst().carriages.remove(self)
        self.head.tail = self.tail
        if self.tail is not None:
            self.tail.head = self.head
        self.line = train.line
        self.head = train
        self.movingClone = None
        self.isOnSegment = True
        self.placeOnLine(True, offset, passengerSize)

    def remove(self):
        self.head.tail = self.tail
        if self.tail is not None:
            self.tail.head = self.head
        self.head = None
        self.tail = None

    def placeOnLine(self, shouldAppendToTrain, offset, passengerSize):
        # operations on the train before propertly setting head
        if shouldAppendToTrain:
            self.head.carriages.append(self)
            if len(self.head.carriages) > 1:
                self.head = self.head.findLast()
        # head is now the proper head
        self.head.tail = self
        self.canMove = True
        self._colour = self.head._colour
        self._angle = self.head._angle

        self.fixPosition(offset, passengerSize)

    def fixPosition(self, offset, passengerSize):
        if self.head.line != self.line:
            return
        carriageDistance = passengerSize*3.5
        self._x = (carriageDistance/offset[0][0])*math.cos(self._angle)+self.head._x
        self._y = (carriageDistance/offset[0][1])*math.sin(self._angle)+self.head._y
        carriageDistance = findDistance((self._x, self._y), (self.head._x, self.head._y))
        self._segmentDistance = self.head._segmentDistance-carriageDistance
        self.direction = self.head.direction
        self.segmentNum = self.head.segmentNum

        # if the carriage is off the segment its head is on, the carriage should be
        # on the previous segment, so find that segment and correctly calculate
        # angle, x, y, and segment distance
        if self._segmentDistance < 0:
            self.segmentNum = self.segmentNum-self.direction
            if self.segmentNum < 0 or self.segmentNum > len(self.line.segments)-1:
                self.segmentNum = min(len(self.line.segments)-1, max(0, self.segmentNum))
                self.direction = -self.direction
            self._segmentDistance = self.line.segments[self.segmentNum].length+self._segmentDistance
            if self.direction == 1:
                self._angle = self.line.segments[self.segmentNum].reverseAngle
                self._x = (self.line.segments[self.segmentNum].firstPoint.X
                           - (self._segmentDistance*math.cos(self._angle)))
                self._y = (self.line.segments[self.segmentNum].firstPoint.Y
                           - (self._segmentDistance*math.sin(self._angle)))
                self._segmentDistance = findDistance((self.line.segments[self.segmentNum]
                                                      .firstPoint.getPosition()),
                                                     (self._x, self._y))
            elif self.direction == -1:
                self._angle = self.line.segments[self.segmentNum].angle
                self._x = (self.line.segments[self.segmentNum].lastPoint.X
                           - (self._segmentDistance*math.cos(self._angle)))
                self._y = (self.line.segments[self.segmentNum].lastPoint.Y
                           - (self._segmentDistance*math.sin(self._angle)))
                self._segmentDistance = findDistance((self.line.segments[self.segmentNum]
                                                      .lastPoint.getPosition()),
                                                     (self._x, self._y))

    def move(self, offset, passengerSize):
        if self._segmentDistance >= self.line.segments[self.segmentNum].length:
            self.line = self.head.line
            self.segmentNum = self.head.segmentNum
            self.direction = self.head.direction
            self._angle = self.head._angle
            self._segmentDistance = 0
        self.fixPosition(offset, passengerSize)
        self._x = self._x + -self._speed*math.cos(self._angle)
        self._y = self._y + -self._speed*math.sin(self._angle)
        self._segmentDistance = self._segmentDistance+self._speed
