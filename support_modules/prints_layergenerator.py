from tkinter import *
from tkinter.ttk import *
import cv2
import numpy as np
import time
import screeninfo
import sys
import winsound
import pycrafter9000
import Libs_Evan as libs
from make_it_2 import make2



# from playsound import playsound

class MyWindow:
    def __init__(self, win):
        instruction = '''
Check List:\n
1. Make sure the DLP Lightcrafter GUI is closed.\n
2. Open A3200 Motion Composer and all three axes are connected.\n
3. Do not open any window in the second screen!!!!!\n

Trouble Shooting:\n
1. USB Input/output error: Close DLP Lightcrafter GUI.\n
2. Reconnect stage with A3200 Motion Composer.\n
3. Over Current Fault: Click the green check "Acknowledge" bottom\n
 on top left in A3200 Motion Composer.\n
4. Reopen the window if elements in this window is not properly shown.\n
'''
        credit = '''
Professor Cheng Sun
Boyuan Sun, boyuansun2026@u.northwestern.edu
Evan Jones, XXX@northwestern.edu
'''
        self.reference = 0
        self.image_list = []
        self.exposure_time = []
        self.thickness = []
        self.win = win
        self.flag = False
        self.flag2 = False
        self.offset = -35
        # self.full_time = StringVar()
        # self.full_time.set(str(0))
        self.cache_clear_layer = 100000
        self.time1 = 1000

        self.canvas1 = Canvas(
            win,
            height=200,
            width=270,
            bg="#FFEFD5"
        )
        self.canvas1.place(x=70, y=520)
        self.canvas2 = Canvas(
            win,
            height=200,
            width=270,
            bg="#FFEFD5"
        )
        self.canvas2.place(x=370, y=520)

        self.lbl0 = Label(win, text='Rush', font='Helvetica 40 bold')
        self.lbl1 = Label(win, text='Directory of Images')
        #         self.lbl2 = Label(win, text='Layer Thickness(um)')
        #         self.lbl3 = Label(win, text='Exposure Time(s)')
        self.lbl4 = Label(win, text='Z Axis Position')
        self.lbl5 = Label(win, text=instruction, font='Helvetica 10', foreground='purple')
        self.lbl6 = Label(win, text=credit, font='Helvetica 7')
        self.lbl7 = Label(win, text='Printing Progress')
        self.lbl8 = Label(win, text='System Message:')
        self.lbl9 = Label(win, text='Move distance(mm)')
        self.lbl10 = Label(win, text='Layer thickness(um)')
        self.lbl11 = Label(win, text='Exposure time(s)')
        self.lbl11_2 = Label(win, text='Base curing time(s)')
        self.lbl12 = Label(win, text='Stage Control', font='Helvetica 12 bold')
        self.lbl13 = Label(win, text='Simple Txt File Generator', font='Helvetica 12 bold')
        self.lbl14 = Label(win, text='LED Current(0-255)')
        self.lbl15 = Label(win, text='Time Remaining: ∞ min')
        self.t1 = Entry(width=160)
        #         self.t2 = Entry()
        #         self.t3 = Entry()
        self.t4 = Entry()
        self.t8 = Entry()
        self.t9 = Entry()
        self.t10 = Entry()
        self.t11 = Entry()
        self.t11_2 = Entry()
        self.t14 = Entry()

        self.lbl0.place(x=550, y=50)
        self.lbl1.place(x=50, y=150)
        self.t1.place(x=180, y=150)
        #         self.lbl2.place(x=50, y=200)
        #         self.t2.place(x=180, y=200)
        #         self.lbl3.place(x=370, y=200)
        #         self.t3.place(x=500, y=200)
        self.lbl4.place(x=50, y=260)
        self.t4.place(x=50, y=280)
        self.lbl5.place(x=710, y=270)
        self.lbl6.place(x=950, y=0)
        self.t8.place(x=500, y=280)
        self.lbl8.place(x=500, y=260)
        self.t9.place(x=140, y=580)
        self.lbl9.place(x=140, y=560)
        self.t10.place(x=400, y=570)
        self.lbl10.place(x=400, y=550)
        self.t11.place(x=400, y=610)
        self.lbl11.place(x=400, y=590)
        self.t11_2.place(x=400, y=650)
        self.lbl11_2.place(x=400, y=630)
        self.lbl12.place(x=150, y=500)
        self.lbl13.place(x=410, y=500)
        self.t14.place(x=240, y=280)
        self.lbl14.place(x=240, y=260)
        self.lbl15.place(x=250, y=460)

        self.progress = Progressbar(win, orient=HORIZONTAL, length=500, mode='determinate')
        self.progress.place(x=50, y=430)
        self.lbl7.place(x=250, y=400)

        self.b1 = Button(win, text='Run', command=self.run)
        self.b2 = Button(win, text='Set Home', command=self.set_home)
        self.b3 = Button(win, text='Get Position', command=self.get_position)
        self.b4 = Button(win, text='Stop', command=self.stop)
        self.b5 = Button(win, text='Move Down', command=self.movedown)
        self.b6 = Button(win, text='Move Up', command=self.moveup)
        self.b7 = Button(win, text='Simple input txt generator', command=self.simple_txt)
        #         self.b8 = Button(win, text='Set Power', command=self.set_power)
        self.b9 = Button(win, text='Make It Two', command=self.make2)


        self.b1.place(x=70, y=200)
        self.b2.place(x=50, y=310)
        self.b3.place(x=130, y=310)
        self.b4.place(x=170, y=200)
        self.b5.place(x=100, y=630)
        self.b6.place(x=200, y=630)
        self.b7.place(x=440, y=680)
        #         self.b8.place(x=240, y=310)
        self.b9.place(x=0, y=0)
        #Init of DLP
        self.controller = pycrafter9000.dmd()
        self.application = libs.Application()
        self.controller.stopsequence()
        self.controller.changemode(3)
        # self.controller.standby()
        self.controller.hdmi()
        #Init of A3200
        ip = 'localhost'
        port = 8000
        self.my_ensemble = libs.Ensemble(ip, port)
        self.my_ensemble.connect()
        self.my_ensemble.write_read('BLOCKMOTION X Y 1')
        self.my_ensemble.write_read('BLOCKMOTION Z 0')
        self.my_ensemble.write_read('ENABLE Z')
        #Init of inputs
        self.t1.delete(0, 'end')
        self.t4.delete(0, 'end')
        self.t8.delete(0, 'end')
        self.t9.delete(0, 'end')
        self.t10.delete(0, 'end')
        self.t11.delete(0, 'end')
        self.t11_2.delete(0, 'end')
        self.t14.delete(0, 'end')
        self.t1.insert(END, str("C:\\Users\\User\\Documents\\Slicings\\power"))
        self.t4.insert(END, str("0"))
        self.t8.insert(END, str("Stage connected"))
        self.t9.insert(END, str("0"))
        self.t10.insert(END, str("5"))
        self.t11.insert(END, str("1.5"))
        self.t11_2.insert(END, str("60"))
        self.t14.insert(END, str("100"))

        screen_id = 0
        self.screen = screeninfo.get_monitors()[screen_id]
        self.window_name = 'show'
        self.black_image = np.zeros((1600, 2560))

    def run(self):
        """
        Perform a print
        """
        self.initilze_stage()
        self.input_directory()
        power = int(self.t14.get())
        self.controller.power(current=0)
        self.flag = True
        self.flag2 = True
        self.my_ensemble.write_read('MOVEABS Z {} 5'.format(self.reference))

        cv2.namedWindow(self.window_name, cv2.WND_PROP_FULLSCREEN)
        cv2.moveWindow(self.window_name, self.screen.x + 1439, self.screen.y - 1)
        cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.imshow(self.window_name, self.black_image)
        cv2.waitKey(1)
        while '4202508' != self.my_ensemble.write_read('AXISSTATUS(Z, DATAITEM_AxisStatus)'):
            time.sleep(0.2)
        re_limit = sys.getrecursionlimit()
        if re_limit < len(self.exposure_time):
            sys.setrecursionlimit(len(self.exposure_time)+1000)
        self.controller.changemode(0)
        time.sleep(5)
        # self.controller.wakeup()
        # self.controller.hdmi()
        self.controller.power(current=power)
        idx_list = np.arange(0,len(self.exposure_time),self.cache_clear_layer)
        for idx in idx_list:
            self.flag = True
            self._(idx)
        # self.controller.standby()
        self.controller.changemode(3)
        self.my_ensemble.write_read('MOVEINC Z {} 5'.format(self.offset))
        cv2.destroyAllWindows()
        while '4202508' != self.my_ensemble.write_read('AXISSTATUS(Z, DATAITEM_AxisStatus)'):
            time.sleep(0.2)
        winsound.Beep(440, 1000)
    #         self.t8.delete(0, 'end')
    #         self.t8.insert(END, str("Print Done"))

    def _(self, idx):
        # print(time.time()-self.time1)
        image = cv2.imread(self.image_list[idx].replace('\\', '\\\\'), cv2.IMREAD_GRAYSCALE)
        #         print(self.image_list)
        #         print(self.image_list[idx].replace('\\','\\\\'))
        cv2.imshow(self.window_name, image)
        cv2.waitKey(1)
        self.my_ensemble.write_read('MOVEINC Z {} {}'.format((self.thickness[idx] * -1) / 1000, self.thickness[idx] / self.exposure_time[idx]))
        time.sleep(self.exposure_time[idx])
        cv2.imshow(self.window_name, self.black_image)
        # self.time1 = time.time()
        cv2.waitKey(1)
        idx += 1
        self.progress['value'] = 100 / len(self.exposure_time) * idx

        minutes = str(np.floor((len(self.exposure_time)-idx)*self.exposure_time[-1]/60))
        seconds = str(np.floor((len(self.exposure_time)-idx)*self.exposure_time[-1]%60))
        self.lbl15.config(text ='Time Remaining (Not accurate): '+minutes+' & '+seconds+' seconds')

        #self.lbl15.config(text='Estimate Time: '+str((len(self.exposure_time)-idx)*self.exposure_time[-1]/60) +' min')
        # if idx%5 == 0:
        #     cv2.destroyAllWindows()
        #     cv2.namedWindow(self.window_name, cv2.WND_PROP_FULLSCREEN)
        #     cv2.moveWindow(self.window_name, self.screen.x + 1439, self.screen.y - 1)
        #     cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        while '4202508' != self.my_ensemble.write_read('AXISSTATUS(Z, DATAITEM_AxisStatus)'):
            time.sleep(0.01)
        if idx >= len(self.exposure_time):
            self.flag2 = False
        if idx%self.cache_clear_layer == 0:
            self.flag = False
        if self.flag and self.flag2:
            self.win.update()
            self.win.after(5, self._(idx))

    def set_home(self):
        """
        Set the position to home
        """
        self.reference = float(self.t4.get())
        self.my_ensemble.write_read('MOVEINC Z -25 5'.format(self.offset))
        self.t8.delete(0, 'end')
        self.t8.insert(END, str("Home Set"))

    def get_position(self):
        """
        Update Current Z Position
        :return:
        """
        self.t4.delete(0, 'end')
        self.t4.insert(END, str(self.my_ensemble.write_read('AXISSTATUS(Z, DATAITEM_PositionCommand)')))

    def stop(self):
        """
        User Interruption
        :return:
        """
        self.controller.stopsequence()
        self.controller.idle_on()
        self.flag2 = False
        cv2.destroyAllWindows()

    def initilze_stage(self):
        self.my_ensemble.write_read('BLOCKMOTION X Y 1')
        self.my_ensemble.write_read('BLOCKMOTION Z 0')
        self.my_ensemble.write_read('ENABLE Z')

    def input_directory(self):
        """
        Input all images from txt
        """
        path = str(self.t1.get())
        #         self.application.generate_debug_txt(path)
        self.image_list, self.exposure_time, self.thickness = self.application.set_image_directory(path)

    def moveup(self):
        """
        Move up by distance(mm) given
        """
        self.my_ensemble.write_read('BLOCKMOTION X Y 1')
        self.my_ensemble.write_read('BLOCKMOTION Z 0')
        self.my_ensemble.write_read('ENABLE Z')
        self.my_ensemble.write_read('MOVEINC Z {} 5'.format(float(self.t9.get()) * -1))

    def movedown(self):
        """
        Move up by distance(mm) given
        """
        self.my_ensemble.write_read('BLOCKMOTION X Y 1')
        self.my_ensemble.write_read('BLOCKMOTION Z 0')
        self.my_ensemble.write_read('ENABLE Z')
        self.my_ensemble.write_read('MOVEINC Z {} 5'.format(self.t9.get()))

    def simple_txt(self):
        """
        Generator txt with given exposure time and layer thickness
        """
        path = str(self.t1.get())
        thickness = str(self.t10.get())
        time = str(self.t11.get())
        base = str(self.t11_2.get())
        self.application.generate_debug_txt(path=path, thickness=thickness, time=time, base=base)

    def make2(self):
        path = str(self.t1.get())
        make2(path=path, extension='png')

#     def set_power(self):
#         """
#         Generator txt with given exposure time and layer thickness
#         """
#         power = int(self.t14.get())
#         self.controller.stopsequence()
#         self.controller.power(current=power)

window = Tk()
mywin = MyWindow(window)
window.title('Rush')
window.geometry("1200x800+10+10")
window.mainloop()