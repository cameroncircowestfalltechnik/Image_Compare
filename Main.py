# #!/usr/bin/python #uncomment to designate the program as executable
from PIL import Image, ImageOps, ImageChops, ImageEnhance, ImageDraw, ImageFilter, ImageStat
from guizero import App,Text,TextBox,PushButton,Picture,Window,Combo,Box,Drawing
import time
import os
import picamera
from io import BytesIO
import numpy as np
import subprocess
from gpiozero import DigitalInputDevice, DigitalOutputDevice

#setup-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
setup_start = time.time() #start startup timer
print("Program starting. Please wait")
#I/O Setup
mold_open = DigitalInputDevice(4) #assign input pin (GPIO4 or Pin 7) to mold open signal
ejector_fire = DigitalInputDevice(17) #assign input pin (GPIO17 or Pin 11) to ejector fire signal
alarm_pin = DigitalOutputDevice(27) #assign output pin (GPIO27 or pin12) to alarm signal

#file path setup
base_folder = "/home/pi/Desktop/Main"
config_path = base_folder+"/config.txt" #define config file path
comparison_folder = base_folder+"/comparison_images"
output_folder = base_folder+"/output"
log_path = output_folder+"/log.csv" #specify log location
startup_log_path = output_folder+"/startup_log.csv" #specify startup log location
image_folder = output_folder+"/images/"
fail_folder = output_folder+"/fail/"
mask_archive = output_folder+"/mask_archive/"
comp_path = comparison_folder+"/compare_" #specify image file location
menu_image = base_folder+"/menu_image.jpg" #specify location of placeholder menu images

#kill the startup program
try: #attempt the following
    os.system("cd /home/pi/Desktop") #navigate to program location (probably redundant)
    os.system("\n pkill Main_Emulated_Startup.py") #kill the startup script-
except: #upon fail (likely indicating this program was started without the startup prgram being run
    pass #do nothing

#intialize/write some variables
is_first_full, is_first_empty = True,True #intialize the first fire status as true (the first time it fires a signal it will know it is the first time)
good = True #create variable to hold pass/fail status
full_qty, empty_qty = 0,0 #intialize image throwout counters
throwout_qty = 3 #define how many images to throwout upon startup
res_max = (3280, 2464) #define the max camera resolution
display_width = 1920 #define display width
display_height = 1080 #define display height
size_max = 5000000000 #set max output folder size (currently 5 GB)
size_status = 1 #create a interger to count how many times the size has been checked and maintain its status
size_check_reset = 10 #define how many times to request a folder check before actually running
fail_count = [0]*2 #counts how many consecutive fails have occured
fail_reset = 10 #specifies how many consectutive fails force a reset
did = [] #create empty list to store mask drawing ids (stores the ids of all drawings on the image)
coords = [] #create empty list to store drawing coordinates
polymode = False #intialize mask drawing mode as polygon mode off
mold_open_old = 1 #intialize the mold open last status
eject_fire_old = 1 #initialize ejector fire last status
full_score = None #intialize full score
full_pass = None #initialize full pass/fail
max_score = None #intialize max score value
x1, y1 = None, None #intialize starting coords of masking tool
tim = time.asctime() #intitizlize current time variable for capture sequence and to save the image mask
tim = tim[:13]+"_"+tim[14:16]+"_"+tim[17:24] #change time text format from hour:minute:second to hour_minute_second (windows filesystems dont like the ":" symbol in filenames)

#define colors for colorizing difference image
black = (0,0,0) #define black pixel rgb value
color = (0,255,0) #define colored pixel rgb value (in this case it's currently green)

#load the control images
full_ctrl = Image.open(comparison_folder+"/compare_full_ctrl.jpg") #load full control from storage
empty_ctrl = Image.open(comparison_folder+"/compare_empty_ctrl.jpg") #load empty control from storage

full_ctrl_candidate = full_ctrl #intialize full control  candidate (this way if the user attempts to reset the control before a candidate is set it doesn' break)
empty_ctrl_candidate = empty_ctrl #intialize empty control candidate

#open the log file
log = open(log_path, "a") #open log csv file in "append mode"

#grab current config settings
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
open_delay = float(lines[9].strip()) #read line 9 as open capture delay
eject_delay = float(lines[10].strip()) #read line 10 as the eject capture delay
server_ip = lines[11].strip() #read line 11 as the server IP
name = lines[12].strip() #read line 12 as the machine name
alarm_access = lines[13].strip() #read line 13 as the alarm access status
if alarm_access == "True": #if it read the text "True"
    alarm_access = True #enable alarm access
else: #otherwise
    alarm_access = False #disable alarm access

#The Camera Zone------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#capture and process the image
def capture():
    cap_start = time.time() #start image capture timer
    
    #take picture
    stream = BytesIO() #create memory buffer to write images to
    camera.capture(stream, format='jpeg', use_video_port=True) #capture to the buffer
    stream.seek(0) #move to the first image captured
    image = Image.open(stream) #write the image to the PIL object "comp" or comparison
    
    #finish timer
    cap_end = time.time() #stop the image capture time
    cap_time = cap_end - cap_start #calculate elapsed time
    #print('Capture "'+name+'" took: {} seconds'.format(round(cap_time,4))) #display it.
    print('Capture took: {} seconds'.format(round(cap_time,4))) #display it.
    return image
    
