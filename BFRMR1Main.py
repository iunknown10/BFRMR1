#!/usr/bin/python

########################################################################################
#
# |B|I|G| |F|A|C|E| |R|O|B|O|T|I|C|S|
#
# A Python script for controlling the BFRMR1 mobile robot
#
#
# Author : Peter Neal
#
# Date : 30 July 2014
#
########################################################################################

import BFRMR1tft
import RPi.GPIO as GPIO
import time
import BFRMR1serialport
import os
import BFRMR1OpenCV
import numpy
import math

GPIO.setup(4, GPIO.IN) #Buttons
GPIO.setup(17, GPIO.IN)
GPIO.setup(21, GPIO.IN)
GPIO.setup(22, GPIO.IN)

RunFindFood = False
RunExplore = False
ViewData = False
TurnRatio = 3.4
RunForwardScan = True

ScreenCounter = 0
PointerCounterMain = 0
PointerCounterTest = 0

# ScreenCounter

MAINSCREEN = 0
FINDFOODSCREEN = 1
EXPLORESCREEN = 2
VIEWDATASCREEN = 3
TESTMOVESCREEN = 4
STOPPINGSCREEN = 255

MapWidth = 200
MapHeight = 200
MapScale = 5 #Map is divided by scale value. The higher the value, the smaller the map


# Data Packet from robot
#
# Byte  Description
# 0	Left Looking IR		
# 1	Centre IR
# 2	Right Looking IR
# 3	Head Pan Position
# 4	Head Tilt Position
# 5	Sonar Sensor
# 6	Left Encoder
# 7	Right Encoder
#          
########################################################################################
#
# Opencv threshold values
#
########################################################################################

YELLOWOBJECTS = [10,160,160,40,255,255]
BLUEOBJECTS = [40,120,120,160,255,255]
ORANGEOBJECTS = [5,170,170,15,255,255]





########################################################################################
#
# Robot control variables
#
########################################################################################
#Instructions
GETDATA = 0
ROBOTFORWARD = 1
ROBOTLEFT = 2
ROBOTRIGHT = 3
ROBOTREVERSE = 4
HEADMOVE = 5
PLAYTONE = 6

headpan = 128
headtilt = 128
LeftEncoderTotal = 0
RightEncoderTotal = 0
SonarThreshold = 20
IRThreshold = 60
AutoSpeed = 5  #speed of robot during automatic operation

########################################################################################
# HeadMove
#
# Takes three arguments of head pan and head tilt angle and speed. The angle is converted to a value
# between 0 and 255 to be sent to arduino. Min angle -80 degrees, Max 80 degrees. Speed value should
# be between 0 and 10.
# Returns a packet of sensor data recieved from robot when command is complete.
########################################################################################
def HeadMove(pan,tilt,speed):

    panservovalue = int(128-(pan*1.45)) #convert from angle to value between 0 and 255
    tiltservovalue = int(128+(tilt*1.45))
    if speed <= 10:
        BFRMR1serialport.sendserial([255, 255, HEADMOVE, panservovalue, tiltservovalue, speed, 0]) #send command to move head
        while True:
            a = BFRMR1serialport.getserial() #wait here until data is received to confirm command complete
            if a is not None:
                break    
        return a #return data packet
    else:
        print "Speed out of range. Value should be between 0 and 10"
    

########################################################################################
# RobotMove
#
# Used to move robot either forward, backwards or turn. Takes a direction argument:
# ROBOTFORWARD = 1
# ROBOTLEFT = 2
# ROBOTRIGHT = 3
# ROBOTREVERSE = 4
# Encodercount argument dictates distance to move/turn and speed is self explanatory.
# Speed values between 1 and 10 are sensible
# Returns a packet of sensor data recieved from robot when command is complete.
########################################################################################
def RobotMove(direction,encodercount,speed, SonarThreshold, IRThreshold):

    # 3.4 degrees = 1 encoder count for a turn
    BFRMR1serialport.sendserial([255, 255, direction, encodercount, speed, SonarThreshold, IRThreshold]) #send command to move head
    while True:
        a = BFRMR1serialport.getserial() #wait here until data is received to confirm command complete
        if a is not None:
            break 
       
    return a #return data packet

