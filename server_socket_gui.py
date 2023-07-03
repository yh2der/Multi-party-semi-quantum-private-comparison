from netsquid.protocols import NodeProtocol
from netsquid.nodes.connections import Connection
from netsquid.nodes import Node, Network
from netsquid.components import ClassicalChannel, QuantumChannel
from netsquid.qubits.qubitapi import create_qubits, operate
from reedsolo import RSCodec
from PIL import Image, ImageTk
import imageio
import threading
import tkinter as tk
import tkinter.ttk as ttk
import netsquid as ns
import random
import socket
import time

#Quantum Channel Connection
class QuantumConnection(Connection):
    def __init__(self, name="QuantumConnection"):
        super().__init__(name=name)
        distance = 2.74 / 1000  # default unit of length in channels is km
        self.add_subcomponent(QuantumChannel("QChannel_A2B", length=distance),
                              forward_input=[("A", "send")],
                              forward_output=[("B", "recv")]) 

#Classical Channel Connection
class ClassicalConnection(Connection):
    def __init__(self, length, name="ClassicalConnection"):
        super().__init__(name=name)
        self.add_subcomponent(ClassicalChannel("Channel_A2B", length=length),
                              forward_input=[("A", "send")],
                              forward_output=[("B", "recv")])

#Network setting
def example_network_setup(num):
    node = []

    #根據num去產生節點
    for i in range(num):
        node.append(Node("node" + str(i)))

    network = Network("Quantum_network")
    network.add_nodes(node) #將node加入network
    q_conn = []

    #建立n-1個量子通道
    for i in range(num-1):
        q_conn.append(QuantumConnection())
 
    port1 = [] #Oout node0 to all
    port2 = [] #Oin  node0 to all

    #先建立port的名稱array
    for i in range(1, num):
        # send port
        port1.append("Qout" + str(node[0].name) + "2" + str(node[i].name))
        # receive port
        port2.append("Qin" + str(node[0].name) + "2" + str(node[i].name))
    
    #將node連接變成量子通道並取名加入network
    for i in range(1, num):
        network.add_connection(node[0], node[i], connection=q_conn[i-1], label="quantum",
                               port_name_node1=port1[i-1], port_name_node2=port2[i-1]
                               )
    
    c_conn = []
    #產生n*(n-1)條傳統通道並設定通道長度
    for i in range((num)*(num-1)):
        c_conn.append(ClassicalConnection(length=4e-3)) 

    port3 = [] #Cout all node to all node
    port4 = [] #Cin all node to all node

    #先建立port的名稱array
    for i in range(num):
        for j in range(num):
            if i != j:
                port3.append("Cout" + str(node[i].name) + "2" + str(node[j].name))
                port4.append("Cin" + str(node[i].name) + "2" + str(node[j].name))

    k=0
    l=0     
    #print(len(node))
    #print(len(c_conn))
    #將node連接變成傳統通道並取名加入network
    for i in range(num):
        for j in range(num):
            if i != j:                
                network.add_connection(node[i], node[j], connection=c_conn[k], label="classical",
                                port_name_node1=port3[l], port_name_node2=port4[l]
                                )
                k += 1
                l+=1
        
    return network

