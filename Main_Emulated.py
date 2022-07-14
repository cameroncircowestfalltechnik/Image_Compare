# #!/usr/bin/python #uncomment to designate the program as executable
from PIL import ImageTk
import PIL
from guizero import App,Text,TextBox,PushButton,Picture,question,Window,Combo,info#,Image
import time
import tkinter as tk
from gpiozero import Button
import os
import picamera
from io import BytesIO
import numpy as np
from PIL import Image
from PIL import ImageOps
from PIL import ImageChops
from PIL import ImageEnhance
import matplotlib.pyplot as plt
import subprocess


#setup-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
try: #attempt the following
    os.system("cd /home/pi/Desktop") #navigate to program location (probably redundant)
    os.system("\n pkill Main_Emulated_Startup.py") #kill the startup script
except: #upon fail (likely indicating this program was started without the startup prgram being run
    pass #do nothing

log = open("Object_Detection/results/log.csv", "a") #open log csv file in "append mode"
if os.stat("Object_Detection/results/log.csv").st_size == 0:#if the csv file is empty do the following
    log.write("Timestamp,Score,Pass?\n") #Rebuild column labels 
    log.flush() #save text

good = True #create variable to hold pass/fail status
setup_start = time.time() #start startup timer
alarm_status = 0
comp_dir = "/home/pi/Desktop/Object_Detection/compare2/compare_" #specify image file location
filetype = ".jpg" #specify image file filetype (leftover debug)
n = 0 #startup image counter
button = Button(4) #assign button to GPIO 4
config_path = "/home/pi/Desktop/Object_Detection/compare2/config.txt" #define config file path
with open(config_path,'r') as f: #open the config file
    lines = f.readlines() #write line by line to "lines"
current_password = lines[0].strip() #read line zero as the password
iso = int(lines[1]) #read line 1 as the iso
ss = int(lines[2]) #read line 2 as the shutter speed
cm = lines[3].strip() #read line 3 as the camera mode
res = (int(lines[4]),int(lines[5])) #read lines 4/5 as the camera resolution
rot = int(lines[6]) #read line 6 as the image rotation
thresh = int(lines[7]) #read line 7 as the image detection threshold
sens = float(lines[8].strip()) #read line 8 as the image detection sensitivity

startup_log = open("Object_Detection/results/startup_log.csv", "a") #open startup log csv file in "append mode"
startup_log.write(time.asctime()+","+str(iso)+","+str(ss)+","+cm+","+str(res[0])+","+str(res[1])+","+str(rot)+","+str(thresh)+","+str(sens)+"\n") #write the current time and settings to the startup log
startup_log.close() #close the startup log (auto saves new data)


#current_password = "123"
#iso = 500
# ss = 60000
# cm = 'sports'
# res = (852,480)
# rot = 0
# thresh = 10000
#sens = 2.25
res_max = (3280, 2464) #define the max camera resolution

