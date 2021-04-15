import socket
import json
import numpy as np
import time
import threading
import math
import rtde_control
import rtde_receive
import cv2
import pyrealsense2
from queue import Queue
from threading import Event




serverIP = '127.0.0.1'
serverPORT = 6000

armIP = "10.0.0.4"
armPORT = 30002

systemStatus = "Offline"

# armVelocity = 0

#For the demo, there will only be one drop position.
#However, for future projects, more can be added
#Will be set to a default position, however, user can change this
# place_position = np.zeros(6)


#Ready to add other functions for arm movement




#z axis = 109mm at workcell level.
#Tells server ready for TCP values
def TCPwrapper(in_q, conn, rtde_c, rtde_r):
    global systemStatus


    #For testing purposes
    systemStatus = "Online"
    #May not need armPosition
    #global armPosition


    #Place holders, set to defaults
    home_position = np.array([-0.093, -0.486, 0.530, 1.56, -2.62, -0.03])
    armVelocity = 0.3

    targetTCP = np.zeros(6)
    place_position = np.zeros(6)


    #Used for testing, remove for final version
    # jsonResult = {"first": "TCP Values", "second": "-0.514", "third": "-0.029" , "fourth": "0.220" , "fifth": "1.05" , "sixth": "-3", "seventh": "-0.15"  }
    #
    #
    # in_q.put(jsonResult)
    #
    # jsonResult = {"first": "Place Location", "second": "-0.050", "third": "-0.565" , "fourth": "0.270" , "fifth": "1.05" , "sixth": "-3", "seventh": "-0.15"  }
    #
    # in_q.put(jsonResult)

    while (True):


        if(systemStatus == "Online"):






                jsonResult = {"first":"Client 1", "second": "Ready for TCP Values"}
                send(conn, jsonResult)



                #Will empty queue at the beginning of each sequence
                #May check for velocity changes between each section.
                while(in_q.empty() == False):
                    jsonReceived = in_q.get()

                    if(jsonReceived["first"] == "TCP Values"):
                        targetTCP[0] = float(jsonReceived["second"])
                        targetTCP[1] = float(jsonReceived["third"])
                        targetTCP[2] = float(jsonReceived["fourth"])
                        targetTCP[3] = float(jsonReceived["fifth"])
                        targetTCP[4] = float(jsonReceived["sixth"])
                        targetTCP[5] = float(jsonReceived["seventh"])

                    elif(jsonReceived["first"] == "Place Location"):
                        place_position[0] = float(jsonReceived["second"])
                        place_position[1] = float(jsonReceived["third"])
                        place_position[2] = float(jsonReceived["fourth"])
                        place_position[3] = float(jsonReceived["fifth"])
                        place_position[4] = float(jsonReceived["sixth"])
                        place_position[5] = float(jsonReceived["seventh"])

                    elif(jsonReceived["first"] == "Velocity Change"):
                        armVelocity = jsonReceived["second"]

                #Async allows us to stop the arm
                #For safety or other issues


                #Called here so if user changes place position while arm is in seqeuence, changes for next sequence.

                #Not doing a current velocity since the user will likely will want the arm to change velocity as quickly as possible

                #This section moves the arm to pickup a package
                movRobot(rtde_c, targetTCP, armVelocity, 0.6, True, False)
                time.sleep(1)

                #armPosition = "Unknown"

                checkTCPValues(rtde_r, rtde_c, targetTCP, armVelocity)
                #
                # pickParcel()
                #
                # #################################################################
                #
                # armVelocity = checkVelocity(in_q, armVelocity)
                #
                # #This section moves the arm to parcel drop location
                movRobot(rtde_c, place_position, armVelocity, 1, True, True)
                time.sleep(1)


                checkTCPValues(rtde_r, rtde_c, place_position, armVelocity)
                #
                # placeParcel()

                #################################################################

                # armVelocity = checkVelocity(in_q, armVelocity)
                #
                movRobot(rtde_c, home_position, armVelocity, 1, True, False)
                time.sleep(1)

                checkTCPValues(rtde_r, rtde_c, home_position, armVelocity)

                #Arm at home position, ready to repeat

                #armPosition =  "Home"






#Ready for code
def pickParcel():
    print()

#Ready for code
def placeParcel():
    print()

def stopRobot(rtde_c):
    print()
    rtde_c.stopJ(2.0)