def process(name): #possible inputs "full" "empty" "calibrate_max"
    global full_score, full_pass, full_ctrl, empty_ctrl, max_score, tim, full_ctrl_candidate, empty_ctrl_candidate, fail_count
    decision_start = time.time() #start image capture timer
    
    #set the correct control image (ie. we are storing the respective controls as PIL images and we write to the "main" control named "control" based on which image we are capturing)
    if name == "full": #if the arg is "full"
        control = full_ctrl #set the main control to the full control
        comp = capture()
        #comp = Image.open(comparison_folder+"/Edit_full_ctrl.jpg") #manually overwrite image to load
    elif name == "empty": #if the arg is empty
        control = empty_ctrl #set the main control to the empty control
        comp = capture()
        #comp = Image.open(comparison_folder+"/Edit_empty_ctrl.jpg") #manually overwrite image to load
    elif name == "calibrate_max":
        control = full_ctrl #set the main control to the full control
        comp = empty_ctrl
    process_start = time.time() #start image processing timer
        
    #compensate for a difference in brightness
    comp_bw = comp.convert("L") #make black and white copy of comparison image
    control_bw = control.convert("L") #make b&w copy of control
    stat = ImageStat.Stat(comp_bw) #get image stats of b&w comparison
    comp_brightness = stat.mean[0] #average the color (this gives the image brightness)
    stat = ImageStat.Stat(control_bw) #get image stats of b&w control
    control_brightness = stat.mean[0] #average the color (this gives the image brightness)
    
    if comp_brightness > control_brightness: #if comparison image is brighter
        factor = comp_brightness/control_brightness #calculate the brightness factor (will be >1)
        enhancer = ImageEnhance.Brightness(control) #Say we want to change the brightness of the control
        control = enhancer.enhance(factor) #increase the control brightness by our brightness factor
    
    elif comp_brightness < control_brightness: #if the control is brighter
        factor = control_brightness/comp_brightness #calculate the brightness factor (will be >1)
        enhancer = ImageEnhance.Brightness(comp) #Say we want to change the brightness of the comparison image
        comp = enhancer.enhance(factor) #increase the comparison brightness by our brightness factor
    
    #find the difference in the images and apply the image mask
    diff = ImageChops.difference(control, comp) #find difference between images and name it "diff" or difference
    diff = ImageOps.grayscale(diff) #convert the difference to black and white
    diff = ImageChops.multiply(diff,mask) #introduce the masking filter (ie. any pixel location where the masking filter is white, the diff image is allowed to pass. Any pixel location where the masking filter is black, the diff image is turned black )
    #diff = diff.point( lambda p: 255 if p > 255/sens else 0) #turn any point above defined sensitivity white "255" and anything below black "0". Effectively turns grayscale to black and white.
    diff = diff.filter(ImageFilter.GaussianBlur(4)) #blur the image to remove noise
    diff = diff.point( lambda p: 255 if p > 255/sens else 0) #Make all pixels below the defined threshold black and all above white
    
    #analyze the difference and do something with the results
    tot = int(np.sum(np.array(diff)/255)) #convert diff to an array and find the elementwise sum, call it tot for "total". This represents the quantity of pixels that are different
    print('Score: '+str(tot)) #print the "total"
    if (tot > thresh) and (name != "calibrate_max") and (tot < max_score): #if the total number of diffent pixels are more than the defined threshold and we are not doing the max score test do the following:
        #print("Object detected") #say an object was detected
        simulate_alarm()
        good = False #designate as not good/fail
    elif (name == "full") and (tot > max_score): #if the score is higher than the max possible and name is "full"
        print("Misfire!") #say it is a misfire
        good = True #dont set off the alarm
        name = "full misfire" #declate it as a full misfire
    elif (name == "empty") and (tot > max_score): #if the score is higher than the max possible and name is "empty"
        print("Misfire!") #say it is a misfire
        good = True #dont set off the alarm
        name = "empty misfire" #declate it as an empty misfire
    else: #otherwise do the following:
        #print("No object detected") #say an object was not detected
        good = True #designate as good/pass
        #reset_alarm()
            
    process_end = time.time() #stop the timer
    process_time = process_end - process_start #calculate elapsed time since processing start
    #print('Process time: {} seconds'.format(process_time)) #display the image processing time
    decision_time = process_end - decision_start #calculate elapsed time  since decision start
    print('Decision Time: {} seconds'.format(round(decision_time,4))) #display the decision making time

    #generate the output image
    diff = ImageOps.colorize(diff, black, color, blackpoint=0, whitepoint=255, midpoint=127) #convert black and white differenc image to black and color for more contrast when displaying
    enhancer = ImageEnhance.Brightness(comp) #specify that we want to adjust the brightness of comp
    candidate = comp #save the comparison image to as a generic candidate for use later
    comp = enhancer.enhance(0.75) #decrease the brightness of comp by 25% for more contrast when displaying
    result = ImageChops.add(diff,comp) #overlay difference ontop of comp and call it result
    
    #rotate image if needed (if camera is mounted sideways or upsidedown)
    result = result.rotate(rot)
    
    if name == "full": #if the name is "full"
        tim = time.asctime() #grab current time as to match log name and file name
        tim = tim[:13]+"_"+tim[14:16]+"_"+tim[17:24] #change time text format from hour:minute:second to hour_minute_second (windows filesystems dont like the ":" symbol in filenames)
        pic_full.image = result #send results to the picture widget on the main page
        #save output to add to log in a moment
        full_score = tot #save the score
        full_pass = good #save the pass/fail
        full_ctrl_candidate = candidate #update the current control candidate (basically copy the image so that it can write over the current control if desired
        fail_index = 1
    elif name == "empty":
        pic_empty.image = result #send results to the picture widget on the main page
        empty_ctrl_candidate = candidate #update the current control candidate   
        #write the the data from empty and close to a line in the log (run at the end of ejector fire as that will ALWAYS happen after mold open)
        log.write(tim+","+str(full_score)+","+str(full_pass)+","+str(tot)+","+str(good)+"\n") #write time, score, and pass/fail to log
        log.flush()#save it
        fail_index = 0
    elif name == "calibrate_max": #if we are running a full test (compare full image to empty to calculate the highest possible score. anything above this score is a mistimed image
        max_score = int(0.6*tot) #update the internal max score (multiply by 0.9 so that values that are close can still trigger as misfire)
        print("Max Score: "+str(max_score)) #print the highest possible score
        return #leave the function
    elif name == "empty misfire": #if the current capture is an empty misfire
        pic_empty.image = result #refresh the main page image
        empty_ctrl_candidate = candidate #update the current control candidate anyway, we may need to set this as the new control anyway
        return #leave the function
    elif name == "full misfire": #if the current capture is a sull misfire
        pic_full.image = result #refresh the main page image
        full_ctrl_candidate = candidate #update the current control candidate anyway, we may need to set this as the new control anyway
        return #leave the function
    
    #the code should only be able to execute the following if "name" is full or empty
    if check_size(output_folder): #if the image folder enough space
        result.save(image_folder+tim+"_"+name+".jpg") #save results as a jpg with the current date and time
        folder_has_space = True
    else:
        print("output folder full, not saving image")
        folder_has_space = False            
    if good == True: #if the image passed
        fail_count[fail_index] = 0 #reset the fail counter
        set_control(name) #reset the control
        app.bg = "light grey" #reset the background color
    else: #if the image failed
        if folder_has_space == True: #if the image folder enough space
            control.save(fail_folder+tim+"_"+name+"_ctrl.jpg") #save the control to the fail folder
            candidate.save(fail_folder+tim+"_"+name+"_raw.jpg") #save the raw image to the fail folder
            result.save(fail_folder+tim+"_"+name+".jpg") #save a copy of the results to the fail folder
        fail_count[fail_index] = fail_count[fail_index]+1 #iterate the fail count for the current index
        if fail_count[fail_index] > fail_reset: #if the fail count of the current index exceeds the limit
            set_control(name) #reset the control images
            log.write(tim+",Reset,Reset,Reset,Reset\n") #describe the event in the log
            print("Found "+str(fail_reset)+" consecutive fails, assuming reset error, resetting control")
            
