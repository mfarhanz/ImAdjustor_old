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
from tkinter.font import Font, families
from io import BytesIO

from PIL import Image, ImageTk, ImageSequence
from numpy import array, clip, uint8

import kernel_ops
from filters import filter_matrix, color_matrix

class Editor:
    def __init__(self):
        self.LAST_TRANSFORM = None
        self.EFFECT_ACTIVE = False
        self.THREAD_REF = []
        self.FRAME_COUNT, self.GIF_DUR, self.CURR_FRAME, self.FILE_SIZE, self.PROCESS_DUR, self.CURR_OVERLAY_FILTER = 0, 30, 0, 0, 0, 0
        self.theta, self.im_width, self.im_height = 1, 0, 0
        self.filter_worker2, self.filter_timer, self.filter_timer2, self.frame_id, self.frame_id2 = [None] * 5
        self.pilframes, self.filtframes, self.cachedframes, self.saveframes, self.frames2 = None, [], [], [], []
        self.dir_path, self.f_path = f'{path.dirname(path.realpath(__file__))}\\filter_frames', None
        self.curr_filter, self.curr_theme, self.curr_overlay_filter, self.dither_opt = [None] * 4
        self.curr_intensity, self.norm_thresh, self.norm_method = [None] * 3
        self.orig_img, self.scaled_img, self.newtkimg, self.filttkimg = [None] * 4
        self.root, self.canvas, self.menubar, self.play_gif, self.btn_inc, self.btn_dec, self.progress_bar = [None] * 7
        self.trans_bg = Image.open("C:\\Users\\mfarh\\OneDrive\\Pictures\\Downloads\\blacksquare3.png")
        self.playbtnstate, self.playbtnid, self.summary_bg, self.summary_txt, self.process_order, self.wrap_cntr = 0, None, None, None, '', 0

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
            filters_menu.add_radiobutton(label=filter_option, variable=self.curr_filter, value=filter_option, command=self.apply_transform_matrix)
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
        self.btn_inc = ttkButton(self.root, text='+', width=6, command=self.intensity_increase)
        self.btn_dec = ttkButton(self.root, text='-', width=6, command=self.intensity_decrease)
        self.canvas.create_window(thresh_scale.winfo_reqwidth() * 3 + 55, 0, anchor="nw", window=self.btn_dec)
        self.canvas.create_window(thresh_scale.winfo_reqwidth() * 3 + 10, 0, anchor="nw", window=self.btn_inc)
        thresh_menu_label = Menu(self.menubar, tearoff=False)
        self.menubar.add_command(label='  ', state="disabled")
        self.menubar.add_cascade(label=f'Threshold:  {self.norm_thresh.get()}', menu=thresh_menu_label, command=lambda: None, state="disabled")
        self.play_gif = Button(self.root, text='\u23F8', width=0, height=0, background='black', foreground='gray45',
                               activebackground='gray45', font='Helvetica 25', borderwidth=0,  command=self.toggle_play_gif)
        self.progress_bar = Progressbar(self.root, orient="horizontal", length=self.canvas.winfo_reqwidth() - 5, mode="determinate")
        self.canvas.create_window(self.canvas.winfo_reqwidth() - self.progress_bar.winfo_reqwidth() - 5,
                                  self.canvas.winfo_reqheight() - self.progress_bar.winfo_reqheight() - 5,
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
            self.process_order, self.wrap_cntr, self.FILE_SIZE = '', 0, 0
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
                if not self.play_gif.winfo_ismapped():
                    self.playbtnid = self.canvas.create_window(self.canvas.winfo_reqwidth() - self.play_gif.winfo_reqwidth() - 30,
                                                           self.canvas.winfo_reqheight() - self.play_gif.winfo_reqheight() - 30,
                                                           anchor="nw", window=self.play_gif)
                # self.FILE_SIZE = round((self.saveframes[0].width*self.saveframes[1].height*3)/1024**2 *len(self.saveframes), 1)
                for ffrm in self.saveframes:
                    bytestream = BytesIO()
                    ffrm.save(bytestream, format="PNG")
                    self.FILE_SIZE += bytestream.getbuffer().nbytes/1024**2
                self.FILE_SIZE = round(self.FILE_SIZE, 1)
                del bytestream, ffrm
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
                # self.FILE_SIZE = round((self.scaled_img.size[0]*self.scaled_img.size[1]*3)/1024**2, 1)
                bytestream = BytesIO()
                self.scaled_img.save(bytestream, format="PNG")
                self.FILE_SIZE = round(bytestream.getbuffer().nbytes/1024**2, 1)
                if self.summary_txt:
                    self.canvas.delete('summary')
                self.frame_summary(self.f_path[-3:])
                del bytestream
            del ret
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
            text = f"Size: {self.FILE_SIZE} MB\nDimensions: {self.saveframes[0].width} x {self.saveframes[1].height}\n" \
                   f"Frame Count: {self.FRAME_COUNT}\nFrame Delay: {self.GIF_DUR} ms\nCurrent Frame: {self.CURR_FRAME+1}\n" \
                   f"Processing time: {self.PROCESS_DUR} ms\nCurrent theme: {self.curr_theme.get()} ({self.curr_intensity.get()})\n" \
                   f"Current filter: {self.curr_filter.get()}\nColor Count: {clr_count}\nApplied: {self.process_order}"
        tkimg = ImageTk.PhotoImage(self.trans_bg.resize((bg_width, bg_height+int(self.wrap_cntr/1.5))))
        self.summary_bg = self.canvas.create_image(x, y, image=tkimg, anchor=NW, tags='summary')
        self.summary_txt = self.canvas.create_text(x+offset, y+offset, text=text, anchor=NW, fill="white", font=Font(family=families()[40], size=10, weight='bold'), tags='summary')
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
        print('no unused threads' if not self.THREAD_REF else f'{len(self.THREAD_REF)} threads in buffer')
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
        if self.curr_theme.get() != 'none':
            self.curr_intensity.set(self.curr_intensity.get()+1)
            self.theta = self.curr_intensity.get()
            self.menubar.entryconfigure(7, label=f'Intensity: {self.curr_intensity.get()}')
            for name, var in {key: getsizeof(value) for key, value in self.__dict__.items()}.items():
                print(f'{name}: {var}')
            print(f'\n{int(process.memory_info().rss / 1024 ** 2)} MB used')
            self.color_matrix_process()

    def intensity_decrease(self):
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
        if self.THREAD_REF:
            for thid, thd in enumerate(self.THREAD_REF):
                thd.join()
                self.THREAD_REF.pop(thid)
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
                    self.EFFECT_ACTIVE = False
                    self.process_order, self.wrap_cntr = '', 0
                    self.saveframes[:] = [frm.convert(mode='RGB') for frm in ImageSequence.Iterator(Image.open(self.f_path))]
                elif self.EFFECT_ACTIVE:
                    self.process_order = self.process_order + '\u2192' + self.curr_theme.get()
                    self.saveframes[:] = [frm.convert(mode='RGB', matrix=color_matrix[self.curr_theme.get()](self.theta)) for frm in self.saveframes]
                elif not self.EFFECT_ACTIVE:
                    self.process_order = '' + self.curr_theme.get()
                    tmpfrms = [frm.convert(mode='RGB') for frm in ImageSequence.Iterator(Image.open(self.f_path))]
                    self.saveframes[:] = [frm.convert(mode='RGB', matrix=color_matrix[self.curr_theme.get()](self.theta)) for frm in tmpfrms]
                    del tmpfrms
            else:
                self.canvas.delete("mainimg")
                if self.curr_theme.get() == 'none':
                    self.EFFECT_ACTIVE = False
                    self.process_order, self.wrap_cntr = '', 0
                    self.scaled_img = self.orig_img.convert('RGB')
                    self.scaled_img = self.orig_img.resize((self.im_width, self.im_height))
                elif self.EFFECT_ACTIVE:
                    self.process_order = self.process_order + '\u2192' + self.curr_theme.get()
                    self.scaled_img = self.scaled_img.convert(mode='RGB', matrix=color_matrix[self.curr_theme.get()](self.theta))
                elif not self.EFFECT_ACTIVE:
                    self.process_order = '' + self.curr_theme.get()
                    self.scaled_img = self.orig_img.convert('RGB')
                    self.scaled_img = self.scaled_img.resize((self.im_width, self.im_height)).convert(mode='RGB',
                                                                matrix=color_matrix[self.curr_theme.get()](self.theta))
                self.newtkimg = ImageTk.PhotoImage(self.scaled_img)
                self.canvas.create_image(0, 0, image=self.newtkimg, anchor=NW, tags='mainimg')
            if self.summary_txt:
                self.canvas.delete(self.summary_bg, self.summary_txt, 'summary')
            self.frame_summary(self.f_path[-3:])

    def transform_matrix_process(self, process_frames):
        self.EFFECT_ACTIVE = True
        strt = perf_counter()
        for frame in process_frames:
            imgarr = array(frame)
            imgchannels = [imgarr[:, :, 0], imgarr[:, :, 1], imgarr[:, :, 2]]
            kernel = array(filter_matrix[self.curr_filter.get()]['kernel'])
            dimx, dimy = imgchannels[0].shape[0], imgchannels[0].shape[1]
            op_type = filter_matrix[self.curr_filter.get()]['type']
            match op_type:
                case 'convolution':
                    pad_len = len(kernel) // 2
                    ret = kernel_ops.channel_op((dimx+2*pad_len)*(dimy+2*pad_len), imgchannels, kernel, op_type).astype(int)
                case 'ordered dither':
                    ret = kernel_ops.channel_op(dimx*dimy, imgchannels, kernel, op_type)
            match self.norm_method.get():
                case 'clip':
                    norm_ret = clip(ret, 0, 255)
                case 'modulo':
                    norm_ret = ret % 255
                case 'threshold':
                    norm_ret = ret.copy()
                    norm_ret[ret <= self.norm_thresh.get()] = 0
                    norm_ret[ret > self.norm_thresh.get()] = 255
            if self.f_path[-3:] == 'gif':
                self.saveframes.append(Image.fromarray(uint8(norm_ret)))
            else:
                self.scaled_img = Image.fromarray(uint8(norm_ret), 'RGB')
                self.newtkimg = ImageTk.PhotoImage(self.scaled_img)
                self.canvas.create_image(0, 0, image=self.newtkimg, anchor=NW, tags='mainimg')
        stp = perf_counter()
        self.progress_bar.stop()
        self.PROCESS_DUR = round((stp - strt) * 1000, 2)
        if self.process_order:
            self.process_order = self.process_order + '\u2192' + self.curr_filter.get()
        else:
            self.process_order += self.curr_filter.get()
        self.canvas.itemconfigure('progress', state="hidden")
        self.frame_summary(self.f_path[-3:])
        for menu in range(len(self.menubar.winfo_children())):
            self.menubar.entryconfigure(menu, state="normal")
        for btn in [self.btn_inc, self.btn_dec, self.play_gif]:
            btn.config(state="normal")

    def apply_transform_matrix(self):
        if not self.f_path:
            return
        for menu in range(len(self.menubar.winfo_children())):
            self.menubar.entryconfigure(menu, state="disabled")
        for btn in [self.btn_inc, self.btn_dec, self.play_gif]:
            btn.config(state="disabled")
        if self.f_path:
            self.canvas.delete(self.summary_txt, self.summary_bg, 'summary')
            if self.f_path[-3:] == 'gif':
                process_frames = [frame for frame in self.saveframes]
                self.root.after_cancel(self.filter_timer)
                self.canvas.delete(self.frame_id)
                self.filter_timer = None
            else:
                process_frames = [self.scaled_img]
                self.canvas.delete("mainimg")
            self.PROCESS_DUR = 0
            self.saveframes[:] = []
            self.progress_bar.configure(maximum=100*len(process_frames))
            th1 = Thread(target=self.transform_matrix_process, args=(process_frames,))
            self.canvas.itemconfigure('progress', state="normal")
            self.progress_bar.start(44)
            self.THREAD_REF.append(th1)
            th1.start()

if __name__ == '__main__':
    process = Process()
    app = Editor()
    app.setup()