n = 20
rounds = 10
err = 1
rsc = RSCodec(err)
#創建TP(Server)物件
class TpProtocol(NodeProtocol):
    def __init__(self, node, num, allnode): #初始化傳入 (node0, 節點數量, 所有節點名稱)
        super().__init__(node)
        self.counts = [] #TP是否使用X基底來測量
        self.mRtp = [] #TP的測量結果
        self.mRtp2 = [] #存放符合用X基底測量的總數是奇數的位置的TP的測量結果
        self.c = [] #修正碼 
        self.X_basis = [] #存放Users用X基底測量的總數(不含TP本身)
        self.num = num
        self.allnode = allnode

    def run(self):
        global text
        while len(self.mRtp2) < n:
            self.mRtp.clear()
            self.counts.clear()
            self.X_basis.clear()
            l = 0
            while l < rounds: #每一輪要產生rounds個量子組合
                qubits = create_qubits(self.num)

                # 0 -> +
                for i in qubits:
                    ns.qubits.operate(i, ns.H)

                # entanglement
                for i in range(self.num):
                    for j in range(i+1, self.num):
                        ns.qubits.operate([qubits[i], qubits[j]], ns.CZ)

                # send Qubits to all Users
                for i in range(1,self.num):
                    self.node.ports["Qout" + str(self.allnode[0].name) + "2" + str(self.allnode[i].name)].tx_output(qubits[i])          

                # TP's qubit
                # do H or not
                Q_H = round(random.random())
                if Q_H == 1:
                    ns.qubits.operate(qubits[0], ns.H)
                    self.counts.append(1) #counts代表tp是否使用X基底去做測量
                else:
                    self.counts.append(0)

                # measurement
                m, b = ns.qubits.measure(qubits[0], observable=ns.Z)
                self.mRtp.append(m) #加入到mRtp

                # make sure all nodes receive q
                for i in range(1, self.num):
                    yield self.await_port_input(self.node.ports["Cin"+str(self.allnode[i].name)+"2"+str(self.allnode[0].name)])
                    self.node.ports["Cin"+str(self.allnode[i].name)+"2"+str(self.allnode[0].name)].rx_input().items[0]

                # ack
                for i in range(1, self.num):
                    self.node.ports["Cout"+str(self.allnode[0].name)+"2"+str(self.allnode[i].name)].tx_output("123")

                l += 1         

            # init X_times
            X_times = [0]*rounds  

            # 接收並計數各User共使用了幾次X基底去測量
            for i in range(1, self.num):
                yield self.await_port_input(self.node.ports["Cin"+str(self.allnode[i].name)+"2"+str(self.allnode[0].name)])
                tmp = self.node.ports["Cin"+str(self.allnode[i].name)+"2"+str(self.allnode[0].name)].rx_input().items

                for i in range(rounds):
                    X_times[i] += tmp[i]

            for i in range(rounds):
                X_times[i] += self.counts[i] #將tp自己的counts也加入

            # if X-basis is odd then store its position and send to Users (大家使用的X基底總和是奇數才能用)
            # 並且算出c  odd = 2*n+1 , if n是奇數, c=1 else c=0
            position = []

            for i in range(rounds):
                # if odd
                if X_times[i]%2 == 1:
                    x = (X_times[i]-1) // 2
                    if x%2 == 1: 
                        self.c.append(1) 
                    else:
                        self.c.append(0)   
                    position.append(1)
                    self.mRtp2.append(self.mRtp[i])
                
                # if even
                else:
                    position.append(0)

            # send position to user
            for i in range(1, self.num):
                self.node.ports["Cout"+str(self.allnode[0].name)+"2"+str(self.allnode[i].name)].tx_output(position)

        # 延時一段時間
        time.sleep(13)

        # send signal to users
        text = '1'
        for client_socket in client_sockets:
            client_socket.send(text.encode())
        print(f"sending qubits to users...")

        # gui
        page0.pack_forget() #將page0刷掉
        page1.pack() #顯示page1
        update_progress(progress1, 0, 30) #將page1底下的進度條從0%增加到30%

        # 延時一段時間
        time.sleep(5)
        
        # delete when len is over num   
        del self.mRtp2[n:]
        del self.c[n:]

        # receive (Users' message XOR qubits) result
        U = []
        for i in range(1, self.num):
            yield self.await_port_input(self.node.ports["Cin"+str(self.allnode[i].name)+"2"+str(self.allnode[0].name)])
            tmp = self.node.ports["Cin"+str(self.allnode[i].name)+"2"+str(self.allnode[0].name)].rx_input().items
            U.append(tmp)

        # send signal to users
        text = '2'
        for client_socket in client_sockets:
            client_socket.send(text.encode())
        print(f"receiving info from users...")

        # gui
        page1.pack_forget()
        page2.pack()
        update_progress(progress2, 30, 65)

        # 延時一段時間
        time.sleep(5)

        # ack
        for i in range(1, self.num):
            self.node.ports["Cout"+str(self.allnode[0].name)+"2"+str(self.allnode[i].name)].tx_output("TP receive!")

        # receice cw
        Ucw = []
        for i in range(1, self.num):
            yield self.await_port_input(self.node.ports["Cin"+str(self.allnode[i].name)+"2"+str(self.allnode[0].name)])
            tmp = self.node.ports["Cin"+str(self.allnode[i].name)+"2"+str(self.allnode[0].name)].rx_input().items[0]
            Ucw.append(tmp)

        #用cw將U還原
        for i in range(self.num-1):
            U[i] = list(rsc.decode(bytearray(U[i]) + Ucw[i])[0])

        # XOR:產生每個bits的各Users' (Users'message XOR qubits)
        UU = [0]*n
        for i in range(self.num-1):
            for j in range(n):
                UU[j] = UU[j] ^ U[i][j]

        ans = []
        flag = True #flag為最終比對結果, flag = Ture 所有Users的Message一樣
        for i in range(n):
            tmp = UU[i] ^ self.mRtp2[i] ^ self.c[i] #(Users'message XOR qubits) XOR TP's qubits XOR c
            if tmp != 0 :
                flag = False
            ans.append(tmp)

        # send signal to users
        text = '3'
        for client_socket in client_sockets:
            client_socket.send(text.encode())
        print(f"sending result of XOR to users...")

        # gui
        page2.pack_forget()
        page3.pack()
        update_progress(progress3, 65, 95)

        # 延時一段時間
        time.sleep(5)

        #print(f"ans:     {ans}")
        if flag == True: #如果Messages都一樣就顯示勾勾畫面
            # send signal to users
            text = '4'
            for client_socket in client_sockets:
                client_socket.send(text.encode())
            print(f"EQUAL...")

            # gui
            page3.pack_forget()
            page4.pack()
            update_progress_fast(progress4)

            # 延时一段时间
            time.sleep(5)  # 这里可以根据需要设置发送字符的间隔时间

        else: #如果Messages不一樣就顯示X畫面
            # send signal to users
            text = '5'
            for client_socket in client_sockets:
                client_socket.send(text.encode())
            print(f"NOT EQUAL...")

            # gui
            page3.pack_forget()
            page5.pack()
            update_progress_fast(progress5)

            # 延时一段时间
            time.sleep(5)  # 这里可以根据需要设置发送字符的间隔时间

        # send signal to users 
        text = '6' 
        for client_socket in client_sockets:
            client_socket.send(text.encode())

        # gui
        page4.pack_forget()
        page5.pack_forget()
        page6.pack()

        # 延时一段时间
        time.sleep(5)  # 这里可以根据需要设置发送字符的间隔时间

