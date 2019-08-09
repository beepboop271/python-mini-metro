###################################################################################################
#
# main.py
# The file that runs the main game of Mini Metro
#
# Kevin Qiao - January 20, 2019
#
###################################################################################################

import random
import copy
import pygame
import pygame.gfxdraw
import MiniMetroClasses as Game
import TimeClass as Time

print "Enter instruction detail level"
print "[0 - Less Detailed (~1 min read), 1 - Detailed (~2 min read, recommended)]"
instructionDetail = input(": ")
while instructionDetail != 0 and instructionDetail != 1:
    instructionDetail = input(": ")
if instructionDetail == 0:
    instructions = open("assets/simpleInstructions.txt", "r")
    print instructions.read()
    instructions.close()
elif instructionDetail == 1:
    instructions = open("assets/detailedInstructions.txt", "r")
    print instructions.read()
    instructions.close()
raw_input("Press ENTER to start")

pygame.init()

# camera (display) coordinates
cWidth = 800
cHeight = 600
display = pygame.display.set_mode((cWidth, cHeight))
# world coordinates
wWidth = 1200
wHeight = 900
worldSurface = pygame.Surface((wWidth, wHeight))

clock = pygame.time.Clock()

# load resources
ubuntuLight30 = pygame.font.Font("assets/fonts/Ubuntu-Light.ttf", 30)
ubuntuBold30 = pygame.font.Font("assets/fonts/Ubuntu-Bold.ttf", 30)
ubuntu70 = pygame.font.Font("assets/fonts/Ubuntu-Regular.ttf", 70)

MUSIC = ["assets/audio/Mini Metro - 01 Keep the City Moving.ogg",
         "assets/audio/Mini Metro - 02 One Week.ogg",
         "assets/audio/Mini Metro - 03 Back to Work.ogg"]
pygame.mixer.music.set_endevent(pygame.USEREVENT)
pygame.mixer.music.load(MUSIC[random.randint(0, 2)])
pygame.mixer.music.play()

STOP_POLYGONS = [pygame.image.load("assets/stops/circle_dark.png").convert_alpha(),
                 pygame.image.load("assets/stops/triangle_dark.png").convert_alpha(),
                 pygame.image.load("assets/stops/square_dark.png").convert_alpha(),
                 pygame.image.load("assets/stops/diamond_dark.png").convert_alpha(),
                 pygame.image.load("assets/stops/trapezoid_dark.png").convert_alpha(),
                 pygame.image.load("assets/stops/parallelogram_dark.png").convert_alpha(),
                 pygame.image.load("assets/stops/pentagon_dark.png").convert_alpha(),
                 pygame.image.load("assets/stops/hexagon_dark.png").convert_alpha(),
                 pygame.image.load("assets/stops/star_dark.png").convert_alpha()]

PASSENGER_POLYGONS = [pygame.image.load("assets/passengers/circle_light.png").convert_alpha(),
                      pygame.image.load("assets/passengers/triangle_light.png").convert_alpha(),
                      pygame.image.load("assets/passengers/square_light.png").convert_alpha(),
                      pygame.image.load("assets/passengers/diamond_light.png").convert_alpha(),
                      pygame.image.load("assets/passengers/trapezoid_light.png").convert_alpha(),
                      pygame.image.load("assets/passengers/parallelogram_light.png").convert_alpha(),
                      pygame.image.load("assets/passengers/pentagon_light.png").convert_alpha(),
                      pygame.image.load("assets/passengers/hexagon_light.png").convert_alpha(),
                      pygame.image.load("assets/passengers/star_light.png").convert_alpha()]
PASSENGER_ICON = pygame.image.load("assets/icons/passenger.png").convert_alpha()

RIVERS = [pygame.image.load("assets/maps/river1.png").convert_alpha(),
          pygame.image.load("assets/maps/river2.png").convert_alpha(),
          pygame.image.load("assets/maps/river3.png").convert_alpha(),
          pygame.image.load("assets/maps/river4.png").convert_alpha()]

ICONS = [pygame.image.load("assets/icons/carriage.png").convert_alpha(),
         pygame.image.load("assets/icons/line.png").convert_alpha(),
         pygame.image.load("assets/icons/train.png").convert_alpha(),
         pygame.image.load("assets/icons/tunnel.png").convert_alpha()]

# pick and place a map
river = random.randint(0, 3)
# top y value
riverY = random.randint(wHeight/2-cHeight/3-RIVERS[river].get_height(),
                        wHeight/2+cHeight/3-RIVERS[river].get_height())
# leftmost x value
riverX = random.randint(wWidth-2000, 0)  # 2000 is the width of the images

