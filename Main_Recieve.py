import os
from time import sleep
import subprocess
import time
import shutil
import csv

main_folder = "/home/pi/Desktop/recieve"
results_path = main_folder+"/output"
client_receipt_path = main_folder+"/client_receipt.csv" #define the location of the client receipt
server_receipt_path = main_folder+"/server_receipt.csv" #define the location of the server receipt
image_path = results_path+"images/" #define the location of recieved images
usb_path = "/media/pi/VISION_SYS1/Archive/" #define the location of the usb drive

processing_path = "/home/pi/Desktop/processing/" #define location of processing folder
archive_path = "/home/pi/Desktop/archive/" #defifne location of archive folder
server_receipt_dest = main_folder #define where in the client the server receipt should go

size_cap = None #create a container for the max size of the archive in bytes, this will be populated later
external_size_cap = int(57.3*0.9*100000000) #specify external size cap. In this case 57.3 Gb usable space we'll allocate 90 percent and then convert from Gb to bytes 
internal_size_cap = int(5*100000000) #specify internal size cap. In this case 5 Gb then convert from Gb to bytes
#intialize variables
curr_size = 0 #initialize variable to track current image folder size

def find_oldest_dir(path): #define function to provide the name of the oldest folder in the given path
    directories = os.listdir(path) #get the names of all the folders in the given path
    age = [None]*len(directories) #create a blank array with as many entries as there are folders. This will store the creation dates of each folder
    for n in range(len(directories)): #sweep through n from 0 to the folder qty
        age[n] = os.stat(path+"/"+directories[n]).st_ctime #write unix creation time of the folder name at index n to its corresponding age index
    return path+"/"+directories[age.index(min(age))] #return the name of the folder at the index of the lowest age index (ie. give the name of the folder with the lowest unix creation time)

def check_folder_size(path): #define code to get the size of a folder
    size = 0 #intialize size counter
    for entry in os.scandir(path): #for every entry in the specified path do the following
        if entry.is_file(): #if it is a file
            size = size+os.path.getsize(entry) #add the file size to the total size
        elif entry.is_dir(): #if it is a folder
            size = size+check_folder_size(entry.path) #get the size of the contents of the folder and add them to the total
    return size #return the folder size in bytes

#check for files
while True: #forever do the following
    file_exists = os.path.exists(client_receipt_path) #check that client receipt has been recieved
   
   #recieve files
    if file_exists == True: #if it has been recieved
        print("Client Receipt Found!")
        sleep(0.25) #wait a moment for the entire receipt to arrive
        #read info from client receipt
        with open(client_receipt_path, 'r') as r: #open the client receipt in read mode
            reader = csv.reader(r) #create reader
            size = next(reader) #read the first line as the image folder size
            client_ip = next(reader) #read the second line as the client ip
            name = next(reader) #read the third line as the machine name
        name = name[0]
        size = int(size[0]) #convert from single element list to interger
        client_ip = client_ip[0] #convert from single element list to string
        #print("client ip: "+client_ip) #print the client ip
        print("File Size: "+str(size))
        print("Name: "+name)
        print("IP: "+client_ip)
        
        while not os.path.exists(results_path): #do nothing until the file system sees the results folder
            sleep(0.25) #sleep for 0.25s
            #pass
        print("Results found")
        #wait until the recieved image folder size is the same as the client receipt says it should be
        same_data_count = 0 #intialize variable to track whether data transfer is complete
        size_last = None
        #check the size of the recieved folder. If it is the same for 10 consecutive checks (spaced 1 second apart) then the entire set of files must be present
        while same_data_count < 10: #if the data size hasnt changed for less than 10 cycles
            curr_size = check_folder_size(results_path) #chcek the current data size 
            #print(curr_size)
            print("Recieved:"+str(round((curr_size/size)*100,1))+"%") #print the recieved folder size as a percent of expected
            sleep(1) #wait before checking size again to lower resource use
            if curr_size == size_last: #if the data size has not changed
                same_data_count = same_data_count+1 #iterate the same data counter
            else: #if the data size has changed
                same_data_count = 0 #reset the counter to zero
            size_last = curr_size #update last size
        
        #indicate file reception
        print("Transfer Complete") #print file transfer complete
        subprocess.run(["scp",server_receipt_path, "pi@"+client_ip+":"+server_receipt_dest]) #send server reciept
        print("Server Receipt Sent!")
        #save files to desired location
        sleep(1)
        os.remove(client_receipt_path) #delete the client reciept
        tim = time.asctime() #get the current date/time
        day = tim[:3] #extract the day
        numday =  time.localtime() #get the local unix time
        num_day = time.strftime("%d",numday) #extract the day of the month as a number
        title = name+"_"+tim[:3]+"_"+tim[4:7]+"_"+num_day+"_at_"+tim[11:13]+"_"+tim[14:16]+"_"+tim[17:19] #Generate the folder title as the current time/date in form: day_month_num day_at_hout_minute_second
        print("Starting Saving")
        if os.path.exists(usb_path): #check if the usb stick path is present (the usb stick is connected and readable
            save_path = usb_path+day #set the output save path as the folder on the usb stick for the current day of the week
            size_cap = external_size_cap #use the external size cap
            print("Saving externally to "+save_path+"/"+title) #print the save location
        else: #otherwise (if the usb stick is not connected)
            save_path = archive_path+day #set the output save path as the folder on the system for the current day of the week (ie. if the usb stick is detached save internally instead)
            size_cap = internal_size_cap #use the internal size cap
            print("Saving internally to "+save_path+"/"+title) #print the save location
        if check_folder_size(save_path) > size_cap: #if archive folder is larger than the folder size cap
            target = find_oldest_dir(save_path) #locate the name of the oldest folder
            shutil.rmtree(target) #delete the oldest folder
            print("Folder full, deleting "+target) #print that we are deleting this folder
        os.system("mv "+results_path+" "+save_path) #move the results to the path defined earlier
        os.rename(save_path+"/output", save_path+"/"+title) #rename it to the name we generated
        print("Complete!")
        #quit() #close the program
        
    #what to do if the client receipt is not present yet
    sleep(0.1) #wait 0.1s to reduce resource use