#創建Users(Client)物件
class UserProtocol(NodeProtocol): #初始化傳入 (node[i], 自己的編號, 所有節點名稱, User的訊息)
    def __init__(self, node, id, allnode, message):
        super().__init__(node)
        self.mRu = [] #Users的測量結果
        self.mRu2 = [] #從TP傳過來的position中挑出來可以用的Users測量結果
        self.counts = [] #計算是否用X基底測量
        self.id = id #用來在傳送時給節點加上自己的編號
        self.allnode = allnode
        self.message = message

    def run(self):
        ack = False
        while len(self.mRu2) < n:
            self.mRu.clear()
            self.counts.clear()
            l = 0
            while l < rounds:
                # receive Qubits from TP
                yield self.await_port_input(self.node.ports["Qin" + str(self.allnode[0].name) + "2" + str(self.allnode[self.id].name)])
                q = self.node.ports["Qin" + str(self.allnode[0].name) + "2" + str(self.allnode[self.id].name)].rx_input().items[0]
                
                #do H or not 決定要用哪種基底去測量的程式寫法
                Q_H = round(random.random())
                if Q_H == 1:
                    ns.qubits.operate(q, ns.H)
                    self.counts.append(1) #如果要用X基底去測量，此bit的counts=1
                else:
                    self.counts.append(0)

                # measurement
                m, prob = ns.qubits.measure(q, observable=ns.Z)
                self.mRu.append(m) #將測量結果加入mRu

                #ack
                self.node.ports["Cout"+str(self.allnode[self.id].name)+"2"+str(self.allnode[0].name)].tx_output(ack)

                # know that tp has receive ack
                yield self.await_port_input(self.node.ports["Cin"+str(self.allnode[0].name)+"2"+str(self.allnode[self.id].name)])
                self.node.ports["Cin"+str(self.allnode[0].name)+"2"+str(self.allnode[self.id].name)].rx_input().items[0]
                l += 1

            # send to tp X-basis times
            self.node.ports["Cout"+str(self.allnode[self.id].name)+"2"+str(self.allnode[0].name)].tx_output(self.counts)

            # receive position
            yield self.await_port_input(self.node.ports["Cin"+str(self.allnode[0].name)+"2"+str(self.allnode[self.id].name)])
            p = self.node.ports["Cin"+str(self.allnode[0].name)+"2"+str(self.allnode[self.id].name)].rx_input().items
            
            #根據所收到的position去將有效的位置的qubit加入到mRu2
            for i in range(rounds):
                if p[i] == 1:
                    self.mRu2.append(self.mRu[i])  

        # delete when len is over num  
        del self.mRu2[n:]

        # mRu2 XOR message
        u =[]
        for i in range(n):
            tmp = int(self.message[i]) ^ self.mRu2[i]
            u.append(tmp)

        # 用ECC產生 mRu2 XOR message的CW
        codeword = rsc.encode(u)

        #寄出mRu2 XOR message
        self.node.ports["Cout"+str(self.allnode[self.id].name)+"2"+str(self.allnode[0].name)].tx_output(u)

        #接收(ack)
        yield self.await_port_input(self.node.ports["Cin"+str(self.allnode[0].name)+"2"+str(self.allnode[self.id].name)])
        tmp = self.node.ports["Cin"+str(self.allnode[0].name)+"2"+str(self.allnode[self.id].name)].rx_input().items[0]
        
        # send CWa to tp
        self.node.ports["Cout"+str(self.allnode[self.id].name)+"2"+str(self.allnode[0].name)].tx_output(codeword[n:])
        