########################################################################################
# GetData
#
# Sends a command to the robot to trigger a packet of sensor data to be returned.
# Returns a packet of sensor data received from robot.
########################################################################################
def GetData():
    BFRMR1serialport.sendserial([255, 255, GETDATA, 0, 0, 0, 0]) #send command to get sensor data from robot
    while True:
        a = BFRMR1serialport.getserial() #wait here until data is received to confirm command complete
        if a is not None:
            break    
    return a #return data packet

########################################################################################
# PlayTone
#
# Sends a command to the robot to play a tone dictated by toneselection argument.
########################################################################################
def PlayTone(toneselection):
    BFRMR1serialport.sendserial([255, 255, PLAYTONE, toneselection, 0, 0, 0]) #send command to play a tone
    return
########################################################################################
#
# Test moves routine. Will execute a move depending on value of PointerCounterTest
#
########################################################################################

def Turn180():
    RobotData = RobotMove(ROBOTLEFT,int(180/TurnRatio),3, 0, 255) #no sonar or IR threshold so move always completes
    print RobotData

def Turn360():
    RobotData = RobotMove(ROBOTLEFT,int(360/TurnRatio),3, 0, 255) #no sonar or IR threshold so move always completes
    print RobotData

def MoveForward():
    RobotData = RobotMove(ROBOTFORWARD,50,AutoSpeed, 0, 255) #no sonar or IR threshold so move always completes
    print RobotData

def MoveReverse():
    RobotData = RobotMove(ROBOTREVERSE,50,AutoSpeed, 0, 255) #no sonar or IR threshold so move always completes
    print RobotData

########################################################################################
#
# DrawLineBresenham
#
# Thanks to http://www.roguebasin.com/index.php?title=Bresenham%27s_Line_Algorithm
#
########################################################################################
def DrawLineBresenham(MapArray, x1, y1, x2, y2, IncValue):
    
    issteep = abs(y2-y1) > abs(x2-x1)
    if issteep:
        x1, y1 = y1, x1
        x2, y2 = y2, x2
    
    if x1 > x2:
        x1, x2 = x2, x1
        y1, y2 = y2, y1
        
    deltax = x2 - x1
    deltay = abs(y2-y1)
    error = int(deltax / 2)
    y = y1
    ystep = None
    if y1 < y2:
        ystep = 1
    else:
        ystep = -1

    for x in range(x1, x2 + 1):    
              
        if(y > 0 and y < MapHeight and x > 0 and x < MapWidth):
            if issteep:
                NewValue = MapArray.item(x,y) + IncValue
                MapArray.itemset(x,y,NewValue)
            else:
                NewValue = MapArray.item(y,x) + IncValue
                MapArray.itemset(y,x,NewValue)

        error -= deltay
        if error < 0:
            y += ystep
            error += deltax

    return MapArray
    

########################################################################################
#
# AddToMap
#
# Takes an array of x,y coordinates as an arguement and uses this to plot free space
# and obstacles on the map. Also takes as an arguement the map array to plot to.
#
########################################################################################
def AddToMap(MapArray,CoordArray):
    
    MapHeightfloat = float(MapHeight)

    #Plot free space between robot and objects detected
    for x in range(0,(len(CoordArray)),1):
         CurrentPoint = CoordArray[x]
         CurrentX = MapWidth/2 + CurrentPoint[0] #Convert to map coordinates
         CurrentY = MapHeight - CurrentPoint[1]
         MapArray = DrawLineBresenham(MapArray,MapWidth/2,MapHeight ,CurrentX,CurrentY, 0.1)

    #Plot area beyond free space as occupied
    for x in range(0,(len(CoordArray)),1):
         CurrentPoint = CoordArray[x]
         CurrentX = MapWidth/2 + CurrentPoint[0] #Convert to map coordinates
         CurrentY = MapHeight - CurrentPoint[1]
         Scale = abs(MapHeightfloat/CurrentPoint[1])
         EndX = int(MapWidth/2 + (CurrentPoint[0] * Scale))
         EndY = int(MapHeight - (CurrentPoint[1] * Scale))
         MapArray = DrawLineBresenham(MapArray,CurrentX,CurrentY ,EndX,EndY, -0.1)

    return MapArray
 



