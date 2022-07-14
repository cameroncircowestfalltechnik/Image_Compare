import os

#This prgram is setup so that the main program can restart itself without creating a memory leak. The prgram would propely launch new instance of itself but never close the old one.
#So, this program is run instead, as it closes the old program first then relaunches it. Finally, this program is terminated on main script start so neither the main or startup scripts leak memory or open multiple instances.

try: #try the following
    os.system("\n pkill -f Main_Emulated.py") #kill the main program (ie. kill it if it is still running)
except:
    pass
os.system("cd /home/pi/Desktop") #mavigate to program location
os.system("\n sudo python Main_Emulated.py") #start the program