worldSurface.blit(RIVERS[river], (riverX, riverY))
world = Game.World(worldSurface)
validStops = [Game.CIRCLE, Game.TRIANGLE, Game.SQUARE]

# scale images
scaledPassengerPolygons = []
for polygon in PASSENGER_POLYGONS:
    scaledPassengerPolygons.append(pygame.transform.smoothscale(polygon,
                                                                (world.passengerSize,
                                                                 world.passengerSize)))

scaledIcons = []
for icon in ICONS:
    scaledIcons.append(pygame.transform.smoothscale(icon,
                                                    (int(world.stopSize*1.5),
                                                     int(world.stopSize*1.5))))

# point list for drawing trains and carriages
rectPoints = [[[-world.passengerSize*1.5, world.passengerSize],
               [world.passengerSize*1.5, world.passengerSize],
               [world.passengerSize*1.5, -world.passengerSize],
               [-world.passengerSize*1.5, -world.passengerSize]],
              [[-world.passengerSize, world.passengerSize/2],
               [0, world.passengerSize/2],
               [world.passengerSize, world.passengerSize/2],
               [world.passengerSize, -world.passengerSize/2],
               [0, -world.passengerSize/2],
               [-world.passengerSize, -world.passengerSize/2]]]


def calculateCameraOffset(cWidth, cHeight, world):
    # calculate the scale and translation operations to move from
    # world coordinates to screen coordinates
    return [[cWidth/float(2*world.validStopDistanceX),
             cHeight/float(2*world.validStopDistanceY)],
            [world.width/2-world.validStopDistanceX,
             world.height/2-world.validStopDistanceY]]


def interpolateQuadratic(time, maxTime, minOutput, maxOutput):
    # interpolate between time range 0->maxTime, to the range minOutput->maxOutput
    # using two parabolas
    # get time in the interval [0, 1] as opposed to [0, maxTime]
    normalizedTime = float(time)/maxTime
    # these two functions make a nice in-out ease over [0, 1]
    # y = 2x^2           {x < 0.5}
    # y = -2(x-1)^2 + 1  {x >= 0.5}
    if normalizedTime < 0.5:
        output = 2*(normalizedTime**2)
    elif normalizedTime >= 0.5:
        output = -2*((normalizedTime-1)**2)+1
    # map output to the desired output
    if minOutput > maxOutput:
        return minOutput-output*abs(maxOutput-minOutput)
    return output*abs(maxOutput-minOutput)+minOutput


def interpolateLinear(time, maxTime, minOutput, maxOutput):
    # interpolate between the time range 0->maxTime to the range minOutput->maxOutput
    # using a line
    normalizedTime = float(time)/maxTime
    output = minOutput+(maxOutput-minOutput)*normalizedTime
    return output


def getPassengerMoveTime(passengersMoved):
    return max(interpolateLinear(passengersMoved, 900, 0.3, 0.07), 0.07)


def getNewStopTime(passengersMoved):
    return max(interpolateQuadratic(passengersMoved, 1000, 10, 2), 2)


def getNewPassengerTime(passengersMoved):
    return max(interpolateLinear(passengersMoved, 1000, 3, 1.5), 1.5)


def getGameTimerTime(passengersMoved):
    return max(interpolateLinear(passengersMoved, 900, 1.0/70, 1.0/160), 1.0/160)


def getSwitchStopTime(passengersMoved):
    if passengersMoved < 400:
        return 10000
    else:
        return max(interpolateLinear(passengersMoved-400, 600, 50, 10), 10)


def togglePaused(paused, timers, world):
    paused = not paused
    for timer in timers:
        timer.toggleActive()
    for stop in world.stops:
        if stop.usingTimer:
            stop.timer.toggleActive()
    return paused


newStopTimer = Time.Time(Time.MODE_TIMER,
                         Time.FORMAT_TOTAL_SECONDS,
                         getNewStopTime(world.passengersMoved))
newPassengerTimer = Time.Time(Time.MODE_TIMER,
                              Time.FORMAT_TOTAL_SECONDS,
                              getNewPassengerTime(world.passengersMoved))
passengerMoveTimer = Time.Time(Time.MODE_TIMER,
                               Time.FORMAT_TOTAL_SECONDS,
                               getPassengerMoveTime(world.passengersMoved))
switchStopTimer = Time.Time(Time.MODE_TIMER,
                            Time.FORMAT_TOTAL_SECONDS,
                            getSwitchStopTime(world.passengersMoved))
gainResourcesTimer = Time.Time(Time.MODE_TIMER,
                               Time.FORMAT_TOTAL_SECONDS,
                               Game.RESOURCE_GAIN_DELAY)
