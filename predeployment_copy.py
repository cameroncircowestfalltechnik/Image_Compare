# #!/usr/bin/python #uncomment to designate the program as executable
from PIL import ImageTk
import PIL
from guizero import App,Text,TextBox,PushButton,Picture,question,Window,Combo,info,Box#,Image
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
from gpiozero import DigitalInputDevice, DigitalOutputDevice
import shutil
import tkinter as tk

#setup-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#os.mkdir('debug2')
# os.chdir('/home/pi/Desktop')

# if os.environ.get('DISPLAY','') == '':
#     print('no display found. using 0.0')
#     os.environ.__setitem__('DISPLAY',':0.0')
    
setup_start = time.time() #start startup timer
#I/O Setup
mold_open = DigitalInputDevice(4) #assign input pin (GPIO4 or Pin 7) to mold open signal
ejector_fire = DigitalInputDevice(17) #assign input pin (GPIO17 or Pin 11) to ejector fire signal
alarm_pin = DigitalOutputDevice(27) #assign output pin (GPIO27 or pin12) to alarm signal
alarm_reset_pin = DigitalOutputDevice(23) #assign output pin (GPIO23 or pin 16) to alarm reset signal
alarm_button = DigitalInputDevice(22) #assign input pin (GPIO22 or pin 15) to alarm reset button

#file path setup
config_path = "/home/pi/Desktop/Object_Detection/compare/config.txt" #define config file path
comp_path = "/home/pi/Desktop/Object_Detection/compare/compare_" #specify image file location
log_path = "/home/pi/Desktop/Object_Detection/results/log.csv" #specify log location
startup_log_path = "/home/pi/Desktop/Object_Detection/results/startup_log.csv" #specify startup log location
image_path = "/home/pi/Desktop/Object_Detection/results/images/" #specify output image path

#kill the startup program
try: #attempt the following
    os.system("cd /home/pi/Desktop") #navigate to program location (probably redundant)
    os.system("\n pkill Main_Emulated_Startup.py") #kill the startup script-
except: #upon fail (likely indicating this program was started without the startup prgram being run
    pass #do nothing

#intialize/write some variables
good = True #create variable to hold pass/fail status
filetype = ".jpg" #specify image file filetype (leftover debug)
n = 0 #startup image counter
res_max = (3280, 2464) #define the max camera resolution
size_max = 500000000 #set max output folder size (currently 500MB)
alarm_access = False #intialize Alarm lockout
#root = tk.Tk()

#open the log file
log = open(log_path, "a") #open log csv file in "append mode"
if os.stat(log_path).st_size == 0:#if the csv file is empty do the following
    log.write("Timestamp,Score,Pass?\n") #Rebuild column labels 
    log.flush() #save text
    
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

#write to startup log
startup_log = open(startup_log_path, "a") #open startup log csv file in "append mode"
startup_log.write(time.asctime()+current_password+","+","+str(iso)+","+str(ss)+","+cm+","+str(res[0])+","+str(res[1])+","+str(rot)+","+str(thresh)+","+str(sens)+"\n") #write the current time and settings to the startup log
startup_log.close() #close the startup log (auto saves new data)