########################################################################################
#
# FindFoodTargets
#
# Scan area in front of robot and return an array containing coordinates and sizes of
# yellow objects found
#
########################################################################################
def FindFoodTargets():

    FoodTargets = [] #create a main array to store all target coordinates found during scan

    for x in range(-20,21,20):
        HeadTiltAngle = x
        for y in range(-50,51,50):
            HeadPanAngle = y
            RobotData = HeadMove(HeadPanAngle,HeadTiltAngle, 7)
            time.sleep(0.5) #small delay, let image settle
            TargetCoords = BFRMR1OpenCV.FindObjects(YELLOWOBJECTS, 1000, RobotData[5],HeadPanAngle,HeadTiltAngle,MapScale)
            print "Target Coordinates",TargetCoords
            BFRMR1OpenCV.AddToMap(MapArray,TargetCoords)
            BFRMR1OpenCV.ShowMap(MapArray)
            #if len(TargetCoords) > 0: #Targets found in current image frame
            #    for x in range(0,len(TargetCoords),4): #cycle through coordinate values returned from image analysis
            #       FoodTargets.append(TargetCoords[x])
            #        FoodTargets.append(TargetCoords[x+1])
                    #FoodTargets.append(TargetCoords[x+2]) #object size
                    #FoodTargets.append(TargetCoords[x+3]) #object distance
   
                
    return FoodTargets

########################################################################################
#
# RankTargetsSize
#
# Takes an array of target coordinates as an argument. Format of array is:
# [x, y, size, distance, x, y, size, distance .......]
# Finds the largest object in the array and forms an array for best target in the form:
# [x, y, size, distance]
# This is returned
########################################################################################
def RankTargetsSize(TargetArray):

    LargestObject = TargetArray[2]
    LargestObjectIndex = 2
    for x in range(6,len(TargetArray),4): #compare size of objects
        if TargetArray[x] > LargestObject:
            LargestObject = TargetArray[x]
            LargestObjectIndex = x

    LargestObjectCoords = [] #create new array of coordinates of largest object
    LargestObjectCoords.append(TargetArray[LargestObjectIndex-2])
    LargestObjectCoords.append(TargetArray[LargestObjectIndex-1])
    LargestObjectCoords.append(TargetArray[LargestObjectIndex])
    LargestObjectCoords.append(TargetArray[LargestObjectIndex+1])

    return LargestObjectCoords

########################################################################################
#
# Button 0 Interrupt Routine
#
########################################################################################
def Button0Pressed(channel):  
    print "Button 0 pressed"
    global PointerCounterMain
    global PointerCounterTest
    global ScreenCounter
    global AutoSpeed
    if ScreenCounter is MAINSCREEN:
        if PointerCounterMain > 0:
            PointerCounterMain -= 1
            BFRMR1tft.EditMainScreen(PointerCounterMain)
    if ScreenCounter is TESTMOVESCREEN:
        if PointerCounterTest > 0:
            PointerCounterTest -= 1
            BFRMR1tft.EditTestMoveScreen(PointerCounterTest)
    if ScreenCounter is EXPLORESCREEN:
        if AutoSpeed > 1:
            AutoSpeed -= 1
            BFRMR1tft.EditExploreScreen(2,AutoSpeed,0)
    
########################################################################################
#
# Button 1 Interrupt Routine
#
########################################################################################
def Button1Pressed(channel):  
    print "Button 1 pressed"
    global PointerCounterMain
    global PointerCounterTest
    global ScreenCounter
    global AutoSpeed
    if ScreenCounter is MAINSCREEN:
        if PointerCounterMain < 5:
            PointerCounterMain += 1
            BFRMR1tft.EditMainScreen(PointerCounterMain)
    if ScreenCounter is TESTMOVESCREEN:
        if PointerCounterTest < 4:
            PointerCounterTest += 1
            BFRMR1tft.EditTestMoveScreen(PointerCounterTest)
    if ScreenCounter is EXPLORESCREEN:
        if AutoSpeed < 10:
            AutoSpeed += 1
            BFRMR1tft.EditExploreScreen(2,AutoSpeed,0)
    