#Password Functions---------------------------------------------------------------------------------------------------------------------------------------
def request_settings(): #define code to request the openeing of the settings page
    keyboard("open") #open the keyboard
    pass_win.show() #show the password window
    pass_input.focus() #focus on the password window (user will not need to click on textbox to type password, they can just start typing)

def check_pass(): #define code to check of the password entered is correct
    password = pass_input.value
    if password == None: #if nothing is put in
        pass #do nothing, window closes
    elif password == current_password: #if the password is correct
        print("password correct!") #report into terminal
        pass_win.hide() #conceal the password window
        set_win.show() #make settings window visible
        pass_input.value = "" #clear the password entry box
        keyboard("close") #close the keyboard
    else: #if the password is incorrect
        pass_win.error("Warning", "Wrong Password") #create a new popup stating wrong password
        pass_input.value = "" #clear the password entry box
        
def cancel_pass(): #define what to do when password cancel button or window close is pressed
    pass_win.hide() #hide the password window
    keyboard("close") #close the keyboard
    pass_input.value = "" #clear the password entry box
    
#Button Functions-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def full_ctrl_focus(): #define code to open/focus the full control window
    full_preview.hide() #hide the window (if already hidden nothing will happen)
    full_preview.show() #show the window (this also brings it to the top)

def empty_ctrl_focus(): #define code to open/focus the empty control window
    empty_preview.hide() #hide the window (if already hidden nothing will happen)
    empty_preview.show() #show the window (this also brings it to the top)
    
def reset_alarm(): #define code to reset the alarm
    print("Alarm Reset") #placeholder: print text
    app.bg = "light grey"
    
def simulate_alarm(): #define the code to simulate the alarm
    app.bg = 'tomato' #set app color to red
    if alarm_access:alarm_pin.blink(on_time=0.1,n=1) #if alarm access is enabled make the alarm line "blink" for 0.1s once

def close_settings(): #define code to close the settings window
    sett_close = set_win.yesno("Restart?", "Restart program to send camera new settings? (Required for camera setting changes)") #create popup to ask if user wants to restart to push new settings to camera
    keyboard("close") #close the keyboard
    if sett_close == True: #if the answer is yes
        restart() #restart the program (maybe just migrate this out of a function if this is the only refrence)
    else: #otherwise (if the window is closed or no is selected)
        set_win.hide() #conceal the settings window
    
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
        set_win.error("Warning", "invalid input, not saving") #create a popup error
        
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
        set_win.error("Warning", "invalid input, not saving")
        
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
        set_win.error("Warning", "invalid input, not saving")

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
        set_win.error("Warning", "invalid width input, not saving") #create a popup error
    elif int(new_resw) > res_max[0]: #if the new width is higher than the max
        set_win.error("Warning", "width higher than camera can capture, not saving") #create a popup error
    elif numericw == True: #if the input is numeric
        print("Setting Camera image width to:"+str(new_resw)) #print to terminal
        res[0] = int(new_resw) #assign new width to its list position
        config_write(4,new_resw) #save to config file
        resw_input.value = "" #clear the textbox
    
    if new_resh == None: #if no height is input
        pass #do nothing
    elif numerich == False: #if the input is non numeric
        set_win.error("Warning", "invalid height input, not saving") #create a popup error
    elif int(new_resh) > res_max[1]: #if the new height is higher than the max
        set_win.error("Warning", "Height higher than camera can capture, not saving") #create popup error
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
        set_win.error("Warning", "invalid input, not saving")

def change_sens(): #define code to change the sensitivity
    try: #attempt the following
        new_sens = float(sens_input.value) #convert input to float
    except: #if it fails (input is non numeric)
        set_win.error("Warning", "invalid input, not saving")
    else: #otherwise (input IS numeric)
        print("Setting Contrast Sensitivity to:"+str(new_sens)) #print to terminal
        sens = new_sens #update the current value
        config_write(8,sens) #save to config file
        sens_curr_text.value = "Current Contrast Sensitivity: "+str(sens) #update window text
        sens_input.value = "" #clear the textbox

def change_open_delay(): #define code to change the sensitivity
    try: #attempt the following
        new_open_delay = float(open_delay_input.value) #convert input to float
    except: #if it fails (input is non numeric)
        set_win.error("Warning", "invalid input, not saving")
    else: #otherwise (input IS numeric)
        print("Setting mold open capture delay to:"+str(new_open_delay)) #print to terminal
        open_delay = new_open_delay #update the current value
        config_write(9,open_delay) #save to config file
        open_delay_curr_text.value = "Current Mold Open Capture Delay: "+str(open_delay) #update window text
        open_delay_input.value = "" #clear the textbox

def change_eject_delay(): #define code to change the sensitivity
    try: #attempt the following
        new_eject_delay = float(eject_delay_input.value) #convert input to float
    except: #if it fails (input is non numeric)
        set_win.error("Warning", "invalid input, not saving")
    else: #otherwise (input IS numeric)
        print("Setting eject fire capture delay to:"+str(new_eject_delay)) #print to terminal
        eject_delay = new_eject_delay #update the current value
        config_write(10,eject_delay) #save to config file
        eject_delay_curr_text.value = "Current Contrast Sensitivity: "+str(eject_delay) #update window text
        eject_delay_input.value = "" #clear the textbox

def change_sip(): #define code to change the server ip
    try: #attempt the following
        new_sip = str(sip_input.value) #grab input and ensure it's converted to string
    except: #if it fails
        set_win.error("Warning", "invalid input, not saving")
    else: #otherwise
        print("Setting Server IP to:"+new_sip) #print to terminal
        server_ip = new_sip #update the current value
        config_write(11,server_ip) #save to config file
        sip_curr_text.value = "Current Server IP: "+str(server_ip) #update window text
        sip_input.value = "" #clear the textbox

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

