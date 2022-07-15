import subprocess
from guizero import App, PushButton, Text
import time
import os
import shutil
import csv

#Define file pathes
source_path = "/home/pi/Desktop/Object_Detection/results/" #defien path to send
destination_path = "/home/pi/Desktop/recieve" #define where to send to 
server_ip = "192.168.0.159" #define who to send to
client_ip = "192.168.0.24" #define my address
image_path = source_path+"images/" #define image folder location
client_receipt_path = "/home/pi/Desktop/Object_Detection/results/client_receipt.csv"
server_receipt_path = "/home/pi/Desktop/recieve/server_receipt.csv" #define receipt location

#define/initialize some variables
timeout_time = 10 #define timeout time in seconds
sleep_time = 0.1 #time in seconds between file checks, increase to lower resource use
size = 0 #intialize size variable
elapsed_time = 0 #initialize elapsed time

#delete the old receipt
try:
    os.remove(server_receipt_path) #attempt to delete the old receipt
except: #on fail
    pass #do nothing

#get image folder size
for n in os.scandir(image_path): #for every item in the directory do the following
    size = size+os.path.getsize(n) #add the size of the file to size

#write the folder size to the client reciept
rec = open(client_receipt_path, 'w') #open the client receipt in write mode
writer = csv.writer(rec) #build a writer
writer.writerow([str(size)]) #write over the first row with the folder size as a single entry
writer.writerow([client_ip]) #write over the second row with client ip as a single entry
rec.close() #close/save the cient receipt

#transmit
subprocess.call(["scp","-r",source_path, "pi@"+server_ip+":"+destination_path])#send entire source folder

#check that server has responded
start_time = time.time() #grab transmit start time
while elapsed_time < timeout_time: #if time since transmit start is less than the timout limit
    elapsed_time = time.time()-start_time #update the elapsed time
    file_exists = os.path.exists(server_receipt_path) #check for the reciept from the recipient
    if file_exists == True: #if the reciept is found
        
        #wipe the images folder
        #shutil.rmtree(image_path) #delete the images folder and all the files within
        #os.mkdir(image_path) #recreate the images folder
        
        #creat success popup
        notif = App(title="Status", width = 200, height = 100) #create the main application window
        text = Text(notif, text="Files Recieved") #create notification text
        button = PushButton(notif, command=quit, text="OK") #press okay button to close the program
        notif.display() #intialize the gui
    time.sleep(sleep_time) #wait for sleep time (lowers time between file checks to lower resource use

#create failure popup
notif = App(title="Status Notification", width = 200, height = 100) #create the main application window
text = Text(notif, text="File transmission timed out") #create notification text
button = PushButton(notif, command=quit, text="OK")#press okay button to close the program
notif.display()
