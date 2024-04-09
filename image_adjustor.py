"""
image/gif filtering viewer tool
p.s. needs kernel_ops.py and filters.py as a dependency
"""
import gc
from os import listdir, path
from threading import Thread
from multiprocessing import Array
from time import perf_counter
from io import BytesIO
from psutil import Process
from gc import collect as gccollect
from tkinter import Tk, Canvas, Button, Radiobutton,Menu, Label, \
    LabelFrame, StringVar, IntVar, NW, HORIZONTAL, filedialog
from tkinter.ttk import Progressbar, Button as ttkButton, Scale as ttkScale
from tkinter.font import Font, families
from ttkthemes import ThemedStyle

from PIL import Image, ImageTk, ImageSequence
from numpy import array, clip, uint8, frombuffer, stack

import kernel_ops
from filters import filter_matrix, color_matrix

class Editor:
    def __init__(self):
        self.EFFECT_ACTIVE = False
        self.THREAD_REF = []
        self.FRAME_COUNT, self.GIF_DUR, self.CURR_FRAME, self.FILE_SIZE, self.PROCESS_DUR = 0, 30, 0, 0, 0
        self.im_width, self.im_height, self.scrx, self.scry = 0, 0, 1200, 720
        self.filter_timer, self.filter_timer2, self.frame_id = [None] * 3
        self.pilframes, self.filtframes, self.cachedframes, self.saveframes, self.frames2, self.rbtns, self.clrscales = None, [], [], [], [], [], []
        self.dir_path, self.f_path = f'{path.dirname(path.realpath(__file__))}', None
        self.curr_filter, self.curr_theme, self.curr_overlay_filter, self.dither_opt = [None] * 4
        self.curr_intensity, self.norm_thresh, self.coefficient, self.channel_id, self.norm_method, self.intensity_red, self.intensity_green, self.intensity_blue = [None] * 8
        self.orig_img, self.scaled_img, self.red_img, self.blue_img, self.green_img, self.newtkimg, self.filttkimg = [None] * 7
        self.root, self.canvas, self.style, self.menubar, self.play_gif, self.progress_bar, self.preview = [None] * 7
        self.btn_inc, self.btn_dec, self.intensity_frame, self.coeff_frame, self.thresh_frame = [None] * 5
        self.trans_bg = Image.open(f'{self.dir_path}\\filter_frames\\blacksquare3.png')
        self.playbtnstate, self.inc, self.dec, self.playbtnid, self.summary_bg, self.summary_txt, self.process_order, self.wrap_cntr, self.orig_file_size = 0, None, None, None, None, None, '', 0, 0

    def setup(self):
        self.root = Tk()
        self.root.title("ImAdjustor")
        # self.style = Style()
        # self.style.theme_use('default')
        self.style = ThemedStyle(theme="black")
        self.root.geometry('%dx%d+%d+%d' % (self.scrx, self.scry, (self.root.winfo_screenmmwidth()-self.root.winfo_reqwidth()),
                                            (self.root.winfo_screenmmheight()-self.root.winfo_reqheight())))
        self.canvas = Canvas(self.root, width=self.scrx, height=self.scry, background='#2B2B2B')
        self.curr_filter, self.curr_theme, self.curr_overlay_filter = StringVar(self.root, 'none'), StringVar(self.root, 'none'), StringVar(self.root, 'none')
        self.norm_method, self.dither_opt = StringVar(self.root, 'clip'), StringVar(self.root, 'min_max')
        self.curr_intensity, self.norm_thresh, self.coefficient = IntVar(self.root, 1), IntVar(self.root, 100), IntVar(self.root, 125)
        self.channel_id, self.intensity_red, self.intensity_green, self.intensity_blue = IntVar(self.root, 0), IntVar(self.root, 85), IntVar(self.root, 85), IntVar(self.root, 85)
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
        self.intensity_frame = LabelFrame(self.root, text=f'Intensity: {self.curr_intensity.get()}', font=Font(family=families()[40], size=10),
                                     background="gray30", foreground='white')
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
                                  background="gray30", foreground='white')
        coeff_scale = ttkScale(self.coeff_frame, from_=5, to=250, orient=HORIZONTAL, variable=self.coefficient,
                               length=105, command=self.update_coefficient)
        self.coeff_frame.pack(), coeff_scale.pack(padx=5, pady=2)
        self.canvas.create_window(self.canvas.winfo_reqwidth() - self.btn_dec.winfo_reqwidth()//2,
                                  self.canvas.winfo_reqheight() - 185, anchor="se", window=self.coeff_frame, tags='coefficient', state="hidden")
        self.thresh_frame = LabelFrame(self.root, text=f'Threshold: {self.norm_thresh.get()}',
                                  font=Font(family=families()[40], size=10),
                                  background="gray30", foreground='white')
        thresh_scale = ttkScale(self.thresh_frame, from_=5, to=250, orient=HORIZONTAL, variable=self.norm_thresh,
                               length=105, command=self.update_thresh)
        thresh_scale.bind("<ButtonRelease-1>", lambda _: self.apply_transform_matrix())
        self.thresh_frame.pack(), thresh_scale.pack(padx=5, pady=2)
        self.canvas.create_window(self.canvas.winfo_reqwidth() - self.btn_dec.winfo_reqwidth() // 2,
                                  self.canvas.winfo_reqheight() - 230, anchor="se", window=self.thresh_frame, tags='threshold', state="hidden")
        self.play_gif = Button(self.root, text='\u23F8', width=0, height=0, background='#2B2B2B', foreground='gray45', relief='raised',
                               activebackground='gray30', font='Helvetica 25', borderwidth=1, command=self.toggle_play_gif)
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
        gccollect()

    def open_file(self):
        ret = filedialog.askopenfilename(filetypes=[('', "*.jpg;*.jpeg;*.png;*.gif;*.bmp")])
        if ret:
            self.f_path = ret
            self.clear_buffers()
            if self.f_path[-3:] == 'gif':
                with Image.open(self.f_path) as gif:
                    self.FRAME_COUNT, self.CURR_FRAME = gif.n_frames, 0
                    self.GIF_DUR = gif.info['duration'] if 'duration' in gif.info.keys() else 30
                    scale_factor = min(self.scrx / gif.size[0], self.scry / gif.size[1])
                    self.im_width, self.im_height = int(scale_factor * gif.size[0]), int(scale_factor * gif.size[1])
                    self.pilframes = ImageSequence.Iterator(Image.open(self.f_path))
                    for frame in self.pilframes:
                        tmpfrm = frame.convert(mode='RGB')
                        self.saveframes.append(tmpfrm)
                    del tmpfrm
                    gccollect()
                if not self.play_gif.winfo_ismapped():
                    self.playbtnid = self.canvas.create_window(self.canvas.winfo_reqwidth()//2,
                                                           self.canvas.winfo_reqheight() - self.play_gif.winfo_reqheight() - 50,
                                                           anchor="nw", window=self.play_gif)

                self.animate(0)
                self.canvas.pack()
            elif self.f_path[-3:] in ['jpg', 'jpeg', 'png', 'bmp']:
                if self.play_gif.winfo_ismapped():
                    self.canvas.delete(self.playbtnid)
                    self.canvas.delete(self.frame_id)
                self.orig_img = Image.open(fp=self.f_path)
                scale_factor = min(self.scrx / self.orig_img.size[0], self.scry / self.orig_img.size[1])
                self.im_width, self.im_height = int(scale_factor * self.orig_img.size[0]), int(scale_factor * self.orig_img.size[1])
                self.scaled_img = self.orig_img.convert(mode='RGB')
                self.scaled_img = self.scaled_img.resize((self.im_width, self.im_height))
                tkimg = ImageTk.PhotoImage(self.scaled_img)
                self.cachedframes.append(tkimg)
                self.canvas.create_image(0, 0, image=tkimg, anchor=NW, tags='mainimg')
                if self.summary_txt:
                    self.canvas.delete('summary')
                self.frame_summary(self.f_path[-3:])
            self.canvas.itemconfigure('channel', state="normal")
            self.canvas.itemconfigure('intensity', state="normal")
            self.canvas.itemconfigure('coefficient', state="normal")
            self.get_size()
            self.orig_file_size = self.FILE_SIZE
            del ret, scale_factor
            gccollect()
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
            clr_count = 256 if not self.saveframes[self.CURR_FRAME].getcolors() else \
                len((self.saveframes, self.red_img, self.green_img, self.blue_img)[self.channel_id.get()][self.CURR_FRAME].getcolors())
            text = f"Size: {self.FILE_SIZE} MB\nDimensions: {self.saveframes[0].width} x {self.saveframes[0].height}\n" \
                   f"Frame Count: {self.FRAME_COUNT}\nFrame Delay: {self.GIF_DUR} ms\nCurrent Frame: {self.CURR_FRAME+1}\n" \
                   f"Processing time: {self.PROCESS_DUR} ms\nCurrent theme: {self.curr_theme.get()} ({self.curr_intensity.get()})\n" \
                   f"Current filter: {self.curr_filter.get()}\nColor Count: {clr_count}\nApplied: {self.process_order}"
        tkimg = ImageTk.PhotoImage(self.trans_bg.resize((bg_width, bg_height+int(self.wrap_cntr/1.5))))
        self.summary_bg = self.canvas.create_image(x, y, image=tkimg, anchor=NW, tags='summary')
        self.summary_txt = self.canvas.create_text(x+offset, y+offset, text=text, anchor=NW, fill="white", font=Font(family=families()[40], size=10, weight='bold'), tags='summary')
        self.canvas.new_image = tkimg
        del tkimg
        gccollect()

    def save_file(self):
        if not self.f_path:
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".png",
            filetypes=([("GIF files", "*.gif")], [("PNG files", "*.png"), ("JPG files", "*.jpg")])[not self.saveframes])
        if file_path:
            if self.saveframes:
                curr_channel = ("saveframes", "red_img", "green_img", "blue_img")[self.channel_id.get()]
                getattr(self, f'{curr_channel}')[0].save(file_path, save_all=True, append_images=getattr(self, f'{curr_channel}')[1:],
                          optimize=False, duration=Image.open(self.f_path).info['duration'], disposal=0, loop=0)
            else:
                curr_channel = ("scaled_img", "red_img", "green_img", "blue_img")[self.channel_id.get()]
                setattr(self, f'{curr_channel}', getattr(self, f'{curr_channel}').resize(self.orig_img.size))
                if file_path[-3:] != 'png':
                    getattr(self, f'{curr_channel}').save(file_path, optimise=False)
                else:
                    getattr(self, f'{curr_channel}').save(file_path, save_all=True, optimise=False)
            del curr_channel, file_path
            text_id = self.canvas.create_text(self.canvas.winfo_reqwidth()-150, self.canvas.winfo_reqheight()-80,
                                              text='Saved.', fill='#AFB1B3', font=Font(family=families()[21], size=11, weight='bold'))
            tmp = self.root.after(3000, lambda: (self.canvas.delete(text_id), self.root.after_cancel(tmp)))
            gccollect()

    def get_size(self):
        self.FILE_SIZE = 0
        if self.f_path[-3:] == 'gif':
            for ffrm in (self.saveframes, self.red_img, self.green_img, self.blue_img)[self.channel_id.get()]:
                bytestream = BytesIO()
                ffrm.save(bytestream, format="PNG")
                self.FILE_SIZE += bytestream.getbuffer().nbytes / 1024 ** 2
            self.FILE_SIZE = round(self.FILE_SIZE, 1)
            del bytestream, ffrm
        else:
            bytestream = BytesIO()
            getattr(self, f'{("scaled", "red", "green", "blue")[self.channel_id.get()]}_img').save(bytestream, format="PNG")
            self.FILE_SIZE = round(bytestream.getbuffer().nbytes / 1024 ** 2, 1)
            del bytestream
        gccollect()

    def load_overlay_filter(self):
        if self.filter_timer2:
            self.root.after_cancel(self.filter_timer2)
            self.canvas.delete('fltrimg')
        self.filter_timer2 = None
        self.frames2[:], self.filtframes[:] = [], []
        print('thread pool empty' if not self.THREAD_REF else f'thread pool count - {len(self.THREAD_REF)}')
        if self.curr_overlay_filter.get() != 'none':
            for filter_frame in listdir(f'{self.dir_path}\\filter_frames\\{self.curr_overlay_filter.get()}'):
                tmp = Image.open(fp=f'{self.dir_path}\\filter_frames\\{self.curr_overlay_filter.get()}\\{filter_frame}')
                self.filtframes.append(tmp.resize((self.scrx, self.scry)))
                self.frames2.append(ImageTk.PhotoImage(self.filtframes[-1]))
                tmp = None
            del tmp
            gccollect()
            self.animate2(0)

    def channel_transform(self):
        if self.summary_txt:
            self.canvas.delete(self.summary_txt, self.summary_bg, 'summary')
        if self.channel_id.get() != 0:
            curr_channel = ("red", "green", "blue")[self.channel_id.get() - 1]
            for channel in ("red", "green", "blue"):
                if channel == curr_channel:
                    continue
                setattr(self, f'{channel}_img', None)
        if self.f_path[-3:] in ['png', 'jpg', 'jpeg', 'bmp']:
            self.canvas.delete("mainimg")
            if self.channel_id.get() != 0:
                setattr(self, f'{curr_channel}_img', None)
                imgarr = array(self.scaled_img).astype(int)[:, :, self.channel_id.get() - 1]
                ret = stack([imgarr, imgarr, imgarr], axis=2)
                setattr(self, f'{curr_channel}_img', Image.fromarray(uint8(ret)))
                del channel, curr_channel, imgarr, ret
                gc.collect()
            self.get_size()
            self.newtkimg = ImageTk.PhotoImage((self.scaled_img, self.red_img, self.green_img, self.blue_img)[self.channel_id.get()])
            self.canvas.create_image(0, 0, image=self.newtkimg, anchor=NW, tags='mainimg')
            self.frame_summary(self.f_path[-3:])
        elif self.f_path[-3:] == 'gif':
            if self.filter_timer:
                self.root.after_cancel(self.filter_timer)
                self.filter_timer = None
                self.canvas.delete(self.frame_id)
            if self.channel_id.get() != 0:
                setattr(self, f'{curr_channel}_img', [])
                for frame in self.saveframes:
                    imgarr = array(frame).astype(int)[:, :, self.channel_id.get()-1]
                    ret = stack([imgarr, imgarr, imgarr], axis=2)
                    getattr(self, f'{curr_channel}_img').append(Image.fromarray(uint8(ret)))
                del channel, curr_channel, imgarr, frame, ret
                gc.collect()
            self.get_size()
            self.animate(self.CURR_FRAME, ch=self.channel_id.get())

    def update_color(self, indx, x:str):
        x = int(float(x))
        match indx + 1:
            case 1:
                self.intensity_red.set(x)
                self.style.configure(f'CustomScale{indx}.Horizontal.TScale', troughcolor=f'#{x:02x}{0:02x}{0:02x}')
            case 2:
                self.intensity_green.set(x)
                self.style.configure(f'CustomScale{indx}.Horizontal.TScale', troughcolor=f'#{0:02x}{x:02x}{0:02x}')
            case 3:
                self.intensity_blue.set(x)
                self.style.configure(f'CustomScale{indx}.Horizontal.TScale', troughcolor=f'#{0:02x}{0:02x}{x:02x}')
        self.preview.configure(bg=f'#{self.intensity_red.get():02x}{self.intensity_green.get():02x}{self.intensity_blue.get():02x}')

    def update_thresh(self, val):
        self.thresh_frame.configure(text=f'Threshold:  {str(int(float(val)))}')

    def update_coefficient(self, val):
        self.coeff_frame.configure(text=f'\u03BB:  {str(int(float(val)))}')

    def intensity_increase(self, _):
        if self.curr_theme.get() != 'none':
            self.curr_intensity.set(self.curr_intensity.get()+1)
            self.intensity_frame.configure(text=f'Intensity: {self.curr_intensity.get()}')
            self.color_matrix_process()
            self.inc = self.root.after(300, self.intensity_increase, _)

    def intensity_decrease(self, _):
        # objgraph.show_most_common_types()
        # dict_objects = [obj for obj in gc.get_objects() if isinstance(obj, type) and obj.__name__ == 'dict']
        # print(dict_objects)
        # print(objgraph.growth())
        # print()
        if self.curr_theme.get() != 'none':
            self.curr_intensity.set(self.curr_intensity.get()-1)
            self.intensity_frame.configure(text=f'Intensity: {self.curr_intensity.get()}')
            self.color_matrix_process()
            self.dec = self.root.after(300, self.intensity_decrease, _)

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

    def animate(self, n, ch=0):
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
            self.filter_timer = self.root.after(self.GIF_DUR, self.animate, self.CURR_FRAME, ch)
        except StopIteration:
            self.pilframes, self.newtkimg = None, None
            if not self.saveframes:
                self.pilframes = ImageSequence.Iterator(Image.open(self.f_path))
            else:
                self.pilframes = iter((self.saveframes, self.red_img, self.green_img, self.blue_img)[self.channel_id.get()])
            self.root.after(1, self.animate, self.CURR_FRAME, self.channel_id.get())

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
            if self.curr_theme.get() == 'custom':
                self.canvas.itemconfigure('color_scale', state="normal")
                self.canvas.itemconfigure('color_preview', state="normal")
            else:
                self.canvas.itemconfigure('color_scale', state="hidden")
                self.canvas.itemconfigure('color_preview', state="hidden")
            r, g, b = self.intensity_red.get()*3/255, self.intensity_green.get()*3/255, self.intensity_blue.get()*3/255
            self.channel_id.set(0)
            if self.f_path[-3:] == 'gif':
                if self.curr_theme.get() == 'none':
                    self.saveframes[:] = [frm.convert(mode='RGB') for frm in ImageSequence.Iterator(Image.open(self.f_path))]
                elif self.EFFECT_ACTIVE:
                    self.process_order = self.process_order + '\u2192' + (self.curr_theme.get(), f'RGB({r*255//3}, {g*255//3}, {b*255//3})')[self.curr_theme.get() == 'custom']
                    self.saveframes[:] = [frm.convert(mode='RGB', matrix=color_matrix[self.curr_theme.get()]((self.curr_intensity.get(), (r, g, b))[self.curr_theme.get() == 'custom'])) for frm in self.saveframes]
                elif not self.EFFECT_ACTIVE:
                    self.process_order = '' + (self.curr_theme.get(), f'RGB({r*255//3}, {g*255//3}, {b*255//3})')[self.curr_theme.get() == 'custom']
                    tmpfrms = [frm.convert(mode='RGB') for frm in ImageSequence.Iterator(Image.open(self.f_path))]
                    self.saveframes[:] = [frm.convert(mode='RGB', matrix=color_matrix[self.curr_theme.get()]((self.curr_intensity.get(), (r, g, b))[self.curr_theme.get() == 'custom'])) for frm in tmpfrms]
                    del tmpfrms
            else:
                self.canvas.delete("mainimg")
                if self.curr_theme.get() == 'none':
                    self.scaled_img = self.orig_img.convert('RGB')
                    self.scaled_img = self.orig_img.resize((self.im_width, self.im_height))
                elif self.EFFECT_ACTIVE:
                    self.process_order = self.process_order + '\u2192' + (self.curr_theme.get(), f'RGB({r*255//3}, {g*255//3}, {b*255//3})')[self.curr_theme.get() == 'custom']
                    self.scaled_img = self.scaled_img.convert(mode='RGB', matrix=color_matrix[self.curr_theme.get()]((self.curr_intensity.get(), (r, g, b))[self.curr_theme.get() == 'custom']))
                elif not self.EFFECT_ACTIVE:
                    self.process_order = '' + self.curr_theme.get()
                    self.scaled_img = self.orig_img.convert('RGB')
                    self.scaled_img = self.scaled_img.resize((self.im_width, self.im_height)).convert(mode='RGB',
                                                                matrix=color_matrix[self.curr_theme.get()]((self.curr_intensity.get(), (r, g, b))[self.curr_theme.get() == 'custom']))
                self.newtkimg = ImageTk.PhotoImage(self.scaled_img)
                self.canvas.create_image(0, 0, image=self.newtkimg, anchor=NW, tags='mainimg')
            del r, g, b
            gccollect()
            if self.curr_theme.get() == 'none':
                self.EFFECT_ACTIVE = False
                self.curr_filter.set('none')
                self.intensity_frame.configure(text='Intensity: 0')
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
            ret = stack(process_channels, axis=2)
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
                self.newtkimg = ImageTk.PhotoImage(self.scaled_img)
                self.canvas.create_image(0, 0, image=self.newtkimg, anchor=NW, tags='mainimg')
        stp = perf_counter()
        self.progress_bar.stop()
        self.channel_id.set(0)
        if self.f_path[-3:] == 'gif':
            self.animate(self.CURR_FRAME)
        self.PROCESS_DUR = round((stp - strt) * 1000, 2)
        del imgarr, imgchannels, process_channels, ret, ops, op_type, pad_len, kernel, strt, stp
        if self.process_order:
            self.process_order = self.process_order + '\u2192' + self.curr_filter.get()
        else:
            self.process_order += self.curr_filter.get()
        self.get_size()
        self.canvas.itemconfigure('progress', state="hidden")
        self.frame_summary(self.f_path[-3:])
        for menu in range(len(self.menubar.winfo_children())):
            self.menubar.entryconfigure(menu, state="normal")
        for btn in [self.btn_inc, self.btn_dec, self.play_gif, *self.rbtns]:
            btn.config(state="normal")
        if len(self.THREAD_REF) > 1:
            self.THREAD_REF[0].join()
            del self.THREAD_REF[0]
            gccollect()
        gccollect()

    def apply_transform_matrix(self):
        print(f'\n{int(process.memory_info().rss / 1024 ** 2)} MB used')
        if not self.f_path or self.curr_filter.get() == 'none':
            return
        for menu in range(len(self.menubar.winfo_children())):
            self.menubar.entryconfigure(menu, state="disabled")
        for btn in [self.btn_inc, self.btn_dec, self.play_gif, *self.rbtns]:
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
                gccollect()
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