########################################################################################
#
# Button 2 Interrupt Routine
#
########################################################################################
def Button2Pressed(channel):
    print "Button 2 pressed"
    global PointerCounterMain
    global PointerCounterTest
    global ScreenCounter
    global RunFindFood
    global RunExplore
    global ViewData
    global RunForwardScan

    if ScreenCounter is TESTMOVESCREEN:
        if PointerCounterTest is 0:
            Turn180()
        if PointerCounterTest is 1:
            Turn360()
        if PointerCounterTest is 2:
            MoveForward()
        if PointerCounterTest is 3:
            MoveReverse()
        if PointerCounterTest is 4:
            RunForwardScan = True

    if ScreenCounter is MAINSCREEN:
        if PointerCounterMain is 0:
            ScreenCounter = FINDFOODSCREEN
            BFRMR1tft.FindFoodScreen()
            RunFindFood = True
            
        if PointerCounterMain is 2:
            ScreenCounter = EXPLORESCREEN
            BFRMR1tft.ExploreScreen()
            BFRMR1tft.EditExploreScreen(2,AutoSpeed,0)
            RunExplore = True
            
        if PointerCounterMain is 3:
            ScreenCounter = VIEWDATASCREEN
            BFRMR1tft.ViewDataScreen()
            ViewData = True

        if PointerCounterMain is 4:
            ScreenCounter = TESTMOVESCREEN
            BFRMR1tft.TestMoveScreen()
            
    
            
            
########################################################################################
#
# Button 3 Interrupt Routine
#
########################################################################################            
def Button3Pressed(channel):
    print "Button 3 pressed"
    global PointerCounterMain
    global ScreenCounter
    global RunFindFood
    global RunExplore
    global ViewData
    global RunForwardScan
    if ScreenCounter is FINDFOODSCREEN:
        ScreenCounter = STOPPINGSCREEN
        BFRMR1tft.StoppingScreen()
        RunFindFood = False
        
    if ScreenCounter is EXPLORESCREEN:
        ScreenCounter = STOPPINGSCREEN
        BFRMR1tft.StoppingScreen()
        RunExplore = False

    if ScreenCounter is VIEWDATASCREEN:
        ScreenCounter = STOPPINGSCREEN
        BFRMR1tft.StoppingScreen()
        ViewData = False
        
    if ScreenCounter is TESTMOVESCREEN:
        ScreenCounter = MAINSCREEN
        BFRMR1tft.MainScreen()
        BFRMR1tft.EditMainScreen(PointerCounterMain)
        RunForwardScan = False



########################################################################################
#
# Main
#
########################################################################################

BFRMR1tft.MainScreen()
GPIO.add_event_detect(4,  GPIO.FALLING, callback=Button0Pressed, bouncetime=200)
GPIO.add_event_detect(17, GPIO.FALLING, callback=Button1Pressed, bouncetime=200)
GPIO.add_event_detect(21, GPIO.FALLING, callback=Button2Pressed, bouncetime=200)
GPIO.add_event_detect(22, GPIO.FALLING, callback=Button3Pressed, bouncetime=200)

MapArray = numpy.zeros((MapWidth, MapHeight), numpy.float32) #numpy array for map
for x in range(MapArray.size):
    MapArray.itemset(x,0.5) #set all cell values to 0.5
for x in range(0,MapHeight,5):
    MapArray.itemset(x,0,1)

while True:
      