gameTimer = Time.Time(Time.MODE_STOPWATCH,
                      Time.FORMAT_TOTAL_SECONDS)
scaleDuration = 2
smoothScaleTimer = Time.Time(Time.MODE_TIMER,
                             Time.FORMAT_TOTAL_SECONDS,
                             scaleDuration)
# also make a list that points to the individual timers
# for operations on all of them
timers = [newStopTimer, newPassengerTimer, passengerMoveTimer,
          switchStopTimer, gainResourcesTimer, gameTimer, smoothScaleTimer]


def drawBase():
    # draw the background, lines, and trains
    # by drawing the base before the overlay, the event processing loop
    # is able to detect clicks correctly as it uses colours to do initial
    # detection
    if paused:
        display.fill((25, 25, 25))
    else:
        display.fill(Game.COLOURS.get("background"))
    display.blit(scaledWorldSurface,
                 (-cameraOffset[1][0]*cameraOffset[0][0],
                  -cameraOffset[1][1]*cameraOffset[0][1]),
                 None,
                 pygame.BLEND_MAX)

    for i in range(len(world.lines)):
        world.lines[i].draw(display, 10, cameraOffset)
        for childLine in world.lines[i].abandonedChildren:
            childLine.draw(display, 10, cameraOffset)
        if (world.lines[i].segments == []
                and world.lines[i].mouseSegments == []):
            world.lines.pop(i)
    for train in world.trains:
        train.draw(display, rectPoints, world.passengerSize, cameraOffset)
    if movingTrain != -1:
        movingTrain[0].movingClone.draw(display, rectPoints, world.passengerSize, cameraOffset)
    for movingClone in trainsToMove:
        movingClone.draw(display, rectPoints, world.passengerSize, cameraOffset)

    for carriage in world.carriages:
        carriage.draw(display, rectPoints, world.passengerSize, cameraOffset)


def drawOverlay():
    # draw all superimposed elements to the screen
    for train in world.trains:
        train.drawAllPassengers(display, rectPoints, world.passengerSize, cameraOffset)

    numTunnels = 0
    for line in world.lines:
        for segment in line.tempSegments:
            if segment.isTunnel:
                numTunnels = numTunnels+1
                segment.drawTunnel(display, 7, cameraOffset, worldSurface, 30/cameraOffset[0][0])

    world.resources[Game.TUNNEL] = world.totalTunnels-numTunnels

    for i in range(len(Game.COLOURS.get("lines"))):
        indicatorCoords = (int(world.stopSize*(2.5+i)+(i*10)),
                           int(cHeight-world.stopSize*1.5))
        if i < len(world.lines):
            pygame.draw.circle(display,
                               Game.COLOURS.get("lines")[i],
                               indicatorCoords,
                               world.stopSize/2)
        elif i < len(world.lines)+world.resources[Game.LINE]:
            pygame.draw.circle(display,
                               Game.COLOURS.get("lines")[i],
                               indicatorCoords,
                               world.stopSize/2,
                               2)
        else:
            pygame.draw.circle(display,
                               Game.COLOURS.get("whiteOutline"),
                               indicatorCoords,
                               world.stopSize/2,
                               2)

    for i in range(len(scaledIcons)):
        iconCoords = (int(cWidth                              # start from the right edge
                          - scaledIcons[i].get_width()*(2+i)  # at least 2 icon widths from edge
                          - (i*20)                            # 20 px of space between each icon
                          - scaledIcons[i].get_width()/2),    # center shape at that point

                      int(cHeight                             # start from bottom edge
                          - scaledIcons[i].get_height()       # one icon height away from edge
                          - scaledIcons[i].get_height()/2))   # center shape at that point
        world.iconHitboxes[i] = pygame.Rect(iconCoords,
                                            (scaledIcons[i].get_width(),
                                             scaledIcons[i].get_height()))
        resourceText = ubuntuBold30.render(str(world.resources[i]),
                                           1,
                                           Game.COLOURS.get("whiteOutline"))
        display.blit(resourceText,
                     (iconCoords[0]+scaledIcons[i].get_width()/2-resourceText.get_width()/2,
                      iconCoords[1]-35))
        display.blit(scaledIcons[i],
                     iconCoords)

    for stop in world.stops:
        stop.draw(display,
                  stopView,
                  world.passengerSize,
                  cameraOffset)

    if pickingResource:
        size = ubuntuLight30.size("Received one:  ")
        width = ubuntuLight30.size("Pick a resource: ")[0]

        background = pygame.Surface((size[0]+5+scaledIcons[0].get_width(),
                                     int(scaledIcons[0].get_height()*3.3+10)),
                                    pygame.SRCALPHA)
        background.fill((0, 0, 0, 150))
        display.blit(background, (cWidth-background.get_width(), 0))

        display.blit(ubuntuLight30.render("Received one:",
                                          1,
                                          Game.COLOURS.get("whiteOutline")),
                     (cWidth-size[0]-scaledIcons[resource].get_width(),
                      scaledIcons[resource].get_height()/2-size[1]/2+5))
        display.blit(scaledIcons[resource],
                     (cWidth-scaledIcons[resource].get_width()-5,
                      5))

        display.blit(ubuntuLight30.render("Pick a resource:",
                                          1,
                                          Game.COLOURS.get("whiteOutline")),
                     (cWidth-width,
                      scaledIcons[resource].get_height()*1.4))
        for option in options:
            display.blit(option[1], (option[2][0], option[2][1]))

    if window == "end" and not isScaling:
        size = ubuntu70.size("Game Over")
        display.blit(ubuntu70.render("Game Over",
                                     1,
                                     Game.COLOURS.get("whiteOutline")),
                     (cWidth/2-size[0]/2,
                      40))
        size = ubuntuLight30.size("Overcrowding at this stop shut down your subway")
        display.blit(ubuntuLight30.render("Overcrowding at this stop shut down your subway",
                                          1,
                                          Game.COLOURS.get("whiteOutline")),
                     (cWidth/2-size[0]/2,
                      120))
        size = ubuntuLight30.size(str(world.passengersMoved)+" passengers transported")
        display.blit(ubuntuLight30.render(str(world.passengersMoved)+" passengers transported",
                                          1,
                                          Game.COLOURS.get("whiteOutline")),
                     (cWidth/2-size[0]/2,
                      cHeight-150))

    display.blit(PASSENGER_ICON, (10, 8))
    display.blit(ubuntuLight30.render(str(world.passengersMoved),
                                      1,
                                      Game.COLOURS.get("whiteOutline")),
                 (50, 10))