#The Camera Zone------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def work():
    global cap_start #set start time as global so the total decision time can be calculated
    process_start = time.time() #start image processing timer
    base = Image.open(comp_dir+'1'+filetype) #load control image
    comp = Image.open(comp_dir+'2'+filetype) #load comparison image
    
    #base = Image.open("/home/pi/Desktop/Object_Detection/compare2/Base.jpg") #override images
    #comp = Image.open("/home/pi/Desktop/Object_Detection/compare2/REF.jpg")

    diff = ImageChops.difference(base, comp) #find difference between images and name it diff
    diff = ImageOps.grayscale(diff) #convert the difference to black and white
    diff = diff.point( lambda p: 255 if p > 255/sens else 0) #turn any point above defined sensitivity white "255" and anything below black "0". Effectively turns grayscale to black and white.
    
    tot = np.sum(np.array(diff)/255) #convert diff to an array and find the elementwise sum, call it tot for "total". This represents the quantity of pixels that are different
    print('Score: '+str(tot)) #print the "total"
    if tot > thresh: #if the total number of diffent pixels are more than the defined threshold do the following:
        print("Object detected") #say an object was detected
        simulate_alarm()
        good = False #designate as not good/fail
    else: #otherwise do the following:
        print("No object detected") #say an object was not detected
        good = True #designate as good/pass
        reset_alarm()

    process_end = time.time() #stop the timer
    process_time = process_end - process_start #calculate elapsed time since processing start
    print('Process time: {} seconds'.format(process_time)) #display the image processing time
    decision_time = process_end - cap_start #calculate elapsed time  since decision start
    print('Decision time: {} seconds'.format(decision_time)) #display the decision making time
    
    disp_start = time.time() #start display time timer
    
    base = base.rotate(rot) #rotate the control image if needed
    comp = comp.rotate(rot) #rotate the comparison image if needed
    diff = diff.rotate(rot) #rotate the difference image if needed

    black = (0,0,0) #define black pixel rgb value
    color = (0,255,0) #define colored pixel rgb value (in this case it's currently green)
    diff = ImageOps.colorize(diff, black, color, blackpoint=0, whitepoint=255, midpoint=127) #convert black and white differenc image to black and color for more contrast when displaying
    #result = ImageChops.hard_light(base,diff)
    comp2 = comp #duplicate the comparison image to comp2
    enhancer = ImageEnhance.Brightness(comp2) #specify that we want to adjust the brightness of comp2
    comp2 = enhancer.enhance(0.75) #decrease the brightness of comp2 by 25% for more contrast when displaying

    result = ImageChops.add(diff,comp2) #overlay difference ontop of comp2 and call it result
    pic.image = result #send results to the picture widget on the main page
    tim = time.asctime() #grab current time as to match log name and file name
    result.save("/home/pi/Desktop/Object_Detection/results/"+tim+".jpg") #save results as a jpg with the current date and time
    log.write(tim+","+str(tot)+","+str(good)+"\n") #write time, score, and pass/fail to log
    log.flush()#save it
    
    
    disp_end = time.time() #stop the timer
    disp_time = disp_end - disp_start #calculate elapsed time since display start
    print('Display time: {} seconds'.format(disp_time)) #display the display time



def capture():
    global n
    #camera.exposure_mode = cm
    #camera.shutter_speed = ss
    #camera.iso = iso
    #camera.resolution = res #specify resolution
    #button.wait_for_press() #wait for button to be bumped
    button.wait_for_release()
    global cap_start
    cap_start = time.time() #start image capture timer
    
    n = n+1 #iterate image counter
    stream = BytesIO() #start writing camera stream to memory
    camera.capture(stream, format='jpeg', use_video_port=True) #capture to the stream
    stream.seek(0) #move to the first image captured
    
    img = Image.open(stream) #open the image
    img = img.save(comp_dir+str(n)+filetype) #save the image
    
    cap_end = time.time() #stop the image capture time
    cap_time = cap_end - cap_start #calculate elapsed time
    print('Capture '+str(n)+' took: {} seconds'.format(cap_time)) #display it.
    
    if n == 2: #if the image counter is two do the following:
        n=0 #reset the image counter
        work() #process the images


#Button Functions-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def reset_alarm(): #define code to reset the alarm
    print("Alarm Reset") #placeholder: print text
    app.bg = "light grey"
    
def request_settings(): #define code to request the openeing of the settings page
    password = app.question(title="password", question="Enter Password:", initial_value=None) #launch popup window requesting password
    if password == None: #if nothing is put in
        pass #do nothing, window closes
    elif password == current_password: #if the password is correct
        print("password correct!") #report into terminal
        set_win.show() #make settings window visible
    else: #if the password is incorrect
        app.error("Warning", "Wrong Password") #create a new popup stating wrong password
        
def request_setting_help(): #define code behind the settings help button
    help_info = set_win.info("Help", "Add helpful text describing all the settings here") #create a popup with helpful text

def close_settings():
    sett_close = set_win.yesno("Restart?", "Restart program to send camera new settings? (Not rquired if changing rotation, sensitivity, or threshold)") #create popup to ask if user wants to restart
    if sett_close == True: #if the answer is yes
        restart() #restart the program (maybe just migrate this out of a function if this is the only refrence)
    else: #otherwise
        set_win.hide() #conceal the window
    
