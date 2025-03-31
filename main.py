import requests
import pandas as pd
from tkinter import *
from tkinter import filedialog
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import re  # 引入正则表达式
import os
from tkinter import ttk
import time
import threading  # 导入 threading 模块
from PIL import Image, ImageTk  # 导入 PIL 库
import configparser  # 导入 configparser 模块
import sys

# 定义 Unicode 字符
LOADING_CHAR = " \u25D0\u25D1\u25D2\u25D3"  # 转圈圈的字符
SUCCESS_CHAR = "\u2705"  # 绿色的对勾
ERROR_CHAR = "\u274C"  # 红色的叉叉

# 定义颜色
BG_COLOR = "#F0F8FF"  # 窗口背景颜色 (淡蓝色)
TEXT_COLOR = "#4682B4"  # 文本颜色 (钢青色)
BUTTON_BG_COLOR = "#B0E2FF"  # 按钮背景颜色 (亮蓝色)
BUTTON_FG_COLOR = "#FFFFFF"  # 按钮文本颜色 (白色)

# 定义字体
LABEL_FONT = ("微软雅黑", 12)
ENTRY_FONT = ("微软雅黑", 12)
BUTTON_FONT = ("微软雅黑", 12, "bold")
LOG_FONT = ("微软雅黑", 10)

# 定义默认窗口大小
DEFAULT_WIDTH = 600
DEFAULT_HEIGHT = 350

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def fetch_data(uid, max_per_page=500, log_callback=None, loading_callback=None):
    base_url = "https://api.aicu.cc/api/v3/search/getreply"
    all_replies = []
    page_number = 1

    while True:
        response = requests.get(base_url, params={
            'uid': uid,
            'pn': page_number,
            'ps': max_per_page,
            'mode': 0
        })

        if response.status_code != 200:
            log_callback(f"请求失败，状态码: {response.status_code}")
            return None  # 返回 None 表示查询失败

        data = response.json()

        if data.get('code') != 0:
            log_callback(f"错误代码: {data.get('code')}")
            return None  # 返回 None 表示查询失败

        replies = data['data']['replies']
        all_replies.extend(replies)

        if data['data']['cursor']['is_end']:
            break

        loading_callback(f"查询中... {LOADING_CHAR[page_number % len(LOADING_CHAR)]}")  # 更新加载动画

        page_number += 1
        time.sleep(0.1)  # 适当的延时

    return all_replies

def save_to_excel(replies, uid, folder_path, log_callback=None):
    df = pd.DataFrame(replies)
    file_name = f"{uid}_评论数据.xlsx"
    file_path = os.path.join(folder_path, file_name)
    df.to_excel(file_path, index=False)
    log_callback(f"评论数据已保存到 {file_path}")

def generate_word_cloud(file_path, log_callback=None):
    log_callback("正在进行分析......")
    df = pd.read_excel(file_path)
    df['message'] = df['message'].fillna('')  # 填充缺失值

    # 使用正则表达式过滤表情包和回复
    def filter_text(text):
        if not isinstance(text, str):
            return ''  # 如果不是字符串，返回空字符串
        text = re.sub(r'\[.*?\]', '', text)  # 移除表情包，例如 [doge]
        text = re.sub(r'^回复 @.+?:\s*', '', text)  # 移除 "回复 @用户名 :"
        return text

    df['message'] = df['message'].apply(filter_text)
    text = ' '.join(df['message'])

    log_callback("云图生成中......")
    # 增加图片分辨率
    wordcloud = WordCloud(width=8000, height=4000, background_color='white', font_path='msyh.ttc').generate(text)

    # 保存词云图片
    output_file_path = os.path.splitext(file_path)[0] + ".png"

    def save_wordcloud_to_file():
        # 调整 matplotlib 显示尺寸
        plt.figure(figsize=(20, 10))
        plt.imshow(wordcloud, interpolation="bilinear")
        plt.axis('off')

        # 保存高清图片到xlsx同一目录下
        plt.savefig(output_file_path, dpi=300)  # 可以选择保存，dpi越高越清晰
        plt.close()  # 关闭图像，防止显示

        log_callback(f"词云已保存到 {output_file_path}")

    # 使用 root.after 将 Matplotlib 代码放到主线程中执行
    root.after(0, save_wordcloud_to_file)

def start_program():
    uid = uid_entry.get()
    folder_path = filedialog.askdirectory()

    log_text.insert(END, "与服务器连接成功！开始查询...\n")
    log_text.see(END)  # 自动滚动到最新内容

    # 禁用开始按钮
    start_button['state'] = DISABLED

    # 创建一个 Label 用于显示加载动画
    loading_label = Label(root, text="任务已下发", font=LABEL_FONT, fg=TEXT_COLOR, bg=BG_COLOR)
    loading_label.pack(pady=10)

    def update_log(message):
        log_text.insert(END, message + "\n")
        log_text.see(END)  # 自动滚动到最新内容
        root.after(0, root.update_idletasks)  # 使用 root.after 更新 UI

    def update_loading(message):
        loading_label.config(text=message)
        root.after(0, root.update_idletasks)

    def run_task():
        try:
            # 获取评论数据
            replies = fetch_data(uid, log_callback=update_log, loading_callback=update_loading)

            if replies is None:
                update_loading(f"任务异常 {ERROR_CHAR}")  # 显示红色叉叉
                update_log("查询失败！")
                return

            # 保存 Excel 文件
            save_to_excel(replies, uid, folder_path, log_callback=update_log)
            update_loading("云图生成中...")  # 开始云图生成动画

            # 生成词云
            file_path = os.path.join(folder_path, f"{uid}_评论数据.xlsx")
            generate_word_cloud(file_path, log_callback=update_log)
            update_loading(f"任务完成！ {SUCCESS_CHAR}")  # 显示绿色对勾
            update_log("任务完成！")  # 添加任务完成的提示
        except Exception as e:
            update_loading(f"任务异常 {ERROR_CHAR}")  # 显示红色叉叉
            update_log(f"发生错误：{e}")
        finally:
            # 启用开始按钮
            root.after(0, lambda: start_button.config(state=NORMAL))  # 使用 root.after 启用按钮
            # 移除加载动画
            # loading_label.destroy() # 暂时不移除，显示最终状态

    # 创建并启动线程
    thread = threading.Thread(target=run_task)
    thread.start()