#The Camera Zone------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#capture and prcess the image
def capture(name):
    global cap_start
    cap_start = time.time() #start image capture timer
    
    #take picture
    stream = BytesIO() #start writing camera stream to memory
    camera.capture(stream, format='jpeg', use_video_port=True) #capture to the stream
    stream.seek(0) #move to the first image captured
    
    #save the picture
    img = Image.open(stream) #open the image
    img = img.save(comp_path+name+filetype) #save the image
    
    cap_end = time.time() #stop the image capture time
    cap_time = cap_end - cap_start #calculate elapsed time
    print('Capture "'+name+'" took: {} seconds'.format(cap_time)) #display it.
    process_start = time.time() #start image processing timer
    
    #open the comparison image and control
    try:
        base = Image.open(comp_path+name+"_ctrl"+filetype) #load control image
    except:
        set_control(name) #set the current base image as the control
        base = Image.open(comp_path+name+"_ctrl"+filetype) #load control image
    comp = Image.open(comp_path+name+filetype) #load comparison image
    
    #find the difference
    diff = ImageChops.difference(base, comp) #find difference between images and name it diff
    diff = ImageOps.grayscale(diff) #convert the difference to black and white
    diff = diff.point( lambda p: 255 if p > 255/sens else 0) #turn any point above defined sensitivity white "255" and anything below black "0". Effectively turns grayscale to black and white.
    
    #analyze the difference and do something with the results
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
    #print('Process time: {} seconds'.format(process_time)) #display the image processing time
    decision_time = process_end - cap_start #calculate elapsed time  since decision start
    print('Decision time: {} seconds'.format(decision_time)) #display the decision making time
    disp_start = time.time() #start display time timer
    
    #rotate images if needed
    base = base.rotate(rot) #rotate the control image if needed
    comp = comp.rotate(rot) #rotate the comparison image if needed
    diff = diff.rotate(rot) #rotate the difference image if needed

    #generate the output image
    black = (0,0,0) #define black pixel rgb value
    color = (0,255,0) #define colored pixel rgb value (in this case it's currently green)
    diff = ImageOps.colorize(diff, black, color, blackpoint=0, whitepoint=255, midpoint=127) #convert black and white differenc image to black and color for more contrast when displaying
    #result = ImageChops.hard_light(base,diff)
    #comp2 = comp #duplicate the comparison image to comp2
    enhancer = ImageEnhance.Brightness(comp) #specify that we want to adjust the brightness of comp2
    comp = enhancer.enhance(0.75) #decrease the brightness of comp2 by 25% for more contrast when displaying
    result = ImageChops.add(diff,comp) #overlay difference ontop of comp2 and call it result
    pic.image = result #send results to the picture widget on the main page
    
    #save the output image and write to the log
    tim = time.asctime() #grab current time as to match log name and file name
    if check_size(image_path):
        result.save(image_path+tim+".jpg") #save results as a jpg with the current date and time
    else:
        print("output folder full, not saving image")
    log.write(tim+","+str(tot)+","+str(good)+"\n") #write time, score, and pass/fail to log
    log.flush()#save it
    
    
    disp_end = time.time() #stop the timer
    disp_time = disp_end - disp_start #calculate elapsed time since display start
    #print('Display time: {} seconds'.format(disp_time)) #display the display time


#Button Functions-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def reset_alarm(): #define code to reset the alarm
    print("Alarm Reset") #placeholder: print text
    app.bg = "light grey"
    if alarm_access:alarm_reset_pin.blink(on_time=0.1,n=1) #make the alarm line "blink" for 0.1s once
    
def simulate_alarm(): #define the code to simulate the alarm
    app.bg = 'tomato' #set app color to red
    print("simulate alarm")
    if alarm_access:alarm_pin.blink(on_time=0.1,n=1) #if alarm access is enabled make the alarm line "blink" for 0.1s once
    
    
def request_settings(): #define code to request the openeing of the settings page
    toggle_keyboard("open")
    pass_win.show()
    pass_input.focus()
    #password = app.question(title="password", question="Enter Password:", initial_value=None) #launch popup window requesting password
    #password.tk.geometry('250x250+600+600')
    #if password == None: #if nothing is put in
    #    pass #do nothing, window closes
    #elif password == current_password: #if the password is correct
    #    print("password correct!") #report into terminal
    #    set_win.show() #make settings window visible
    #else: #if the password is incorrect
    #    app.error("Warning", "Wrong Password") #create a new popup stating wrong password

def check_pass():
    password = pass_input.value
    if password == None: #if nothing is put in
        pass #do nothing, window closes
    elif password == current_password: #if the password is correct
        print("password correct!") #report into terminal
        pass_win.hide()
        set_win.show() #make settings window visible
        pass_input.value = ""
    else: #if the password is incorrect
        app.error("Warning", "Wrong Password") #create a new popup stating wrong password

def request_setting_help(): #define code behind the settings help button
    help_info = set_win.info("Help", "Add helpful text describing all the settings here") #create a popup with helpful text

def close_settings():
    sett_close = set_win.yesno("Restart?", "Restart program to send camera new settings? (Not rquired if changing rotation, sensitivity, or threshold)") #create popup to ask if user wants to restart
    toggle_keyboard("close")
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

def pass_reset_enter(event):
    if event.key == "\r": #check if key pressed is enter
        reset_pass() #update the entry
        
def pass_enter(event):
    if event.key == "\r": #check if key pressed is enter
        check_pass() #update the entry
        
#Utility Functions------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def check_size(dest): #create function to check if folder size is greater than max
    global size_max  #make max size readable
    size = 0 #intialize/reset size variable
    for n in os.scandir(dest): #for every item in the directory do the following
        size = size+os.path.getsize(n) #add the size of the file to size
    if size < size_max: #if size is greater than max size (ie. has space for more files)
        return True
    else:
        return False
    
def config_write(line,text): #create function to write over a line in config file (arguments:line number to write to, text/number to write)
    lines[line] = str(text)+"\n" #save new text to sepcified entry in "lines" array
    with open(config_path,'w') as f: #open the config file in write mode
        f.writelines(lines) #write the lines array to it
    
