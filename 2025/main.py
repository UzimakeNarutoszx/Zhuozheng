import arcade as aa
import tkinter as tk
from tkinter import filedialog
from PIL import Image
from pyglet.media import Player, load, StaticSource
import time
import os
import sys

# resource
base_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
os.chdir(base_dir)

def scale_change(image):
    texture = aa.load_texture(image)
    width, height = texture.width, texture.height
    scale1, scale2 = 1280 / width, 720 / height
    
    return max(scale1, scale2)

def min_scale_change(image):
    texture = aa.load_texture(image)
    width, height = texture.width, texture.height
    scale1, scale2 = 960 / width, 540 / height
    
    return min(scale1, scale2)

class Using(aa.View):
    def __init__(self):
        super().__init__()
        self.mb = aa.Sprite()
        self.start_mb = True
        self.over_mb = False

    def in_out(self, xian, yin, c_view):
        if xian:
            if self.start_mb:
                self.mb.alpha -= 3
                if self.mb.alpha == 0:
                    self.start_mb = False

        if yin:
            if self.over_mb:
                self.mb.alpha += 3
                if self.mb.alpha == 255:
                    self.over_mb = False
                    self.window.show_view(c_view)

class Start(Using):
    def __init__(self):
        super().__init__()
        self.bg = aa.Sprite('images/背景/拙政园1.jpeg', scale=scale_change('images/背景/拙政园1.jpeg'))
        self.bg.position = 640, 360
        self.bgmb = aa.Sprite('images/背景/mb1.jpg', scale=3)
        self.bgmb.position = 640, 360
        self.title = aa.Sprite('images/title.png', scale=0.5)
        self.title.position = 640, 470
        self.sb = aa.Sprite('images/start_button.png', scale=0.4)
        self.sb.position = 640, 240
        self.mb = aa.Sprite('images/背景/mb2.jpg', scale=3)
        self.mb.position = 640, 360

        self.bgmb.alpha = 100
        self.mb.alpha = 0
        self.start_mb = True
        self.over_mb = False

        self.bgm_player = Player()
        self.bgm_player.queue(load('files/古风bgm.mp3'))
        self.bgm_player.loop = True
        self.bgm_player.play()

    def on_draw(self):
        self.clear()
        self.bg.draw()
        self.bgmb.draw()
        self.sb.draw()
        self.title.draw()
        self.mb.draw()

    def on_update(self, time):
        self.in_out(False, True, intro)

    def on_mouse_release(self, x, y, button, modifiers):
        if self.sb.collides_with_point((x, y)):
            self.over_mb = True

class Introduction(Using):
    def __init__(self):
        super().__init__()
        self.bg = aa.Sprite('images/背景/古香5.jpg', scale=0.9)
        self.bg.position = 640, 360
        self.bgmb = aa.Sprite('images/背景/mb1.jpg', scale=3)
        self.bgmb.position = 640, 360
        self.mb = aa.Sprite('images/背景/mb2.jpg', scale=3)
        self.mb.position = 640, 360

        self.luanch_index = 0
        self.alpha_pm = True
        self.luanch_time = time.time()
        self.pictures = aa.SpriteList()
        for i in range(12):
            texture = aa.load_texture(f'images/框景/框景{i+1}.jpg')
            width = texture.width
            pic = aa.Sprite(f'images/框景/框景{i+1}.jpg', scale=400 / width)
            pic.position = 250, 400
            pic.alpha = 0
            self.pictures.append(pic)       

        self.small_title = aa.Sprite('images/small_title.png', scale=0.3)
        self.small_title.position = 900, 630
        self.content = aa.Sprite('images/intro.png', scale=0.5)
        self.content.position = 900, 360

        self.start_use = aa.Sprite('images/start_use.png', scale=0.25)
        self.start_use.position = 940, 100
        self.jt = aa.Sprite('images/箭头.png', scale=0.6)
        self.jt.position = 1070, 105
        
        self.bgmb.alpha = 100
        self.start_mb = True
        self.over_mb = False

    def on_draw(self):
        self.clear()
        self.bg.draw()
        self.bgmb.draw()
        self.pictures.draw()
        self.content.draw()
        self.small_title.draw()
        self.start_use.draw()
        self.jt.draw()
        self.mb.draw()

    def on_update(self, time):
        self.in_out(True, True, creat)
        self.luanch()

    def luanch(self):
        if self.alpha_pm:
            self.pictures[self.luanch_index].alpha += 3
            if self.pictures[self.luanch_index].alpha == 255:
                self.alpha_pm = False

        if not self.alpha_pm and time.time() - self.luanch_time >= 5:
            self.pictures[self.luanch_index].alpha -= 3
            if self.pictures[self.luanch_index].alpha == 0:
                self.alpha_pm = True
                self.luanch_time = time.time()
                if self.luanch_index == 11:
                    self.luanch_index = -1
                self.luanch_index += 1

    def on_mouse_release(self, x, y, button, modifiers):
        if self.jt.collides_with_point((x, y)):
            self.over_mb = True