def change_name(): #define code to change the machine name
    try: #attempt the following
        new_name = str(name_input.value) #grab input and ensure it's converted to string
    except: #if it fails
        set_win.error("Warning", "invalid input, not saving")
    else: #otherwise
        print("Setting Machine Name to:"+new_name) #print to terminal
        name = new_name #update the current value
        config_write(12,name) #save to config file
        name_curr_text.value = "Current Name: "+str(name) #update window text
        name_input.value = "" #clear the textbox

#create functions to check each box for an enter key press
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

def open_delay_enter(event):
    if event.key == "\r": #check if key pressed is enter
        change_open_delay() #update the entry

def eject_delay_enter(event):
    if event.key == "\r": #check if key pressed is enter
        change_eject_delay() #update the entry

def sip_enter(event):
    if event.key == "\r": #check if key pressed is enter
        change_sip() #update the entry

def name_enter(event):
    if event.key == "\r": #check if key pressed is enter
        change_name() #update the entry

def pass_reset_enter(event):
    if event.key == "\r": #check if key pressed is enter
        reset_pass() #update the entry
        
def pass_enter(event):
    if event.key == "\r": #check if key pressed is enter
        check_pass() #update the entry
            
#Utility Functions------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def update_startup_log(): #define code to write to the startup log
    startup_log = open(startup_log_path, "a") #open startup log csv file in "append mode"
    startup_log.write(time.asctime()+","+current_password+","+str(iso)+","+str(ss)+","+cm+","+str(res[0])+","+str(res[1])+","+str(rot)+","+str(thresh)+","+str(sens)+","+str(open_delay)+","+str(eject_delay)+","+server_ip+","+str(max_score)+","+name+"\n") #write the current time and settings to the startup log
    startup_log.close() #close the startup log (auto saves new data)
    
def check_folder_size(path): #define code to get the size of a folder
    size = 0 #intialize size counter
    for entry in os.scandir(path): #for every entry in the specified path do the following
        if entry.is_file(): #if it is a file
            size = size+os.path.getsize(entry) #add the file size to the total size
        elif entry.is_dir(): #if it is a folder
            size = size+check_folder_size(entry.path) #get the size of the contents of the folder and add them to the total
    return size #return the folder size in bytes

def check_size(path): #create function to check if folder size is greater than max
    #this is setup to refresh the status every 10 requests and if the folder is full to remeber that and not continue checking. This is done to limit read cycles and processing time.
    global size_max, size_status  #make relevant variables global
    if size_status == 0: #if status is mode 0 dont attempt to check size again, we already know it's full
        return False
    elif size_status == 1: #if the size check counter has tickesd down to 1, check the folder size and reset the counter
        size = check_folder_size(path)
        if size < size_max: #if size is greater than max size (ie. has space for more files)
            size_status = size_check_reset #reset the size check counter
            return True
        else: #if the folder is full
            size_status = 0 #set the size status to code 0 (save that the folder is full and stop attempting to read it)
            return False
    elif size_status > 1: #if the counter is not at 1, we need to wait longer until checking again
        size_status = size_status-1 #iterate the counter by -1
        return True #allow it to write to the folder
    
def config_write(line,text): #create function to write over a line in config file (arguments:line number to write to, text/number to write)
    lines[line] = str(text)+"\n" #save new text to sepcified entry in "lines" array
    with open(config_path,'w') as f: #open the config file in write mode
        f.writelines(lines) #write the lines array to it
    
def check_signals(): #define code to check the signals
    global mold_open_old, eject_fire_old, full_qty, empty_qty, full_ctrl_candidate, empty_ctrl_candidate#import signal last statuses and first fire status
    t = time.localtime() #grab the current time
    current_time = (str(t[3])+":"+str(t[4])+":"+str(t[5])) #format it as a (hour:minute:second)
    
    if (mold_open.value == 1) and (mold_open_old == 0): #if the mold open signal line is on and the last time we checked it was off
        print("") #add an empty line
        print(current_time +": mold open, checking if full") #report signal status
        time.sleep(open_delay) #wait a user defined time before proceeding
        if full_qty < throwout_qty:
            print("Ignoring first few full")
            full_qty = full_qty+1 #increment empty_qty
            if full_qty == throwout_qty:
                full_ctrl_candidate = capture()
                set_control("full")
        else:
            process("full") #run processing for full mold
    mold_open_old = mold_open.value #update mold open last status
    
    if (ejector_fire.value == 1) and (eject_fire_old == 0): #if the mold open signal line is on and the last time we checked it was off
        print("") #add an empty line
        print(current_time +": ejector fire, checking if empty") #report signal status
        time.sleep(eject_delay) #wait user defined time before proceeding
        if empty_qty < throwout_qty:
            print("Ignoring first few empty")
            empty_qty = empty_qty+1 #increment empty_qty
            if empty_qty == throwout_qty:
                empty_ctrl_candidate = capture()
                set_control("empty")
        else:
            process("empty") #run processing for empty mold
    eject_fire_old = ejector_fire.value #update ejector fire last status

def toggle_alarm_access(): #define code to toggle alarm lockout
    global alarm_access #make the access state global
    if alarm_access == True: #if access is currently enabled
        alarm_access = False #disable it
        print("Disabling Alarm") #print the change
    elif alarm_access == False: #if access is currently disabled
        alarm_access = True #enable it
        print("Enabling Alarm") #print the change
    alarm_lock.text = "Alarm access is "+str(alarm_access) #update the button text with the new state
    config_write(13,alarm_access) #save to config file

def restart(): #define code to restart the program
    keyboard("close") #close the keyboard
    camera.close() #shutoff the camera
    app.destroy() #kill the new windows created by the programs
    os.system("\n sudo python Main_Startup.py") #run the prgram startup script

def shutdown(): #define code to shutdown the program
    keyboard("close") #close the keyboard
    camera.close() #shutoff the camera
    app.destroy() #kill the new windows created by the programs
    quit() #stop the program
    
def transmit(): #define code to transmit files to server This could probably jsut be done by a really long guizero button instead of as a function
    subprocess.Popen(["python", "Main_Transmit.py", "-pop"]) #run the transmit script with popups enabled

