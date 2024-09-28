import tkinter as tk
import tkinter.ttk as ttk
import socket
import threading
import time
import imageio
from PIL import Image, ImageTk

# 创建 Socket
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# 连接服务器
server_address = ('192.168.14.148', 9004)
client_socket.connect(server_address)

# 创建一个整数变量 page
page = ''

def check_page():
    global page
    if page is None:
        root.after(100, check_page)
        return

    page1.pack_forget()
    page2.pack_forget()
    page3.pack_forget()
    page4.pack_forget()
    page5.pack_forget()
    page6.pack_forget()

    # 检查 page 的值并根据不同的值显示相应的页面
    if page == '1':
        page0.pack_forget()
        page1.pack()
        update_progress(progress1, 0, 30)
    elif page == '2':
        page2.pack()
        update_progress(progress2, 30, 65)
    elif page == '3':
        page3.pack()
        update_progress(progress3, 65, 95)
    elif page == '4':
        page4.pack()
        update_progress_fast(progress4)  # 快速填满进度条
    elif page == '5':
        page5.pack()
        update_progress_fast(progress5)  # 快速填满进度条
    elif page == '6':
        page6.pack()

    page = None
    root.after(100, check_page)

def change_page():
    global page
    while True:               
        data = client_socket.recv(1024)
    
        # 处理接收到的字符
        page = data.decode()
        print('received:', page)
        if page == '6':
            client_socket.close()
            break

def update_progress(progress, start_value, end_value):
    current_value = progress['value']
    if current_value < start_value:
        current_value = start_value
    if current_value < end_value:
        increment = 1 if current_value < start_value else (end_value - start_value) / 100  # 将值的增量分成100个步骤
        while current_value < end_value:
            current_value += increment
            if current_value > end_value:
                current_value = end_value
            progress['value'] = current_value
            root.update()
            time.sleep(0.01)

def update_progress_fast(progress):
    progress['value'] = 100
    root.update()

# 建立畫面
root = tk.Tk()
root.title("Bob")
root.option_add('*Dialog*background', 'black')
root.geometry("800x600")

# Load the image
image = Image.open("qn.jpg")
# Specify the desired size for the background image
bg_width = 1000
bg_height = 800

# Resize the image to the specified size
resized_image = image.resize((bg_width, bg_height))

# Create a PhotoImage object from the resized image
background_image = ImageTk.PhotoImage(resized_image)

# Create a label widget to display the background image
background_label = tk.Label(root, image=background_image)
background_label.place(x=0, y=0, relwidth=1, relheight=1)

# 创建两个页面，每个页面放在一个 Frame 中
# 创建一个宽度为500，高度为300的Frame
page0 = tk.Frame(root, bg="black", width=650, height=600)
page1 = tk.Frame(root, bg="black", width=650, height=600)
page2 = tk.Frame(root, bg="black", width=650, height=600)
page3 = tk.Frame(root, bg="black", width=650, height=600)
page4 = tk.Frame(root, bg="black", width=650, height=600)
page5 = tk.Frame(root, bg="black", width=650, height=600)
page6 = tk.Frame(root, bg="black", width=650, height=600)

# 预设只显示第一个页面
page0.pack()
page1.pack_forget()
page2.pack_forget()
page3.pack_forget()
page4.pack_forget()
page5.pack_forget()
page6.pack_forget()


def load_and_resize_gif(gif_path, new_size):
    # 載入原始的GIF圖像
    gif = imageio.mimread(gif_path)
    # 縮小GIF圖像的每個幀
    gif_resized = []
    for frame in gif:
        frame_resized = Image.fromarray(frame).resize(new_size, Image.LANCZOS)
        gif_resized.append(frame_resized)
    # 將縮小後的GIF圖像轉換為Tkinter的PhotoImage
    frames_photo = [ImageTk.PhotoImage(frame) for frame in gif_resized]
    return frames_photo

def update_gif_frame(gif_label, frames_photo, index):
    gif_label.configure(image=frames_photo[index])
    index = (index + 1) % len(frames_photo)
    root.after(100, update_gif_frame, gif_label, frames_photo, index)

# 載入和縮小GIF圖像
new_size = (600, 450)
frames_photo0 = load_and_resize_gif("tp.gif", new_size)
frames_photo1 = load_and_resize_gif("recv.gif", new_size)
frames_photo2 = load_and_resize_gif("send.gif", new_size)
frames_photo3 = load_and_resize_gif("recv.gif", new_size)
new_size = (450, 450)
frames_photo4 = load_and_resize_gif("correct.gif", new_size)
frames_photo5 = load_and_resize_gif("incorrect.gif", new_size)
new_size = (600, 450)
frames_photo6 = load_and_resize_gif("end.gif", new_size)

