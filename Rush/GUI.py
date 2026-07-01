from tkinter import *
from tkinter.ttk import *
import time
# from playsound import playsound

class MyWindow:
    def __init__(self, win, img, exposure):
        instruction = '''
Contrary to popular belief, Lorem Ipsum is not simply random text. \n
It has roots in a piece of classical Latin literature from 45 BC, m\n
it over 2000 years old. Richard McClintock, a Latin professor at Ha\n
College in Virginia, looked up one of the more obscure Latin words,\n
from a Lorem Ipsum passage, and going through the cites of the word\n
literature, discovered the undoubtable source. Lorem Ipsum comes fr\n
10.32 and 1.10.33 of "de Finibus Bonorum et Malorum" (The Extremes \n
by Cicero, written in 45 BC. This book is a treatise on the theory \n
popular during the Renaissance. The first line of Lorem Ipsum, "Lor\n
'''
        credit = '''
Boyuan Sun, boyuansun2026@u.northwestern.edu
Evan Jones, XXX@northwestern.edu
'''
        self.reference = 0
        self.image_list = img
        self.exposure_time = exposure
        self.win = win
        self.flag = False

        self.lbl0 = Label(win, text='Rush', font='Helvetica 40 bold')
        self.lbl1 = Label(win, text='Directory of Images')
        self.lbl2 = Label(win, text='Layer Thickness(um)')
        self.lbl3 = Label(win, text='Exposure Time(s)')
        self.lbl4 = Label(win, text='Z Axis Position')
        self.lbl5 = Label(win, text=instruction, font='Helvetica 10 underline')
        self.lbl6 = Label(win, text=credit, font='Helvetica 7')
        self.lbl7 = Label(win, text='Printing Progress')
        self.t1 = Entry(width=160)
        self.t2 = Entry()
        self.t3 = Entry()
        self.t4 = Entry()

        self.lbl0.place(x=550, y=50)
        self.lbl1.place(x=50, y=150)
        self.t1.place(x=180, y=150)
        self.lbl2.place(x=50, y=200)
        self.t2.place(x=180, y=200)
        self.lbl3.place(x=370, y=200)
        self.t3.place(x=500, y=200)
        self.lbl4.place(x=50, y=330)
        self.t4.place(x=180, y=330)
        self.lbl5.place(x=700, y=270)
        self.lbl6.place(x=950, y=0)
        self.lbl7.place(x=250, y=450)

        self.progress = Progressbar(win, orient=HORIZONTAL, length=500, mode='determinate')
        self.progress.place(x=50, y=480)

        self.b1 = Button(win, text='Run', command=self.run)
        self.b2 = Button(win, text='Set Home', command=self.set_home)
        self.b3 = Button(win, text='Get Position', command=self.get_position)
        self.b4 = Button(win, text='Stop', command=self.stop)

        self.b1.place(x=70, y=240)
        self.b2.place(x=170, y=370)
        self.b3.place(x=70, y=370)
        self.b4.place(x=170, y=240)

    def run(self):
        """
        Perform a print
        """
        self.flag = True
        self._(0)

    def set_home(self):
        """
        Set the position to home
        """
        self.reference = float(self.t4.get())
        self.t3.insert(END, str(self.reference))
    def get_position(self):
        """
        Update Current Z Position
        :return:
        """
        self.t4.delete(0, 'end')
        position = 23333.345
        self.t4.insert(END, str(position))
    def stop(self):
        """
        User Interruption
        :return:
        """
        self.flag = False

    def _(self, idx):
        print("1. dispaly image")
        print("2. turn on DLP")
        print("3. move stage")
        while True:
            time.sleep(0.2)
            break
        print("4. turn off DLP")
        print("5. destory image")
        idx += 1
        self.progress['value'] = 100/len(self.exposure_time)*idx
        if idx >= len(self.exposure_time):
            self.flag = False
        if self.flag:
            self.win.update()
            self.win.after(5, self._(idx))


window = Tk()
img, exposure = [1]*120, [2]*120
mywin = MyWindow(window, img, exposure)
window.title('Rush')
window.geometry("1200x600+10+10")
window.mainloop()