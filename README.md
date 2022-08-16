# Main.py is currently the most up to date version!
# Image_Compare
This is yet another look at the current state of the project. Below I will go over each file in the repo. This time around the system contains two Raspberry Pi's a client attached to the machine that is able to operate independently and a server that is currently just used for data archival.

# Scripts
### Main.py
This is the main program of the current config and lives on the client. It has two "daughter" programs that allow it to transmit to the server and restart properly but we'll go through those a little later.  
The general flow of the program is the following:  
-Startup and pull settings from config txt and write to the startup log  
-Calculate the max possible score to be able to classify misfires  
-startup the camera and wait for the input signals  
  -On mold open it collects an image of a mold full of parts then processes/analyzes it  
  -After eject fire it waits a moment and then takes a picture of the empty mold then processes/analyzes it  
  -Interprets the processing output and decides to either throw the alarm or not  
-Simultaneously it maintins a GUI capable of the following:  
  -Changing the camera/analysis settings behind a password protected window  
  -Save the settings to the config file  
  -Genearate an image mask to specify regions to check for discrepencies  
  -See help on how to operate the system  
  -Grant alarm access  
  -Transmit files  
  -Reset the password  
  -Open/close a touchscreen keyboard ([See this tutorial for setup](https://ozzmaker.com/virtual-keyboard-for-the-raspberry-pi/))  
  -View and reset both control images  
 I recommend going through the code line by line for exact detail as I commented just about every line

### Dev_old.py
This is a depreceated version of Main that moved most of the settings buttons to the main GUI page, this made debugging much easier as they buttons were not on their own password protected window.  

### Main_B.py
This is a variant of the main program designed to be deployed on a different setup. The main changes are that it is designed to maintaina single image, used larger images and process more efficiently. This is described in detail below:  
-Only processes masked areas at the cost of forcing masked area to be rectangular  
-Uses opencv contour detection to detect the areas defined by masking tool  
-Captures 1920x1080 images by default and then downscales them in all the GUI elements in order to display properly  

### Main_Startup.py
 This program allows the main script to restart itself. I encountered an issue where the program could start a new iteration of itself but would never close the old one. This would lead to a memory leak. As such this program is designed to attempt to close the main program and then launches it. Finally, the main program attempts to stop this program on its startup. This program is intended to be run on client startup.  

### Main_Transmit.py
This program is designed to transmit the the log files and output images to the server via SCP. From there it deletes the output images to save storage on the client. Additionally, this script is designed to wait for a receipt from the server or will timeout after a designated time as to designate to the operator whether or not files have been recieved by the server. This can also accept a couple arguments. Argument one is an optional argument to override the default server ip. Argument two is an optional argument to make the transmission status display via popups. Seeing as this script will run autonomously via scheduling but must also be able to run via user input it is important to give the user feedback with popups but not spam the screen with popups when run automatically. This script lives on the client.   

### Main_Recieve.py
This program is hosted on the server and checks for the reception of the client receipt. Upon its arrival it checks the receipt for the incoming image folder size as well as client IP. From there it waits for the image folder it is recieveing to be the same size as designated by the receipt. Once the whole folder is transfered, this script sends the server receipt. From here the script moves the files to the archive for the current day of the week. The archive in this case is a usb flash drive that can simply de disconnected to view data. Additionally if the usb drive is not foubd it will backup locally. This program is intended to be run on startup of the server.  

### Wiring_Check.py  
This program is meant to check the wiring of the relay and test the I/O. It presents a window that allows you to send the alarm and reset signals and displays the mold open and ejector fire signals. Additionally it writes the input signals to the termianl with a timestamp for more detail.  

# Files   
### server_receipt.csv
This is the receipt the server sends to the client. It has no contents and more or less acts as a way for the transmit script to check for a file sent from the server. This could be a good way for the server to send back some info similar to the client receipt discussed below.  
### start.desktop
I followed [this tutorial](https://learn.sparkfun.com/tutorials/how-to-run-a-raspberry-pi-program-on-startup/method-2-autostart) on setting up programs to run on boot with a GUI. Currently, in my system, its destination folder is /home/pi/.config/autostart. On the pi the file is called "prog" not "start" but this is likely a difference in raspbian vs windows choosing how to display as "prog" is defined in the contents of the file. In the current setup in just launches predeployment_copy.py but in the main deployment will run Main_Emulated_Startup.py. A similar setup of this is used to run Main_Recieve.py on startup of the server.  
### run.desktop  
I followed [this tutorial](https://www.hackster.io/kamal-khan/desktop-shortcut-for-python-script-on-raspberry-pi-fd1c63) on setting up executables for programs. This is meant to live on the desktop screen and acts as a shortcut to startup Main.py if operators accidentally close the program. I recommend enabling "Don't ask options on launch executable file" under Edit->Prefrences->General in the raspbian file explorer to execute this more seamlessly.  

# Main folder
This is a sample of the filesystem client programs use. It shows some samples of outputs as well as demonstrates the layout of the file system.  
### client_receipt.csv
This is the csv file sent by Main_Emulated_Transmit.py to the server to tell it the file size and client ip. Additionally the server checks for this file to confirm it is recieveing files. Line one contains the image folder size in bytes, line two contains the client ip.  
###  log.csv
This is the main log that tracks the decision making of Main.py every time it does processing. This formatted as to be self explanitory. As you can see logs contain the timestamp which doubles as the output image title, the score the image recieved, and whether or not it set off the alarm.  
### log_template.csv  
This is a copy of the log but with no data present. It is used by transmit to wipe the log file. This is done by copying this file over the log and naming it log.  
### startup_log.csv
This log is written to once on every startup, it tracks the startup time and settings upon startup. This one is also formatted to it should be pretty self explanitory when viewed in github.  
### config.txt
This is a sample of my current config file. It stores the following in this order, password, ISO, shutter speed, camera mode, image width, image height, image rotation, image detection threshold, sensitivity, mold open delay, ejector fire delay, machine name, and alarm access. 
### menu_image.jpg
This is a sample image that is used as the first image to be displayed when the client programs are launched. It stands as a placeholder until the program processes and displays a new image.  
### mask_preview.jpg  
This an image of the full control with the mask overlayed on top of it. It is intended to be part of the archive and allows the user to have a visual representation fo exactly what parts of the mold are being examined at the time of archival. This image is updated on startup and everytime a new mask is generated.  
### images folder
This is where the outpput images go to be stored and then sent to the server.  
### comparison_images folder
This is the folder in which the sample and control images are stored while the client programs run as well as the image mask.
### fail folder  
This folder contains a set of images for every failure/time the alarm is triggered. Upon an image not passing it saves the current raw input, the processed output, and the control image it is being compared against. This is intended to gice the user plenty of data for analyzing failed images.  

# archive Folder
This is a sample layout of the archive stored on the server desktop and USB drive. It is meant to be copied to theses locations for easy setup. Ignore/delete the files name placeholder, they are present to force githb to keep the folder.  

# Misc/Common Bugs/Setup
### SCP Setup
When setting up SCP file transfer (especially when scheduled via crontab) it is imprtant that the root user also has the credentials for scp transfer. This can be done by following [this tutorial](https://raspberrypi.stackexchange.com/questions/51877/will-an-automated-scp-script-share-files-between-pis-without-passwords/53214#53214) and then configuring it to be run by root by following [these instructions](https://raspberrypi.stackexchange.com/a/121742) in which you first generate a keyset, copy them between machines and then copy the keyset to be accessed by root. In a couple cases I had to manually make the /root/.ssh folder first.  
### Crontab Setup
I added the following lines to crontab to autorun some things (to make it run correctly setup with the command "sudo crontab -e".  
I added the following line to the client:  
`00 00 * * * /sbin/shutdown -r now` This restarts the system at midnight everyday.  
`05 00 * * * /usr/bin/python3 /home/pi/Desktop/Main_Transmit.py >> /home/pi/logs/Transmit.log 2>&1` This runs Main_Transmit.py everyday at 12:05 am and writes to a log at the specified location for debugging (this will be removed in final deployment).  
I added the following to the server:  
`00 00 * * * /sbin/shutdown -r now` This restarts the system at midnight everyday.  
`@reboot /usr/bin/python3 /home/pi/Desktop/Main_Recieve.py >> /home/pi/Desktop/log.log 2>&1` This runs the file recieve script on boot
### Documentation
This folder contains important files relating to the documentation of the project.
CAD: This folder contains all CAD files relating to the construction of the project. Everything designed to be 3d printed also has an stl.  
BOM.xlsx: This is a spreadsheet of the bill of materials to completely replicate the system
Setup tutorial.docx: This is a word document describing how to setup the system.
Wiring Diagram.png: This is an illustration of the wiring required to setup the system.