def movRobot(rtde_c, targetTCP,v, a, asnc, payload):

    if(v == "ECO"):
        if(payload == False):
            print()
            #Move at higher velocity
            rtde_c.moveL(targetTCP, v, a, asnc)

        elif(payload == True):
            print()
            #Reduce velocity by 20%
            rtde_c.moveL(targetTCP, v, a, asnc)

    else:
        #Assuming if v != ECO, is a int in string format
        v = int(v)
        rtde_c.moveL(targetTCP, 0.1, 0.1, asnc)
        print("MOVING TO POSITION")


def checkVelocity(in_q, currentArmVelocity):

    if (in_q.empty() == False):

        jsonReceived = in_q.get()

        if(jsonReceived["first"] == "Velocity Change"):
            armVelocity = jsonReceived["second"]
            return armVelocity
    else:
        #Get pops the data from the queue, putting data back into queue
        in_q.put(jsonReceived)
        return currentArmVelocity

#This function will be used to compare target TCP vs current TCP
def checkTCPValues(rtde_r, rtde_c, targetTCP, armVelocity):
    global systemStatus
    flag = 0

    currentTCPValues = rtde_r.getActualTCPPose()

    currentTCPValues = currentTCPValues[0:3]

    targetTCP = targetTCP[0:3]

    # print("Current TCP Values" + str(currentTCPValues))
    # print("Target TCP Values" + str(targetTCP))

    #Run in loop until arm arrives at targetTCP
    #Flag varible is used to moniter if the system is online
    #If flag is set to 1, means system stopped at some point.
    #Need to finish the last step before moving on.
    while ( np.allclose(currentTCPValues, targetTCP, 0.01) == False) :

        # print("Current TCP Values" + str(currentTCPValues))
        # print("Target TCP Values" + str(targetTCP))
        try:
            currentTCPValues = rtde_r.getActualTCPPose()
            time.sleep(1)
            currentTCPValues = currentTCPValues[0:3]

            if(flag == 0):

                if(systemStatus != "Online"):
                    flag = 1
                    stopRobot(rtde_c)

            elif(systemStatus == "Online"):

                if(flag == 1):
                    movRobot(rtde_c, targetTCP, armVelocity, 1, True)
        except Exception as error:
            print(error)
            print("Error is caught here")
            movRobot(rtde_c, targetTCP, armVelocity, 0.6, True, False)

            #currentTCPValues = rtde_r.getActualTCPPose()


def receive(conn):
    jsonReceived = conn.recv(1024)
    jsonReceived = json.loads(jsonReceived.decode("utf-8"))
    return jsonReceived

def send(conn, data):

    jsonResult = json.dumps(data)
    conn.send(bytes(jsonResult, encoding="utf-8"))


def moniterUserInput(out_q, conn):
    global systemStatus


    while(True):
        jsonReceived = receive(conn)

        #Add commands for this script
        #System Pasue, shutdown, velocity change, etc.

        if(jsonReceived["first"] == "System Started"):
            print("System online")
            systemStatus = "Online"

        elif(jsonReceived["first"] == "Go into Standby"):
            print("System in standby")
            systemStatus = "Standby"

        elif(jsonReceived["first"] == "Shut Down System"):
            print("System offline")
            systemStatus = "Offline"


        elif(jsonReceived["first"] == "Velocity Change"):
            print("Velocity Change")

            out_q.put((jsonReceived))

        elif(jsonReceived["first"] == "Place Location"):
            print("Drop Location Changed")

            out_q.put((jsonReceived))

        elif(jsonReceived["first"] == "TCP Values"):
            print("TCP Values")

            out_q.put((jsonReceived))




def main():
    connected = False

    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    rtde_c = 0
    rtde_r = 0

    #Connect to arm
    while not(connected):

        try:

            rtde_c = rtde_control.RTDEControlInterface(armIP)
            rtde_r = rtde_receive.RTDEReceiveInterface(armIP)
            connected = True
        except Exception as e:
            print(e)
        finally:
            time.sleep(1)

    #Move arm to home position


    # Reset variable
    # Connect to server.
    connected = False
    while not(connected):

        try:
            conn.connect((serverIP, serverPORT))
            connected = True
        except Exception as e:
            print(e)
        finally:
            time.sleep(1)

    q = Queue()
    # t1 = threading.Thread(target = moniterUserInput, args = (q, conn, ))
    t2 = threading.Thread(target = TCPwrapper, args = (q, conn, rtde_c, rtde_r,  ))

    #t1.start()
    t2.start()

    #t1.join()
    t2.join()



if __name__ == "__main__":
    main()