def check_button():
    #if button.is_pressed: capture() #if button is pressed run "capture"
    t = time.localtime() #grab the current time
    current_time = (str(t[3])+":"+str(t[4])+":"+str(t[5])) #format it as a (hour:minute:second)
    
    if mold_open.value == 1: #if the mold open signal line is on
        print("") #add an empty line
        print(current_time +": mold open, checking if full") #report button status
        capture("full") #run processing for full mold
    elif ejector_fire.value == 1: #if the mold open signal line is on
        print("") #add an empty line
        print(current_time +": ejector fire, checking if empty") #report button status
        capture("empty") #run processing for empty mold
    elif reset_button.value == 1:
        print("") #add an empty line
        print(current_time +": Resetting alarm") #report button status
        reset_alarm() #reset the alarm

def toggle_alarm_access():
    global alarm_access
    if alarm_access == True:
        alarm_access = False
        print("Disabling Alarm")
    elif alarm_access == False:
        alarm_access = True
        print("Enabling Alarm")
    alarm_lock.text = "Alarm access is "+str(alarm_access)

def restart():
    camera.close() #shutoff the camera
    app.destroy() #kill the new windows created by the programs
    os.system("\n sudo python Main_Emulated_Startup.py") #run the prgram startup script

def shutdown():
    camera.close() #shutoff the camera
    app.destroy() #kill the new windows created by the programs
    quit()
    
def transmit():
    #DISABLED
    #subprocess.Popen(["python", "Main_Emulated_Transmit.py"]) #run the transmit script
    print("transmission disabled on this version")
    pass

def toggle_keyboard(arg):        
    if arg == "open": #if the argument is asking to open the keyboard do the following
        try: #attempt the following
            prog_id = subprocess.check_output(['pidof', 'matchbox-keyboard']) #read the program id of the keyboard
            prog_id = int(prog_id) #convert the id to an interger in order to remove superfluous text
        except subprocess.CalledProcessError: #if an error is returned (the program id is not found and thus not running)
            subprocess.Popen(["toggle-matchbox-keyboard.sh"]) #open matchbox keyboard
        else: #if a the command runs fine (a program id is found)
            pass #do nothing (these two lines are technically not needed but aid comprehension)
    
    elif arg == "close": #if the argument is asking to close the keyboard do the following
        try: #attemp the following
            prog_id = subprocess.check_output(['pidof', 'matchbox-keyboard']) #read the program id of the keyboard
            prog_id = int(prog_id) #convert the id to an interger in order to remove superfluous text
        except subprocess.CalledProcessError: #if an error is returned (the program id is not found and thus not running)
            pass #do nothing
        else: #if a the command runs fine (a program id is found)
            prog_id = str(prog_id) #convert the program id back to a string
            subprocess.run(['kill', prog_id]) #kill a program with the program id we grabbed above
    
    elif arg == "toggle": #if the argument is "toggle" do the following
        subprocess.Popen(["toggle-matchbox-keyboard.sh"]) #toggle the keyboard
    
    else: #if an unspecified argument is entered
        print("toggle_keyboard: invalid argument") #print an error

def set_control(name):
    print("resetting "+name)
    try: #attempt to do the following
        os.remove(comp_path+name+"_ctrl"+filetype) #delete the current control
    except: #upon failure do the following
        pass #do nothing
    shutil.copyfile(comp_path+name+filetype,comp_path+name+"_ctrl"+filetype) #copy the current comparison image as the control
    if name == "full": #if name is "full"
        full_pic.image = comp_path+name+"_ctrl"+filetype #update the preview image
    elif name == "empty": #if name is "empty"
        empty_pic.image = comp_path+name+"_ctrl"+filetype #update the preview image
    