def keyboard(arg): #define code to open/close/toggle the keyboard
    #recieved argument:"open"
    if arg == "open": #if the argument is asking to open the keyboard do the following
        try: #attempt the following
            prog_id = subprocess.check_output(['pidof', 'matchbox-keyboard']) #read the program id of the keyboard
            prog_id = int(prog_id) #convert the id to an interger in order to remove superfluous text
        except subprocess.CalledProcessError: #if an error is returned (the program id is not found and thus not running)
            subprocess.Popen(["toggle-matchbox-keyboard.sh"]) #open matchbox keyboard
        else: #if a the command runs fine (a program id is found)
            pass #do nothing (these two lines are technically not needed but aid comprehension)
    
    #recieved argument:"close"
    elif arg == "close": #if the argument is asking to close the keyboard do the following
        try: #attemp the following
            prog_id = subprocess.check_output(['pidof', 'matchbox-keyboard']) #read the program id of the keyboard
            prog_id = int(prog_id) #convert the id to an interger in order to remove superfluous text
        except subprocess.CalledProcessError: #if an error is returned (the program id is not found and thus not running)
            pass #do nothing
        else: #if a the command runs fine (a program id is found)
            prog_id = str(prog_id) #convert the program id back to a string
            subprocess.run(['kill', prog_id]) #kill a program with the program id we grabbed above
    
    #recieved argument:"toggle"
    elif arg == "toggle": #if the argument is "toggle" do the following
        subprocess.Popen(["toggle-matchbox-keyboard.sh"]) #toggle the keyboard
    
    #recieved argument:none of the above
    else: #if an unspecified argument is entered
        print("keyboard: invalid argument") #print an error

def set_control(name): #define code to set the control image as the current candidate image (acceptable arguments:"full","empty") 
    global full_ctrl, empty_ctrl #make full_ctrl and empty_ctrl global so they can be written to
    app.bg = "light grey" #reset the background color
    print("resetting "+name) #print status message
    try: #attempt to do the following
        os.remove(comp_path+name+"_ctrl.jpg") #delete the current control image
    except: #upon failure do the following (will fail if no image is present)
        pass #do nothing
    #save the control candidate as the control jpg and update windows containing the control images
    if name == "full": #if name is "full"
        full_ctrl_candidate.save(comparison_folder+"/compare_"+name+"_ctrl.jpg") #save the full control candidate
        full_ctrl = full_ctrl_candidate #write over the current control with the candidate
        full_pic.image = full_ctrl
    elif name == "empty": #if name is "empty"
        empty_ctrl_candidate.save(comparison_folder+"/compare_"+name+"_ctrl.jpg") #save the empty control candidate
        empty_ctrl = empty_ctrl_candidate #write over the current control with the candidate
        empty_pic.image = empty_ctrl #update the preview image

def refresh_mask_preview(): #define code to generate and save the mask preview for use in the mask tool and archive
    global mask, current_mask
    mask = Image.open(comparison_folder+"/mask.jpg") #load image mask (yes this is necessary)
    mask_color = ImageOps.colorize(mask, black, color, blackpoint=0, whitepoint=255, midpoint=127) #convert from black and white to rgb
    enhancer = ImageEnhance.Brightness(mask_color) #specify that we want to adjust the brightness of the mask
    mask_color = enhancer.enhance(0.5) #decrease the brightness by 50% as to not obstruct the parts in the image
    current_mask = ImageChops.add(mask_color,full_ctrl) #superimpose the images
    current_mask.save(output_folder+"/mask_preview.jpg") #write over the currently archived mask preview
    mask = mask.convert("1") #convert it to mode "1" (1 or 0 value for each pixel ie. B&W one channel binary) for use as the filter
    
#Masking Tool Functions------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def launch_mask_tool(): #define code to launch masking tool window
    global pid #make picture id global
    drawing.delete(pid) #delete the current image in the window
    kill_all() #delete all the user made drawings
    pid = drawing.image(0,0,image=full_ctrl, width = res[0], height = res[1]) #update the masking window image with the new control image and svae the pic id
    mask_win.hide() #make the mask tool window invisible if possible
    mask_win.show() #make the mask tool window visible and bring to front
    
def toggle_mode(): #define code to toggle polygon mode on/off
    global polymode #make the status global
    if polymode == True: #if polygon mode is enabled
        polymode = False #turn it off
        mask_polymode.text = "Mode: Rectangle" #update button text
    else: #otherwise
        polymode = True #turn it on
        mask_polymode.text = "Mode: Polygon" #update button text

def start(event_data): #define what to do when starting a drawing
    global x1, y1 #make x1 and y1 global
    x1 = event_data.x #make x1 the mouse x position
    y1 = event_data.y #make y1 th mouse y position
    if polymode: #if polygon mode is on
        coords.append((x1,y1)) #add the coordinates to the coordinates array
    
def drag(event_data): #define what to do while dragging mouse (continually redraw a "preview" until the cursor is released)
    global x1, y1, x2, y2 #make x2 and y2 global
    x2 = event_data.x #save/update mouse x position as x2
    y2 = event_data.y #save/update mouse y position as y2
    
    if x1 == None: #if x1 and y1 have not yet been defined
        x1,y1 = x2,y2 #duplicate x2 and y2 to them
        
    if polymode: #if polygon mode is on
        coords.append((x2,y2)) #add the coordinates to the coords array
        tid = drawing.polygon(coords,color="light green") #create a polygon and save id to tid or "Temp ID" (this makes a polygon of the coords "dragged" so far)
    else: #otherwise (polygon mode is off)
        tid = drawing.rectangle(x1,y1,x2,y2, color="light green") #create box and save id to tid or "Temp ID"(this makes a box around the area selected so far)
    #delete the last "preview"
    if pid != (tid-1): #if the last drawing id is not the picture id
        drawing.delete(tid-1) #delete the last drawing

def finish(event_data): #define what to do when click is released
    global x1, y1, did #defined drawing id list as global

    if polymode: #if polygon mode is on
        tid = drawing.polygon(coords,color="light green") #draw a polygon of the coords swept by cursor. temporarily save the drawing id
        msk.polygon(coords, fill="white") #draw an identical polygon to the PIL image
        coords.clear() #wipe the coords array
    else: #otherwise
        tid = drawing.rectangle(x1,y1,x2,y2,color="light green") #draw a rectangle from where the mouse was pressed to where it was released. temporarily save the id
        msk.rectangle([(x1,y1),(x2,y2)], fill="white") #draw an identical rectangle to the PIL image
    did.append(tid) #add the drawing id of the drawing just made to the drawing id list
    x1,y1 = None,None #Wipe the original coords
    
