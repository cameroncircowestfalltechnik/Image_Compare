# Predeployment copy is currently the most up to date version!!! Main emulated is depreceated!
# Image_Compare
This is yet another look at the current state of the project. Below I will go over each file in the repo. This time around the system contains two Raspberry Pi's a client attached to the machine that is able to operate independently and a server that is currently just used for data archival.

# Scripts
### Main_Emulated.py
This is the main program of the current config and lives on the client. It has two "daughter" programs that allow it to transmit to the server and restart properly but we'll go through those a little later. It is titled as emulated as I am currently emulating machine inputs with a button.  
The general flow of the program is the following:  
-Startup and pull settings from config txt and write to the startup log  
-startup the camera and wait for the button to be pressed  
  -On the first press it collects the control image  
  -On the second press it collects the refrence image and runs processing  
  -Interprets the processing output to either throw the alarm or not  
-Simultaneously it maintins a GUI capable of the following:  
  -Changing the camera/analysis settings behind a password protected window  
  -Save the settings to the config file  
  -See help as to how to operate the system  
  -Emulate alarm/alarm reset  
  -Transmit the files  
  -Reset the password  
  -open/close a touchscreen keyboard  
 I recommend going through the code line by line for exact detail as I commented just about every line
 
### Main_Emulated_Startup.py
 This program allows the main script to restart itself. I encountered an issue where the program could start a new iteration of itself but would never close the old one. This would lead to a memory leak. As such this program is designed to attempt to close the main program and then launches it. Finally, the main program attempts to stop this program on its startup. This program is intended to be run on client startup.  

### Main_Emulated_Transmit.py
This program is designed to transmit the the log files and output images to the server via SCP. From there it deletes the output images to save storage on the client. Additionally, this script is designed to wait for a receipt from the server or will timeout after a designated time as to designate to the operator whether or not files have been recieved by the server. This can also accept an optional argument to override the default server ip.  

### file_recieve_reply.py
This program is hosted on the server and checks for the reception of the client receipt. Upon its arrival it checks the receipt for the incoming image folder size as well as client IP. From there it waits for the image folder it is recieveing to be the same size as designated by the receipt. Once the whole folder is transfered, this script sends the server receipt. From here the script saves a copy of the images to the processing folder to be interpretted later and another copy to the archive for the current day of the week. Finally, it clears the reception folder. This program is intended to be run on startup of the server and will eventually be configured to loop forever.  
### predeployment_copy.py
I was recently asked to deploy my system on a machine that was malfunctioning. As the entire system is obviously not completely fully function I agreed to create a variant of the current setup to rush into deployment. This program is a copy of Main_Emulated with the follwoing changes.  
  -Changed I/O to feature digitial input/output for alarm signals and mold status.  
  -Changed workflow of image capture to be inline with actual use case. Ie. a single control image is maintained as opposed to taking a new one every time.  
  -Designed to maintain images and adapt processing for two image states.  
  -Added Gui elements to rest and view the control images as well as toggle access to alarms.  
  -File transmission to the server was removed.  
  
### Wiring_Check.py  
This program is meant to check the wiring of the optocouplers and test the I/O. It presents a window that allows you to send the alarm and reset signals and displays the mold open and ejector fire signals. Additionally it writes the input signals to the termianl with a timestamp for more detail.  

# Files 
### config.txt
This is a sample of my current config file. It stores the following in this order, password, ISO, shutter speed, camera mode, image width, image height, image rotation, image detection threshold, and sensitivity.  
### server_receipt.csv
This is the receipt the server sends to the client. It has not contents and more or less acts as a way for the transmit script to check for a file sent from the server. This could be a good way for the server to send back some info similar to the client receipt discussed below.  
### start.desktop
I followed [this tutorial](https://learn.sparkfun.com/tutorials/how-to-run-a-raspberry-pi-program-on-startup/method-2-autostart) on setting up programs to run on boot with a GUI. Currently, in my system, its destination folder is /home/pi/.config/autostart. On the pi the file is called "prog" not "start" but this is likely a difference in raspbian vs windows choosing how to display as "prog" is defined in the contents of the file. In the current setup in just launches predeployment_copy.py but in the main deployment will run Main_Emulated_Startup.py.  


# main_emulated folder
This is a sample of all the folders that the client programs use. It shows some samples of outputs as well as demonstrates the layout of the file system. Additionally, an images folder will be present here of all the images displayed in the GUI for archival.  
### client_receipt.csv
This is the csv file sent by Main_Emulated_Transmit.py to the server to tell it the file size and client ip. Additionally the server checks for this file to confirm it is recieveing files. Line one contains the image folder size in bytes, line two contains the client ip.  
###  log.csv
This is the main log that tracks the decision making of main_emulated every time it does processing. This one is actually formatted and as you can see logs the timestamp which doubles as the output image title, the score the image recieved, and whether or not it set off the alarm.  
### startup_log.csv
This log is written to once on every startup, it tracks the startup time and settings upon startup. This one is also formatted to it should be pretty  self explanitory when viewed in github.  
### config.txt
This is the config file maintained by the client programs. It stores all the setting for processing and image collection.  
### menu_image.jpg
This is a sample image that is used as the first image to be displayed when the client programs are launched. It stands as a placeholder until the program processes and displays a new image.  
### images folder
This is where the outpput images go to be stored and then sent to the server.  
### comparison_images folder
This is the folder in which the sample and control images are stored while the client programs run.  