class Creation(Using):
    def __init__(self):
        super().__init__()
        self.bg = aa.Sprite('images/背景/古香3.jpg', scale=scale_change('images/背景/古香3.jpg'))
        self.bg.position = 640, 360
        self.bgmb = aa.Sprite('images/背景/mb1.jpg', scale=3)
        self.bgmb.position = 640, 360
        self.mb = aa.Sprite('images/背景/mb2.jpg', scale=3)
        self.mb.position = 640, 360

        self.start_mb = True
        self.over_mb = False
        self.bgmb.alpha = 100

        self.b1 = aa.Sprite('images/button1.png', scale=0.3)
        self.b1.position = 100, 65
        self.b2 = aa.Sprite('images/button2.png', scale=0.3)
        self.b2.position = 300, 65
        self.b3 = aa.Sprite('images/button3.png', scale=0.3)
        self.b3.position = 500, 65
        self.b4 = aa.Sprite('images/button4.png', scale=0.3)
        self.b4.position = 700, 65
        self.b5 = aa.Sprite('images/button5.png', scale=0.3)
        self.b5.position = 900, 65
        
        self.select_button = aa.Sprite('images/select_button.png', scale=0.3)
        self.select_button.position = 500, 400
        self.selected_sprite = aa.Sprite()
        self.select = True

        self.huabu = aa.Sprite('images/背景/mb3.jpg', scale=960 / 600)
        self.huabu.position = 500, 400
        self.cklist = aa.SpriteList()
        for i in range(5):
            ck = aa.Sprite(f'images/窗框{i+1}.png')
            ck.position = 500, 400
            ck.alpha = 0
            self.cklist.append(ck)

        self.save_button = aa.Sprite('images/save.png', scale=0.3)
        self.save_button.position = 1130, 450

    def on_draw(self):
        self.clear()
        self.bg.draw()
        self.bgmb.draw()
        self.huabu.draw()
        if self.select:
            self.select_button.draw()
        else:
            self.b1.draw()
            self.b2.draw()
            self.b3.draw()
            self.b4.draw()
            self.b5.draw()
            self.save_button.draw()
        self.selected_sprite.draw()
        self.cklist.draw()
        self.mb.draw()

    def on_update(self, time):
        self.in_out(True, True, end)

    def on_mouse_release(self, x, y, button, modifiers):
        if self.select_button.collides_with_point((x, y)):
            self.pic_select()

        if self.save_button.collides_with_point((x, y)):
            self.save()

        if self.b1.collides_with_point((x, y)):
            self.cklist[0].alpha = 255
            for i in range(4):
                self.cklist[i+1].alpha = 0
        elif self.b2.collides_with_point((x, y)):
            self.cklist[1].alpha = 255
            for i in range(4):
                if i == 1:
                    i += 1
                self.cklist[i].alpha = 0
        elif self.b3.collides_with_point((x, y)):
            self.cklist[2].alpha = 255
            for i in range(4):
                if i == 2:
                    i += 1
                self.cklist[i].alpha = 0
        elif self.b4.collides_with_point((x, y)):
            self.cklist[3].alpha = 255
            for i in range(4):
                if i == 3:
                    i += 1
                self.cklist[i].alpha = 0
        elif self.b5.collides_with_point((x, y)):
            self.cklist[4].alpha = 255
            for i in range(4):
                if i == 4:
                    i += 1
                self.cklist[i].alpha = 0

    def pic_select(self):
        self.select = False
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        
        # 设置文件类型过滤器
        file_types = [
            ("图片文件", "*.png *.jpg *.jpeg *.gif *.bmp *.tga"),
            ("PNG文件", "*.png"),
            ("JPEG文件", "*.jpg *.jpeg"),
            ("所有文件", "*.*")
        ]
        
        # 打开文件选择对话框
        file_path = filedialog.askopenfilename(
            title="选择图片文件",
            initialdir=os.path.expanduser("~"),
            filetypes=file_types
        )
        root.destroy()
        
        if file_path:
            self.texture = aa.load_texture(file_path)
            img = Image.open(file_path)
            widthb, heightb = self.texture.width / 960, self.texture.height / 540
            if widthb > heightb:
                new_img = img.crop((0, 0, 960 * heightb, self.texture.height))
            else:
                new_img = img.crop((0, 0, self.texture.width, 540 * widthb))

            if file_path[-3] == 'j' or file_path[-4] == 'j':
                new_img.save('临时文件/临时.jpg')
                self.selected_sprite = aa.Sprite('临时文件/临时.jpg')
            else:
                new_img.save('临时文件/临时.png')
                self.selected_sprite = aa.Sprite('临时文件/临时.png')
            self.selected_sprite.position = 500, 400
            self.selected_sprite.scale = 960 / new_img.width

    def save(self):
        root = tk.Tk()
        root.withdraw()
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")]
        )

        get = aa.get_image().save('临时文件/截图文件.png')
        get_pic = Image.open('临时文件/截图文件.png')
        save_img = get_pic.crop((20, 50, 980, 590))
        save_img.save(file_path)
        self.over_mb = True