#Value Change Functions-------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def change_iso(): #define code to change the iso
    new_iso = iso_input.value #write the input to a variable, "new_iso"
    numeric = new_iso.isnumeric() #check if the input is a number
    if new_iso == None: #if nothing is input
        pass #do nothing
    elif numeric == True: #if the input is numeric do the following
        print("Setting ISO to:"+str(new_iso)) #print to terminal
        iso = int(new_iso) #write over the old value with the new one
        config_write(1,iso) #save to config file
        iso_curr_text.value = "Current ISO: "+str(iso) #update the settings page text
        iso_input.value = "" #clear the textbox
    else: #if the input is not a number
        app.error("Warning", "invalid input, not saving") #create a popup error
        
def change_ss(): #define code to change the shutter speed (operates identical to change_iso, see that for line by line)
    new_ss = ss_input.value
    numeric = new_ss.isnumeric()
    if new_ss == None:
        pass
    elif numeric == True:
        print("Setting Shutter Speed to:"+str(new_ss))
        ss = int(new_ss)
        config_write(2,ss) #save to config file
        ss_curr_text.value = "Current Shutter Speed: "+str(ss)
        ss_input.value = "" #clear the textbox
    else:
        app.error("Warning", "invalid input, not saving")
        
def change_cm(): #define code to change camera mode
    cm = cm_combo.value #write the input to the camera mode variable
    config_write(3,cm) #save to config file
    print("Setting Camera Mode to:"+cm) #print to terminal
    cm_curr_text.value = "Current Camera Mode: "+cm #update settings page text
    
def change_rot(): #define code to change the image rotation (operates identical to change_iso, see that for line by line)
    new_rot = rot_input.value
    numeric = new_rot.isnumeric()
    if new_rot == None:
        pass
    elif numeric == True:
        print("Setting Image Rotation to:"+str(new_rot))
        rot = int(new_rot)
        config_write(6,rot) #save to config file
        rot_curr_text.value = "Current Image Rotation: "+str(rot)
        rot_input.value = "" #clear the textbox
    else:
        app.error("Warning", "invalid input, not saving")

def change_res(): #define code to change image resolution
    global res #define resolutiion tuple as global
    new_resw = resw_input.value #write the new width to a varibale
    new_resh = resh_input.value #write the new height to a variable
    numericw = new_resw.isnumeric() #check if width input is numeric
    numerich = new_resh.isnumeric() #check if height input is numeric
    res = list(res) #convert resolution tuple to list so it can be written to
    if new_resw == None: #if no width is input
        pass #do nothing
    elif numericw == False: #if the input is non numeric
        app.error("Warning", "invalid width input, not saving") #create a popup error
    elif int(new_resw) > res_max[0]: #if the new width is higher than the max
        app.error("Warning", "width higher than camera can capture, not saving") #create a popup error
    elif numericw == True: #if the input is numeric
        print("Setting Camera image width to:"+str(new_resw)) #print to terminal
        res[0] = int(new_resw) #assign new width to its list position
        config_write(4,new_resw) #save to config file
        resw_input.value = "" #clear the textbox
    
    if new_resh == None: #if no height is input
        pass #do nothing
    elif numerich == False: #if the input is non numeric
        app.error("Warning", "invalid height input, not saving") #create a popup error
    elif int(new_resh) > res_max[1]: #if the new height is higher than the max
        app.error("Warning", "Height higher than camera can capture, not saving") #create popup error
    elif numerich == True: #if the input is numeric
        print("Setting Camera image height to:"+str(new_resh)) #print to terminal
        res[1] = int(new_resh) #assign new height to its list position
        config_write(5,new_resh) #save to config file
        resh_input.value = "" #clear the textbox

    res = tuple(res) #convert the resolution back to a tuple
    res_curr_text.value = "Current Camera Resolution: "+str(res[0])+" , "+str(res[1]) #update the settings page text