cameraOffset = calculateCameraOffset(cWidth, cHeight, world)
scaledWorldSurface = pygame.transform.scale(worldSurface,
                                            (int(wWidth*cameraOffset[0][0]),
                                             int(wHeight*cameraOffset[0][1])))

stopView = int(world.stopSize*((cameraOffset[0][0]+cameraOffset[0][1])/2.0))
scaledStopPolygons = []
for polygon in STOP_POLYGONS:
    scaledStopPolygons.append(pygame.transform.smoothscale(polygon,
                                                           (stopView,
                                                            stopView)))

for shape in range(3):
    # spawn a square, circle, and triangle before the game starts,
    # trying as many times as needed
    while len(world.stops) < shape+1:
        world.addRandomStop(shape, scaledStopPolygons)
cameraOffset = calculateCameraOffset(cWidth, cHeight, world)
stopView = int(world.stopSize*((cameraOffset[0][0]+cameraOffset[0][1])/2.0))
for i in range(len(scaledStopPolygons)):
    scaledStopPolygons[i] = pygame.transform.smoothscale(STOP_POLYGONS[i],
                                                         (stopView,
                                                          stopView))
scaledWorldSurface = pygame.transform.scale(worldSurface,
                                            (int(wWidth*cameraOffset[0][0]),
                                             int(wHeight*cameraOffset[0][1])))

window = "game"
running = True
isScaling = False        # if the window is zooming out
doneScaling = False      # if the game will no longer zoom out
pickingResource = False  # if the player is choosing a resource
movingLine = -1          # line being edited
clickedIcon = -1         # resource being added
movingTrain = -1         # train/carriage being moved
trainsToMove = []        # holding list for trains/carriages until they can be legally moved
paused = False
# some hitboxes get generated upon drawing,
# so let them generate before they are used
drawOverlay()