class Ending(Using):
    def __init__(self):
        super().__init__()
        self.global_y = 0
        self.bg = aa.Sprite('images/背景/古香2.jpg', scale=scale_change('images/背景/古香2.jpg'))
        self.bg.position = 640, 360
        self.bgmb = aa.Sprite('images/背景/mb1.jpg', scale=3)
        self.bgmb.position = 640, 360
        self.mb = aa.Sprite('images/背景/mb2.jpg', scale=3)
        self.mb.position = 640, 360

        self.start_mb = True
        self.over_mb = False
        self.bgmb.alpha = 100
        
    def on_draw(self):
        self.clear()
        self.bg.draw()
        self.bgmb.draw()
        self.mb.draw()
        self.global_y += 0.5

        aa.draw_text('感谢使用', 640, self.global_y, color=aa.color.BLACK, font_size=50, 
                     font_name='Simhei', anchor_x='center', anchor_y='center')
        aa.draw_text('开发团队', 640, self.global_y - 200, color=aa.color.BLACK, font_size=40, 
                     font_name='Simhei', anchor_x='center', anchor_y='center')
        aa.draw_text('项目总监 ： 史梓轩', 640, self.global_y - 300, color=aa.color.BLACK, font_size=25, 
                     font_name='Simhei', anchor_x='center', anchor_y='center')
        aa.draw_text('程序员 ： 史梓轩', 640, self.global_y - 380, color=aa.color.BLACK, font_size=25, 
                     font_name='Simhei', anchor_x='center', anchor_y='center')
        aa.draw_text('图片提供 ： 百度图片  豆包AI', 640, self.global_y - 460, color=aa.color.BLACK, font_size=25, 
                     font_name='Simhei', anchor_x='center', anchor_y='center')
        aa.draw_text('艺术设计 ： 张若瑄  陈钰涵  范佳宜', 640, self.global_y - 540, color=aa.color.BLACK, font_size=25, 
                     font_name='Simhei', anchor_x='center', anchor_y='center')
        aa.draw_text('资料提供 ： 张懿文', 640, self.global_y - 620, color=aa.color.BLACK, font_size=25, 
                     font_name='Simhei', anchor_x='center', anchor_y='center')

    def on_update(self, time):
        self.in_out()

    def in_out(self):
        if self.start_mb:
            self.mb.alpha -= 3
            if self.mb.alpha == 0:
                self.start_mb = False
        
w = aa.Window(1280, 720, '拙政园的造景手法')
start = Start()
intro = Introduction()
creat = Creation()
end = Ending()
w.show_view(start)
w.run()