# 顯示縮小後的GIF圖像
gif_label0 = tk.Label(page0)
# 在适当的位置添加这段代码，将GIF图像定位在屏幕中央下方

gif_label0.pack(side=tk.TOP, pady=30)



update_gif_frame(gif_label0, frames_photo0, 0)
text0 = tk.Label(page0, text="\nCONNECTING...\n\n", font=("Arial", 20), fg="white")
text0.config(highlightthickness=0, bd=0, bg="black")
text0.pack(side=tk.BOTTOM, pady=10)

gif_label1 = tk.Label(page1)
# 在适当的位置添加这段代码，将GIF图像定位在屏幕中央下方
gif_label1.pack(side=tk.TOP, pady=30)

update_gif_frame(gif_label1, frames_photo1, 0)
text1 = tk.Label(page1, text="receiving qubits from server...\n", font=("Arial", 20), fg="white")
text1.config(highlightthickness=0, bd=0, bg="black")
text1.pack()
style = ttk.Style()
style.configure("Custom.Horizontal.TProgressbar", troughcolor="black", background="blue", thickness=10)

progress1 = ttk.Progressbar(page1, orient=tk.HORIZONTAL, length=600, mode='determinate', style="Custom.Horizontal.TProgressbar")
progress1.pack()
progress1['value'] = 0

gif_label2 = tk.Label(page2)
gif_label2.pack(side=tk.TOP, pady=30)
update_gif_frame(gif_label2, frames_photo2, 0)
text2 = tk.Label(page2, text="sending info to server...\n", font=("Arial", 20), fg="white")
text2.config(highlightthickness=0, bd=0, bg="black")
text2.pack()
progress2 = ttk.Progressbar(page2, orient=tk.HORIZONTAL, length=600, mode='determinate', style="Custom.Horizontal.TProgressbar")
progress2.pack()
progress2['value'] = 0

gif_label3 = tk.Label(page3)
gif_label3.pack(side=tk.TOP, pady=30)
update_gif_frame(gif_label3, frames_photo3, 0)
text3 = tk.Label(page3, text="receiving result from server...\n", font=("Arial", 20), fg="white")
text3.config(highlightthickness=0, bd=0, bg="black")
text3.pack()
progress3 = ttk.Progressbar(page3, orient=tk.HORIZONTAL, length=600, mode='determinate', style="Custom.Horizontal.TProgressbar")
progress3.pack()
progress3['value'] = 0

gif_label4 = tk.Label(page4)
gif_label4.pack(side=tk.TOP, pady=30)
update_gif_frame(gif_label4, frames_photo4, 0)
text4 = tk.Label(page4, text="EQUAL\n", font=("Arial", 20), fg="white")
text4.config(highlightthickness=0, bd=0, bg="black")
text4.pack()
progress4 = ttk.Progressbar(page4, orient=tk.HORIZONTAL, length=600, mode='determinate', style="Custom.Horizontal.TProgressbar")
progress4.pack()
progress4['value'] = 0

gif_label5 = tk.Label(page5)
gif_label5.pack(side=tk.TOP, pady=30)
update_gif_frame(gif_label5, frames_photo5, 0)
text5 = tk.Label(page5, text="NOT EQUAL\n", font=("Arial", 20), fg="white")
text5.config(highlightthickness=0, bd=0, bg="black")
text5.pack()
progress5 = ttk.Progressbar(page5, orient=tk.HORIZONTAL, length=600, mode='determinate', style="Custom.Horizontal.TProgressbar")
progress5.pack()
progress5['value'] = 0

gif_label6 = tk.Label(page6)
gif_label6.pack(side=tk.TOP, pady=70)
update_gif_frame(gif_label6, frames_photo6, 0)
text6 = tk.Label(page6, text="\n\n\n", font=("Arial", 20), fg="white")
text6.config(highlightthickness=0, bd=0, bg="black")
text6.pack()


# 创建并启动两个线程
check_page_thread = threading.Thread(target=check_page)
change_page_thread = threading.Thread(target=change_page)

check_page_thread.start()
change_page_thread.start()

# 启动 GUI
root.mainloop()

# 等待线程结束
check_page_thread.join()
change_page_thread.join()
