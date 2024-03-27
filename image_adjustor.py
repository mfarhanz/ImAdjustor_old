"""
image/gif filtering viewer tool
p.s. needs kernel_ops.py as a dependency
"""
from os import listdir, path
from threading import Thread
from time import perf_counter
from sys import getsizeof
from psutil import Process
from tkinter import Tk, Canvas, Button, Scale, Menu, StringVar, IntVar, NW, HORIZONTAL, CENTER, filedialog, PanedWindow, Label, BOTH, RIGHT, SUNKEN
from tkinter.ttk import Progressbar, Button as ttkButton

from PIL import Image, ImageTk, ImageSequence
from numpy import array, clip, uint8

import kernel_ops
from filters import filter_matrix, color_matrix

class Editor:
    def __init__(self):
        self.LAST_TRANSFORM = None
        self.EFFECT_ACTIVE = False
        self.THREAD_REF = []
        self.FRAME_COUNT, self.GIF_DUR, self.CURR_FRAME, self.FILE_SIZE, self.CURR_OVERLAY_FILTER = 0, 30, 0, 0, 0
        self.theta, self.im_width, self.im_height = 1, 0, 0
        self.filter_worker2, self.filter_timer, self.filter_timer2, self.frame_id, self.frame_id2 = [None] * 5
        self.pilframes, self.filtframes, self.cachedframes, self.saveframes, self.frames2 = None, [], [], [], []
        self.dir_path, self.f_path = f'{path.dirname(path.realpath(__file__))}\\filter_frames', None
        self.curr_filter, self.curr_theme, self.curr_overlay_filter, self.dither_opt = [None] * 4
        self.curr_intensity, self.norm_thresh, self.norm_method = [None] * 3
        self.orig_img, self.scaled_img, self.newtkimg, self.filttkimg = [None] * 4
        self.root, self.canvas, self.menubar, self.play_gif, self.playbtnid, self.progress_bar = [None] * 6
        self.trans_bg = Image.open("C:\\Users\\mfarh\\OneDrive\\Pictures\\Downloads\\blacksquare3.png")
        self.playbtnstate, self.summary_bg, self.summary_txt = 0, None, None

    def setup(self):
        self.root = Tk()
        self.root.title("ImAdjustor")
        # f_path = "C:/Users/mfarh/OneDrive/Pictures/Screenshots/elizabeth.png"
        self.root.geometry('%dx%d+%d+%d' % (1200, 700, self.root.winfo_screenmmwidth() / 4,
                                            self.root.winfo_screenmmheight() / 4))
        self.canvas = Canvas(self.root, width=1200, height=700, background='black')
        self.curr_filter, self.curr_overlay_filter = StringVar(self.root, 'none'), StringVar(self.root, 'none')
        self.curr_theme, self.curr_filter = StringVar(self.root, 'none'), StringVar(self.root, 'none')
        self.norm_method, self.dither_opt = StringVar(self.root, 'Clip'), StringVar(self.root, 'Min_Max')
        self.curr_intensity, self.norm_thresh = IntVar(self.root, 1), IntVar(self.root, 100)
        self.menubar = Menu(self.root)
        self.root.config(menu=self.menubar)
        self.root.resizable(False, False)
        file_menu = Menu(self.menubar, tearoff=False)
        self.menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open", command=self.open_file)
        file_menu.add_command(label="Save As", command=self.save_file)
        themes_menu = Menu(self.menubar, tearoff=False)
        self.menubar.add_cascade(label="Themes", menu=themes_menu)
        for theme in list(color_matrix.keys()):
            themes_menu.add_radiobutton(label=theme, variable=self.curr_theme, value=theme, command=self.apply_color_matrix)
        filters_menu = Menu(self.menubar, tearoff=False)
        self.menubar.add_cascade(label="Filters", menu=filters_menu)
        for filter_option in list(filter_matrix.keys()):
            filters_menu.add_radiobutton(label=filter_option, variable=self.curr_filter, value=filter_option)
        normalize_menu = Menu(self.menubar, tearoff=False)
        self.menubar.add_cascade(label="Normalize", menu=normalize_menu)
        norm_options = ['clip', 'modulo', 'threshold']
        self.norm_method.set(norm_options[0])
        for option in norm_options:
            normalize_menu.add_radiobutton(label=option, variable=self.norm_method, value=option, command=self.toggle_scale)
        dither_menu = Menu(self.menubar, tearoff=False)
        self.menubar.add_cascade(label="DitherOpts", menu=dither_menu)
        dither_opts = ['min_max', 'round', 'set_to_matrix', 'norm_round', 'inv_min_max']
        self.dither_opt.set(dither_opts[0])
        for opt in dither_opts:
            dither_menu.add_radiobutton(label=opt, variable=self.dither_opt, value=opt)
        overlay_filter_menu = Menu(self.menubar, tearoff=False)
        self.menubar.add_cascade(label="Overlay", menu=overlay_filter_menu)
        overlay_filters = ['none', *(listdir(self.dir_path))]
        for fltr in overlay_filters:
            overlay_filter_menu.add_radiobutton(label=fltr, variable=self.curr_overlay_filter,
                                                value=fltr, command=self.load_overlay_filter)
        thresh_scale = Scale(self.root, from_=5, to=250, orient=HORIZONTAL, variable=self.norm_thresh,
                             showvalue=False, width=17, command=self.update_thresh)
        self.canvas.create_window(thresh_scale.winfo_reqwidth() * 4 - 4, 0, anchor="nw", window=thresh_scale, tags='threshold', state="hidden")
        intensity_menu_label = Menu(self.menubar, tearoff=False)
        self.menubar.add_cascade(label=f'Intensity: {self.curr_intensity.get()}', menu=intensity_menu_label, command=lambda: None)
        btn_inc = ttkButton(self.root, text='+', width=6, command=self.intensity_increase)
        btn_dec = ttkButton(self.root, text='-', width=6, command=self.intensity_decrease)
        self.canvas.create_window(thresh_scale.winfo_reqwidth() * 3 + 55, 0, anchor="nw", window=btn_dec)
        self.canvas.create_window(thresh_scale.winfo_reqwidth() * 3 + 10, 0, anchor="nw", window=btn_inc)
        thresh_menu_label = Menu(self.menubar, tearoff=False)
        self.menubar.add_command(label='  ', state="disabled")
        self.menubar.add_cascade(label=f'Threshold:  {self.norm_thresh.get()}', menu=thresh_menu_label, command=lambda: None, state="disabled")
        self.play_gif = Button(self.root, text='\u23F8', width=0, height=0, background='black', foreground='gray45',
                               activebackground='gray45', font='Helvetica 25', borderwidth=0,  command=self.toggle_play_gif)
        self.progress_bar = Progressbar(self.root, orient="horizontal", length=self.canvas.winfo_reqwidth() - 5, mode="determinate")
        self.canvas.create_window(self.canvas.winfo_reqwidth() - self.progress_bar.winfo_reqwidth() - 5,
                                  self.canvas.winfo_reqheight() - self.progress_bar.winfo_reqheight() - 20,
                                  anchor="nw", window=self.progress_bar, tags='progress', state="hidden")
        self.canvas.pack()
        self.root.mainloop()

    def clear_buffers(self):
        if self.cachedframes:
            self.cachedframes[:] = []
            self.scaled_img, self.orig_img = None, None
            self.canvas.delete("mainimg")
        if self.pilframes:
            self.pilframes, self.saveframes = None, []
            if self.filter_timer:
                self.root.after_cancel(self.filter_timer)
                self.filter_timer = None
                self.canvas.delete(self.frame_id)

    def open_file(self):
        ret = filedialog.askopenfilename(filetypes=[('', "*.jpg;*.jpeg;*.png;*.gif;*.bmp")])
        if ret:
            self.f_path = ret
            self.clear_buffers()
            if self.f_path[-3:] == 'gif':
                with Image.open(self.f_path) as gif:
                    self.FRAME_COUNT = gif.n_frames
                    self.CURR_FRAME = 0
                    self.GIF_DUR = gif.info['duration'] if 'duration' in gif.info.keys() else 30
                    if gif.size[0] > gif.size[1]:
                        self.im_width, self.im_height = 1200, int(700 / (gif.size[0] / gif.size[1])+gif.size[0]-gif.size[1])
                    else:
                        self.im_height, self.im_width = 700, int(700 / (gif.size[1] / gif.size[0]))
                    self.pilframes = ImageSequence.Iterator(Image.open(self.f_path))
                    for frame in self.pilframes:
                        tmpfrm = frame.convert(mode='RGB')
                        self.saveframes.append(tmpfrm)
                    del tmpfrm
                if not self.play_gif.winfo_ismapped():
                    self.playbtnid = self.canvas.create_window(self.canvas.winfo_reqwidth() - self.play_gif.winfo_reqwidth() - 30,
                                                           self.canvas.winfo_reqheight() - self.play_gif.winfo_reqheight() - 30,
                                                           anchor="nw", window=self.play_gif)
                self.FILE_SIZE = round((self.saveframes[0].width*self.saveframes[1].height*3)/1024**2 *len(self.saveframes), 1)
                self.animate(0)
                self.canvas.pack()
            elif self.f_path[-3:] in ['jpg', 'jpeg', 'png', 'bmp']:
                if self.play_gif.winfo_ismapped():
                    self.canvas.delete(self.playbtnid)
                    self.canvas.delete(self.frame_id)
                self.orig_img = Image.open(fp=self.f_path)
                if self.orig_img.size[0] > self.orig_img.size[1]:
                    self.im_width, self.im_height = 1200, int((self.orig_img.size[1]*1200)/self.orig_img.size[0])
                else:
                    self.im_height, self.im_width = 700, int((self.orig_img.size[0]*700)/self.orig_img.size[1])
                self.scaled_img = self.orig_img.convert(mode='RGB')
                self.scaled_img = self.scaled_img.resize((self.im_width, self.im_height))
                tkimg = ImageTk.PhotoImage(self.scaled_img)
                self.cachedframes.append(tkimg)
                self.canvas.create_image(0, 0, image=tkimg, anchor=NW, tags='mainimg')
                self.FILE_SIZE = round((self.scaled_img.size[0]*self.scaled_img.size[1]*3)/1024**2, 1)
                if self.summary_txt:
                    self.canvas.delete('summary')
                self.frame_summary(self.f_path[-3:])
            del ret
        else:
            del ret

    def frame_summary(self, ftype):
        if ftype in ['png', 'jpg', 'jpeg', 'bmp']:
            text = f"Size: {self.FILE_SIZE} MB\n" \
                   f"Dimensions: {self.orig_img.width} x {self.orig_img.height}\n" \
                   f"Processing time: {0} ms\nCurrent theme: {self.curr_theme.get()} ({self.curr_intensity.get()})\n" \
                   f"Current filter: {self.curr_filter.get()}"
            x, y = self.canvas.winfo_reqwidth() - 260, 50
            offsetx, offsety = 155, 20
        else:
            clr_count = 256 if not self.saveframes[self.CURR_FRAME].getcolors() else len(self.saveframes[self.CURR_FRAME].getcolors())
            text = f"Size: {self.FILE_SIZE} MB\nDimensions: {self.saveframes[0].width} x {self.saveframes[1].height}\n" \
                   f"Frame Count: {self.FRAME_COUNT}\nFrame Delay: {self.GIF_DUR} ms\nCurrent Frame: {self.CURR_FRAME+1}\n" \
                   f"Processing time: {0} ms\nCurrent theme: {self.curr_theme.get()} ({self.curr_intensity.get()})\n" \
                   f"Current filter: {self.curr_filter.get()}\nColor Count: {clr_count}"
            x, y = self.canvas.winfo_reqwidth() - 260, 50
            offsetx, offsety = 155, 50
        tkimg = ImageTk.PhotoImage(self.trans_bg.resize((190, 170 if ftype == 'gif' else 110)))
        self.summary_bg = self.canvas.create_image(x+60, y-35, image=tkimg, anchor=NW, tags='summary')
        self.summary_txt = self.canvas.create_text(x+offsetx, y+offsety, text=text, fill="white", font=("Arial", 12), tags='summary')
        self.canvas.new_image = tkimg
        del tkimg

    def save_file(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".png",
            filetypes=([("GIF files", "*.gif")], [("PNG files", "*.png"), ("JPG files", "*.jpg")])[not self.saveframes])
        if file_path:
            if self.saveframes:
                self.saveframes[0].save(file_path, save_all=True, append_images=self.saveframes[1:],
                               optimize=False, duration=Image.open(self.f_path).info['duration'], disposal=0, loop=0)
            else:
                self.scaled_img = self.scaled_img.resize(self.orig_img.size)
                self.scaled_img.save(file_path, save_all=True, optimize=False)

            print(f'{"GIF" if file_path[-3:] == "gif" else "Image"} saved to:  {file_path}')

    def load_overlay_filter(self):
        if self.filter_timer2:
            self.root.after_cancel(self.filter_timer2)
            self.canvas.delete('fltrimg')
        self.filter_timer2 = None
        self.frames2[:], self.filtframes[:] = [], []
        if self.curr_overlay_filter.get() != 'none':
            for filter_frame in listdir(f'{self.dir_path}\\{self.curr_overlay_filter.get()}'):
                tmp = Image.open(fp=f'{self.dir_path}\\{self.curr_overlay_filter.get()}\\{filter_frame}')
                self.filtframes.append(tmp.resize((1200, 700)))
                self.frames2.append(ImageTk.PhotoImage(self.filtframes[-1]))
                tmp = None
            del tmp
            self.animate2(0)

    def update_thresh(self, val):
        self.menubar.entryconfigure(9, label=f'Threshold:  {val}')

    def intensity_increase(self):
        self.curr_intensity.set(self.curr_intensity.get()+1)
        self.theta = self.curr_intensity.get()
        self.menubar.entryconfigure(7, label=f'Intensity: {self.curr_intensity.get()}')
        for name, var in {key: getsizeof(value) for key, value in self.__dict__.items()}.items():
            print(f'{name}: {var}')
        print(f'\n{int(process.memory_info().rss / 1024 ** 2)} MB used')
        self.color_matrix_process()

    def intensity_decrease(self):
        self.curr_intensity.set(self.curr_intensity.get()-1)
        self.theta = self.curr_intensity.get()
        self.menubar.entryconfigure(7, label=f'Intensity: {self.curr_intensity.get()}')
        self.color_matrix_process()

    def animate2(self, n):
        if n < len(self.frames2):
            self.canvas.delete('fltrimg')
            self.canvas.create_image(0, 0, image=self.frames2[n], anchor=NW, tags='fltrimg')
            self.canvas.create_image(self.frames2[n].width(), 0, image=self.frames2[n], anchor=NW, tags='fltrimg')
            self.canvas.create_image(self.frames2[n].width()*2, 0, image=self.frames2[n], anchor=NW, tags='fltrimg')
            self.canvas.create_image(0, self.frames2[n].height(), image=self.frames2[n], anchor=NW, tags='fltrimg')
            self.canvas.create_image(self.frames2[n].width(), self.frames2[n].height(), image=self.frames2[n], anchor=NW, tags='fltrimg')
            self.canvas.create_image(self.frames2[n].width()*2, self.frames2[n].height(), image=self.frames2[n], anchor=NW, tags='fltrimg')
            n = n + 1 if n != len(self.frames2) - 1 else 0
            self.filter_timer2 = self.root.after(2, self.animate2, n)

    def animate(self, n):
        try:
            self.cachedframes[:] = []
            self.canvas.delete(self.frame_id)
            self.newtkimg = ImageTk.PhotoImage(next(self.pilframes).resize((self.im_width, self.im_height)))
            self.cachedframes.append(self.newtkimg)
            self.CURR_FRAME = (n + 1) % (len(self.saveframes))
            self.frame_id = self.canvas.create_image(0, 0, image=self.newtkimg, anchor=NW)
            if self.summary_txt:
                self.canvas.delete(self.summary_txt, self.summary_bg, 'summary')
            self.frame_summary(self.f_path[-3:])
            self.filter_timer = self.root.after(self.GIF_DUR, self.animate, self.CURR_FRAME)
        except StopIteration:
            self.pilframes, self.newtkimg = None, None
            if not self.saveframes:
                self.pilframes = ImageSequence.Iterator(Image.open(self.f_path))
            else:
                self.pilframes = iter(self.saveframes)
            self.root.after(1, self.animate, self.CURR_FRAME)

    # def toggle_filter():
    #     global CURR_OVERLAY_FILTER, filter_timer2, filtframes, frames2, dir_path, curr_dir
    #     filtframes[:] = []
    #     if CURR_OVERLAY_FILTER < len(listdir(dir_path)):
    #         curr_dir = dir_path+f'\\{listdir(dir_path)[CURR_OVERLAY_FILTER]}'
    #         for filter_frame in listdir(curr_dir):
    #             filtframes.append(Image.open(fp=f'{curr_dir}/{filter_frame}').resize((x, y)))
    #         frames2[:] = [ImageTk.PhotoImage(ffrm) for ffrm in filtframes]
    #     CURR_OVERLAY_FILTER = (CURR_OVERLAY_FILTER + 1) % (len(listdir(dir_path))+1)
    #     print(CURR_OVERLAY_FILTER)
    #     print('no unused threads' if not THREAD_REF
    #           else f'{len(THREAD_REF)} threads in buffer')
    #     if not filter_timer2:
    #         animate2(0)
    #     elif CURR_FILTER == len(listdir(dir_path)):
    #         root.after_cancel(filter_timer2)
    #         canvas.delete('fltrimg')
    #         filter_timer2 = None
    #     else:
    #         root.after_cancel(filter_timer2)
    #         canvas.delete('fltrimg')
    #         filter_timer2 = None
    #         animate2(0)

    def toggle_play_gif(self):
        self.playbtnstate = self.playbtnstate ^ 1
        self.play_gif.configure(text=('\u23F8', '\u25B6')[self.playbtnstate])
        if not self.filter_timer:
            self.animate(self.CURR_FRAME)
        else:
            self.root.after_cancel(self.filter_timer)
            self.filter_timer = None

    def toggle_scale(self):
        if self.norm_method.get() in ['clip', 'modulo']:
            self.menubar.entryconfigure(9, state="disabled")
            self.canvas.itemconfigure('threshold', state="hidden")
        else:
            self.menubar.entryconfigure(9, state="normal")
            self.canvas.itemconfigure('threshold', state="normal")

    def apply_color_matrix(self):
        self.theta = 0
        self.curr_intensity.set(0)
        if self.THREAD_REF:
            for thid, thd in enumerate(self.THREAD_REF):
                thd.join()
                self.THREAD_REF.pop(thid)
        self.color_matrix_process()

    def color_matrix_process(self):
        print(f'\r{self.theta} {self.curr_theme.get()}')
        if self.f_path:
            if self.f_path[-3:] == 'gif':
                if self.curr_theme.get() == 'none':
                    self.EFFECT_ACTIVE = False
                    self.saveframes[:] = [frm.convert(mode='RGB') for frm in ImageSequence.Iterator(Image.open(self.f_path))]
                elif self.EFFECT_ACTIVE:
                    self.saveframes[:] = [frm.convert(mode='RGB', matrix=color_matrix[self.curr_theme.get()](self.theta)) for frm in self.saveframes]
                elif not self.EFFECT_ACTIVE:
                    tmpfrms = [frm.convert(mode='RGB') for frm in ImageSequence.Iterator(Image.open(self.f_path))]
                    self.saveframes[:] = [frm.convert(mode='RGB', matrix=color_matrix[self.curr_theme.get()](self.theta)) for frm in tmpfrms]
                    del tmpfrms
            else:
                self.canvas.delete("mainimg")
                if self.curr_theme.get() == 'none':
                    self.EFFECT_ACTIVE = False
                    self.scaled_img = self.orig_img.convert('RGB')
                    self.scaled_img = self.orig_img.resize((self.im_width, self.im_height))
                elif self.EFFECT_ACTIVE:
                    self.scaled_img = self.scaled_img.convert(mode='RGB', matrix=color_matrix[self.curr_theme.get()](self.theta))
                elif not self.EFFECT_ACTIVE:
                    self.scaled_img = self.orig_img.convert('RGB')
                    self.scaled_img = self.scaled_img.resize((self.im_width, self.im_height)).convert(mode='RGB',
                                                                matrix=color_matrix[self.curr_theme.get()](self.theta))
                self.newtkimg = ImageTk.PhotoImage(self.scaled_img)
                self.canvas.create_image(0, 0, image=self.newtkimg, anchor=NW, tags='mainimg')
            if self.summary_txt:
                self.canvas.delete(self.summary_bg, self.summary_txt, 'summary')
            self.frame_summary(self.f_path[-3:])

    def transform_matrix_process(process_frames):
        global scaled_img, saveframes, frames, newtkimg, EFFECT_ACTIVE
        strt = perf_counter()
        EFFECT_ACTIVE = True
        canvas.delete("mainimg")
        for frame in process_frames:
            imgarr = array(frame)
            imgchannels = [imgarr[:, :, 0], imgarr[:, :, 1], imgarr[:, :, 2]]
            kernel = array(transform_matrix[curr_filter.get()]['kernel'])
            dimx, dimy = imgchannels[0].shape[0], imgchannels[0].shape[1]
            op_type = transform_matrix[curr_filter.get()]['type']
            match op_type:
                case 'convolution':
                    pad_len = len(kernel) // 2
                    ret = kernel_ops.channel_op((dimx+2*pad_len)*(dimy+2*pad_len), imgchannels, kernel, op_type).astype(int)
                case 'ordered dither':
                    ret = kernel_ops.channel_op(dimx*dimy, imgchannels, kernel, op_type)
            match norm_method.get():
                case 'clip':
                    norm_ret = clip(ret, 0, 255)
                case 'modulo':
                    norm_ret = ret % 255
                case 'threshold':
                    norm_ret = ret.copy()
                    norm_ret[ret <= norm_thresh.get()] = 0
                    norm_ret[ret > norm_thresh.get()] = 255
            if f_path[-3:] == 'gif':
                saveframes.append(Image.fromarray(uint8(norm_ret)))
                frames.append(ImageTk.PhotoImage(saveframes[-1]))
            else:
                scaled_img = Image.fromarray(uint8(norm_ret), 'RGB')
                newtkimg = ImageTk.PhotoImage(scaled_img)
                canvas.create_image(0, 0, image=newtkimg, anchor=NW, tags='mainimg')
            stp = perf_counter()
            print(f'{(stp - strt) * 1000}ms')
        progress_bar.stop()
        print(f'\r{curr_filter.get()}')
        canvas.itemconfigure('progress', state="hidden")
        for wid in [btn1, btn2, menu1, menu2, menu3, scale1, spinner1]:
            if wid in [menu1, menu2, menu3]:
                wid.configure(state='readonly')
            else:
                wid.configure(state='normal')
        if f_path[-3:] == 'gif':
            btn3.configure(state='normal')

    def apply_transform_matrix(_):
        global THREAD_REF, scaled_img, pilframes, saveframes
        for wid in [btn1, btn2, menu1, menu2, menu3, scale1, spinner1]:
            wid.configure(state='disabled')
        if f_path[-3:] == 'gif':
            btn3.configure(state='disabled')
            process_frames = [frame for frame in pilframes]
            saveframes[:], frames[:] = [], []
        else:
            process_frames = [scaled_img]
        progress_bar.configure(maximum=100*len(process_frames))
        th1 = Thread(target=transform_matrix_process, args=(process_frames,))
        canvas.itemconfigure('progress', state="normal")
        progress_bar.start(44)
        THREAD_REF.append(th1)
        th1.start()