########################################################################################
#
# Find Food routine. Will run while RunFindFood is true
#
########################################################################################

    while RunFindFood is True:
        
        FoodTargets = FindFoodTargets() #look around for yellow objects
        if len(FoodTargets) is 0:
            #print "No target found" #no target found
            if ScreenCounter is FINDFOODSCREEN:
                BFRMR1tft.EditFindFoodScreen(0,0,0)
            PlayTone(1)      
        else:
            #print "Target found at", FoodTargets
            PlayTone(0)
            LargestObject = RankTargetsSize(FoodTargets) #find the largest target in the list
            if ScreenCounter is FINDFOODSCREEN:
                BFRMR1tft.EditFindFoodScreen(1,LargestObject[0],LargestObject[1])
            print "Largest target found at", LargestObject
            if LargestObject[0] > 0:
                # Turn to face largest object
                RobotData = RobotMove(ROBOTRIGHT,int(abs(LargestObject[0]/TurnRatio)),3, SonarThreshold, IRThreshold) 
            elif LargestObject[0] < 0:
                RobotData = RobotMove(ROBOTLEFT,int(abs(LargestObject[0]/TurnRatio)),3, SonarThreshold, IRThreshold)
            MoveDistance = 100
            RobotData = RobotMove(ROBOTFORWARD,MoveDistance,3, SonarThreshold, IRThreshold)
            print RobotData
            if ScreenCounter is FINDFOODSCREEN:
                BFRMR1tft.EditFindFoodScreen(2,RobotData[6],RobotData[7])
            if RobotData[6] >= MoveDistance and RobotData[7] >= MoveDistance:
                if ScreenCounter is FINDFOODSCREEN:
                    BFRMR1tft.EditFindFoodScreen(3,0,0)
                print "No obstacle - All is well"
            else:
                if RobotData[5] <= SonarThreshold:
                    if ScreenCounter is FINDFOODSCREEN:
                        BFRMR1tft.EditFindFoodScreen(3,1,0)
                    print "Obstacle encountered - Sonar Sensor"
                if RobotData[0] >= IRThreshold:
                    if ScreenCounter is FINDFOODSCREEN:
                        BFRMR1tft.EditFindFoodScreen(3,2,0)
                    print "Obstacle encountered - Left IR"
                elif RobotData[1] >= IRThreshold:
                    if ScreenCounter is FINDFOODSCREEN:
                        BFRMR1tft.EditFindFoodScreen(3,2,1)
                    print "Obstacle encountered - Centre IR"
                elif RobotData[2] >= IRThreshold:
                    if ScreenCounter is FINDFOODSCREEN:
                        BFRMR1tft.EditFindFoodScreen(3,2,2)
                    print "Obstacle encountered - Right IR"

        if RunFindFood is False:
            ScreenCounter = MAINSCREEN
            BFRMR1tft.MainScreen()
            BFRMR1tft.EditMainScreen(PointerCounterMain) 
        

