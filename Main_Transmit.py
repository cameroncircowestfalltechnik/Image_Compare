import subprocess
from guizero import App, PushButton, Text
import time
import os
import csv
import argparse
import shutil

#define file paths/defaults
base_folder = "/home/pi/Desktop/Main"
config_path = base_folder+"/config.txt" #define config file path
output_path = base_folder+"/output" #define path to send
destination_path = "/home/pi/Desktop/recieve" #define where to send to 
image_path = output_path+"/images/" #define image folder location
fail_image_path = output_path+"/fail/" #define fail image location
client_receipt_path = output_path+"/client_receipt.csv"
server_receipt_path = "/home/pi/Desktop/recieve/server_receipt.csv" #define receipt location
popups_allowed = False #by default disable popups (this means when this cript is called by crontab it wont make popups

#define arguments
parser = argparse.ArgumentParser() #start argument parser
parser.add_argument("-pop","--popup", action="store_true") #create argument to allow popups (it just needs to be entered to enable popups)
args = parser.parse_args() #parse the argument(s)

if args.popup:
    print("Popups allowed set to :"+str(args.popup))
    popups_allowed = args.popup

#Define/initialize some variables
timeout_time = 20 #define timeout time in seconds
sleep_time = 0.1 #time in seconds between file checks, increase to lower resource use
size = 0 #intialize size variable
elapsed_time = 0 #initialize elapsed time

def check_folder_size(path): #define code to get the size of a folder
    size = 0 #intialize size counter
    for entry in os.scandir(path): #for every entry in the specified path do the following
        if entry.is_file(): #if it is a file
            size = size+os.path.getsize(entry) #add the file size to the total size
        elif entry.is_dir(): #if it is a folder
            size = size+check_folder_size(entry.path) #get the size of the contents of the folder and add them to the total
    return size #return the folder size in bytes

#grab current config settings
with open(config_path,'r') as f: #open the config file
    lines = f.readlines() #write line by line to "lines"
server_ip = lines[11].strip() #read line 11 as the server IP
name = lines[12].strip() #read line 12 as the machine name

#grab the client IP
client_ip = subprocess.getoutput('hostname -I').rstrip() #grab the client ip and write it to client_ip

#clear the send folder if it still exists
try:
    shutil.rmtree(base_folder+"/send", ignore_errors=True) #delete the send folder and all the files within
except: #if it fails to delete
    pass #do nothing
#delete the old receipt
try:
    os.remove(server_receipt_path) #attempt to delete the old receipt
except: #on fail
    pass #do nothing

size = check_folder_size(output_path) #run check folder size function and save folder size to size
#write the folder size to the client reciept
rec = open(client_receipt_path, 'w') #open the client receipt in write mode
writer = csv.writer(rec) #build a writer
writer.writerow([str(size)]) #write over the first row with the folder size as a single entry
writer.writerow([client_ip]) #write over the second row with client ip as a single entry
writer.writerow([name]) #write over the third row with the machine name as a single entry
rec.close() #close/save the cient receipt

#transmit
print("Attempting Transmission")
try: #try the following
    subprocess.check_output(["scp","-r",client_receipt_path, "pi@"+server_ip+":"+destination_path])#send the client receipt
except subprocess.CalledProcessError: #upon an error (no route to host)
    #Print Error and terminate
    if popups_allowed:
        notif = App(title="Status", width = 400, height = 150) #create the main application window
        Text(notif, text="Unable to find Server\n\nThe error may be cause by the following:\n-Either server or client are not connected to internet\n-Specified server IP is incorrect") #create notification text
        PushButton(notif, command=quit, text="OK") #press ok button to close the program
        notif.display() #intialize the gui
    else:
        print("Error: server not found")
        quit()

#rename output and rebuild it so that images can continue to be saved
os.rename(output_path,base_folder+"/send") #rename output to "send"
os.mkdir(output_path) #reacreate output
shutil.copy(base_folder+"/log_template.csv",output_path+"/log.csv") #copy the log template over and name it log (this effectively adds back an empty log)
shutil.copyfile(base_folder+"/send/startup_log.csv",output_path+"/startup_log.csv") #copy over the startup log from send
shutil.copyfile(base_folder+"/send/client_receipt.csv",output_path+"/client_receipt.csv") #copy over the client receipt from send
os.mkdir(image_path) #recreate the image path
os.mkdir(fail_image_path) #recreate the fail path
os.system("sudo chmod 777 -R "+output_path) #set the permissions to full for all users

subprocess.check_output(["scp","-r",base_folder+"/send", "pi@"+server_ip+":"+destination_path])#send entire "send" folder

#check that server has responded
start_time = time.time() #grab transmit start time
while elapsed_time < timeout_time: #if time since transmit start is less than the timout limit
    elapsed_time = time.time()-start_time #update the elapsed time
    file_exists = os.path.exists(server_receipt_path) #check for the reciept from the recipient
    if file_exists == True: #if the reciept is found
        
        #wipe the images folder
        shutil.rmtree(base_folder+"/send", ignore_errors=True) #delete the send folder and all the files within
        os.remove(server_receipt_path) #delete the server receipt
        #report complete status
        if popups_allowed:
            notif = App(title="Status", width = 200, height = 100) #create the main application window
            Text(notif, text="Files Recieved") #create notification text
            PushButton(notif, command=quit, text="OK") #press okay button to close the program
            notif.display() #intialize the gui
        else:
            print("Files Recieved") #print status
            quit() #close the script
    time.sleep(sleep_time) #wait for sleep time (lowers time between file checks to lower resource use

#create failure notification
if popups_allowed:
    notif = App(title="Status Notification", width = 200, height = 100) #create the main application window
    Text(notif, text="File transmission timed out") #create notification text
    PushButton(notif, command=quit, text="OK")#press okay button to close the program
    notif.display()
else:
    print("Error: timed out") #print to terminal
    quit() #close the script