#更新進度條(progess, 起始%, 結束%)
def update_progress(progress, start_value, end_value):
    current_value = progress['value'] #此進度條目前的%數

    if current_value < start_value: #讓此進度條跳到起始位置
        current_value = start_value

    if current_value < end_value: #讓此進度條慢慢跑到結束位置
        increment = 1 if current_value < start_value else (end_value - start_value) / 100  # 將值的增量分成100个步驟
        while current_value < end_value:
            current_value += increment
            if current_value > end_value:
                current_value = end_value
            progress['value'] = current_value
            root.update()
            time.sleep(0.01)

#進度條直接跑到100%
def update_progress_fast(progress):
    progress['value'] = 100
    root.update()

def run():
    #執行socket的連接
    conn() 

    # input how many nodes
    num = 3 

    # reset ns
    ns.sim_reset()

    # set up network 並傳入要多少個節點
    network = example_network_setup(num)   

    node = []
    protocol = []

    #將節點加入network
    for i in range(num):
        node.append(network.get_node("node" + str(i)))

    #產生1個TP跟(num-1)個Users加入Protocol    
    for i in range(num):
        if i == 0:
            protocol.append(TpProtocol(node[i], num, node))
        else:
            if i == 1:
                protocol.append(UserProtocol(node[i], i, node,"00000000000000000000"))
            else:
                protocol.append(UserProtocol(node[i], i, node,"00000000000000000001"))

    #啟動協定            
    for i in range(num):
        protocol[i].start()

    ns.sim_run(500)    

def conn():
    global text
    global server_socket, client_socket, client_sockets 
    # 創建 Socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # 綁定地址和端口
    server_address = ('192.168.14.148', 9005)
    server_socket.bind(server_address)

    # listen connection
    clients = 1
    server_socket.listen(clients)
    print('WAITING CONNECTION...')

    # 存儲客戶端套接字
    client_sockets = []  
    connected_client = 0
    
    # 接受樹梅派連接
    while True:
        client_socket, client_address = server_socket.accept()
        print('SUCCESSFULLY CONNECTED:', client_address)
        client_sockets.append(client_socket)
        connected_client += 1

        #在連接設備達到目標數量前不跳出迴圈
        if connected_client >= clients:
            break

    # default signal
    text = '1'

#圖片處理
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

#更新gif的FPS
def update_gif_frame(gif_label, frames_photo, index):
    gif_label.configure(image=frames_photo[index])
    index = (index + 1) % len(frames_photo)
    root.after(100, update_gif_frame, gif_label, frames_photo, index)

# init text
text = '0'

# 建立畫面
root = tk.Tk()
root.title("TP SERVER")
root.option_add('*Dialog*background', 'black')
root.geometry("800x600")

# Load the image
image = Image.open("qn.jpg")
server = Image.open("123.png")

# Specify the desired size for the background image
bg_width = 1000
bg_height = 800

# Resize the image to the specified size
resized_image = image.resize((bg_width, bg_height))
resized_server = server.resize((50, 50), Image.LANCZOS)

# Create a PhotoImage object from the resized image
background_image = ImageTk.PhotoImage(resized_image)
server_image = ImageTk.PhotoImage(resized_server)

# Create a label widget to display the background image
background_label = tk.Label(root, image=background_image)
background_label.place(x=0, y=0, relwidth=1, relheight=1)
server_label = tk.Label(root, image=server_image, fg='black')
server_label.place(x=0,y=0)

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