def change_thresh(): #define code to change the threshold (operates identical to change_iso, see that for line by line)
    new_thresh = thresh_input.value
    numeric = new_thresh.isnumeric()
    if new_thresh == None:
        pass
    elif numeric == True:
        print("Setting Decision Threshold to:"+str(new_thresh))
        thresh = int(new_thresh)
        config_write(7,thresh,) #save to config file
        thresh_curr_text.value = "Current Decision Threshold: "+str(thresh)
        thresh_input.value = "" #clear the textbox
    else:
        app.error("Warning", "invalid input, not saving")

def change_sens(): #define code to change the sensitivity
    try: #attempt the following
        new_sens = float(sens_input.value) #convert input to float
    except: #if it fails (input is non numeric)
        app.error("Warning", "invalid input, not saving")
    else: #otherwise (input IS numeric)
        print("Setting Contrast Sensitivity to:"+str(new_sens)) #print to terminal
        sens = new_sens #update the current value
        config_write(8,sens) #save to config file
        sens_curr_text.value = "Current Contrast Sensitivity: "+str(sens) #update window text
        sens_input.value = "" #clear the textbox

def reset_pass(): #define code to change the password
    global current_password #set current password as global variable
    print("Start password reset") #write to terminal
    old_pass = old_pass_input.value #write old password input to variable
    new_pass = new_pass_input.value #write new password input to variable
    conf_pass = conf_pass_input.value #write confirmation password to variable
    if old_pass == "" or new_pass == "" or conf_pass == "": #check if any field is empty (for some reason "None" didnt work here
        pass_reset_win.warn("Warning", "missing an input, not saving") #create popup
    elif old_pass != current_password: #check that the old password is incorrect
        pass_reset_win.warn("Warning", "Wrong old password, not saving") #create popup
    elif new_pass != conf_pass: #cehck if new and confrimation password are mismatched
        pass_reset_win.warn("Warning", "New password mismatch, not saving") #create popup
    elif new_pass == conf_pass: #check if new password and confirmation password match
        current_password = new_pass #save new password
        pass_reset_win.info("Success", 'Password scuccessfully set as "'+current_password+'".') #create popup
        print("new password :"+current_password) #write to terminal
        config_write(0,current_password) #save new password to config file
        old_pass_input.value = "" #clear the textboxes
        new_pass_input.value = ""
        conf_pass_input.value = ""
        pass_reset_win.hide() #conceal password reset window
#create functions to check each box for an enter press
def iso_enter(event):
    if event.key == "\r": #check if key pressed is enter
        change_iso() #update the entry
        
def ss_enter(event):
    if event.key == "\r": #check if key pressed is enter
        change_ss() #update the entry

def rot_enter(event):
    if event.key == "\r": #check if key pressed is enter
        change_rot() #update the entry

def res_enter(event):
    if event.key == "\r": #check if key pressed is enter
        change_res() #update the entry
        
def thresh_enter(event):
    if event.key == "\r": #check if key pressed is enter
        change_thresh() #update the entry

def sens_enter(event):
    if event.key == "\r": #check if key pressed is enter
        change_sens() #update the entry



#Utility Functions------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def config_write(line,text): #create function to write over a line in config file (arguments:line number to write to, text/number to write)
    lines[line] = str(text)+"\n" #save new text to sepcified entry in "lines" array
    with open(config_path,'w') as f: #open the config file in write mode
        f.writelines(lines) #write the lines array to it
        
def convert_img(name): #define code to convert an image (input argument is the image name as a string)
    conv_start_time = time.time() #start conversion timer
    
    img = Image.open("/home/pi/Desktop/Object_Detection/compare2/"+name+".jpg") #open the image as a jpg
    img.save("/home/pi/Desktop/Object_Detection/compare2/"+name+".png") #save it as a png
    
    conv_end_time = time.time() #stop the timer
    conv_elapsed_time = conv_end_time - conv_start_time #calculate elapsed time since conversion start
    print('Convert time: {} seconds'.format(conv_elapsed_time)) #display the conversion time
    
def refresh_img(): #define the code to refresh the main page image, PLACEHOLDER
    global pic #make the pic entity global (redundant?)
    #This is placeholder/demo code for replacing the image
    print("Refresh Control") #print to terminal
    #load_img("ref2") #i dont think this does anything
    #pic.destroy() #delete the image
    #pic = Picture(app, image="/home/pi/Desktop/Object_Detection/compare2/ref2.png", align='top') #write a new copy
    pic.image = "/home/pi/Desktop/Object_Detection/compare2/ref2.jpg"
    