# 创建 configparser 对象
config = configparser.ConfigParser()
config_file = 'config.ini'  # 配置文件名

try:
    config.read(config_file)
except:
    pass

if 'Window' not in config:
    config['Window'] = {}

root = Tk()
root.title("哔哩视奸小助手 - 凰十九定制版")
root.geometry(f"{DEFAULT_WIDTH}x{DEFAULT_HEIGHT}")

# 读取窗口位置
try:
    x = int(config['Window'].get('x', 100))  # 默认位置
    y = int(config['Window'].get('y', 100))  # 默认位置
    root.geometry(f"+{x}+{y}")
except:
    pass

# 设置窗口图标
try:
    icon_path = resource_path("xz.ico")
    root.iconbitmap(icon_path)
except Exception as e:
    print(f"设置图标失败：{e}")

# 禁止手动调整窗口大小
root.resizable(False, False)

# 加载背景图片
try:
    bg_path = resource_path("xz.jpg")
    bg_image = Image.open(bg_path)

    def resize_image(width, height):
        global bg_photo, bg_label

        # 计算图片的宽高比
        img_width, img_height = bg_image.size
        img_ratio = img_width / img_height
        # 计算窗口的宽高比
        window_ratio = width / height

        if img_ratio > window_ratio:
            # 图片更宽，以高度为基准进行缩放
            scale = height / img_height
            new_width = int(img_width * scale)
            x = (width - new_width) // 2
            y = 0
            region = (0, 0, img_width, img_height)
        else:
            # 图片更高，以宽度为基准进行缩放
            scale = width / img_width
            new_height = int(img_height * scale)
            x = 0
            y = (height - new_height) // 2
            region = (0, 0, img_width, img_height)

        resized_image = bg_image.resize((int(img_width * scale), int(img_height * scale)), Image.LANCZOS)  # 调整大小

        # 创建裁剪区域
        crop_x1 = max(0, (resized_image.width - width) // 2)
        crop_y1 = max(0, (resized_image.height - height) // 2)
        crop_x2 = crop_x1 + width
        crop_y2 = crop_y1 + height

        # 进行裁剪
        cropped_image = resized_image.crop((crop_x1, crop_y1, crop_x2, crop_y2))

        bg_photo = ImageTk.PhotoImage(cropped_image)
        bg_label.config(image=bg_photo)
        bg_label.image = bg_photo  # 保持引用

    def toggle_fullscreen(event=None):
        root.attributes("-fullscreen", not root.attributes("-fullscreen"))
        if root.attributes("-fullscreen"):
            # 全屏
            width = root.winfo_screenwidth()
            height = root.winfo_screenheight()
            resize_image(width, height)
        else:
            # 默认大小
            resize_image(DEFAULT_WIDTH, DEFAULT_HEIGHT)

    bg_photo = ImageTk.PhotoImage(bg_image)

    # 创建一个 Label 用于显示背景图片
    bg_label = Label(root, image=bg_photo)
    bg_label.place(x=0, y=0, relwidth=1, relheight=1)  # 覆盖整个窗口

    # 绑定全屏事件 (例如 F11 键)
    root.bind("<F11>", toggle_fullscreen)
    # 初始加载时也调整大小
    resize_image(DEFAULT_WIDTH, DEFAULT_HEIGHT)

except FileNotFoundError:
    print("错误：找不到背景图片！")
    BG_COLOR = "#FFFFFF"  # 白色
    TEXT_COLOR = "#000000"  # 黑色
    BUTTON_BG_COLOR = "#DDDDDD"  # 浅灰色
    BUTTON_FG_COLOR = "#000000"  # 黑色

except Exception as e:
    print(f"加载背景图片错误：{e}")
    BG_COLOR = "#FFFFFF"  # 白色
    TEXT_COLOR = "#000000"  # 黑色
    BUTTON_BG_COLOR = "#DDDDDD"  # 浅灰色
    BUTTON_FG_COLOR = "#000000"  # 黑色

# 设置窗口颜色
root.configure(bg=BG_COLOR)

uid_label = Label(root, text="请输入B站UID:", font=LABEL_FONT, fg=TEXT_COLOR, bg=BG_COLOR)
uid_label.pack(pady=(10, 5))

uid_entry = Entry(root, font=ENTRY_FONT, bd=2, relief="groove")
uid_entry.pack(pady=(0, 10), padx=20, fill="x")

start_button = Button(root, text="开始", command=start_program, font=BUTTON_FONT, bg=BUTTON_BG_COLOR, fg=BUTTON_FG_COLOR, bd=2, relief="raised")
start_button.pack(pady=(5, 10))

# 添加日志显示框
log_text = Text(root, height=8, width=70, font=LOG_FONT, bd=2, relief="sunken")
log_text.pack(pady=(0, 10), padx=20)

# 保存窗口位置
def on_closing():
    config['Window']['x'] = str(root.winfo_x())
    config['Window']['y'] = str(root.winfo_y())

    with open(config_file, 'w') as f:
        config.write(f)

    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

root.mainloop()