# 載入和縮小GIF圖像
new_size = (600, 450)
frames_photo0 = load_and_resize_gif("tp.gif", new_size)
frames_photo1 = load_and_resize_gif("send.gif", new_size)
frames_photo2 = load_and_resize_gif("recv.gif", new_size)
frames_photo3 = load_and_resize_gif("send.gif", new_size)
new_size = (450, 450)
frames_photo4 = load_and_resize_gif("correct.gif", new_size)
frames_photo5 = load_and_resize_gif("incorrect.gif", new_size)
new_size = (600, 450)
frames_photo6 = load_and_resize_gif("end.gif", new_size)

# page0
gif_label0 = tk.Label(page0)
gif_label0.pack(side=tk.TOP, pady=30)
update_gif_frame(gif_label0, frames_photo0, 0)
text0 = tk.Label(page0, text="\nCONNECTING...\n\n", font=("Arial", 20), fg="white")
text0.config(highlightthickness=0, bd=0, bg="black")
text0.pack(side=tk.BOTTOM, pady=10)

# page1
gif_label1 = tk.Label(page1)
gif_label1.pack(side=tk.TOP, pady=30)
update_gif_frame(gif_label1, frames_photo1, 0)
text1 = tk.Label(page1, text="sending qubits to USERS...\n", font=("Arial", 20), fg="white")
text1.config(highlightthickness=0, bd=0, bg="black")
text1.pack()
style = ttk.Style()
style.configure("Custom.Horizontal.TProgressbar", troughcolor="gray", background="red", thickness=10)
progress1 = ttk.Progressbar(page1, orient=tk.HORIZONTAL, length=600, mode='determinate', style="Custom.Horizontal.TProgressbar")
progress1.pack()
progress1['value'] = 0

# page2
gif_label2 = tk.Label(page2)
gif_label2.pack(side=tk.TOP, pady=30)
update_gif_frame(gif_label2, frames_photo2, 0)
text2 = tk.Label(page2, text="receiving qubits from USERS...\n", font=("Arial", 20), fg="white")
text2.config(highlightthickness=0, bd=0, bg="black")
text2.pack()
progress2 = ttk.Progressbar(page2, orient=tk.HORIZONTAL, length=600, mode='determinate', style="Custom.Horizontal.TProgressbar")
progress2.pack()
progress2['value'] = 0

# page3
gif_label3 = tk.Label(page3)
gif_label3.pack(side=tk.TOP, pady=30)
update_gif_frame(gif_label3, frames_photo3, 0)
text3 = tk.Label(page3, text="sending info to USERS...\n", font=("Arial", 20), fg="white")
text3.config(highlightthickness=0, bd=0, bg="black")
text3.pack()
progress3 = ttk.Progressbar(page3, orient=tk.HORIZONTAL, length=600, mode='determinate', style="Custom.Horizontal.TProgressbar")
progress3.pack()
progress3['value'] = 0

# page4
gif_label4 = tk.Label(page4)
gif_label4.pack(side=tk.TOP, pady=30)
update_gif_frame(gif_label4, frames_photo4, 0)
text4 = tk.Label(page4, text="EQUAL\n", font=("Arial", 20), fg="white")
text4.config(highlightthickness=0, bd=0, bg="black")
text4.pack()
progress4 = ttk.Progressbar(page4, orient=tk.HORIZONTAL, length=600, mode='determinate', style="Custom.Horizontal.TProgressbar")
progress4.pack()
progress4['value'] = 0

# page5
gif_label5 = tk.Label(page5)
gif_label5.pack(side=tk.TOP, pady=30)
update_gif_frame(gif_label5, frames_photo5, 0)
text5 = tk.Label(page5, text="NOT EQUAL\n", font=("Arial", 20), fg="white")
text5.config(highlightthickness=0, bd=0, bg="black")
text5.pack()
progress5 = ttk.Progressbar(page5, orient=tk.HORIZONTAL, length=600, mode='determinate', style="Custom.Horizontal.TProgressbar")
progress5.pack()
progress5['value'] = 0

# page6
gif_label6 = tk.Label(page6)
gif_label6.pack(side=tk.TOP, pady=70)
update_gif_frame(gif_label6, frames_photo6, 0)
text6 = tk.Label(page6, text="\n\n\n", font=("Arial", 20), fg="white")
text6.config(highlightthickness=0, bd=0, bg="black")
text6.pack()

# set thread
run_thread = threading.Thread(target=run)

# start thread
run_thread.start()

# activate root
root.mainloop()
