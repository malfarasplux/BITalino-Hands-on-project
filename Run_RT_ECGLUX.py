import bitalino
import numpy as np
import time
from pylab import *

#Set MAC (Windows)
macAddress = "20:17:09:18:46:98"
device = bitalino.BITalino(macAddress)
time.sleep(1)

#Biosignal acquisition parameters
srate = 100
nframes = 300

#Processing parameters
luxthreshold = 10
winsize = 300
drange = np.arange(winsize)
slwin = 3
pwinrange = 10
pwin = np.arange(-pwinrange,pwinrange,1)
hbfactor = 2.5
p2pfactor = 5
bpmthreshold = 70

#Moving average
def slideMean(x, N):
    return np.convolve(x, np.ones((N,))/N)[(N-1):]
	
device.start(srate, [1,5])
print ("START")

#Warmup data collection (initialise x3 Reads)
ECG0=[]
data = device.read(nframes)
ECG0 = np.append(ECG0,data[:, -2])
data = device.read(nframes)
ECG0 = np.append(ECG0,data[:, -2])
data = device.read(nframes)
ECG0 = np.append(ECG0,data[:, -2])

#Loop execution
ECG = ECG0
try:
    while True:

        #Read data
        data = device.read(nframes)
        
        #Check button
        if np.mean(data[:, 1]) < 1: break

        LUX = data[:, -1]
        ECG = np.append(ECG[nframes:],data[:, -2])        
        
		#Thresholding LUX average
        luxmean = np.mean(abs((LUX)))      
        if luxmean < luxthreshold:
            #Starting LED sequence
            device.trigger([1, 0])
            device.trigger([0, 0])
            device.trigger([1, 0])
            device.trigger([0, 0])

            #Estimate hr
            hrd = -1 
            conv = slideMean(ECG,slwin)
            lconv = len(conv)
            conv = conv[slwin:lconv-slwin]
            ECG_absdiff = abs(conv)
                
            ### First derivative
            conv1 = np.diff(conv)
            
            ### Second derivative
            conv2 = np.diff(conv1)
            data = conv2
            
            #Get peaks using second derivative and std
            dstd = np.std(data)
            peaks = np.where(abs(data) > hbfactor*dstd)[0]
            
            #Avoid neighbours pointing to the same peak
            dpeaks = np.diff(peaks)
            ipeaks = np.append(True, (dpeaks > 20))
            rpeaks = peaks[ipeaks]
            rpeaks0 = rpeaks
                
            #Peak to peak range to confirm
            is_peak = np.zeros((len(rpeaks)), dtype=bool)
            for j in xrange(0,len(rpeaks)):
                pwin_i = pwin + rpeaks[j]
                pwin_i = np.intersect1d(pwin_i[(pwin_i >= 0)],pwin_i[(pwin_i < len(data))])
                p2p = np.ptp(data[pwin_i])
                if (p2p > p2pfactor*dstd):
                    is_peak[j]=True      
            rpeaks=rpeaks[is_peak]
            
            #Compute hr(bpm)
            s0 = size(rpeaks0)
            s = size(rpeaks)

            if s > 1:
                hrd = (rpeaks[-1]-rpeaks[0])
                hrt = 1.0/(s-1) * hrd * 1.0/srate
                hr = 60.0 / hrt
                if hr > bpmthreshold:
                    #Alarm ==> BUZ + Conclude LED sequence (longer)
                    device.trigger([1, 1])
                    device.trigger([0, 0])
                    device.trigger([1, 0])
                    device.trigger([0, 0])
                    device.trigger([1, 0])
                    device.trigger([0, 0])
                    
                else:
                    #No Alarm ==> Conclude LED sequence
                    device.trigger([1, 0])
                    device.trigger([0, 0])                  
            else:
                hr = -1
            print(hr)
		
        else:
            #Turn LED off
            device.trigger([0, 0])
finally:
    device.trigger([0, 0])
    print "STOP"
    device.stop()
    device.close()