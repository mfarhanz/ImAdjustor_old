"""
image/gif filtering viewer tool
p.s. needs kernel_ops.py and filters.py as a dependency
"""
from os import listdir, path
from threading import Thread
from multiprocessing import Array
from time import perf_counter
from sys import getsizeof
from io import BytesIO
from psutil import Process
from tkinter import Tk, Canvas, Button, Radiobutton,\
    Scale, Menu, StringVar, IntVar, NW, HORIZONTAL, filedialog
from tkinter.ttk import Style, Progressbar, Button as ttkButton
from tkinter.font import Font, families

from PIL import Image, ImageTk, ImageSequence
from numpy import array, clip, uint8, frombuffer, stack, float64

import kernel_ops
import objgraph
import gc
from filters import filter_matrix, color_matrix

class Editor:
    def __init__(self):
        self.EFFECT_ACTIVE = False
        self.THREAD_REF = []
        self.FRAME_COUNT, self.GIF_DUR, self.CURR_FRAME, self.FILE_SIZE, self.PROCESS_DUR = 0, 30, 0, 0, 0
        self.theta, self.im_width, self.im_height = 1, 0, 0
        self.filter_timer, self.filter_timer2, self.frame_id = [None] * 3
        self.pilframes, self.filtframes, self.cachedframes, self.saveframes, self.frames2 = None, [], [], [], []
        self.dir_path, self.f_path = f'{path.dirname(path.realpath(__file__))}', None
        self.curr_filter, self.curr_theme, self.curr_overlay_filter, self.dither_opt = [None] * 4
        self.curr_intensity, self.norm_thresh, self.coefficient, self.channel_id, self.norm_method = [None] * 5
        self.orig_img, self.scaled_img, self.red_img, self.blue_img, self.green_img, self.newtkimg, self.filttkimg = [None] * 7
        self.root, self.canvas, self.menubar, self.play_gif, self.btn_inc, self.btn_dec, self.progress_bar = [None] * 7
        self.trans_bg = Image.open(f'{self.dir_path}\\filter_frames\\blacksquare3.png')
        self.playbtnstate, self.playbtnid, self.summary_bg, self.summary_txt, self.process_order, self.wrap_cntr, self.orig_file_size = 0, None, None, None, '', 0, 0

    def setup(self):
        self.root = Tk()
        self.root.title("ImAdjustor")
        self.root.geometry('%dx%d+%d+%d' % (1200, 700, self.root.winfo_screenmmwidth() / 4,
                                            self.root.winfo_screenmmheight() / 4))
        self.canvas = Canvas(self.root, width=1200, height=700, background='black')
        self.curr_filter, self.curr_theme, self.curr_overlay_filter = StringVar(self.root, 'none'), StringVar(self.root, 'none'), StringVar(self.root, 'none')
        self.norm_method, self.dither_opt = StringVar(self.root, 'clip'), StringVar(self.root, 'min_max')
        self.curr_intensity, self.norm_thresh, self.coefficient, self.channel_id = IntVar(self.root, 1), IntVar(self.root, 100), IntVar(self.root, 125), IntVar(self.root, 0)
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
            filters_menu.add_radiobutton(label=filter_option, variable=self.curr_filter, value=filter_option, command=self.apply_transform_matrix)
        normalize_menu = Menu(self.menubar, tearoff=False)
        self.menubar.add_cascade(label="Normalize", menu=normalize_menu)
        norm_options = ['clip', 'modulo', 'threshold']
        self.norm_method.set(norm_options[0])
        for option in norm_options:
            normalize_menu.add_radiobutton(label=option, variable=self.norm_method, value=option, command=self.toggle_scale)
        dither_menu = Menu(self.menubar, tearoff=False)
        self.menubar.add_cascade(label="DitherOpts", menu=dither_menu)
        dither_opts = ['min_max', 'round', 'set_to_matrix', 'mod_round', 'inv_min_max', 'inv_set_to_matrix', 'gamma_correct', 'perturb']
        self.dither_opt.set(dither_opts[0])
        for opt in dither_opts:
            dither_menu.add_radiobutton(label=opt, variable=self.dither_opt, value=opt)
        overlay_filter_menu = Menu(self.menubar, tearoff=False)
        self.menubar.add_cascade(label="Overlay", menu=overlay_filter_menu)
        overlay_filters = ['none', *(listdir(f'{self.dir_path}\\filter_frames'))]
        for fltr in overlay_filters:
            overlay_filter_menu.add_radiobutton(label=fltr, variable=self.curr_overlay_filter,
                                                value=fltr, command=self.load_overlay_filter)
        thresh_scale = Scale(self.root, from_=5, to=250, orient=HORIZONTAL, variable=self.norm_thresh,
                             showvalue=False, width=17, command=self.update_thresh)
        coeff_scale = Scale(self.root, from_=5, to=250, orient=HORIZONTAL, variable=self.coefficient,
                             showvalue=False, width=17, command=self.update_coefficient)
        thresh_scale.bind("<ButtonRelease-1>", lambda _: self.apply_transform_matrix())
        self.canvas.create_window(thresh_scale.winfo_reqwidth() * 4 - 4, 0, anchor="nw", window=thresh_scale, tags='threshold', state="hidden")
        self.canvas.create_window(thresh_scale.winfo_reqwidth() * 5 - 4, 0, anchor="nw", window=coeff_scale)
        intensity_menu_label = Menu(self.menubar, tearoff=False)
        self.menubar.add_cascade(label=f'Intensity: {self.curr_intensity.get()}', menu=intensity_menu_label, command=lambda: None)
        self.btn_inc = ttkButton(self.root, text='+', width=6, command=self.intensity_increase)
        self.btn_dec = ttkButton(self.root, text='-', width=6, command=self.intensity_decrease)
        self.canvas.create_window(thresh_scale.winfo_reqwidth() * 3 + 55, 0, anchor="nw", window=self.btn_dec)
        self.canvas.create_window(thresh_scale.winfo_reqwidth() * 3 + 10, 0, anchor="nw", window=self.btn_inc)
        thresh_menu_label = Menu(self.menubar, tearoff=False)
        self.menubar.add_command(label='  ', state="disabled")
        self.menubar.add_cascade(label=f'Threshold:  {self.norm_thresh.get()}', menu=thresh_menu_label, command=lambda: None, state="disabled")
        theta_menu_label = Menu(self.menubar, tearoff=False)
        self.menubar.add_command(label=' ', state="disabled")
        self.menubar.add_cascade(label=f'\u03BB:  {self.coefficient.get()}', menu=theta_menu_label, command=lambda: None)
        self.play_gif = Button(self.root, text='\u23F8', width=0, height=0, background='black', foreground='gray45', relief='groove',
                               activebackground='gray45', font='Helvetica 25', borderwidth=1, command=self.toggle_play_gif)
        for i in range(4):
            rbtn = Radiobutton(self.root, text=('R', 'G', 'B', 'All')[i], variable=self.channel_id, value=(1, 2, 3, 0)[i],
                               bg='black', width=2, padx=5, pady=0, indicatoron=False, fg=('#FFB6B6', '#B6FFB9', '#B6D5FF', '#C5C5C5')[i],
                               font=Font(family=families()[40], size=8, weight='bold'), selectcolor='black',
                               activebackground=('#FFB6B6', '#B6FFB9', '#B6D5FF', '#C5C5C5')[i], command=self.channel_transform)
            rbtn.grid(row=0, column=i)
            self.canvas.create_window(self.canvas.winfo_reqwidth()-rbtn.winfo_reqwidth()*4+i*rbtn.winfo_reqwidth(),
                                      self.canvas.winfo_reqheight()-28, anchor="se", window=rbtn, tags='channel', state="hidden")
        style = Style()
        style.theme_use('default')
        style.configure("custom.Horizontal.TProgressbar", troughcolor='#221b33', background='#008f30', borderwidth=0)
        self.progress_bar = Progressbar(self.root, style="custom.Horizontal.TProgressbar", orient="horizontal", length=self.canvas.winfo_reqwidth() - 5, mode="determinate")
        self.canvas.create_window(self.canvas.winfo_reqwidth() - self.progress_bar.winfo_reqwidth() - 5,
                                  self.canvas.winfo_reqheight() - self.progress_bar.winfo_reqheight() - 5,
                                  anchor="nw", window=self.progress_bar, tags='progress', state="hidden")
        self.canvas.pack()
        self.root.mainloop()

    def clear_buffers(self):
        self.cachedframes[:], self.filtframes[:], self.frames2[:], self.saveframes[:] = [], [], [], []
        self.scaled_img, self.orig_img, self.red_img, self.green_img, self.blue_img, self.frame_id, self.filttkimg, self.newtkimg, self.pilframes = [None] * 9
        self.process_order, self.wrap_cntr, self.PROCESS_DUR, self.GIF_DUR, self.FRAME_COUNT, self.FILE_SIZE = '', 0, 0, 0, 0, 0
        self.canvas.delete("mainimg")
        self.curr_filter.set('none')
        self.curr_theme.set('none')
        self.curr_overlay_filter.set('none')
        self.curr_intensity.set(1)
        self.norm_thresh.set(100)
        self.norm_method.set('clip')
        self.dither_opt.set('min_max')
        if self.filter_timer2:
            self.root.after_cancel(self.filter_timer2)
            self.filter_timer2 = None
            self.canvas.delete('fltrimg')
        if self.filter_timer:
            self.root.after_cancel(self.filter_timer)
            self.filter_timer = None
            self.canvas.delete(self.frame_id)
        if self.THREAD_REF:
            for thd in self.THREAD_REF:
                thd.join()
                self.THREAD_REF.remove(thd)
        gc.collect()

    def open_file(self):
        ret = filedialog.askopenfilename(filetypes=[('', "*.jpg;*.jpeg;*.png;*.gif;*.bmp")])
        if ret:
            self.f_path = ret
            self.clear_buffers()
            if self.f_path[-3:] == 'gif':
                with Image.open(self.f_path) as gif:
                    self.FRAME_COUNT, self.CURR_FRAME = gif.n_frames, 0
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
                    gc.collect()
                if not self.play_gif.winfo_ismapped():
                    self.playbtnid = self.canvas.create_window(self.canvas.winfo_reqwidth() - self.play_gif.winfo_reqwidth() - 30,
                                                           self.canvas.winfo_reqheight() - self.play_gif.winfo_reqheight() - 50,
                                                           anchor="nw", window=self.play_gif)

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
                if self.summary_txt:
                    self.canvas.delete('summary')
                self.frame_summary(self.f_path[-3:])
            self.canvas.itemconfigure('channel', state="normal")
            self.get_size()
            self.orig_file_size = self.FILE_SIZE
            del ret
            gc.collect()
        else:
            del ret

    def frame_summary(self, ftype):
        bg_width = 200 + (len(self.curr_filter.get()) * 5, len(self.curr_theme.get()) * 5)[len(self.curr_filter.get()) <
                                                                                           len(self.curr_theme.get())]
        bg_height, offset, x, y = 180 if ftype == 'gif' else 125, 10, self.canvas.winfo_reqwidth() - bg_width - 15, 10
        if len(self.process_order[self.wrap_cntr:]) > 22:
            self.process_order += '\n\t'
            self.wrap_cntr += 22
        if ftype in ['png', 'jpg', 'jpeg', 'bmp']:
            text = f"Size: {self.FILE_SIZE} MB\n" \
                   f"Dimensions: {self.orig_img.width} x {self.orig_img.height}\n" \
                   f"Processing time: {self.PROCESS_DUR} ms\nCurrent theme: {self.curr_theme.get()} ({self.curr_intensity.get()})\n" \
                   f"Current filter: {self.curr_filter.get()}\nApplied: {self.process_order}"
        else:
            clr_count = 256 if not self.saveframes[self.CURR_FRAME].getcolors() else len(self.saveframes[self.CURR_FRAME].getcolors())
            text = f"Size: {self.FILE_SIZE} MB\nDimensions: {self.saveframes[0].width} x {self.saveframes[0].height}\n" \
                   f"Frame Count: {self.FRAME_COUNT}\nFrame Delay: {self.GIF_DUR} ms\nCurrent Frame: {self.CURR_FRAME+1}\n" \
                   f"Processing time: {self.PROCESS_DUR} ms\nCurrent theme: {self.curr_theme.get()} ({self.curr_intensity.get()})\n" \
                   f"Current filter: {self.curr_filter.get()}\nColor Count: {clr_count}\nApplied: {self.process_order}"
        tkimg = ImageTk.PhotoImage(self.trans_bg.resize((bg_width, bg_height+int(self.wrap_cntr/1.5))))
        self.summary_bg = self.canvas.create_image(x, y, image=tkimg, anchor=NW, tags='summary')
        self.summary_txt = self.canvas.create_text(x+offset, y+offset, text=text, anchor=NW, fill="white", font=Font(family=families()[40], size=10, weight='bold'), tags='summary')
        self.canvas.new_image = tkimg
        del tkimg
        gc.collect()

    def save_file(self):
        if not self.f_path:
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".png",
            filetypes=([("GIF files", "*.gif")], [("PNG files", "*.png"), ("JPG files", "*.jpg")])[not self.saveframes])
        if file_path:
            if self.saveframes:
                self.saveframes[0].save(file_path, save_all=True, append_images=self.saveframes[1:],
                               optimize=False, duration=Image.open(self.f_path).info['duration'], disposal=0, loop=0)
            else:
                if self.channel_id.get() == 1 and self.red_img:
                    self.red_img = self.red_img.resize(self.orig_img.size)
                    self.red_img.save(file_path, save_all=True, optimize=False)
                elif self.channel_id.get() == 2 and self.green_img:
                    self.green_img = self.green_img.resize(self.orig_img.size)
                    self.green_img.save(file_path, save_all=True, optimize=False)
                elif self.channel_id.get() == 3 and self.blue_img:
                    self.blue_img = self.blue_img.resize(self.orig_img.size)
                    self.blue_img.save(file_path, save_all=True, optimize=False)
                else:
                    self.scaled_img = self.scaled_img.resize(self.orig_img.size)
                    self.scaled_img.save(file_path, save_all=True, optimize=False)
            text_id = self.canvas.create_text(self.canvas.winfo_reqwidth()-150, self.canvas.winfo_reqheight()-80,
                                              text='Saved.', fill='green', font=Font(family=families()[21], size=11, weight='bold'))
            tmp = self.root.after(3000, lambda: (self.canvas.delete(text_id), self.root.after_cancel(tmp)))

            gc.collect()

    def get_size(self):
        self.FILE_SIZE = 0
        if self.f_path[-3:] == 'gif':
            for ffrm in self.saveframes:
                bytestream = BytesIO()
                ffrm.save(bytestream, format="PNG")
                self.FILE_SIZE += bytestream.getbuffer().nbytes / 1024 ** 2
            self.FILE_SIZE = round(self.FILE_SIZE, 1)
            del bytestream, ffrm
        else:
            bytestream = BytesIO()
            self.scaled_img.save(bytestream, format="PNG")
            self.FILE_SIZE = round(bytestream.getbuffer().nbytes / 1024 ** 2, 1)
            del bytestream
        gc.collect()

    def load_overlay_filter(self):
        if self.filter_timer2:
            self.root.after_cancel(self.filter_timer2)
            self.canvas.delete('fltrimg')
        self.filter_timer2 = None
        self.frames2[:], self.filtframes[:] = [], []
        print('no unused threads' if not self.THREAD_REF else f'{len(self.THREAD_REF)} threads in buffer')
        if self.curr_overlay_filter.get() != 'none':
            for filter_frame in listdir(f'{self.dir_path}\\filter_frames\\{self.curr_overlay_filter.get()}'):
                tmp = Image.open(fp=f'{self.dir_path}\\filter_frames\\{self.curr_overlay_filter.get()}\\{filter_frame}')
                self.filtframes.append(tmp.resize((1200, 700)))
                self.frames2.append(ImageTk.PhotoImage(self.filtframes[-1]))
                tmp = None
            del tmp
            gc.collect()
            self.animate2(0)

    def channel_transform(self):
        if self.f_path[-3:] != 'gif' and self.EFFECT_ACTIVE:
            self.canvas.delete("mainimg")
            if self.summary_txt:
                self.canvas.delete(self.summary_txt, self.summary_bg, 'summary')
            if self.channel_id.get() == 1 and self.red_img:
                self.newtkimg = ImageTk.PhotoImage(self.red_img)
                self.canvas.create_image(0, 0, image=self.newtkimg, anchor=NW, tags='mainimg')
            elif self.channel_id.get() == 2 and self.green_img:
                self.newtkimg = ImageTk.PhotoImage(self.green_img)
                self.canvas.create_image(0, 0, image=self.newtkimg, anchor=NW, tags='mainimg')
            elif self.channel_id.get() == 3 and self.blue_img:
                self.newtkimg = ImageTk.PhotoImage(self.blue_img)
                self.canvas.create_image(0, 0, image=self.newtkimg, anchor=NW, tags='mainimg')
            elif self.channel_id.get() == 0 and self.red_img:
                self.newtkimg = ImageTk.PhotoImage(self.scaled_img)
                self.canvas.create_image(0, 0, image=self.newtkimg, anchor=NW, tags='mainimg')
            self.frame_summary(self.f_path[-3:])

    def update_thresh(self, val):
        self.menubar.entryconfigure(9, label=f'Threshold:  {val}')

    def update_coefficient(self, val):
        self.menubar.entryconfigure(11, label=f'\u03BB:  {val}')

    def intensity_increase(self):
        if self.curr_theme.get() != 'none':
            self.curr_intensity.set(self.curr_intensity.get()+1)
            self.theta = self.curr_intensity.get()
            self.menubar.entryconfigure(7, label=f'Intensity: {self.curr_intensity.get()}')
            # for name, var in {key: getsizeof(value) for key, value in self.__dict__.items()}.items():
            #     print(f'{name}: {var}')
            print(f'\n{int(process.memory_info().rss / 1024 ** 2)} MB used')
            self.color_matrix_process()

    def intensity_decrease(self):
        # objgraph.show_most_common_types()
        dict_objects = [obj for obj in gc.get_objects() if isinstance(obj, type) and obj.__name__ == 'dict']
        print(dict_objects)
        print(objgraph.growth())
        print()

        if self.curr_theme.get() != 'none':
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
        self.color_matrix_process()

    def color_matrix_process(self):
        if not self.f_path:
            return
        if self.process_order[-(len(self.curr_theme.get())):] == self.curr_theme.get():
            self.process_order = self.process_order[:-len(self.curr_theme.get())-1]
        if self.f_path:
            if self.f_path[-3:] == 'gif':
                if self.curr_theme.get() == 'none':
                    self.saveframes[:] = [frm.convert(mode='RGB') for frm in ImageSequence.Iterator(Image.open(self.f_path))]
                elif self.EFFECT_ACTIVE:
                    self.process_order = self.process_order + '\u2192' + self.curr_theme.get()
                    self.saveframes[:] = [frm.convert(mode='RGB', matrix=color_matrix[self.curr_theme.get()](self.theta)) for frm in self.saveframes]
                elif not self.EFFECT_ACTIVE:
                    self.process_order = '' + self.curr_theme.get()
                    tmpfrms = [frm.convert(mode='RGB') for frm in ImageSequence.Iterator(Image.open(self.f_path))]
                    self.saveframes[:] = [frm.convert(mode='RGB', matrix=color_matrix[self.curr_theme.get()](self.theta)) for frm in tmpfrms]
                    del tmpfrms
                    gc.collect()
            else:
                self.canvas.delete("mainimg")
                if self.curr_theme.get() == 'none':
                    self.red_img, self.green_img, self.blue_img = [None] * 3
                    self.scaled_img = self.orig_img.convert('RGB')
                    self.scaled_img = self.orig_img.resize((self.im_width, self.im_height))
                elif self.EFFECT_ACTIVE:
                    self.process_order = self.process_order + '\u2192' + self.curr_theme.get()
                    self.scaled_img = self.scaled_img.convert(mode='RGB', matrix=color_matrix[self.curr_theme.get()](self.theta))
                    if self.red_img:
                        self.red_img = self.red_img.convert(mode='RGB', matrix=color_matrix[self.curr_theme.get()](self.theta))
                        self.green_img = self.green_img.convert(mode='RGB', matrix=color_matrix[self.curr_theme.get()](self.theta))
                        self.blue_img = self.blue_img.convert(mode='RGB', matrix=color_matrix[self.curr_theme.get()](self.theta))
                elif not self.EFFECT_ACTIVE:
                    self.red_img, self.green_img, self.blue_img = [None] * 3
                    self.process_order = '' + self.curr_theme.get()
                    self.scaled_img = self.orig_img.convert('RGB')
                    self.scaled_img = self.scaled_img.resize((self.im_width, self.im_height)).convert(mode='RGB',
                                                                matrix=color_matrix[self.curr_theme.get()](self.theta))
                self.newtkimg = ImageTk.PhotoImage(self.scaled_img)
                self.canvas.create_image(0, 0, image=self.newtkimg, anchor=NW, tags='mainimg')
            if self.curr_theme.get() == 'none':
                self.EFFECT_ACTIVE = False
                self.curr_filter.set('none')
                self.process_order, self.wrap_cntr, self.PROCESS_DUR, self.FILE_SIZE = '', 0, 0, self.orig_file_size
            if self.summary_txt:
                self.canvas.delete(self.summary_bg, self.summary_txt, 'summary')
            self.frame_summary(self.f_path[-3:])

    def transform_matrix_process(self, process_frames):
        self.EFFECT_ACTIVE = True
        strt = perf_counter()
        kernel = array(filter_matrix[self.curr_filter.get()]['kernel'])
        op_type = filter_matrix[self.curr_filter.get()]['type']
        pad_len = len(kernel) // 2
        threads = []
        for frame in process_frames:
            threads[:] = []
            ops = ['convolution', 'ordered dither', 'error diffusion']
            imgarr = array(frame).astype(int)
            imgchannels = [imgarr[:, :, 0], imgarr[:, :, 1], imgarr[:, :, 2]]
            process_channels = [Array('i', imgchannels[0].shape[0] * imgchannels[0].shape[1]) for _ in range(3)]
            for i in range(3):
                thd = Thread(target=(kernel_ops.convolve, kernel_ops.ordered_dither, kernel_ops.error_diffuse)[ops.index(op_type)],
                             args=((imgchannels[i], kernel, process_channels[i], pad_len),
                                   (imgchannels[i], kernel, process_channels[i], self.coefficient.get(), self.dither_opt.get()),
                                   (imgchannels[i], kernel, process_channels[i], self.coefficient.get(), self.dither_opt.get()))[ops.index(op_type)])
                threads.append(thd)
                thd.start()
            for thd in threads:
                thd.join()
            process_channels[:] = [frombuffer(channel.get_obj(), dtype=int).reshape(imgchannels[0].shape)
                                   for channel in process_channels]
            if self.f_path[-3:] == 'gif':
                chosen_channel = [0, 0, 0] if self.channel_id.get() == 1 \
                                else [1, 1, 1] if self.channel_id.get() == 2 \
                                else [2, 2, 2] if self.channel_id.get() == 3 else [0, 1, 2]
                ret = stack([process_channels[chosen_channel[0]], process_channels[chosen_channel[1]], process_channels[chosen_channel[2]]], axis=2)
            else:
                ret = stack([process_channels[0], process_channels[1], process_channels[2]], axis=2)
                ret_red = stack([process_channels[0], process_channels[0], process_channels[0]], axis=2)
                ret_green = stack([process_channels[1], process_channels[1], process_channels[1]], axis=2)
                ret_blue = stack([process_channels[2], process_channels[2], process_channels[2]], axis=2)
                match self.norm_method.get():
                    case 'clip':
                        norm_ret_red, norm_ret_green, norm_ret_blue = clip(ret_red, 0, 255), clip(ret_green, 0, 255), clip(ret_blue, 0, 255)
                    case 'modulo':
                        norm_ret_red, norm_ret_green, norm_ret_blue = ret_red % 255, ret_green % 255, ret_blue % 255
                    case 'threshold':
                        norm_ret_red, norm_ret_green, norm_ret_blue = ret_red.copy(), ret_green.copy(), ret_blue.copy()
                        norm_ret_red[ret <= self.norm_thresh.get()], norm_ret_red[ret > self.norm_thresh.get()] = 0, 255
                        norm_ret_green[ret <= self.norm_thresh.get()], norm_ret_green[ret > self.norm_thresh.get()] = 0, 255
                        norm_ret_blue[ret <= self.norm_thresh.get()], norm_ret_blue[ret > self.norm_thresh.get()] = 0, 255
            match self.norm_method.get():
                case 'clip':
                    norm_ret = clip(ret, 0, 255)
                case 'modulo':
                    norm_ret = ret % 255
                case 'threshold':
                    norm_ret = ret.copy()
                    norm_ret[ret <= self.norm_thresh.get()], norm_ret[ret > self.norm_thresh.get()] = 0, 255
            self.progress_bar.step(1)
            if self.f_path[-3:] == 'gif':
                self.saveframes.append(Image.fromarray(uint8(norm_ret)))
            else:
                self.scaled_img = Image.fromarray(uint8(norm_ret), 'RGB')
                self.red_img = Image.fromarray(uint8(norm_ret_red), 'RGB')
                self.green_img = Image.fromarray(uint8(norm_ret_green), 'RGB')
                self.blue_img = Image.fromarray(uint8(norm_ret_blue), 'RGB')
                self.newtkimg = ImageTk.PhotoImage(self.scaled_img)
                self.canvas.create_image(0, 0, image=self.newtkimg, anchor=NW, tags='mainimg')
        del imgarr, imgchannels, process_channels, ret, ops, op_type, pad_len, kernel
        if self.f_path[-3:] == 'gif':
            del chosen_channel
        else:
            del ret_red, ret_green, ret_blue, norm_ret, norm_ret_red, norm_ret_blue, norm_ret_green
        gc.collect()
        stp = perf_counter()
        self.progress_bar.stop()
        if self.f_path[-3:] == 'gif':
            self.animate(self.CURR_FRAME)
        self.PROCESS_DUR = round((stp - strt) * 1000, 2)
        if self.process_order:
            self.process_order = self.process_order + '\u2192' + self.curr_filter.get()
        else:
            self.process_order += self.curr_filter.get()
        self.get_size()
        self.canvas.itemconfigure('progress', state="hidden")
        self.frame_summary(self.f_path[-3:])
        for menu in range(len(self.menubar.winfo_children())):
            self.menubar.entryconfigure(menu, state="normal")
        for btn in [self.btn_inc, self.btn_dec, self.play_gif]:
            btn.config(state="normal")
        if len(self.THREAD_REF) > 1:
            self.THREAD_REF[0].join()
            del self.THREAD_REF[0]
            gc.collect()

    def apply_transform_matrix(self):
        if not self.f_path or self.curr_filter.get() == 'none':
            return
        for menu in range(len(self.menubar.winfo_children())):
            self.menubar.entryconfigure(menu, state="disabled")
        for btn in [self.btn_inc, self.btn_dec, self.play_gif]:
            btn.config(state="disabled")
        if self.f_path:
            self.canvas.delete(self.summary_txt, self.summary_bg, 'summary')
            if self.f_path[-3:] == 'gif':
                process_frames = [frame for frame in self.saveframes]
                if self.filter_timer:
                    self.root.after_cancel(self.filter_timer)
                    self.filter_timer = None
                    self.canvas.delete(self.frame_id)
            else:
                self.red_img, self.green_img, self.blue_img = [None] * 3
                process_frames = [self.scaled_img]
                self.canvas.delete("mainimg")
                gc.collect()
            self.PROCESS_DUR = 0
            self.saveframes[:] = []
            self.progress_bar.configure(maximum=len(process_frames))
            th1 = Thread(target=self.transform_matrix_process, args=(process_frames,))
            self.canvas.itemconfigure('progress', state="normal")
            self.THREAD_REF.append(th1)
            th1.start()

if __name__ == '__main__':
    process = Process()
    app = Editor()
    app.setup()