def kill_last(): #define code to delete the last drawing
    if not len(did) == 0: #if the length drawing ids is not zero (if there are drawings present to delete)
        tid = did[-1:] #isolate the last entry
        tid = tid[0] #convert it to interger
        drawing.delete(tid) #kill that drawing number
        drawing.delete(tid-1) #kill the drawing before it too (technically the final drawing overlaps an identical preview version so this line deletes th preview underneath. yes i know this is a weird/inefficient way to do it)
        did.pop() #delete the last element from the drawing id list
    
def kill_all(): #define code to kill all drawings
    global pid #make picture id global
    did.clear() #wipe drawing id array
    drawing.clear() #delete all drawings
    pid = drawing.image(0,0,image=comparison_folder+"/compare_full_ctrl.jpg", width = res[0], height = res[1]) #add the image back in and save pic id to pid

def show_current_mask(): #define the code for displaying the current mask
    mask_preview.hide() #hide the window (if already hidden nothing will happen)
    mask_preview.show() #show the window (this also brings it to the top)

def request_mask_help(): #define what to do when help is requested in the masking tool window
    help_info = mask_win.info("Help", "Use this window to drag a box or polygon around the region to examine. Areas covered in green will be processed. Use kill last mask to delete the last drawng or the kill all masks button to dleete all of them and start over. Press the mode button to toggle between rectanlge mode and polygon mode. Dont forget to save the mask before closing. Finally, use the prevview button to view the current mask.") #create a popup with helpful text

def save_mask():
    global mask_img, msk
    mask_img.save(comparison_folder+"/mask.jpg") #saves PIL image built above as a jpg
    #reset the PIL Canvas
    mask_img = Image.new("1", res) #create PIL image in mode "1" (one channel, 1 bit per pixel b&w) with the same dimensions as the capture resolution
    msk = ImageDraw.Draw(mask_img) #make it so the image can be drawn on (create a container called msk)
    kill_all()#reset drawings
    refresh_mask_preview()
    mask_pic.image = output_folder+"/mask_preview.jpg"

#Main Window----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#code resumes here after running setup stuff at the top
refresh_mask_preview() #refresh update the preview mask in the output folder now that we have loaded all functions (this also loads the mask PIL image)
process("calibrate_max")
update_startup_log()

camera = picamera.PiCamera() #start up the camera
#set camera settings
camera.exposure_mode = cm #set camera mode
camera.shutter_speed = ss #set shutter speed
camera.iso = iso #set camera iso
camera.resolution = res #set camera resolution
time.sleep(2.5) #wait 2.5 seconds to allow camera to auto adjust/warmup
camera.exposure_mode = "off" #lock camera settings

#start camera stream
stream = picamera.PiCameraCircularIO(camera, seconds=1) #generate a camera stream in which the camera retains 1 second of footage
camera.start_recording(stream, format='h264') #start recording to the stream

#create windows
#app = App(title='main', layout='auto', width = 1700, height = 800) #create the main application window as a small window
app = App(title='Main', layout='auto', width = display_width, height = display_height) #create the main application window in a fullsize window
app.when_closed=shutdown #when the close button is pressed on the main window, stop the program
mask_win = Window(app, title='Masking Tool', layout='auto', width = 950, height = 800, visible=False, bg="gray75") #create the masking tool window, make the background slight;y darker than main for contrast
set_win = Window(app, title="Settings",layout="grid", width = 1920, height = 700, visible=False) #create the settings window
set_win.tk.geometry('%dx%d+%d+%d' % (1920, 700, 0, 0)) #center the window
settings_help_win = Window(set_win, title="Help", width=1600, height=800, visible=False) #create a settings help window

#control preview------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
full_preview = Window(app, title="full preview", width=800, height=600, visible=False) #create a "full" preview window
full_pic = Picture(full_preview, image=comp_path+"full_ctrl.jpg") #add the current full control as an image
PushButton(full_preview, command=full_preview.hide, text="Close",width=10, height=3) #add close button
empty_preview = Window(app, title="empty preview", width=800, height=600, visible=False) #create an "empty" preview window
empty_pic = Picture(empty_preview, image=comp_path+"empty_ctrl.jpg") #add the curent empty control as an image
PushButton(empty_preview, command=empty_preview.hide, text="Close",width=10, height=3) #add close button

#setup main window-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
PushButton(app, command=request_settings, text="Settings", align='bottom', height=3, width=20) #define settings button widget
pic_full = Picture(app, image=menu_image, align='top') #create picture widget to show the mold open image
pic_empty = Picture(app, image=menu_image, align='bottom') #create picture widget to show the ejector fire image
pic_full.repeat(1, check_signals) #attach repeat widget to the picture widget to run "check_signals" every 1ms

#Setup Masking Tool Window-----------------------------------------------------------------------------------------------------------------------------------------------------
mask_img = Image.new("1", res) #create PIL image in mode "1" (one channel, 1 bit per pixel b&w) with the same dimensions as the capture resolution
msk = ImageDraw.Draw(mask_img) #make it so the image can be drawn on (create a container called msk)

drawing = Drawing(mask_win,res[0],res[1]) #create drawing widget that fills the window
pid = drawing.image(0,0,image=comparison_folder+"/compare_full_ctrl.jpg", width = res[0], height = res[1]) #add the current control image to the drawing widget
mask_row1 = Box(mask_win, width=250, height=75, align='bottom') #create a container
PushButton(mask_row1, command=show_current_mask, text="Show Current Mask", align='left',height="fill",width="fill") #create a button to display the current mask
PushButton(mask_row1, command=request_mask_help, text="Help", align='right',height="fill",width="fill") #create a button to open mask tool help
mask_row2 = Box(mask_win, width=200, height=75, align='bottom') #create a container
PushButton(mask_row2, command=save_mask, text="Save Mask", align='left',height="fill",width="fill") #define button to save mask
PushButton(mask_row2, command=mask_win.hide, text="Close", align='right',height="fill",width="fill") #define polygon mode toggle button widget
mask_row3 = Box(mask_win, width=270, height=75, align='bottom') #create a container
PushButton(mask_row3, command=kill_last, text="Kill Last Mask", align='left',height="fill",width="fill") #define kill last button widget
PushButton(mask_row3, command=kill_all, text="Kill All Masks", align='right',height="fill",width="fill") #define kill all button widget
mask_polymode = PushButton(mask_win, command=toggle_mode, text="Mode: Rectangle", align='bottom',height=3) #define polygon mode toggle button widget
 
drawing.when_left_button_pressed = start #check for the left click to be pressed
drawing.when_mouse_dragged = drag #check for the mouse to drag
drawing.when_left_button_released = finish #checks for left click release