if __name__ == '__main__':
    process = Process()
    app = Editor()
    app.setup()



    # spinner1 = Spinbox(name="change", command=(root.register(color_matrix_process), '%d'), width=0, highlightthickness=4,
    #                    font=Font(family=families()[3], size=20, weight='bold'), state='readonly',
    #                    textvariable=StringVar(root, '\u03BA'))
    # btn1 = Button(name="save", text="save", width=5, command=savegif)
    # btn2 = Button(name="toggle", text="toggle filter", width=10, command=toggle_filter)
    # btn3 = Button(name="play_gif", text="play/pause", width=10, command=toggle_play_gif)
    # menu1 = Combobox(root, justify='center', height=5, textvariable=curr_theme,
    #                  values=list(color_matrix.keys()), state='readonly')
    # menu1.bind("<<ComboboxSelected>>", apply_color_matrix)
    # menu1label, menu2label = Label(root, text="theme :"), Label(root, text="effect :")
    # menu3label, menu4label = Label(root, text="normalize :"), Label(root, text="dither_opt :")
    # menu2 = Combobox(root, justify='center', height=5, textvariable=curr_filter,
    #                  values=list(transform_matrix.keys()), state='readonly')
    # menu2.bind("<<ComboboxSelected>>", apply_transform_matrix)
    # menu3 = Combobox(root, justify='center', height=5, textvariable=norm_method,
    #                  values=['clip', 'modulo', 'threshold'], state='readonly', width=10)
    # menu3.bind("<<ComboboxSelected>>", toggle_scale)
    # menu4 = Combobox(root, justify='center', height=5, textvariable=dither_opt,
    #                  values=['min_max', 'round', 'set_to_matrix', 'norm_round', 'inv_min_max'], state='readonly', width=10)
    # scale1 = Scale(root, from_=5, orient="horizontal", to=250, variable=norm_thresh, sliderlength=20)
    # progress_bar = Progressbar(root, orient="horizontal", length=canvas.winfo_reqwidth()-5, mode="determinate")
    # canvas.create_window(spinner1.winfo_reqwidth() * 1 + 20, 10, anchor="nw", window=spinner1)
    # canvas.create_window(spinner1.winfo_reqwidth() * 2 + 35, 10, anchor="nw", window=menu1label)
    # canvas.create_window(spinner1.winfo_reqwidth() * 3 + 20, 10, anchor="nw", window=menu1)
    # canvas.create_window(spinner1.winfo_reqwidth() * 6 + 40, 10, anchor="nw", window=menu2label)
    # canvas.create_window(spinner1.winfo_reqwidth() * 7 + 32, 10, anchor="nw", window=menu2)
    # canvas.create_window(spinner1.winfo_reqwidth() * 10 + 52, 10, anchor="nw", window=menu3label)
    # canvas.create_window(spinner1.winfo_reqwidth() * 12 + 20, 10, anchor="nw", window=menu3)
    # canvas.create_window(spinner1.winfo_reqwidth() * 14 + 30, 10, anchor="nw", window=menu4label)
    # canvas.create_window(spinner1.winfo_reqwidth() * 15 + 54, 10, anchor="nw", window=menu4)
    # canvas.create_window(canvas.winfo_reqwidth()-btn1.winfo_reqwidth()*3-10, 10, anchor="nw", window=btn1)
    # canvas.create_window(canvas.winfo_reqwidth()-btn1.winfo_reqwidth()*2, 10, anchor="nw", window=btn2)
    # canvas.create_window(canvas.winfo_reqwidth()-btn1.winfo_reqwidth()*2, 50, anchor="nw", window=btn3,
    #                      state="normal" if f_path[-3:] == 'gif' else "hidden")
    # canvas.create_window(spinner1.winfo_reqwidth() * 14 + 10, 10, anchor="nw", window=scale1, tags='threshold',
    #                      state="hidden")
    # canvas.create_window(canvas.winfo_reqwidth()-progress_bar.winfo_reqwidth()-5,
    #                      canvas.winfo_reqheight()-progress_bar.winfo_reqheight()-5,
    #                      anchor="nw", window=progress_bar, tags='progress', state="hidden")