while running:
    drawBase()
    for event in pygame.event.get():
        # if the window's X button is clicked
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            # press space to pause the game
            if event.key == pygame.K_SPACE and window != "end":
                paused = togglePaused(paused, timers, world)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                movingLine = world.getClickedLine(display.get_at(event.pos)[:3])
                clickedIcon = world.getClickedIcon(event.pos)
                movingTrain = world.getClickedTrainLine(display.get_at(event.pos)[:3])
                mouseObject = Game.MousePosition(event.pos, cameraOffset)
                # if a line was clicked
                if movingLine > -1:
                    line = world.lines[movingLine]
                    line.isMoving = True
                    clickedSegment = line.getClickedSegment(event.pos,
                                                            mouseObject)
                    # create mouse segments and abandon
                    # segments on the track
                    if clickedSegment > -1:
                        line.createMouseSegments(clickedSegment,
                                                 mouseObject,
                                                 line.segments[clickedSegment].firstPoint,
                                                 line.segments[clickedSegment].lastPoint)
                        segmentToFollow = 0
                    else:
                        movingLine = -1
                # if an existing train or carriage was clicked
                elif movingTrain > -1:
                    movingTrain = world.getClickedTrain(event.pos, movingTrain)
                    if movingTrain != -1:
                        movingTrain[0].startMouseMove()
                # if the carriage icon was clicked to create a new carriage
                elif clickedIcon == Game.CARRIAGE and world.resources[Game.CARRIAGE] > 0:
                    mouseWorld = mouseObject.getWorld()
                    world.carriages.append(Game.Carriage(*mouseWorld, speed=world.trainSpeed))
                    world.resources[Game.CARRIAGE] = world.resources[Game.CARRIAGE]-1
                # if the train icon was clicked to create a new carriage
                elif clickedIcon == Game.TRAIN and world.resources[Game.TRAIN] > 0:
                    mouseWorld = mouseObject.getWorld()
                    world.trains.append(Game.Train(*mouseWorld,
                                                   speed=world.trainSpeed))
                    world.resources[Game.TRAIN] = world.resources[Game.TRAIN]-1
                # if the new resource selection is showing
                elif pickingResource:
                    for option in options:
                        if option[2].collidepoint(event.pos):
                            pickingResource = False
                            if paused:
                                paused = togglePaused(paused, timers, world)
                            world.resources[option[0]] = world.resources[option[0]]+1
                            if option[0] == Game.TUNNEL:
                                world.totalTunnels = world.totalTunnels+1
                # else try to create a new line
                else:
                    clickedIcon = -1
                    # see if any stops can create a new line
                    # dont use a for loop because we only want to
                    # find one new line
                    i = 0
                    while (i < len(world.stops)
                           and (not world.stops[i].withinRadius(mouseObject.x,
                                                                mouseObject.y,
                                                                Game.ENDPOINT_SEGMENT_DISTANCE))):
                        i = i+1
                    if i < len(world.stops) and world.resources[Game.LINE] > 0:
                        movingLine = world.createNewLine(mouseObject,
                                                         world.stops[i])
                        world.resources[Game.LINE] = world.resources[Game.LINE]-1
        elif event.type == pygame.MOUSEMOTION:
            # move the line around with the mouse
            if movingLine > -1:
                mouseObject.updateWithView(event.pos, cameraOffset)
                line = world.lines[movingLine]
                # if there are enough tunnels for the segments being edited
                # to go over the water, restrict them
                if world.resources[Game.TUNNEL]-len(line.mouseSegments) < 0:
                    for mouseSegment in line.mouseSegments:
                        mouseSegment.calculateData()
                    point = event.pos
                    if len(line.mouseSegments) == 1:
                        if line.mouseSegments[0].checkOverWater(worldSurface):
                            point = line.mouseSegments[0].getPointsOverWater(3, worldSurface)[0]
                            mouseObject.updateWithWorld(point)
                    elif (line.mouseSegments[0].checkOverWater(worldSurface)
                          and not line.mouseSegments[1].checkOverWater(worldSurface)):
                        segmentToFollow = 1
                    elif (line.mouseSegments[1].checkOverWater(worldSurface)
                          and not line.mouseSegments[0].checkOverWater(worldSurface)):
                        segmentToFollow = 0
                    elif (line.mouseSegments[0].checkOverWater(worldSurface)
                          and line.mouseSegments[1].checkOverWater(worldSurface)):
                        point = line.mouseSegments[segmentToFollow].getPointsOverWater(3, worldSurface)[0]
                        mouseObject.updateWithWorld(point)

                    if point == event.pos:
                        world.lines[movingLine].processMouseSegments(world.stops,
                                                                     mouseObject,
                                                                     cameraOffset,
                                                                     worldSurface)
                else:
                    world.lines[movingLine].processMouseSegments(world.stops,
                                                                 mouseObject,
                                                                 cameraOffset,
                                                                 worldSurface)
            # if the a train is being clicked and moved, see if it can be
            # attached to a line
            elif movingTrain != -1:
                mouseObject.updateWithView(event.pos, cameraOffset)
                movingTrain[0].movingClone.updateMouse(mouseObject)
                segment = world.getSegmentFromWorld(mouseObject,
                                                    cameraOffset)
                if segment != -1:
                    if movingTrain[1] == "train":
                        movingTrain[0].movingClone.unsnapFromLine()
                        movingTrain[0].movingClone.snapToLine(world.lines[segment[0]],
                                                              segment[1])
                    elif movingTrain[1] == "carriage":
                        movingTrain[0].movingClone.unsnapFromLine()
                        movingTrain[0].movingClone.snapToLine(world.lines[segment[0]])
                else:
                    movingTrain[0].movingClone.unsnapFromLine()
            # see if a newly created carriage can go to a line
            elif clickedIcon == Game.CARRIAGE:
                mouseObject.updateWithView(event.pos, cameraOffset)
                world.carriages[-1].updateMouse(mouseObject)
                line = world.getLineByHitbox(mouseObject, cameraOffset)
                if line != -1:
                    world.carriages[-1].unsnapFromLine()
                    world.carriages[-1].snapToLine(world.lines[line])
                else:
                    world.carriages[-1].unsnapFromLine()
            # see if a newly created train can go to a line
            elif clickedIcon == Game.TRAIN:
                mouseObject.updateWithView(event.pos, cameraOffset)
                world.trains[-1].updateMouse(mouseObject)
                # we have no way of isolating which line was
                # clicked on, so check every rect
                segment = world.getSegmentFromWorld(mouseObject,
                                                    cameraOffset)
                if segment != -1:
                    world.trains[-1].unsnapFromLine()
                    world.trains[-1].snapToLine(world.lines[segment[0]],
                                                segment[1])
                else:
                    world.trains[-1].unsnapFromLine()
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                # commit changes made by the line being edited
                if movingLine > -1:
                    line = world.lines[movingLine]
                    line.isMoving = False
                    movingLine = -1
                    if len(line.mouseSegments) > 1:
                        line.tempSegments.insert(line.mouseSegments[0].index+1,
                                                 Game.Segment(line.mouseSegments[0].firstPoint,
                                                              line.mouseSegments[1].firstPoint,
                                                              line.mouseSegments[1].index))
                    line.update(worldSurface, True)
                    # if the line has no segments, completely remove
                    # everything and return resources to the player
                    for i in range(len(world.lines)-1, -1, -1):
                        if len(world.lines[i].segments) == 0:
                            world.removeLine(i)
                # queue an operation to move the train
                elif movingTrain != -1:
                    if movingTrain[0].movingClone.isOnSegment:
                        trainsToMove.append(movingTrain[0].movingClone)
                    elif world.getClickedIcon(event.pos) > -1:
                        trainsToMove.append(movingTrain[0])
                    else:
                        movingTrain[0].stopMouseMove()
                    movingTrain = -1
                # create a new carriage on the line it was placed on
                elif clickedIcon == Game.CARRIAGE:
                    if world.carriages[-1].isOnSegment:
                        world.carriages[-1].placeOnLine(True, cameraOffset, world.passengerSize)
                    else:
                        world.carriages.pop()
                        world.resources[Game.CARRIAGE] = world.resources[Game.CARRIAGE]+1
                    clickedIcon = -1
                # create a new train on the line it was placed on
                elif clickedIcon == Game.TRAIN:
                    if world.trains[-1].isOnSegment:
                        world.trains[-1].placeOnLine()
                    else:
                        world.trains.pop()
                        world.resources[Game.TRAIN] = world.resources[Game.TRAIN]+1
                    clickedIcon = -1
        elif event.type == pygame.USEREVENT:  # music is done
            pygame.mixer.music.load(MUSIC[random.randint(0, 2)])
            pygame.mixer.music.play()

    newStopTimer.tick()
    # if the timer to create a new stop has ended
    if newStopTimer.checkTimer(not doneScaling, getNewStopTime(world.passengersMoved)):
        stop = random.randint(0, 99)
        if stop < 55:  # 55% chance of making a circle stop
            stopInfo = world.addRandomStop(Game.CIRCLE,
                                           scaledStopPolygons)
        elif stop < 90:  # 90-55 = 35% chance for triangles
            stopInfo = world.addRandomStop(Game.TRIANGLE,
                                           scaledStopPolygons)
        elif stop < 100:  # 100-90 = 10% chance for squares
            stopInfo = world.addRandomStop(Game.SQUARE,
                                           scaledStopPolygons)
        if stopInfo[0]:  # the game area was expanded
            # start the animation to move the camera
            oldCameraOffset = copy.deepcopy(cameraOffset)
            newCameraOffset = calculateCameraOffset(cWidth, cHeight, world)
            isScaling = True
            smoothScaleTimer.restart()
        # the game area did not expand because it is done expanding
        elif stopInfo[1] and not doneScaling:
            oldCameraOffset = copy.deepcopy(cameraOffset)
            newCameraOffset = calculateCameraOffset(cWidth, cHeight, world)
            isScaling = True
            smoothScaleTimer.restart()
            doneScaling = True

    switchStopTimer.tick()
    # if the timer to switch a common stop to a unique stop
    # has finished, restart and switch a stop
    if switchStopTimer.checkTimer(True):
        newShape = world.switchRandomStop(range(Game.SQUARE+1, Game.STAR+1),
                                          validStops,
                                          worldSurface)
        # if a shape was switched and the new shape hasn't already
        # been generated
        if newShape != -1 and newShape not in validStops:
            # add the stop to the list of stops that passengers
            # can go to
            validStops.append(newShape)

    gainResourcesTimer.tick()
    # if the timer to give the player resources has ended,
    # give the player a random resource and let them choose
    # another one between two valid options
    if gainResourcesTimer.checkTimer(True) and not pickingResource:
        if not paused:
            paused = togglePaused(paused, timers, world)
        options = [0, 1, 2, 3]
        if world.resources[Game.LINE]+len(world.lines) > 6:
            options.remove(Game.LINE)
        resource = random.choice(options)
        world.resources[resource] = world.resources[resource]+1
        if resource == Game.TUNNEL:
            world.totalTunnels = world.totalTunnels+1
        pickingResource = True
        if world.resources[Game.LINE]+len(world.lines) > 6 and Game.LINE in options:
            options.remove(Game.LINE)
        else:
            options.remove(resource)
        if len(options) > 2:
            options.remove(random.choice(options))
        options[0] = [options[0],
                      scaledIcons[options[0]],
                      pygame.Rect(cWidth-scaledIcons[options[0]].get_width()*4,
                                  scaledIcons[options[0]].get_height()*2.3,
                                  scaledIcons[options[0]].get_width(),
                                  scaledIcons[options[0]].get_height())]
        options[1] = [options[1],
                      scaledIcons[options[1]],
                      pygame.Rect(cWidth-scaledIcons[options[1]].get_width()*2,
                                  scaledIcons[options[1]].get_height()*2.3,
                                  scaledIcons[options[1]].get_width(),
                                  scaledIcons[options[1]].get_height())]

    newPassengerTimer.tick()
    newPassengerProbability = min(interpolateLinear(world.passengersMoved, 1200, 30, 50), 50)
    # if the passenger spawn timer has finished,
    # restart it and add some passengers
    if newPassengerTimer.checkTimer(True, getNewPassengerTime(world.passengersMoved)):
        for stop in world.stops:
            # random chance for each stop to get a passenger
            if random.randint(0, 99) < newPassengerProbability:
                stop.addRandomPassenger(validStops,
                                        scaledPassengerPolygons)

    passengerMoveTimer.tick()
    # timer that synchronizes and adds delay to all movements to/from stops
    if passengerMoveTimer.checkTimer(True, getPassengerMoveTime(world.passengersMoved)):
        for stop in world.stops:
            for train in stop.trains:
                world.passengersMoved = (world.passengersMoved
                                         + stop.processTrain(train, trainsToMove))
            # start counting up with timers on stops if they are overcrowing
            if len(stop.passengers) > 6:
                if not stop.usingTimer:
                    stop.usingTimer = True
                    if not stop.timer.isActive:
                        stop.timer.toggleActive()
                if stop.timer.timeMode != Time.MODE_STOPWATCH:
                    stop.timer.tick()
                    stop.timer = Time.Time(Time.MODE_STOPWATCH,
                                           Time.FORMAT_TOTAL_SECONDS,
                                           stop.timer.time)
            # the stop is no longer overcrowding, so start making the timer
            # go back down
            else:
                if stop.usingTimer and stop.timer.timeMode == Time.MODE_STOPWATCH:
                    stop.timer.tick()
                    stop.timer = Time.Time(Time.MODE_TIMER,
                                           Time.FORMAT_TOTAL_SECONDS,
                                           stop.timer.time)
                if stop.timer.checkTimer(False):
                    stop.timer = Time.Time(Time.MODE_STOPWATCH,
                                           Time.FORMAT_TOTAL_SECONDS,
                                           0)
                    stop.usingTimer = False
                    if stop.timer.isActive:
                        stop.timer.toggleActive()
            # if the timer has counted past the threshold to lose the game
            if stop.timer.time > Game.LOSE_DURATION:
                if not paused:
                    paused = togglePaused(paused, timers, world)
                    smoothScaleTimer.toggleActive()
                isScaling = True
                oldCameraOffset = copy.deepcopy(cameraOffset)
                stopPosition = stop.getPosition()
                newCameraOffset = [[cWidth/150.0,
                                    cHeight/150.0],
                                   [stopPosition[0]-75,
                                    stopPosition[1]-75]]
                window = "end"
                smoothScaleTimer.restart()

    gameTimer.tick()
    timeElapsed = gameTimer.time
    gameTimer.restart(timeElapsed % getGameTimerTime(world.passengersMoved))
    # run the actual moving elements controlled by the game at a certain speed
    # independent of the speed the screen refreshes
    # (since the scaling animation is limited by the cpu and
    # using multithreading is overkill)
    for tick in range(int(timeElapsed/getGameTimerTime(world.passengersMoved))):
        for i in range(len(world.trains)-1, -1, -1):
            # move trains
            if world.trains[i].canMove:
                world.trains[i].move(cameraOffset, world.passengerSize)
            # if there are no passengers on the train and the train
            # is in the list to move trains, move it
            if len(world.trains[i].passengers) == 0:
                # if the moving clone is in the list, that means it needs to
                # be moved into another line
                if world.trains[i].movingClone in trainsToMove:
                    trainsToMove.remove(world.trains[i].movingClone)
                    if (world.trains[i].stop is not None
                            and world.trains[i] in world.trains[i].stop.trains):
                        world.trains[i].stop.trains.remove(world.trains[i])
                    world.trains[i] = world.trains[i].moveLines(cameraOffset, world.passengerSize)
                # if the train itself is in the list, that means it needs
                # to be removed from the world
                elif world.trains[i] in trainsToMove:
                    trainsToMove.remove(world.trains[i])
                    if world.trains[i] in world.trains[i].stop.trains:
                        world.trains[i].stop.trains.remove(world.trains[i])
                    for carriage in world.trains[i].carriages:
                        world.carriages.remove(carriage)
                        world.resources[Game.CARRIAGE] = world.resources[Game.CARRIAGE]+1
                    world.trains[i].line.trains.remove(world.trains[i])
                    world.trains[i].remove()
                    world.resources[Game.TRAIN] = world.resources[Game.TRAIN]+1
                    world.trains.pop(i)
        for i in range(len(world.carriages)-1, -1, -1):
            # if the number of passengers on the train is low enough
            # to take out a carriage:
            if (world.carriages[i].head is not None
                    and (len(world.carriages[i].findFirst().passengers)
                         <= len(world.carriages[i].findFirst().carriages)*6)):
                # move it to another line
                if world.carriages[i].movingClone in trainsToMove:
                    trainsToMove.remove(world.carriages[i].movingClone)
                    # find the last carriage to move off
                    tail = world.carriages[i].findLast()
                    train = world.carriages[i].movingClone.head  # destination train
                    tail.moveLines(train, len(train.carriages), cameraOffset, world.passengerSize)
                    world.carriages[i].stopMouseMove()
                # remove it
                elif world.carriages[i] in trainsToMove:
                    trainsToMove.remove(world.carriages[i])
                    tail = world.carriages[i].findLast()
                    world.carriages[i].stopMouseMove()
                    world.carriages.remove(tail)
                    tail.findFirst().carriages.remove(tail)
                    tail.remove()
                    world.resources[Game.CARRIAGE] = world.resources[Game.CARRIAGE]+1

        for line in world.lines:
            # remove abandoned segments that are split off lines
            # if there are no trains or carriages on them
            for i in range(len(line.abandonedChildren)-1, -1, -1):
                isClear = True
                if len(line.abandonedChildren[i].trains) > 0:
                    isClear = False
                for train in line.trains:
                    for carriage in train.carriages:
                        if carriage.line == line.abandonedChildren[i]:
                            isClear = False
                if isClear:
                    line.abandonedChildren.pop(i)

    if isScaling:
        # scale out the game view
        smoothScaleTimer.tick()
        for i in range(len(cameraOffset)):
            for j in range(len(cameraOffset[i])):
                cameraOffset[i][j] = interpolateQuadratic(scaleDuration-smoothScaleTimer.time,
                                                          scaleDuration,
                                                          oldCameraOffset[i][j],
                                                          newCameraOffset[i][j])
        stopView = int(world.stopSize*((cameraOffset[0][0]+cameraOffset[0][1])/2.0))
        newWidth = int(wWidth*cameraOffset[0][0])
        newHeight = int(wHeight*cameraOffset[0][1])
        scaledWorldSurface = pygame.Surface((newWidth, newHeight))
        pygame.transform.scale(worldSurface,
                               (newWidth,
                                newHeight),
                               scaledWorldSurface)
        for i in range(len(scaledStopPolygons)):
            scaledStopPolygons[i] = pygame.transform.smoothscale(STOP_POLYGONS[i],
                                                                 (stopView,
                                                                  stopView))
        if smoothScaleTimer.checkTimer(True):
            isScaling = False

    clock.tick(70)
    drawOverlay()
    pygame.display.update()
pygame.quit()