#create mask preview window
mask_preview = Window(mask_win, title="full preview", width=900, height=600, visible=False) #create a mask preview window
mask_pic = Picture(mask_preview, image=current_mask) #add the current mask as an image
PushButton(mask_preview, command=mask_preview.hide, text="Close",width=10,height=3) #add close button
#Password Entry Window------------------------------------------------------------------------------------------------------------------------------------------
pass_win = Window(app, title="Enter Password",layout="auto", width = 300, height = 100, visible=False) #create the password reset window
pass_win.when_closed=cancel_pass #when the close button is pressed on the password entry window, run the function "cancel_pass"
pass_input = TextBox(pass_win, align='top') #add old password textbox
pass_button_box = Box(pass_win, width=200, height=75, align='bottom') #create a container for password window buttons
PushButton(pass_button_box, command=cancel_pass, text="Cancel", align='right',height="fill",width=10)
PushButton(pass_button_box, command=check_pass, text="Ok", align='left',height="fill", width=10)
pass_input.when_key_pressed = pass_enter #if a key is pressed in the text box run the enter check
pass_win.tk.geometry('%dx%d+%d+%d' % (300, 100, display_width/2-(300/2), (display_height/2)-100)) #respecify settings window size (redundant but required) then position. The window is moved here to be out of the way of the keyboard)

#Password Reset Window Setup------------------------------------------------------------------------------------------------------------------------------------------------------------
pass_reset_win = Window(app, title="Password Reset",layout="grid", width = 300, height = 200, visible=False) #create the password reset window
Text(pass_reset_win, text="Old Password:" , grid=[1,1], height=2) #add old password text
old_pass_input = TextBox(pass_reset_win, grid=[2,1]) #add old password textbox
Text(pass_reset_win, text="New Password:" , grid=[1,2], height=2) #add new password text
new_pass_input = TextBox(pass_reset_win, grid=[2,2]) #add new password textbox
Text(pass_reset_win, text="Confirm New Password:" , grid=[1,3], height=2) #add password confirm text
conf_pass_input = TextBox(pass_reset_win, grid=[2,3]) #add password confirm textbox
PushButton(pass_reset_win, command=reset_pass, text="set", grid=[2,4], height=3, width=10) #add password set button
conf_pass_input.when_key_pressed = pass_reset_enter #if a key is pressed in the text box run the enter check
pass_reset_win.tk.geometry('%dx%d+%d+%d' % (300, 200, display_width/2, display_height/2)) #center the window

#Settings Window Setup--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#create section for ISO
iso_curr_text = Text(set_win, text="Current ISO: "+str(iso), grid=[1,1]) #define text widget to display current value
iso_input = TextBox(set_win, grid=[2,1]) #create text box widget to allow input of new value
iso_input.when_key_pressed = iso_enter #if a key is pressed in the text box run the enter check
PushButton(set_win, command=change_iso, text="set", grid=[4,1], height=2, width=10) #create button widget to save new value
Text(set_win, text="Range: 100-800", grid=[5,1]) #create text widget to display recommended range

#create secton for shutter speed (setup identical to ISO, see that section for line by line)
ss_curr_text = Text(set_win, text="Current Shutter Speed: "+str(ss), grid=[1,2]) 
ss_input = TextBox(set_win, grid=[2,2])
ss_input.when_key_pressed = ss_enter #if a key is pressed in the text box run the enter check
PushButton(set_win, command=change_ss, text="set", grid=[4,2], height=2, width=10)
Text(set_win, text="Range: 0-60,000", grid=[5,2])

#create section for setting camera mode
cm_curr_text = Text(set_win, text="Current Shutter Mode: "+cm, grid=[1,3]) #create text widget to display current mode
cm_combo = Combo(set_win, options=['sports', 'auto','antishake'], grid=[2,3], height=2) #create drop down menu widget to select new camera mode TO DO: Add more options
PushButton(set_win, command=change_cm, text="set", grid=[4,3], height=2, width=10) #create button widget to save mode
Text(set_win, text="Default: sports", grid=[5,3]) #create text widget to display recommended mode

#create secton for image rotation (setup identical to ISO, see that section for line by line)
rot_curr_text = Text(set_win, text="Current Image Rotation: "+str(rot), grid=[1,4])
rot_input = TextBox(set_win, grid=[2,4])
rot_input.when_key_pressed = rot_enter #if a key is pressed in the text box run the enter check
PushButton(set_win, command=change_rot, text="set", grid=[4,4], height=2, width=10)
Text(set_win, text="Range: 0-180", grid=[5,4])

#create section for image resolution
res_curr_text = Text(set_win, text="Current Camera Resolution: "+str(res[0])+" , "+str(res[1]), grid=[1,5]) #create text widget to display current value
resw_input = TextBox(set_win, grid=[2,5]) #create textbox widget for width input
resh_input = TextBox(set_win, grid=[3,5]) #create textbox widget for height input
resw_input.when_key_pressed = res_enter #if a key is pressed in the text box run the enter check
resh_input.when_key_pressed = res_enter #if a key is pressed in the text box run the enter check
PushButton(set_win, command=change_res, text="set", grid=[4,5], height=2, width=10) #create button widget to save resolution
Text(set_win, text="Default: 852 480", grid=[5,5]) #create text widget to display recommended/max values

#create secton for image threshold (setup identical to ISO, see that section for line by line)
thresh_curr_text = Text(set_win, text="Current Decision Threshold: "+str(thresh), grid=[1,6])
thresh_input = TextBox(set_win, grid=[2,6])
thresh_input.when_key_pressed = thresh_enter #if a key is pressed in the text box run the enter check
PushButton(set_win, command=change_thresh, text="set", grid=[4,6], height=2, width=10)
Text(set_win, text="Range: 8000-20,000", grid=[5,6])

#create secton for sensitivity (setup identical to ISO, see that section for line by line)
sens_curr_text = Text(set_win, text="Current Contrast Sensitivity: "+str(sens), grid=[6,1])
sens_input = TextBox(set_win, grid=[7,1])
sens_input.when_key_pressed = sens_enter #if a key is pressed in the text box run the enter check
PushButton(set_win, command=change_sens, text="set", grid=[8,1], height=2, width=10)
Text(set_win, text="Range: 3-15 (Decimal)", grid=[9,1])