########################################################################################
#
# Explore routine. Obstacle avoidance
#
########################################################################################


    while RunExplore is True:

        MoveDistance = 250
        if ScreenCounter is EXPLORESCREEN: #Only write to screen if on Explore screen
            BFRMR1tft.EditExploreScreen(1,ROBOTFORWARD,0)
        RobotData = RobotMove(ROBOTFORWARD,MoveDistance,AutoSpeed, SonarThreshold, IRThreshold)
        print RobotData
        if RobotData[6] >= MoveDistance and RobotData[7] >= MoveDistance:
                if ScreenCounter is EXPLORESCREEN:
                    BFRMR1tft.EditExploreScreen(0,0,0)
                print "No obstacle - All is well"
        else:
                if RobotData[5] <= SonarThreshold: #Obstacle detected by sonar sensor
                    if ScreenCounter is EXPLORESCREEN:
                        BFRMR1tft.EditExploreScreen(0,1,0)
                    print "Obstacle encountered - Sonar Sensor"
                    MoveDistance = 20
                    if ScreenCounter is EXPLORESCREEN:
                        BFRMR1tft.EditExploreScreen(1,ROBOTREVERSE,0)
                    RobotData = RobotMove(ROBOTREVERSE,MoveDistance,AutoSpeed, 0, 255) #no sonar or IR threshold so move always completes
                    print RobotData
                    if ScreenCounter is EXPLORESCREEN:
                        BFRMR1tft.EditExploreScreen(1,ROBOTRIGHT,0)
                    RobotData = RobotMove(ROBOTRIGHT,int(180/TurnRatio),AutoSpeed, 0, 255) #no sonar or IR threshold so move always completes

                if RobotData[0] >= IRThreshold: #obstacle detected by left looking IR sensor
                    if ScreenCounter is EXPLORESCREEN:
                        BFRMR1tft.EditExploreScreen(0,2,0) #update tft screen
                    print "Obstacle encountered - Left IR"
                    if ScreenCounter is EXPLORESCREEN:
                        BFRMR1tft.EditExploreScreen(1,ROBOTRIGHT,0)
                    RobotData = RobotMove(ROBOTRIGHT,int(45/TurnRatio),AutoSpeed, 0, 255) #no sonar or IR threshold so move always completes

                elif RobotData[1] >= IRThreshold:  #obstacle detected by centre IR sensor
                    if ScreenCounter is EXPLORESCREEN:
                        BFRMR1tft.EditExploreScreen(0,3,0)
                    print "Obstacle encountered - Centre IR"
                    MoveDistance = 20
                    if ScreenCounter is EXPLORESCREEN:
                        BFRMR1tft.EditExploreScreen(1,ROBOTREVERSE,0)
                    RobotData = RobotMove(ROBOTREVERSE,MoveDistance,AutoSpeed, 0, 255) #no sonar or IR threshold so move always completes
                    print RobotData
                    if ScreenCounter is EXPLORESCREEN:
                        BFRMR1tft.EditExploreScreen(1,ROBOTRIGHT,0)
                    RobotData = RobotMove(ROBOTRIGHT,int(180/TurnRatio),AutoSpeed, 0, 255) #no sonar or IR threshold so move always completes

                elif RobotData[2] >= IRThreshold: #obstacle detected by right looking IR sensor
                    if ScreenCounter is EXPLORESCREEN:
                        BFRMR1tft.EditExploreScreen(0,4,0)
                    print "Obstacle encountered - Right IR"
                    if ScreenCounter is EXPLORESCREEN:
                        BFRMR1tft.EditExploreScreen(1,ROBOTLEFT,0)
                    RobotData = RobotMove(ROBOTLEFT,int(45/TurnRatio),AutoSpeed, 0, 255) #no sonar or IR threshold so move always completes


        if RunExplore is False:
            ScreenCounter = MAINSCREEN
            BFRMR1tft.MainScreen()
            BFRMR1tft.EditMainScreen(PointerCounterMain)

########################################################################################
#
# View data routine. Displays real time data from sensors
#
########################################################################################

    while ViewData is True:

        RobotData = GetData()
        print RobotData
        BFRMR1tft.EditViewDataScreen(RobotData[0], RobotData[1], RobotData[2], RobotData[3], RobotData[4], RobotData[5])
        time.sleep(0.05)


        if ViewData is False:
            ScreenCounter = MAINSCREEN
            BFRMR1tft.MainScreen()
            BFRMR1tft.EditMainScreen(PointerCounterMain)

########################################################################################
#
# Forward Scan routine. Scans area in front of robot with camera, looking for obstacles
#
########################################################################################

    while RunForwardScan is True:
        
        #for x in range(-10,11,10):
        #    HeadTiltAngle = x
        #    for y in range(-40,41,10):
        #        HeadPanAngle = y
        #        RobotData = HeadMove(HeadPanAngle,HeadTiltAngle, 8)
        #        time.sleep(0.1) #small delay, let image settle
        #        print "Scanning image"
        #        BFRMR1OpenCV.ReadQRCode()

        #MapArray = BFRMR1OpenCV.NewMap(MapWidth,MapHeight)
        
    

        #FoodTargets = FindFoodTargets() #look around for yellow objects
        #if len(FoodTargets) is 0:
        #    print "No target found" #no target found
        #    PlayTone(1)      
        #else:
        #    print "Target found at", FoodTargets
            #LargestObject = RankTargetsSize(FoodTargets) #find the largest target in the list
            #print "Largest target found at", LargestObject

        print "Find Ball"
        BallCentre = BFRMR1OpenCV.FindBall(ORANGEOBJECTS)
        if BallCentre is 0:
            print "Ball not found in image"
        else:
            print BallCentre
        
        if RunForwardScan is False:
            ScreenCounter = MAINSCREEN
            BFRMR1tft.MainScreen()
            BFRMR1tft.EditMainScreen(PointerCounterMain)


BFRMR1serialport.closeserial()  





