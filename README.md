# Image_Compare
This is yet another look at the current state of the project. Below I will go over each file in the repo. This time around the system contains two Raspberry Pi's a client attached to the machine that is able to operate independently and a server that is currently just used for data archival.

### Main_Emulated.py
This is the main program of the current config and lives on the client. It has two "daughter" programs that allow it to transmit to the server and restart properly but we'll go through those later.  
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
 I recommend going through the code line by line for exact detail as I commented just about every line
 
 ### Main_Emulated_Startup.py
 This program allows the main script to restart itself. I encountered an issue where the program could start a new iteration of itself but would never close the old one. This would lead to a memory leak. As such this program is designed to attempt to close the main program and then launches it. Finally, the main program attempts to stop this program on its startup.

### Main_Emulated_Transmit.py
This program is designed to transmit the the log files and output images to the server via SCP. From there it deletes the output images to save storage on the client. Additionally, this script is designed to wait for a receipt from the server or will timeout after a designated time as to designate to the operator whether or not files have been recieved by the server. 