#create secton for mold open capture delay (setup identical to ISO, see that section for line by line)
open_delay_curr_text = Text(set_win, text="Current Mold Open Capture Delay: "+str(open_delay), grid=[6,2])
open_delay_input = TextBox(set_win, grid=[7,2])
open_delay_input.when_key_pressed = open_delay_enter #if a key is pressed in the text box run the enter check
PushButton(set_win, command=change_sens, text="set", grid=[8,2], height=2, width=10)
Text(set_win, text="Range: 0.01-0.2 (Decimal)", grid=[9,2])

#create secton for ejector fire capture delay (setup identical to ISO, see that section for line by line)
eject_delay_curr_text = Text(set_win, text="Current Ejector Fire Capture Delay: "+str(eject_delay), grid=[6,3])
eject_delay_input = TextBox(set_win, grid=[7,3])
eject_delay_input.when_key_pressed = eject_delay_enter #if a key is pressed in the text box run the enter check
PushButton(set_win, command=change_sens, text="set", grid=[8,3], height=2, width=10)
Text(set_win, text="Range: 0.1-0.3 (Decimal)", grid=[9,3])

#create secton for server ip (setup identical to ISO, see that section for line by line)
sip_curr_text = Text(set_win, text="Current Server IP: "+server_ip, grid=[6,4])
sip_input = TextBox(set_win, grid=[7,4])
sip_input.when_key_pressed = sip_enter #if a key is pressed in the text box run the enter check
PushButton(set_win, command=change_sip, text="set", grid=[8,4], height=2, width=10)
Text(set_win, text="Default: 192.168.0.159", grid=[9,4])

#create secton for machine name (setup identical to ISO, see that section for line by line)
name_curr_text = Text(set_win, text="Current Machine Name: "+name, grid=[6,5])
name_input = TextBox(set_win, grid=[7,5])
name_input.when_key_pressed = name_enter #if a key is pressed in the text box run the enter check
PushButton(set_win, command=change_name, text="set", grid=[8,5], height=2, width=10)
Text(set_win, text="Default: Machine Number", grid=[9,5])

#add settings buttons
PushButton(set_win, command=lambda: keyboard("toggle"), text="Toggle Keyboard", grid=[2,11], height=3, width=15) #Add button to toggle keyboard
PushButton(set_win, command=settings_help_win.show, text="Help", grid=[3,11], height=3, width=15) #Add button to settings window for help window
PushButton(set_win, command=close_settings, text="Close", grid=[4,11], height=3, width=15) #create button widget to be able to close settings page (just executes hide command)
PushButton(set_win, command=lambda: process("calibrate_max"), text="Refresh Max Score", grid=[5,11], height=3, width=15) #Depreceated button
PushButton(set_win, command=pass_reset_win.show, text="Reset Password", grid=[6,11], height=3, width=15) #create button widget to reset the password
PushButton(set_win, command=transmit, text="Manually Transmit", grid=[5,12], height=3, width=15) #create button widget to reset the password
PushButton(set_win, command=simulate_alarm, text="Simulate Alarm", grid=[3,12], height=3, width=15) #define settings button widget
PushButton(set_win, command=lambda: set_control("full"), text="Reset Full Control", grid=[7,11], height=3, width=15) #define full control override button
PushButton(set_win, command=lambda: set_control("empty"), text="Reset Empty Control", grid=[8,11], height=3, width=15) #define empty control override button
PushButton(set_win, command=empty_ctrl_focus, text="Preview Empty Control", align='right', grid=[7,12], height=3, width=20) #define empty control preview button
PushButton(set_win, command=full_ctrl_focus, text="Preview Full Control", align='left', grid=[8,12], height=3, width=20) #define full control preview button
alarm_lock = PushButton(set_win, command=toggle_alarm_access, text="Alarm access is "+str(alarm_access), grid=[6,12], height=3, width=20) #define settings button widget
PushButton(set_win, command=lambda: process("empty"), text="Simulate Eject", grid=[8,6], height=3, width=15) #define simulate eject button widget
PushButton(set_win, command=lambda: process("full"), text="Simulate Open", grid=[7,6], height=3, width=15) #define simulate opeb button widget
PushButton(set_win, command=launch_mask_tool, text="Masking Tool", grid=[4,12], height=3, width=15) #define the asking tool button widget

#Settings help window setup-------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Text(settings_help_win, text="""ISO: Determine sensitivity to light, lower=darker and higher=brighter.\n
Shutter Speed: How fast the image is taken: A higher shutter speed makes an images less blurry, however the image is darker as there is less time to take in light.\n
The opposite goes for a low shutter speed, it will be more blurry yet brighter.\n
Shutter mode: Defines the camera mode. Auto:oriented for normal image capture. Sports:auto but oriented for higher shutter speed. OFF: Special mode that locks camera settings.\n
Image Rotation: Rotate displayed image. For use if camera needs to be mounted upside-down or sideways.\n
Camera Resolution: Defines the size of the image take (width x height). A higher resolution contains more detail but takes more time to process.\n
Decision Threshold: Defines the number of pixels that are different between the control and sample to setoff the alarm.\n
Contrast sensitivity: How sensitive program is to flag a pixel as different from the control. Higher means more likely.\n
Capture delays: How long to wait before capturing a picture of the mold in seconds.\n
Server IP: IP of the raspberry pi the data will be transmitted to via manual transmit.\n
Machine Name: Name of the client. This is the name at the beginning of the archive folder name.\n
Refresh Max Score: Runs processing of the controls to obtain the maximum possible score. This allows the program to automatically ignore mistimed or blurry images.\n
Simulate Buttons: Command the system to emulate the mold status or send the alarm signal (this is used to test alarm wiring and camera setup)\n
Control Resets: Allows you to manually override the controls, this must be run if the machine configuration changes as the system will look for the old layout unless rebooted\n
Preview Controls: Allows you to view the currently set control for each status.\n
Masking Tool: Allows you to designate the regions for the system to check.\n
Manually Transmit: Manually run the scheduled file upload from the client(this machine) to the server.\n
Alarm Access: Allows you to lock out the system from alarm access if it is creating too many false positives.""") #create a popup with helpful text
settings_help_close = PushButton(settings_help_win, command=settings_help_win.hide, text="Close",width=10,height=3) #add close button
settings_help_win.tk.geometry('%dx%d+%d+%d' % (1600, 700, display_width/2-(1600/2), 100)) #center the window

#Setup Finish------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
setup_end = time.time() #stop the timer
setup_time = setup_end - setup_start #calculate elapsed time since setup start
print('Setup time: {} seconds'.format(setup_time)) #display the setup making time
 
app.display() #push everything to the gui