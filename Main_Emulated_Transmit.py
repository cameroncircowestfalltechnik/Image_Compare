import subprocess
from guizero import App, PushButton, Text
import time
import os
import shutil

timeout_time = 10 #define timeout time in seconds
receipt_destination = "/home/pi/Desktop/recieve/receipt.csv" #define receipt location
sleep_time = 0.1 #time in seconds between file checks, increase to lower resource use

try:
    os.remove(receipt_destination) #attempt to delete the old receipt
except: #on fail
    pass #do nothing

subprocess.run(["scp","-r","/home/pi/Desktop/Object_Detection/results/", "pi@192.168.0.159:/home/pi/Desktop/recieve"])#send an entire folder


start_time = time.time() #grab transmit start time
elapsed_time = 0 #initialize elapsed time
while elapsed_time < timeout_time: #if time since transmit start is less than the timout limit
    elapsed_time = time.time()-start_time #update the elpased time
    file_exists = os.path.exists(receipt_destination) #check for the reciept from the recipient
    if file_exists == True: #if the reciept is found
        #create success popup
        os.rename("/home/pi/Desktop/Object_Detection/results/log.csv", "/home/pi/Desktop/recieve/log.csv")
        os.rename("/home/pi/Desktop/Object_Detection/results/startup_log.csv", "/home/pi/Desktop/recieve/log_startup.csv")
        os.rename("/home/pi/Desktop/Object_Detection/results/z.csv", "/home/pi/Desktop/recieve/z.csv")
        shutil.rmtree("/home/pi/Desktop/Object_Detection/results")
        os.mkdir("/home/pi/Desktop/Object_Detection/results")
        os.rename("/home/pi/Desktop/recieve/log.csv", "/home/pi/Desktop/Object_Detection/results/log.csv")
        os.rename("/home/pi/Desktop/recieve/log_startup.csv", "/home/pi/Desktop/Object_Detection/results/startup_log.csv")
        os.rename("/home/pi/Desktop/recieve/z.csv", "/home/pi/Desktop/Object_Detection/results/z.csv")
        notif = App(title="Status Notification", width = 200, height = 100) #create the main application window
        text = Text(notif, text="Files Recieved") #create notification text
        button = PushButton(notif, command=quit, text="OK") #press okay button to close the program
        notif.display() #intialize the gui
    time.sleep(sleep_time) #wait for sleep time

#if timout passes, create fail popup
notif = App(title="Status Notification", width = 200, height = 100) #create the main application window
text = Text(notif, text="File transmission timed out") #create notification text
button = PushButton(notif, command=quit, text="OK")#press okay button to close the program
notif.display()
