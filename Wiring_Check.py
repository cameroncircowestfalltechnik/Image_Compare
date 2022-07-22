from gpiozero import DigitalInputDevice, DigitalOutputDevice
from guizero import App, Text, PushButton
import time

mold_open = DigitalInputDevice(4) #assign input pin (GPIO4 or Pin 7) to mold open signal
ejector_fire = DigitalInputDevice(17) #assign input pin (GPIO17 or Pin 11) to ejector fire signal
alarm_pin = DigitalOutputDevice(27) #assign output pin (GPIO27 or pin12) to alarm signal
alarm_reset_pin = DigitalOutputDevice(23) #assign output pin (GPIO23 or pin 16) to alarm reset signal
alarm_button = DigitalInputDevice(22) #assign input pin (GPIO22 or pin 15) to alarm reset button


def check_button():
    #if button.is_pressed: capture() #if button is pressed run "capture"
    t = time.localtime() #grab the current time
    current_time = (str(t[3])+":"+str(t[4])+":"+str(t[5])) #format it as a (hour:minute:second)
    
    if mold_open.value == 1: #if the mold open signal line is on
        print("") #add an empty line
        print(current_time +": mold open") #report button status
        mold_open_text.value = 'mold open: 1'
    else:
        mold_open_text.value = 'mold open: 0'
        
    if ejector_fire.value == 1: #if the mold open signal line is on
        print("") #add an empty line
        print(current_time +": ejector fire") #report button status
        ejector_fire_text.value = 'ejector fire: 1'
    else:
        ejector_fire_text.value = 'ejector fire: 0'

app = App(title='main', layout='auto', width = 250, height = 150) #create the main application window
app.when_closed=quit #when the close button is pressed on the main window, stop the program
mold_open_text = Text(app, text='mold open: 0')
ejector_fire_text = Text(app, text='ejector fire: 0')
alarm_but = PushButton(app, command=lambda: alarm_pin.blink(on_time=0.1,n=1), text="Simulate Alarm") #add alarm button
reset_but = PushButton(app, command=lambda: alarm_reset_pin.blink(on_time=0.1,n=1), text="Reset Alarm") #add reset button
app.repeat(1, check_button)
app.display()