def simulate_alarm():
    alarm_status = True
    app.bg = 'tomato' #set app color to red
    print("simulate alarm")

def check_button():
    if button.is_pressed: capture() #if button is pressed run "capture"
    
def restart():
    camera.close() #shutoff the camera
    app.destroy() #kill the new windows created by the programs
    os.system("\n sudo python Main_Emulated_Startup.py") #run the prgram startup script
    
def transmit():
    subprocess.Popen(["python", "Main_Emulated_Transmit.py"]) #run the transmit script

#Main Window----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#convert_img("ref") #convert image to png
with picamera.PiCamera() as camera: #start up the camera
    camera.exposure_mode = cm #set camera mode
    camera.shutter_speed = ss #set shutter speed
    camera.iso = iso #set camera iso
    camera.resolution = res #set camera resolution
    stream = picamera.PiCameraCircularIO(camera, seconds=1) #generate a camera stream in which the camera retains 1 second of footage
    camera.start_recording(stream, format='h264') #start recording to the stream
    camera.wait_recording(0.25) #allow the camera to run a second to allow it to autofocus
    #setup main window
    app = App(title='main', layout='auto', width = 900, height = 575+50) #create the main application window
    pic = Picture(app, image="/home/pi/Desktop/Object_Detection/compare2/ref.jpg", align='top') #create picture widget
    reset_button = PushButton(app, command=reset_alarm, text="Reset", align='bottom') #define reset button widget
    settings_button = PushButton(app, command=request_settings, text="Settings", align='bottom') #define settings button widget
    sim_button = PushButton(app, command=simulate_alarm, text="Simulate Alarm", align='bottom') #define settings button widget
    pic.repeat(1, check_button) #attach repeat widget to the picture widget to run "check_button" every 1ms
    #reset_button.repeat(500, check_alarm)

    #Password Reset Window Setup------------------------------------------------------------------------------------------------------------------------------------------------------------
    pass_reset_win = Window(app, title="Password Reset",layout="grid", width = 300, height = 120) #create the password reset window
    old_pass_text = Text(pass_reset_win, text="Old Password:" , grid=[1,1]) #add old password text
    old_pass_input = TextBox(pass_reset_win, grid=[2,1]) #add old password textbox
    new_pass_text = Text(pass_reset_win, text="New Password:" , grid=[1,2]) #add new password text
    new_pass_input = TextBox(pass_reset_win, grid=[2,2]) #add new password textbox
    conf_pass_text = Text(pass_reset_win, text="Confirm New Password:" , grid=[1,3]) #add password confirm text
    conf_pass_input = TextBox(pass_reset_win, grid=[2,3]) #add password confirm textbox
    pass_reset_button = PushButton(pass_reset_win, command=reset_pass, text="set", grid=[2,4]) #add password set button
    pass_reset_win.hide()

    #Settings Window Setup--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    set_win = Window(app, title="Settings",layout="grid", width = 900, height = 600) #create the settings window

    #create section for ISO
    iso_curr_text = Text(set_win, text="Current ISO: "+str(iso), grid=[1,1]) #define text widget to display current value
    iso_input = TextBox(set_win, grid=[2,1]) #create text box widget to allow input of new value
    iso_input.when_key_pressed = iso_enter #if a key is pressed in the text box run the enter check
    iso_set = PushButton(set_win, command=change_iso, text="set", grid=[4,1]) #create button widget to save new value
    iso_rec_text = Text(set_win, text="Suggested range: 100-800", grid=[5,1]) #create text widget to display recommended range

    #create secton for shutter speed (setup identical to ISO, see that section for line by line)
    ss_curr_text = Text(set_win, text="Current Shutter Speed: "+str(ss), grid=[1,2]) 
    ss_input = TextBox(set_win, grid=[2,2])
    ss_input.when_key_pressed = ss_enter #if a key is pressed in the text box run the enter check
    ss_set = PushButton(set_win, command=change_ss, text="set", grid=[4,2])
    ss_rec_text = Text(set_win, text="Suggested range: 0-60,000", grid=[5,2])

    #create section for setting camera mode
    cm_curr_text = Text(set_win, text="Current Shutter Mode: "+cm, grid=[1,3]) #create text widget to display current mode
    cm_combo = Combo(set_win, options=['sports', 'off', 'auto', 'night','antishake'], grid=[2,3]) #create drop down menu widget to select new camera mode TO DO: Add more options
    cm_set = PushButton(set_win, command=change_cm, text="set", grid=[4,3]) #create button widget to save mode
    cm_rec_text = Text(set_win, text="Suggested Mode: sports", grid=[5,3]) #create text widget to display recommended mode

    #create secton for image rotation (setup identical to ISO, see that section for line by line)
    rot_curr_text = Text(set_win, text="Current Image Rotation: "+str(rot), grid=[1,4])
    rot_input = TextBox(set_win, grid=[2,4])
    rot_input.when_key_pressed = rot_enter #if a key is pressed in the text box run the enter check
    rot_set = PushButton(set_win, command=change_rot, text="set", grid=[4,4])
    rot_rec_text = Text(set_win, text="Suggested range: 0-180", grid=[5,4])

    #create section for image resolution
    res_curr_text = Text(set_win, text="Current Camera Resolution: "+str(res[0])+" , "+str(res[1]), grid=[1,5]) #create text widget to display current value
    resw_input = TextBox(set_win, grid=[2,5]) #create textbox widget for width input
    resh_input = TextBox(set_win, grid=[3,5]) #create textbox widget for height input
    resw_input.when_key_pressed = res_enter #if a key is pressed in the text box run the enter check
    resh_input.when_key_pressed = res_enter #if a key is pressed in the text box run the enter check
    res_set = PushButton(set_win, command=change_res, text="set", grid=[4,5]) #create button widget to save resolution
    res_rec_text = Text(set_win, text="Suggested: 852 480 Max: 3280 2464", grid=[5,5]) #create text widget to display recommended/max values

    #create secton for image threshold (setup identical to ISO, see that section for line by line)
    thresh_curr_text = Text(set_win, text="Current Decision Threshold: "+str(thresh), grid=[1,6])
    thresh_input = TextBox(set_win, grid=[2,6])
    thresh_input.when_key_pressed = thresh_enter #if a key is pressed in the text box run the enter check
    thresh_set = PushButton(set_win, command=change_thresh, text="set", grid=[4,6])
    thresh_rec_text = Text(set_win, text="Suggested range: 8000-20,000", grid=[5,6])

    #create secton for sensitivity (setup identical to ISO, see that section for line by line)
    sens_curr_text = Text(set_win, text="Current Contrast Sensitivity: "+str(sens), grid=[1,7])
    sens_input = TextBox(set_win, grid=[2,7])
    sens_input.when_key_pressed = sens_enter #if a key is pressed in the text box run the enter check
    sens_set = PushButton(set_win, command=change_sens, text="set", grid=[4,7])
    sens_rec_text = Text(set_win, text="Suggested range: 3-15 (decimal)", grid=[5,7])



    #add settings buttons
    help_but = PushButton(set_win, command=request_setting_help, text="Help", grid=[2,8]) #create button widget for help popup
    close_but = PushButton(set_win, command=close_settings, text="Close", grid=[3,8]) #create button widget to be able to close settings page (just executes hide command)
    refresh_but = PushButton(set_win, command=refresh_img, text="Refresh Control Image", grid=[4,8]) #create button widget to refresh the refrence image
    new_pass_but = PushButton(set_win, command=pass_reset_win.show, text="Reset Password", grid=[5,8]) #create button widget to reset the password
    transmit_but = PushButton(set_win, command=transmit, text="Manually Transmit", grid=[1,8]) #create button widget to reset the password

    set_win.hide() #make the settngs window invisible

    #Setup Finish------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    setup_end = time.time() #stop the timer
    setup_time = setup_end - setup_start #calculate elapsed time since setup start
    print('Setup time: {} seconds'.format(setup_time)) #display the setup making time
     
    app.display() #push everything