#Main Window----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
with picamera.PiCamera() as camera: #start up the camera
    camera.exposure_mode = cm #set camera mode
    camera.shutter_speed = ss #set shutter speed
    camera.iso = iso #set camera iso
    camera.resolution = res #set camera resolution
    stream = picamera.PiCameraCircularIO(camera, seconds=1) #generate a camera stream in which the camera retains 1 second of footage
    camera.start_recording(stream, format='h264') #start recording to the stream
    camera.wait_recording(0.25) #allow the camera to run a second to allow it to autofocus
    
    #app = App(title='main', layout='auto', width = 900, height = 575+50+50) #create the main application window
    app = App(title='main', layout='auto', width = 1920, height = 1080) #create the main application window
    app.when_closed=shutdown #when the close button is pressed on the main window, stop the program
    #app.set_full_screen()
    #control preview------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    full_preview = Window(app, title="full preview", width=800, height=550, visible=False) #create a "full" preview window
    full_pic = Picture(full_preview, image=comp_path+"full_ctrl"+filetype) #add the current full control as an image
    full_pic_close = PushButton(full_preview, command=full_preview.hide, text="close") #add close button
    empty_preview = Window(app, title="empty preview", width=800, height=550, visible=False) #create an "empty" preview window
    empty_pic = Picture(empty_preview, image=comp_path+"empty_ctrl"+filetype) #add the curent empty control as an image
    empty_pic_close = PushButton(empty_preview, command=empty_preview.hide, text="close") #add close button
    #full_preview.hide() #conceal the full preview
    #empty_preview.hide() #conceal the empty preview
    
    #setup main window-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    pic = Picture(app, image="/home/pi/Desktop/Object_Detection/compare/ref.jpg", align='top') #create picture widget
    row1 = Box(app, width=180, height=50, align='bottom') #create a container for the reset and alarm buttons. call it row1
    reset_button = PushButton(row1, command=reset_alarm, text="Reset", align='left') #define reset button widget
    sim_button = PushButton(row1, command=simulate_alarm, text="Simulate Alarm", align='right') #define settings button widget
    row2 = Box(app, width=300, height=50, align='bottom') #create a container for the control set buttons, call it row2
    ctrl_set_full = PushButton(row2, command=lambda: set_control("full"), text="Reset Full Control", align='left')
    ctrl_set_empty = PushButton(row2, command=lambda: set_control("empty"), text="Reset Empty Control", align='right')
    row3 = Box(app, width=320, height=50, align='bottom') #create a container for the control preview buttons, call it row3
    empty_see = PushButton(row3, command=empty_preview.show, text="Preview Empty Control", align='right')
    full_see = PushButton(row3, command=full_preview.show, text="Preview Full Control", align='left')
    row4 = Box(app, width=240, height=50, align='bottom') #create a container for the control preview buttons, call it row3
    settings_button = PushButton(row4, command=request_settings, text="Settings", align='left') #define settings button widget
    alarm_lock = PushButton(row4, command=toggle_alarm_access, text="Alarm access is "+str(alarm_access), align='right') #define settings button widget
    pic.repeat(1, check_button) #attach repeat widget to the picture widget to run "check_button" every 1ms
    #reset_button.repeat(500, check_alarm)
    
    #Password Entry Window
    pass_win = Window(app, title="Enter Password",layout="auto", width = 300, height = 100, visible=False) #create the password reset window
    pass_input = TextBox(pass_win, align='top') #add old password textbox
    pass_button_box = Box(pass_win, width=100, height=50, align='bottom') #create a container for password window buttons
    pass_cancel = PushButton(pass_button_box, command=pass_win.hide, text="Cancel", align='right')
    pass_ok = PushButton(pass_button_box, command=check_pass, text="Ok", align='left')
    pass_input.when_key_pressed = pass_enter #if a key is pressed in the text box run the enter check
    pass_win.tk.geometry('300x100+960+560') #respecify settings window size (redundant but required) then position. The window is moved here to be out of the way of the keyboard)
    #pass_win.hide()
    
    #Password Reset Window Setup------------------------------------------------------------------------------------------------------------------------------------------------------------
    pass_reset_win = Window(app, title="Password Reset",layout="grid", width = 300, height = 120, visible=False) #create the password reset window
    old_pass_text = Text(pass_reset_win, text="Old Password:" , grid=[1,1]) #add old password text
    old_pass_input = TextBox(pass_reset_win, grid=[2,1]) #add old password textbox
    new_pass_text = Text(pass_reset_win, text="New Password:" , grid=[1,2]) #add new password text
    new_pass_input = TextBox(pass_reset_win, grid=[2,2]) #add new password textbox
    conf_pass_text = Text(pass_reset_win, text="Confirm New Password:" , grid=[1,3]) #add password confirm text
    conf_pass_input = TextBox(pass_reset_win, grid=[2,3]) #add password confirm textbox
    pass_reset_button = PushButton(pass_reset_win, command=reset_pass, text="set", grid=[2,4]) #add password set button
    conf_pass_input.when_key_pressed = pass_reset_enter #if a key is pressed in the text box run the enter check
    #pass_reset_win.hide() #conceal the password reset window

    #Settings Window Setup--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    set_win = Window(app, title="Settings",layout="grid", width = 900, height = 600, visible=False) #create the settings window

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
    #but = PushButton(set_win, command=print("placeholder"), text="Placeholder", grid=[4,8]) #Depreceated button
    new_pass_but = PushButton(set_win, command=pass_reset_win.show, text="Reset Password", grid=[5,8]) #create button widget to reset the password
    transmit_but = PushButton(set_win, command=transmit, text="Manually Transmit", grid=[1,8]) #create button widget to reset the password

    #set_win.hide() #make the settngs window invisible

    #Setup Finish------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    setup_end = time.time() #stop the timer
    setup_time = setup_end - setup_start #calculate elapsed time since setup start
    print('Setup time: {} seconds'.format(setup_time)) #display the setup making time
     
    app.display() #push everything
