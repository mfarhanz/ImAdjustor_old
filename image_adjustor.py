"""
image/gif filtering viewer tool
p.s. needs kernel_ops.py and filters.py as a dependency
"""
import tkinter
from os import listdir, path, remove as delfile, rename
from threading import Thread
from multiprocessing import Array
from time import perf_counter
from io import BytesIO
from uuid import uuid4
from psutil import Process
from gc import collect as gccollect
from _pickle import dump as pdump, load as pload
from tkinter import Tk, Canvas, Button, Radiobutton,Menu, Label, \
    LabelFrame, StringVar, IntVar, NW, HORIZONTAL, filedialog
from tkinter.ttk import Progressbar, Button as ttkButton, Scale as ttkScale
from tkinter.font import Font, families
from ttkthemes import ThemedStyle

from PIL import Image, ImageTk, ImageSequence
from numpy import array, clip, uint8, frombuffer, stack

from utils.kernel_ops import *
from utils.filters import color_matrix, filter_matrix

class Editor:
    def __init__(self):
        self.EFFECT_ACTIVE = False
        self.THREAD_REF, self.GIF_CHUNKS = [], []
        self.FRAME_COUNT, self.GIF_DUR, self.CURR_FRAME, self.FILE_SIZE, self.PROCESS_DUR = 0, 20, 0, 0, 0
        self.orig_width, self.orig_height, self.im_width, self.im_height, self.scrx, self.scry = 0, 0, 0, 0, 1200, 720
        self.filter_timer, self.filter_timer2, self.frame_id, self.temp_id, self.newtkimg = [None] * 5
        self.frames2, self.rbtns, self.clrscales, self.color_counts = [], [], [], []
        self.dir_path, self.f_path = f'{path.dirname(path.realpath(__file__))}', None
        self.curr_filter, self.curr_theme, self.curr_overlay_filter, self.dither_opt = [None] * 4
        self.curr_intensity, self.norm_thresh, self.coefficient, self.channel_id, self.norm_method, self.intensity_red, self.intensity_green, self.intensity_blue, self.frame_pointer = [None] * 9
        self.root, self.canvas, self.style, self.menubar, self.play_gif, self.frame_carousel, self.progress_bar, self.preview = [None] * 8
        self.btn_inc, self.btn_dec, self.clearbtn, self.intensity_frame, self.coeff_frame, self.thresh_frame = [None] * 6
        self.trans_bg = Image.open(f'{self.dir_path}\\assets\\blacksquare3.png')
        self.playbtnstate, self.inc, self.dec, self.summary_bg, self.summary_txt, self.process_order, self.wrap_cntr = 0, None, None, None, None, '', 0

    def setup(self):
        self.root = Tk()
        self.root.title("ImAdjustor")
        self.style = ThemedStyle(theme="black")
        self.root.geometry('%dx%d+%d+%d' % (self.scrx, self.scry, (self.root.winfo_screenmmwidth()-self.root.winfo_reqwidth()),
                                            (self.root.winfo_screenmmheight()-self.root.winfo_reqheight())))
        self.canvas = Canvas(self.root, width=self.scrx, height=self.scry, background='#2B2B2B')
        self.curr_filter, self.curr_theme, self.curr_overlay_filter = StringVar(self.root, 'None'), StringVar(self.root, 'None'), StringVar(self.root, 'None')
        self.norm_method, self.dither_opt = StringVar(self.root, 'Clip'), StringVar(self.root, 'Min-Max')
        self.curr_intensity, self.norm_thresh, self.coefficient, self.frame_pointer = IntVar(self.root, 1), IntVar(self.root, 100), IntVar(self.root, 125), IntVar(self.root, 0)
        self.channel_id, self.intensity_red, self.intensity_green, self.intensity_blue = IntVar(self.root, 0), IntVar(self.root, 85), IntVar(self.root, 85), IntVar(self.root, 85)
        self.menubar = Menu(self.root)
        self.root.config(menu=self.menubar)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.init_canvas()
        file_menu = Menu(self.menubar, tearoff=False)
        self.menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open", command=self.open_file)
        file_menu.add_command(label="Save As", command=self.save_file)
        file_menu.add_command(label="Clear", command=self.clear_screen)
        themes_menu = Menu(self.menubar, tearoff=False)
        self.menubar.add_cascade(label="Themes", menu=themes_menu)
        for theme in list(color_matrix.keys()):
            themes_menu.add_radiobutton(label=theme, variable=self.curr_theme, value=theme, command=self.apply_color_matrix)
        filters_menu = Menu(self.menubar, tearoff=False)
        self.menubar.add_cascade(label="Filters", menu=filters_menu)
        for filter_option in list(filter_matrix.keys()):
            if filter_option.isdigit():
                filters_menu.add_separator()
            else:
                filters_menu.add_radiobutton(label=filter_option, variable=self.curr_filter, value=filter_option, command=self.apply_transform_matrix)
        normalize_menu = Menu(self.menubar, tearoff=False)
        self.menubar.add_cascade(label="Normalize", menu=normalize_menu)
        norm_options = ['Clip', 'Modulo', 'Absolute', 'Inverted', 'Threshold', 'Threshold (inverted)']
        self.norm_method.set(norm_options[0])
        for option in norm_options:
            normalize_menu.add_radiobutton(label=option, variable=self.norm_method, value=option, command=self.toggle_scale)
        dither_menu = Menu(self.menubar, tearoff=False)
        self.menubar.add_cascade(label="DitherOpts", menu=dither_menu)
        dither_opts = ['Min-Max', 'Round', 'Set to Matrix', 'Rounded Modulo', 'Min-Max (inverted)', 'Set to Matrix (inverted)', 'Gamma Correct', 'Perturb']
        self.dither_opt.set(dither_opts[0])
        for opt in dither_opts:
            dither_menu.add_radiobutton(label=opt, variable=self.dither_opt, value=opt)
        overlay_filter_menu = Menu(self.menubar, tearoff=False)
        self.menubar.add_cascade(label="Overlay", menu=overlay_filter_menu)
        for fltr in ['None', *(listdir(f'{self.dir_path}\\assets\\filter_frames'))]:
            overlay_filter_menu.add_radiobutton(label=fltr, variable=self.curr_overlay_filter,
                                                value=fltr, command=self.load_overlay_filter)
        self.intensity_frame = LabelFrame(self.root, text=f'Intensity: {self.curr_intensity.get()}', font=Font(family=families()[40], size=10),
                                     background="#3C3F41", foreground='white')
        self.btn_inc = ttkButton(self.intensity_frame, text='   \u2795', width=6, padding=(2,))
        self.btn_dec = ttkButton(self.intensity_frame, text='   \u2796', width=6, padding=(2,))
        self.btn_inc.bind('<ButtonPress-1>', self.intensity_increase)
        self.btn_inc.bind('<ButtonRelease-1>', lambda _: self.root.after_cancel(self.inc) if self.inc else None)
        self.btn_dec.bind('<ButtonPress-1>', self.intensity_decrease)
        self.btn_dec.bind('<ButtonRelease-1>', lambda _: self.root.after_cancel(self.dec) if self.dec else None)
        self.intensity_frame.pack()
        self.btn_inc.grid(row=0, column=0, padx=5, pady=2)
        self.btn_dec.grid(row=0, column=1, padx=5, pady=2)
        self.canvas.create_window(self.canvas.winfo_reqwidth() - self.btn_dec.winfo_reqwidth()//2,
                                  self.canvas.winfo_reqheight() - 125, anchor="se", window=self.intensity_frame, tags='intensity', state="hidden")
        self.coeff_frame = LabelFrame(self.root, text=f'\u03BB: {self.coefficient.get()}', font=Font(family=families()[40], size=10),
                                  background="#3C3F41", foreground='white')
        coeff_scale = ttkScale(self.coeff_frame, from_=5, to=250, orient=HORIZONTAL, variable=self.coefficient,
                               length=105, command=self.update_coefficient)
        self.coeff_frame.pack(), coeff_scale.pack(padx=5, pady=2)
        self.canvas.create_window(self.canvas.winfo_reqwidth() - self.btn_dec.winfo_reqwidth()//2,
                                  self.canvas.winfo_reqheight() - 185, anchor="se", window=self.coeff_frame, tags='coefficient', state="hidden")
        self.thresh_frame = LabelFrame(self.root, text=f'Threshold: {self.norm_thresh.get()}',
                                  font=Font(family=families()[40], size=10),
                                  background="#3C3F41", foreground='white')
        thresh_scale = ttkScale(self.thresh_frame, from_=5, to=250, orient=HORIZONTAL, variable=self.norm_thresh,
                               length=105, command=self.update_thresh)
        thresh_scale.bind("<ButtonRelease-1>", lambda _: self.apply_transform_matrix())
        self.thresh_frame.pack(), thresh_scale.pack(padx=5, pady=2)
        self.canvas.create_window(self.canvas.winfo_reqwidth() - self.btn_dec.winfo_reqwidth() // 2,
                                  self.canvas.winfo_reqheight() - 230, anchor="se", window=self.thresh_frame, tags='threshold', state="hidden")
        self.clearbtn = Button(self.root, text='\u27F2', width=3, height=0, background='#2B2B2B', foreground='#AFB1B3', relief='raised',
                          activebackground='#AFB1B3', font='Courier 21', borderwidth=0, command=lambda: (self.curr_theme.set('None'), self.apply_color_matrix()))
        self.play_gif = Button(self.root, text='\u23F8', width=0, height=0, background='#2B2B2B', foreground='#AFB1B3', relief='raised',
                               activebackground='#AFB1B3', font='Courier 20', borderwidth=0, command=self.toggle_play_gif)
        self.frame_carousel = ttkScale(self.root, from_=1, to=10, length=3*self.canvas.winfo_reqwidth()//4, style=f'Carousel.Horizontal.TScale',
                                       orient="horizontal", variable=self.frame_pointer, command=lambda x: (self.jump_to_frame(int(float(x))), self.frame_pointer.set(int(float(x)))))
        self.canvas.create_window(self.play_gif.winfo_reqwidth()+50, self.canvas.winfo_reqheight()-70, anchor="nw", window=self.frame_carousel, tags='carousel', state="hidden")
        self.canvas.create_window(20, self.canvas.winfo_reqheight() - 2*self.play_gif.winfo_reqheight() - 55, anchor="nw", window=self.clearbtn, tags='clear', state="hidden")
        self.style.configure(f'Carousel.Horizontal.TScale', sliderlength=30, troughcolor='#313335', slidercolor='#87939A')
        for i in range(4):
            self.rbtns.append(Radiobutton(self.root, text=('R', 'G', 'B', 'All')[i], variable=self.channel_id, value=(1, 2, 3, 0)[i],
                               bg='#2B2B2B', width=2, padx=5, pady=0, indicatoron=False, fg=('#FFB6B6', '#B6FFB9', '#B6D5FF', '#C5C5C5')[i],
                               font=Font(family=families()[40], size=8, weight='bold'), selectcolor='#3C3F41',
                               activebackground=('#FFB6B6', '#B6FFB9', '#B6D5FF', '#C5C5C5')[i], command=self.channel_transform))
            self.rbtns[-1].grid(row=0, column=i)
            self.canvas.create_window(self.canvas.winfo_reqwidth()-self.rbtns[-1].winfo_reqwidth()*4+i*self.rbtns[-1].winfo_reqwidth(),
                                      self.canvas.winfo_reqheight()-28, anchor="se", window=self.rbtns[-1], tags='channel', state="hidden")
        for i in range(3):
            self.clrscales.append(ttkScale(self.root, from_=0, to=255, value=170, length=100, style=f'CustomScale{i}.Horizontal.TScale', command=lambda x, indx=i: self.update_color(indx, x),
                             variable=(self.intensity_red, self.intensity_green, self.intensity_blue)[i], orient="horizontal"))
            self.clrscales[-1].bind("<ButtonRelease-1>", lambda _: self.apply_color_matrix())
            self.style.configure(f'CustomScale{i}.Horizontal.TScale', sliderlength=24, sliderrelief='flat', troughcolor='black')
            self.canvas.create_window(self.canvas.winfo_reqwidth() - self.clrscales[-1].winfo_reqwidth()//4,
                                      self.canvas.winfo_reqheight()-(self.clrscales[-1].winfo_reqheight()+3)*i-60, anchor="se", window=self.clrscales[-1], tags='color_scale', state="hidden")
            if i == 2:
                self.preview = Label(self.root, width=4, height=3, bg='black')
                self.canvas.create_window(self.canvas.winfo_reqwidth() - 3/2 * self.clrscales[-1].winfo_reqwidth()+10,
                                          self.canvas.winfo_reqheight() - self.clrscales[-1].winfo_reqheight()*i-30,
                                          anchor="se", window=self.preview, tags='color_preview', state="hidden")
        self.style.configure("custom.Horizontal.TProgressbar", troughcolor='#221b33', background='#008f30', borderwidth=0)
        self.progress_bar = Progressbar(self.root, style="custom.Horizontal.TProgressbar", orient="horizontal", length=self.canvas.winfo_reqwidth() - 5, mode="determinate")
        self.canvas.create_window(self.canvas.winfo_reqwidth() - self.progress_bar.winfo_reqwidth() - 5,
                                  self.canvas.winfo_reqheight() - self.progress_bar.winfo_reqheight() - 5,
                                  anchor="nw", window=self.progress_bar, tags='progress', state="hidden")
        self.canvas.pack()
        self.root.mainloop()

    def on_close(self):
        for file in listdir(f'{self.dir_path}\\bin'):
            if file.startswith(('0', '1', '2', '3')):
                try:
                    delfile(f'{self.dir_path}\\bin\\{file}')
                except OSError:
                    print(f'Error: could not delete {file}')
        self.root.destroy()

    def init_canvas(self):
        self.canvas.create_text(self.canvas.winfo_reqwidth() // 2, self.canvas.winfo_reqheight() // 2 - 30,
                                text='\U0001F4C2',
                                font=Font(family=families()[40], size=100), fill='#AFB1B3',
                                tags=['placeholder_ico', 'placeholder'])
        self.canvas.create_text(self.canvas.winfo_reqwidth() // 2, self.canvas.winfo_reqheight() // 2 + 60,
                                text='Load an Image',
                                font=Font(family=families()[40], size=20), fill='#AFB1B3',
                                tags=['placeholder_txt', 'placeholder'])
        self.canvas.create_text(self.canvas.winfo_reqwidth() // 2, self.canvas.winfo_reqheight() // 2 + 100,
                                text='\t    or\nOpen Explorer (Right-Click)',
                                font=Font(family=families()[40], size=13), fill='#AFB1B3',
                                tags=['placeholder_alt', 'placeholder'])
        self.canvas.itemconfigure('placeholder_alt', state="hidden")
        self.canvas.tag_bind('placeholder', "<Enter>", self.init_hover_enter)
        self.canvas.tag_bind('placeholder', "<Leave>", self.init_hover_leave)
        self.canvas.tag_bind('placeholder', "<Button-1>", self.init_action)
        self.canvas.tag_bind('placeholder', "<Button-3>", lambda _: self.open_file())

    def init_hover_enter(self, _):
        try:
            clipboard = self.root.clipboard_get()
            if '"' in clipboard or "'" in clipboard:
                clipboard = clipboard.replace('"', '').replace("'", '')
            if path.exists(clipboard) and clipboard[-3:] in ['png', 'jpg', 'bmp', 'gif']:
                self.canvas.itemconfigure('placeholder_alt', fill='#838E95', state="normal")
                self.canvas.itemconfigure('placeholder_ico', fill='#838E95', text='\U0001F4CB')
                self.canvas.itemconfigure('placeholder_txt', fill='#838E95', text='Paste from Clipboard')
            else:
                self.canvas.itemconfigure('placeholder', fill='#838E95')
        except tkinter.TclError:
            self.canvas.itemconfigure('placeholder', fill='#838E95')

    def init_hover_leave(self, _):
        try:
            clipboard = self.root.clipboard_get()
            if '"' in clipboard or "'" in clipboard:
                clipboard = clipboard.replace('"', '').replace("'", '')
            if path.exists(clipboard) and clipboard[-3:] in ['png', 'jpg', 'bmp', 'gif']:
                self.canvas.itemconfigure('placeholder_alt', fill='#AFB1B3', state="hidden")
                self.canvas.itemconfigure('placeholder_ico', fill='#AFB1B3', text='\U0001F4C2')
                self.canvas.itemconfigure('placeholder_txt', fill='#AFB1B3', text='Load an Image')
            else:
                self.canvas.itemconfigure('placeholder', fill='#AFB1B3')
        except tkinter.TclError:
            self.canvas.itemconfigure('placeholder', fill='#AFB1B3')

    def init_action(self, _):
        try:
            clipboard = self.root.clipboard_get()
            self.root.clipboard_clear()
            if '"' in clipboard or "'" in clipboard:
                clipboard = clipboard.replace('"', '').replace("'", '')
            if path.exists(clipboard) and clipboard[-3:] in ['png', 'jpg', 'bmp', 'gif']:
                self.open_file(file=clipboard)
            else:
                self.open_file()
        except tkinter.TclError:
            self.open_file()

    def clear_screen(self):
        self.clear_buffers()
        self.init_canvas()
        for widget_tag in ['intensity', 'coefficient', 'threshold', 'carousel',
                           'play', 'clear', 'channel', 'color_preview', 'color_scale']:
            self.canvas.itemconfigure(widget_tag, state="hidden")

    def clear_buffers(self):
        self.GIF_CHUNKS.clear()
        self.color_counts.clear()
        self.orig_width, self.orig_height, self.im_width, self.im_height = 0, 0, 0, 0
        self.frame_id, self.newtkimg = [None] * 2
        self.process_order, self.wrap_cntr, self.PROCESS_DUR, self.GIF_DUR, self.FRAME_COUNT, self.FILE_SIZE = '', 0, 0, 0, 0, 0
        self.canvas.delete("mainimg")
        self.curr_filter.set('None')
        self.curr_theme.set('None')
        self.curr_overlay_filter.set('None')
        self.channel_id.set(0)
        self.frame_pointer.set(0)
        self.curr_intensity.set(1)
        self.coefficient.set(125)
        self.norm_thresh.set(100)
        self.intensity_red.set(85)
        self.intensity_green.set(85)
        self.intensity_blue.set(85)
        self.norm_method.set('Clip')
        self.dither_opt.set('Min-Max')
        if self.filter_timer2:
            self.root.after_cancel(self.filter_timer2)
            self.filter_timer2 = None
            self.canvas.delete('fltrimg')
        if self.filter_timer:
            self.toggle_play_gif()
            self.canvas.delete(self.frame_id)
        if self.summary_txt:
            self.canvas.delete('summary')
        if self.THREAD_REF:
            for thd in self.THREAD_REF:
                thd.join()
                self.THREAD_REF.remove(thd)
        for file in listdir(f'{self.dir_path}\\bin'):
            if file.startswith(('0', '1', '2', '3')):
                try:
                    delfile(f'{self.dir_path}\\bin\\{file}')
                except OSError:
                    print(f'Error: could not delete {file}')
        gccollect()

    def open_file(self, file=None):
        if not file:
            file = filedialog.askopenfilename(filetypes=[('', "*.jpg;*.jpeg;*.png;*.gif;*.bmp")])
        if file:
            self.f_path = file
            self.clear_buffers()
            self.canvas.delete('placeholder')
            self.temp_id = uuid4()
            if self.f_path[-3:] == 'gif':
                with Image.open(self.f_path) as gif:
                    self.CURR_FRAME, self.FRAME_COUNT = 0, gif.n_frames
                    self.GIF_DUR = gif.info['duration'] if 'duration' in gif.info.keys() else 20
                    scale_factor = min(self.scrx / gif.size[0], self.scry / gif.size[1])
                    self.orig_width, self.orig_height = gif.size[0], gif.size[1]
                    self.im_width, self.im_height = int(scale_factor * gif.size[0]), int(scale_factor * gif.size[1])
                    with open(f'{self.dir_path}\\bin\\0-{self.temp_id}.bin', 'wb') as gif_data:
                        for frame in ImageSequence.Iterator(gif):
                            pdump(frame.convert(mode='RGB'), gif_data)
                            self.GIF_CHUNKS.append(gif_data.tell())
                            self.update_color_counts(frame)
                    self.get_size()
                    gccollect()
                if not self.play_gif.winfo_ismapped():
                    self.canvas.create_window(20, self.canvas.winfo_reqheight() - self.play_gif.winfo_reqheight() - 50,
                                              anchor="nw", window=self.play_gif, tags='play')
                self.frame_carousel.configure(from_=1, to=self.FRAME_COUNT-1)
                self.canvas.itemconfigure('carousel', state="normal")
                if not self.filter_timer:
                    self.toggle_play_gif()
            elif self.f_path[-3:] in ['jpg', 'jpeg', 'png', 'bmp']:
                if self.play_gif.winfo_ismapped():
                    self.canvas.delete('play')
                    self.canvas.delete(self.frame_id)
                with Image.open(fp=self.f_path) as img:
                    scale_factor = min(self.scrx / img.size[0], self.scry / img.size[1])
                    self.orig_width, self.orig_height = img.size[0], img.size[1]
                    self.im_width, self.im_height = int(scale_factor * img.size[0]), int(scale_factor * img.size[1])
                    with open(f'{self.dir_path}\\bin\\0-{self.temp_id}.bin', 'wb') as img_data:
                        pdump(img.convert(mode='RGB'), img_data)
                        self.update_color_counts(img)
                with open(f'{self.dir_path}\\bin\\0-{self.temp_id}.bin', 'rb') as img:
                    self.newtkimg = ImageTk.PhotoImage(pload(img).resize((self.im_width, self.im_height)))
                    self.canvas.create_image(0, 0, image=self.newtkimg, anchor=NW, tags='mainimg')
                if self.summary_txt:
                    self.canvas.delete(self.summary_txt, self.summary_bg, 'summary')
                self.get_size()
                self.frame_summary(self.f_path[-3:])
                self.canvas.itemconfigure('carousel', state="hidden")
            self.canvas.itemconfigure('channel', state="normal")
            self.canvas.itemconfigure('intensity', state="normal")
            self.canvas.itemconfigure('coefficient', state="normal")
            self.canvas.itemconfigure('clear', state="normal")
            del file, scale_factor
            gccollect()
        else:
            del file

    def frame_summary(self, ftype):
        bg_width = 200 + (len(self.curr_filter.get()) * 5, len(self.curr_theme.get()) * 5)[len(self.curr_filter.get()) <
                                                                                           len(self.curr_theme.get())]
        bg_height, offset, x, y = 180 if ftype == 'gif' else 140, 10, self.canvas.winfo_reqwidth() - bg_width - 15, 10
        if len(self.process_order[self.wrap_cntr:]) > 22:
            self.process_order += '\n\t'
            self.wrap_cntr += 22
        if ftype in ['png', 'jpg', 'jpeg', 'bmp']:
            text = f"Size: {self.FILE_SIZE} MB\n" \
                   f"Dimensions: {self.orig_width} x {self.orig_height}\n" \
                   f"Processing time: {self.PROCESS_DUR} ms\nCurrent theme: {self.curr_theme.get()} ({self.curr_intensity.get()})\n" \
                   f"Current filter: {self.curr_filter.get()}\nColor Count: {self.color_counts[0] if self.color_counts[0] else '20000+'}\n" \
                   f"Applied: {self.process_order}"
        else:
            text = f"Size: {self.FILE_SIZE} MB\nDimensions: {self.im_width} x {self.im_height}\n" \
                   f"Frame Count: {self.FRAME_COUNT}\nFrame Delay: {self.GIF_DUR} ms\nCurrent Frame: {self.CURR_FRAME}\n" \
                   f"Processing time: {self.PROCESS_DUR} ms\nCurrent theme: {self.curr_theme.get()} ({self.curr_intensity.get()})\n" \
                   f"Current filter: {self.curr_filter.get()}\nColor Count: {self.color_counts[self.CURR_FRAME] if self.color_counts[self.CURR_FRAME] else '20000+'}\n" \
                   f"Applied: {self.process_order}"
        tkimg = ImageTk.PhotoImage(self.trans_bg.resize((bg_width, bg_height+int(self.wrap_cntr/1.5))))
        self.summary_bg = self.canvas.create_image(x, y, image=tkimg, anchor=NW, tags='summary')
        self.summary_txt = self.canvas.create_text(x+offset, y+offset, text=text, anchor=NW, fill="white",
                                                   font=Font(family=families()[40], size=10, weight='bold'), tags='summary')
        self.canvas.new_image = tkimg
        del tkimg
        gccollect()

    def save_file(self):
        if not self.f_path:
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".png",
            filetypes=([("PNG files", "*.png"), ("JPG files", "*.jpg")], [("GIF files", "*.gif")])[self.f_path[-3:] == 'gif'])
        if file_path:
            if self.f_path[-3:] == 'gif':
                def gen_gif():
                    with open(f'{self.dir_path}\\bin\\{(0, 1, 2, 3)[self.channel_id.get()]}-{self.temp_id}.bin', 'rb') as gif:
                        try:
                            while True:
                                yield pload(gif)
                        except EOFError:
                            pass
                with open(f'{self.dir_path}\\bin\\{(0, 1, 2, 3)[self.channel_id.get()]}-{self.temp_id}.bin', 'rb'):
                    frame1 = gen_gif()
                    next(frame1).save(file_path, save_all=True, append_images=list(gen_gif()), optimize=False,
                                duration=Image.open(self.f_path).info['duration'], disposal=0, loop=0)
                del frame1
            else:
                with open(f'{self.dir_path}\\bin\\{(0, 1, 2, 3)[self.channel_id.get()]}-{self.temp_id}.bin', 'rb') as img:
                    if file_path[-3:] != 'png':
                        pload(img).save(file_path, optimise=False)
                    else:
                        pload(img).save(file_path, save_all=True, optimise=False)
                del img
            text_id = self.canvas.create_text(self.canvas.winfo_reqwidth()-150, self.canvas.winfo_reqheight()-80,
                                              text='Saved.', fill='#AFB1B3', font=Font(family=families()[21], size=11, weight='bold'))
            tmp = self.root.after(3000, lambda: (self.canvas.delete(text_id), self.root.after_cancel(tmp)))
            gccollect()

    def get_size(self):
        self.FILE_SIZE = 0
        if self.f_path[-3:] == 'gif':
            with open(f'{self.dir_path}\\bin\\{(0, 1, 2, 3)[self.channel_id.get()]}-{self.temp_id}.bin', 'rb') as gif:
                for i in range(self.FRAME_COUNT):
                    bytestream = BytesIO()
                    pload(gif).save(bytestream, format='GIF')
                    gif.seek(self.GIF_CHUNKS[i])
                    self.FILE_SIZE += bytestream.getbuffer().nbytes / (1024 ** 2)
                    bytestream.close()
            self.FILE_SIZE = (self.FILE_SIZE*100//1)/100
            del bytestream, gif
        else:
            with open(f'{self.dir_path}\\bin\\{(0, 1, 2, 3)[self.channel_id.get()]}-{self.temp_id}.bin', 'rb') as img:
                bytestream = BytesIO()
                pload(img).save(bytestream, format='PNG')
                print('in get size')
                self.FILE_SIZE = (bytestream.getbuffer().nbytes / (1024 ** 2)*100//1)/100
                bytestream.close()
            del bytestream
        gccollect()

    def load_overlay_filter(self):
        if self.filter_timer2:
            self.root.after_cancel(self.filter_timer2)
            self.canvas.delete('fltrimg')
        self.filter_timer2 = None
        self.frames2[:], self.filtframes[:] = [], []
        print('thread pool empty' if not self.THREAD_REF else f'thread pool count - {len(self.THREAD_REF)}')
        if self.curr_overlay_filter.get() != 'None':
            for filter_frame in listdir(f'{self.dir_path}\\filter_frames\\{self.curr_overlay_filter.get()}'):
                tmp = Image.open(fp=f'{self.dir_path}\\filter_frames\\{self.curr_overlay_filter.get()}\\{filter_frame}')
                self.filtframes.append(tmp.resize((self.scrx, self.scry)))
                self.frames2.append(ImageTk.PhotoImage(self.filtframes[-1]))
                tmp = None
            del tmp
            gccollect()
            self.animate2(0)

    def update_color_counts(self, frame):
        try:
            self.color_counts.append(len(frame.getcolors(20000)))
        except TypeError:
            self.color_counts.append(None)

    def update_color(self, indx, x: str):
        x = int(float(x))
        if indx + 1 == 1:
            self.intensity_red.set(x)
            self.style.configure(f'CustomScale{indx}.Horizontal.TScale', troughcolor=f'#{x:02x}{0:02x}{0:02x}')
        elif indx + 1 == 2:
            self.intensity_green.set(x)
            self.style.configure(f'CustomScale{indx}.Horizontal.TScale', troughcolor=f'#{0:02x}{x:02x}{0:02x}')
        elif indx + 1 == 3:
            self.intensity_blue.set(x)
            self.style.configure(f'CustomScale{indx}.Horizontal.TScale', troughcolor=f'#{0:02x}{0:02x}{x:02x}')
        self.preview.configure(bg=f'#{self.intensity_red.get():02x}{self.intensity_green.get():02x}{self.intensity_blue.get():02x}')

    def update_thresh(self, val):
        self.thresh_frame.configure(text=f'Threshold:  {str(int(float(val)))}')

    def update_coefficient(self, val):
        self.coeff_frame.configure(text=f'\u03BB:  {str(int(float(val)))}')

    def intensity_increase(self, _):
        if self.curr_theme.get() != 'None':
            self.curr_intensity.set(self.curr_intensity.get()+1)
            self.intensity_frame.configure(text=f'Intensity: {self.curr_intensity.get()}')
            self.color_matrix_process()
            self.inc = self.root.after(300, self.intensity_increase, _)

    def intensity_decrease(self, _):
        if self.curr_theme.get() != 'None':
            self.curr_intensity.set(self.curr_intensity.get()-1)
            self.intensity_frame.configure(text=f'Intensity: {self.curr_intensity.get()}')
            self.color_matrix_process()
            self.dec = self.root.after(300, self.intensity_decrease, _)

    def animate2(self, n):
        pass
        # if n < len(self.frames2):
        #     self.canvas.delete('fltrimg')
        #     self.canvas.create_image(0, 0, image=self.frames2[n], anchor=NW, tags='fltrimg')
        #     self.canvas.create_image(self.frames2[n].width(), 0, image=self.frames2[n], anchor=NW, tags='fltrimg')
        #     self.canvas.create_image(self.frames2[n].width()*2, 0, image=self.frames2[n], anchor=NW, tags='fltrimg')
        #     self.canvas.create_image(0, self.frames2[n].height(), image=self.frames2[n], anchor=NW, tags='fltrimg')
        #     self.canvas.create_image(self.frames2[n].width(), self.frames2[n].height(), image=self.frames2[n], anchor=NW, tags='fltrimg')
        #     self.canvas.create_image(self.frames2[n].width()*2, self.frames2[n].height(), image=self.frames2[n], anchor=NW, tags='fltrimg')
        #     n = n + 1 if n != len(self.frames2) - 1 else 0
        #     self.filter_timer2 = self.root.after(2, self.animate2, n)

    def animate(self):
        with open(f'{self.dir_path}\\bin\\{(0, 1, 2, 3)[self.channel_id.get()]}-{self.temp_id}.bin', 'rb') as gif:
            try:
                self.canvas.delete(self.frame_id)
                gif.seek(self.GIF_CHUNKS[self.CURR_FRAME])
                self.CURR_FRAME = (self.CURR_FRAME + 1) % self.FRAME_COUNT
                self.frame_pointer.set(self.CURR_FRAME)
                self.newtkimg = ImageTk.PhotoImage(pload(gif).resize((self.im_width, self.im_height)))
                self.frame_id = self.canvas.create_image(0, 0, anchor=NW, image=self.newtkimg)
                if self.summary_txt:
                    self.canvas.delete(self.summary_txt, self.summary_bg, 'summary')
                self.frame_summary(self.f_path[-3:])
                self.filter_timer = self.root.after(self.GIF_DUR, self.animate)
            except EOFError:
                self.CURR_FRAME = 0
                self.filter_timer = self.root.after(0, self.animate)

    def jump_to_frame(self, x):
        if self.filter_timer:
            self.toggle_play_gif()
            self.canvas.delete(self.frame_id)
        with open(f'{self.dir_path}\\bin\\{(0, 1, 2, 3)[self.channel_id.get()]}-{self.temp_id}.bin', 'rb') as gif:
            self.CURR_FRAME = x
            gif.seek(self.GIF_CHUNKS[self.CURR_FRAME - 1])
            self.newtkimg = ImageTk.PhotoImage(pload(gif).resize((self.im_width, self.im_height)))
            if self.frame_id:
                self.canvas.delete(self.frame_id)
            if self.summary_txt:
                self.canvas.delete(self.summary_txt, self.summary_bg, 'summary')
            self.frame_id = self.canvas.create_image(0, 0, anchor=NW, image=self.newtkimg)
            self.frame_summary('gif')
            gccollect()

    def toggle_play_gif(self):
        self.playbtnstate = self.playbtnstate ^ 1
        self.play_gif.configure(text=('\u25B6', '\u23F8')[self.playbtnstate])
        if self.filter_timer:
            self.root.after_cancel(self.filter_timer)
            self.filter_timer = None
        else:
            self.animate()

    def toggle_scale(self):
        if self.norm_method.get() in ['Clip', 'Modulo', 'Absolute', 'Inverted']:
            self.canvas.itemconfigure('threshold', state="hidden")
        else:
            self.canvas.itemconfigure('threshold', state="normal")

    def apply_color_matrix(self):
        self.curr_intensity.set(0)
        self.color_matrix_process()

    def color_matrix_process(self):
        if not self.f_path:
            return
        if self.process_order[-(len(self.curr_theme.get())):] == self.curr_theme.get():
            self.process_order = self.process_order[:-len(self.curr_theme.get())-1]
        if self.f_path:
            if self.curr_theme.get() == 'Custom':
                self.canvas.itemconfigure('color_scale', state="normal"), self.canvas.itemconfigure('color_preview', state="normal")
            else:
                self.canvas.itemconfigure('color_scale', state="hidden"), self.canvas.itemconfigure('color_preview', state="hidden")
            r, g, b = self.intensity_red.get()*3/255, self.intensity_green.get()*3/255, self.intensity_blue.get()*3/255
            self.channel_id.set(0)
            self.color_counts.clear()
            if self.f_path[-3:] == 'gif':
                self.GIF_CHUNKS.clear()
                if self.filter_timer:
                    self.toggle_play_gif()
                if self.curr_theme.get() == 'None':
                    with open(f'{self.dir_path}\\bin\\0-{self.temp_id}.bin', 'wb') as gif_data:
                        for frame in ImageSequence.Iterator(Image.open(self.f_path)):
                            pdump(frame.convert(mode='RGB'), gif_data)
                            self.GIF_CHUNKS.append(gif_data.tell())
                            self.update_color_counts(frame)
                elif self.EFFECT_ACTIVE:
                    self.process_order = self.process_order + '\u2192' + (self.curr_theme.get(), f'RGB({r*255//3}, {g*255//3}, {b*255//3})')[self.curr_theme.get() == 'Custom']
                    with open(f'{self.dir_path}\\bin\\0-{self.temp_id}.bin', 'rb') as src:
                        with open(f'{self.dir_path}\\bin\\{self.temp_id}.bin', 'wb') as tgt:
                            try:
                                while True:
                                    frame = pload(src).convert(mode='RGB', matrix=color_matrix[self.curr_theme.get()]((self.curr_intensity.get(), (r, g, b))[self.curr_theme.get() == 'Custom']))
                                    pdump(frame, tgt)
                                    self.GIF_CHUNKS.append(tgt.tell())
                                    self.update_color_counts(frame)
                            except EOFError:
                                pass
                    delfile(f'{self.dir_path}\\bin\\0-{self.temp_id}.bin')
                    rename(f'{self.dir_path}\\bin\\{self.temp_id}.bin', f'{self.dir_path}\\bin\\0-{self.temp_id}.bin')
                elif not self.EFFECT_ACTIVE:
                    self.process_order = '' + (self.curr_theme.get(), f'RGB({r*255//3}, {g*255//3}, {b*255//3})')[self.curr_theme.get() == 'Custom']
                    with open(f'{self.dir_path}\\bin\\0-{self.temp_id}.bin', 'wb') as gif_data:
                        for frame in ImageSequence.Iterator(Image.open(self.f_path)):
                            frame = frame.convert('RGB')
                            frame = frame.convert(mode='RGB', matrix=color_matrix[self.curr_theme.get()]((self.curr_intensity.get(), (r, g, b))[self.curr_theme.get() == 'Custom']))
                            pdump(frame, gif_data)
                            self.GIF_CHUNKS.append(gif_data.tell())
                            self.update_color_counts(frame)
                self.toggle_play_gif()
            else:
                self.canvas.delete("mainimg")
                if self.curr_theme.get() == 'None':
                    t1 = perf_counter()
                    with open(f'{self.dir_path}\\bin\\0-{self.temp_id}.bin', 'wb') as img_data:
                        frame = Image.open(self.f_path).convert(mode='RGB')
                        pdump(frame, img_data)
                        self.update_color_counts(frame)
                elif self.EFFECT_ACTIVE:
                    self.process_order = self.process_order + '\u2192' + (self.curr_theme.get(), f'RGB({r*255//3}, {g*255//3}, {b*255//3})')[self.curr_theme.get() == 'Custom']
                    with open(f'{self.dir_path}\\bin\\0-{self.temp_id}.bin', 'rb') as src:
                        with open(f'{self.dir_path}\\bin\\{self.temp_id}.bin', 'wb') as tgt:
                            try:
                                frame = pload(src).convert(mode='RGB', matrix=color_matrix[self.curr_theme.get()]((self.curr_intensity.get(), (r, g, b))[self.curr_theme.get() == 'Custom']))
                                pdump(frame, tgt)
                                self.update_color_counts(frame)
                            except EOFError:
                                pass
                    delfile(f'{self.dir_path}\\bin\\0-{self.temp_id}.bin')
                    rename(f'{self.dir_path}\\bin\\{self.temp_id}.bin', f'{self.dir_path}\\bin\\0-{self.temp_id}.bin')
                elif not self.EFFECT_ACTIVE:
                    self.process_order = '' + (self.curr_theme.get(), f'RGB({r * 255 // 3}, {g * 255 // 3}, {b * 255 // 3})')[self.curr_theme.get() == 'Custom']
                    with open(f'{self.dir_path}\\bin\\0-{self.temp_id}.bin', 'wb') as img_data:
                        frame = Image.open(self.f_path).convert(mode='RGB', matrix=color_matrix[self.curr_theme.get()]((self.curr_intensity.get(), (r, g, b))[self.curr_theme.get() == 'Custom']))
                        pdump(frame, img_data)
                        self.update_color_counts(frame)
                with open(f'{self.dir_path}\\bin\\0-{self.temp_id}.bin', 'rb') as img:
                    self.newtkimg = ImageTk.PhotoImage(pload(img).resize((self.im_width, self.im_height)))
                    self.canvas.create_image(0, 0, image=self.newtkimg, anchor=NW, tags='mainimg')
            self.get_size()
            del r, g, b
            gccollect()
            if self.curr_theme.get() == 'None':
                self.EFFECT_ACTIVE = False
                self.curr_filter.set('None')
                self.intensity_frame.configure(text='Intensity: 0')
                self.process_order, self.wrap_cntr, self.PROCESS_DUR = '', 0, 0
            if self.summary_txt:
                self.canvas.delete(self.summary_bg, self.summary_txt, 'summary')
            self.frame_summary(self.f_path[-3:])

    def channel_transform(self):
        if self.summary_txt:
            self.canvas.delete(self.summary_txt, self.summary_bg, 'summary')
        self.color_counts.clear()
        if self.f_path[-3:] in ['png', 'jpg', 'jpeg', 'bmp']:
            self.canvas.delete("mainimg")
            if self.channel_id.get() != 0:
                with open(f'{self.dir_path}\\bin\\0-{self.temp_id}.bin', 'rb') as img:
                    with open(f'{self.dir_path}\\bin\\{(1, 2, 3)[self.channel_id.get()-1]}-{self.temp_id}.bin', 'wb') as channel:
                        imgarr = array(pload(img)).astype(int)[:, :, self.channel_id.get() - 1]
                        ret = stack([imgarr, imgarr, imgarr], axis=2)
                        frame = Image.fromarray(uint8(ret))
                        pdump(frame, channel)
                        self.update_color_counts(frame)
                    del frame, imgarr, ret
            else:
                with open(f'{self.dir_path}\\bin\\0-{self.temp_id}.bin', 'rb') as gif:
                    frame = pload(gif)
                    self.update_color_counts(frame)
                del frame
            gccollect()
            with open(f'{self.dir_path}\\bin\\{(0, 1, 2, 3)[self.channel_id.get()]}-{self.temp_id}.bin', 'rb') as img:
                self.newtkimg = ImageTk.PhotoImage(pload(img).resize((self.im_width, self.im_height)))
                self.canvas.create_image(0, 0, image=self.newtkimg, anchor=NW, tags='mainimg')
            self.get_size()
            self.frame_summary(self.f_path[-3:])
        if self.f_path[-3:] == 'gif':
            if self.filter_timer:
                self.toggle_play_gif()
                self.canvas.delete(self.frame_id)
            self.GIF_CHUNKS.clear()
            if self.channel_id.get() != 0:
                with open(f'{self.dir_path}\\bin\\0-{self.temp_id}.bin', 'rb') as gif:
                    with open(f'{self.dir_path}\\bin\\{(1, 2, 3)[self.channel_id.get()-1]}-{self.temp_id}.bin', 'wb') as channel:
                        try:
                            while True:
                                frame = pload(gif)
                                imgarr = array(frame).astype(int)[:, :, self.channel_id.get()-1]
                                ret = stack([imgarr, imgarr, imgarr], axis=2)
                                frame = Image.fromarray(uint8(ret))
                                pdump(frame, channel)
                                self.GIF_CHUNKS.append(channel.tell())
                                self.update_color_counts(frame)
                        except EOFError:
                            del frame, imgarr, ret
            else:
                with open(f'{self.dir_path}\\bin\\0-{self.temp_id}.bin', 'rb') as gif:
                    try:
                        while True:
                            frame = pload(gif)
                            self.GIF_CHUNKS.append(gif.tell())
                            self.update_color_counts(frame)
                    except EOFError:
                        del frame
            gccollect()
            self.toggle_play_gif()
            self.get_size()

    def transform_matrix_process(self):
        self.EFFECT_ACTIVE = True
        strt = perf_counter()
        kernel = array(filter_matrix[self.curr_filter.get()]['kernel'])
        op_type = filter_matrix[self.curr_filter.get()]['type']
        pad_len = len(kernel) // 2
        threads = []

        def run_op(frame):
            threads[:] = []
            ops = ['convolution', 'ordered dither', 'error diffusion']
            imgarr = array(frame.convert(mode='RGB')).astype(int)
            imgchannels = [imgarr[:, :, 0], imgarr[:, :, 1], imgarr[:, :, 2]]
            process_channels = [Array('i', imgchannels[0].shape[0] * imgchannels[0].shape[1]) for _ in range(3)]
            for i in range(3):
                thd = Thread(target=(convolve, ordered_dither, error_diffuse)[ops.index(op_type)],
                             args=((imgchannels[i], kernel, process_channels[i], pad_len),
                                   (imgchannels[i], kernel, process_channels[i], self.coefficient.get(),
                                    self.dither_opt.get()),
                                   (imgchannels[i], kernel, process_channels[i], self.coefficient.get(),
                                    self.dither_opt.get()))[ops.index(op_type)])
                threads.append(thd)
                thd.start()
            for thd in threads:
                thd.join()
            process_channels[:] = [frombuffer(channel.get_obj(), dtype=int).reshape(imgchannels[0].shape)
                                   for channel in process_channels]
            ret = stack(process_channels, axis=2)
            if self.norm_method.get() == 'Clip':
                norm_ret = clip(ret, 0, 255)
            elif self.norm_method.get() == 'Modulo':
                norm_ret = ret % 255
            elif self.norm_method.get() == 'Absolute':
                norm_ret = abs(ret)
            elif self.norm_method.get() == 'Inverted':
                norm_ret = 255 - abs(ret)
            elif self.norm_method.get() == 'Threshold':
                norm_ret = ret.copy()
                norm_ret[ret <= self.norm_thresh.get()], norm_ret[ret > self.norm_thresh.get()] = 0, 255
            elif self.norm_method.get() == 'Threshold (Inverted)':
                norm_ret = ret.copy()
                norm_ret[ret <= self.norm_thresh.get()], norm_ret[ret > self.norm_thresh.get()] = 255, 0
            self.progress_bar.step(1)
            gccollect()
            return Image.fromarray(uint8(norm_ret))

        def gen_gif():
            with open(f'{self.dir_path}\\bin\\0-{self.temp_id}.bin', 'rb') as data:
                try:
                    while True:
                        yield run_op(pload(data))
                except EOFError:
                    pass
        self.GIF_CHUNKS.clear()
        self.color_counts.clear()
        with open(f'{self.dir_path}\\bin\\{self.temp_id}.bin', 'wb') as f:
            gen = gen_gif()
            while True:
                try:
                    frame = next(gen)
                    pdump(frame, f)
                    self.GIF_CHUNKS.append(f.tell())
                    self.update_color_counts(frame)
                except StopIteration:
                    break
        with open(f'{self.dir_path}\\bin\\{self.temp_id}.bin', 'rb') as src:
            with open(f'{self.dir_path}\\bin\\0-{self.temp_id}.bin', 'wb') as tgt:
                while True:
                    chunk = src.read(4096)
                    if not chunk:
                        break
                    tgt.write(chunk)
        delfile(f'{self.dir_path}\\bin\\{self.temp_id}.bin')
        stp = perf_counter()
        self.progress_bar.stop()
        self.channel_id.set(0)
        self.PROCESS_DUR = round((stp - strt) * 1000, 2)
        del op_type, pad_len, kernel, strt, stp, frame, src, tgt, f
        if self.process_order:
            self.process_order = self.process_order + '\u2192' + self.curr_filter.get()
        else:
            self.process_order += self.curr_filter.get()
        if self.f_path[-3:] == 'gif':
            self.toggle_play_gif()
            self.get_size()
        else:
            self.get_size()
            with open(f'{self.dir_path}\\bin\\0-{self.temp_id}.bin', 'rb') as img:
                self.newtkimg = ImageTk.PhotoImage(pload(img).resize((self.im_width, self.im_height)))
                self.canvas.create_image(0, 0, image=self.newtkimg, anchor=NW, tags='mainimg')
            self.frame_summary(self.f_path[-3:])
        self.canvas.itemconfigure('progress', state="hidden")
        for menu in range(len(self.menubar.winfo_children())):
            self.menubar.entryconfigure(menu+1, state="normal")
        for btn in [self.btn_inc, self.btn_dec, self.play_gif, *self.rbtns]:
            btn.config(state="normal")
        if len(self.THREAD_REF) > 1:
            self.THREAD_REF[0].join()
            del self.THREAD_REF[0]
            gccollect()
        gccollect()

    def apply_transform_matrix(self):
        print(f'\n{int(process.memory_info().rss / 1024 ** 2)} MB used')
        if not self.f_path or self.curr_filter.get() == 'None':
            return
        for menu in range(len(self.menubar.winfo_children())):
            self.menubar.entryconfigure(menu+1, state="disabled")
        for btn in [self.btn_inc, self.btn_dec, self.play_gif, *self.rbtns]:
            btn.config(state="disabled")
        if self.f_path:
            self.canvas.delete(self.summary_txt, self.summary_bg, 'summary')
            if self.f_path[-3:] == 'gif':
                if self.filter_timer:
                    self.toggle_play_gif()
                    self.canvas.delete(self.frame_id)
            else:
                self.canvas.delete("mainimg")
            self.PROCESS_DUR = 0
            self.progress_bar.configure(maximum=self.FRAME_COUNT)
            th1 = Thread(target=self.transform_matrix_process)
            self.canvas.itemconfigure('progress', state="normal")
            self.THREAD_REF.append(th1)
            th1.start()

if __name__ == '__main__':
    process = Process()
    app = Editor()
    app.setup()
