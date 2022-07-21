import os
from time import sleep
import subprocess
import time
import shutil
import csv

main_folder = "/home/pi/Desktop/recieve"
results_path = main_folder+"/results/"
client_receipt_path = results_path+"/client_receipt.csv" #define the location of the client receipt
server_receipt_path = main_folder+"/server_receipt.csv" #define the location of the server receipt
image_path = results_path+"/images/" #define the location of recieved images

processing_path = "/home/pi/Desktop/processing/" #define location of processing folder
archive_path = "/home/pi/Desktop/archive/" #defifne location of archive folder
server_receipt_dest = main_folder #define where in the client the server receipt should go

#intialize variables
curr_size = 0 #initialize varaible to track current image folder size

#check for files
while True: #forever do the following
    file_exists = os.path.exists(client_receipt_path) #check that client receipt has been recieved
   
   #recieve files
    if file_exists == True: #if it has been recieved
        
        sleep(0.1) #wait a moment for the images folder to show up
        
        #read info from client receipt
        with open(client_receipt_path, 'r') as r: #open the client receipt in read mode
            reader = csv.reader(r) #create reader
            size = next(reader) #read the first line as the image folder size
            client_ip = next(reader) #read the second line as the client ip
        size = int(size[0]) #convert from single element list to interger
        client_ip = client_ip[0] #convert from single element list to string
        #print("client ip: "+client_ip) #print the client ip
        print("File Size: "+str(size))
        
        #wait until the recieved image folder size is the same as the client receipt says it should be
        while curr_size < size:
            curr_size = 0
            for n in os.scandir(image_path): #for every item in the image folder do the following
                curr_size = curr_size+os.path.getsize(n) #add its size to the counter
            #print(curr_size)
            print("Recieved:"+str(round((curr_size/size)*100,1))+"%") #print the recieved folder size as a percent of expected
            sleep(0.1) #wait before checking size again to lower resource use
        
        #indicate file reception
        print("Transfer Complete") #print file transfer complete
        subprocess.run(["scp",server_receipt_path, "pi@"+client_ip+":"+server_receipt_dest]) #send server reciept
        
        #save files to desired locations
        shutil.copy(results_path+'log.csv', processing_path+'log.csv') #copy the log to the processing folder
        shutil.rmtree(processing_path+'current/') #delete old processing folder
        shutil.copytree(results_path, processing_path+'current/') #copy the results to the processing folder
        day = time.asctime() #get the current date/time
        day = day[:3] #extract the day
        os.rename(results_path , archive_path+'/'+day+'/'+time.asctime()) #move the results to the archive and timestamp it
        quit() #close the program
        
    #what to do if the client receipt is not present yet
    else: #if it has not been recieved
        print("waiting") #print as such
    sleep(0.1) #wait 0.1s to reduce resource use