import os
from time import sleep
import subprocess
import time
import shutil

while True: #forever do the following
    file_exists = os.path.exists('/home/pi/Desktop/recieve/results/z.csv') #check that z.csv has been recieved (named as to be recieved last, ie. indicating all files have been recieved)
    if file_exists == True: #if it has been recieved
        print("recieved") #print as such
        subprocess.run(["scp","/home/pi/Desktop/recieve/receipt.csv", "pi@192.168.0.24:/home/pi/Desktop/recieve"]) #send a reciept
        shutil.copy('/home/pi/Desktop/recieve/results/log.csv', '/home/pi/Desktop/processing/log.csv') #copy the log to the processing folder
        shutil.rmtree('/home/pi/Desktop/processing/current/') #delete old processing folder
        shutil.copytree('/home/pi/Desktop/recieve/results/', '/home/pi/Desktop/processing/current/') #copy the results to the processing folder
        os.rename("/home/pi/Desktop/recieve/results" , "/home/pi/Desktop/archive/"+time.asctime()) #move the results to the archive and timestamp it
        quit() #close the program
    else: #if it has not been recieved
        print("waiting") #print as such
    sleep(0.1) #wait 0.1s to reduce resource use