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


class QuantumConnection(Connection):
    def __init__(self, name="QuantumConnection"):
        super().__init__(name=name)
        distance = 2.74 / 1000  # default unit of length in channels is km
        self.add_subcomponent(QuantumChannel("QChannel_A2B", length=distance),
                              forward_input=[("A", "send")],
                              forward_output=[("B", "recv")]) 


class ClassicalConnection(Connection):
    def __init__(self, length, name="ClassicalConnection"):
        super().__init__(name=name)
        self.add_subcomponent(ClassicalChannel("Channel_A2B", length=length),
                              forward_input=[("A", "send")],
                              forward_output=[("B", "recv")])

def example_network_setup(num):
    node = []
    for i in range(num):
        node.append(Node("node" + str(i)))
    network = Network("Quantum_network")
    network.add_nodes(node)
    q_conn = []
    for i in range(num-1):
        q_conn.append(QuantumConnection())
    port1 = []
    port2 = []
    for i in range(1, num):
        # send port
        port1.append("Qout" + str(node[0].name) + "2" + str(node[i].name))
        # receive port
        port2.append("Qin" + str(node[0].name) + "2" + str(node[i].name))
    
    for i in range(1, num):
        network.add_connection(node[0], node[i], connection=q_conn[i-1], label="quantum",
                               port_name_node1=port1[i-1], port_name_node2=port2[i-1]
                               )
    c_conn = []
    for i in range((num)*(num-1)):
        c_conn.append(ClassicalConnection(length=4e-3)) 
    port3 = []
    port4 = []
    for i in range(num):
        for j in range(num):
            if i != j:
                port3.append("Cout" + str(node[i].name) + "2" + str(node[j].name))
                port4.append("Cin" + str(node[i].name) + "2" + str(node[j].name))
    k=0
    l=0     
    #print(len(node))
    #print(len(c_conn))
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
class TpProtocol(NodeProtocol):
    def __init__(self, node, num, allnode):
        super().__init__(node)
        self.counts = []
        self.mRtp = []
        self.mRtp2 = []
        self.c = []
        self.X_basis = []
        self.num = num
        self.allnode = allnode

    def run(self):
        while len(self.mRtp2) < n:
            self.mRtp.clear()
            self.counts.clear()
            self.X_basis.clear()
            l = 0
            while l < rounds:
                qubits = create_qubits(self.num)
                # 0 -> +
                for i in qubits:
                    ns.qubits.operate(i, ns.H)
                # entanglement
                for i in range(self.num):
                    for j in range(i+1, self.num):
                        ns.qubits.operate([qubits[i], qubits[j]], ns.CZ)
                # send Qubits
                for i in range(1,self.num):
                    self.node.ports["Qout" + str(self.allnode[0].name) + "2" + str(self.allnode[i].name)].tx_output(qubits[i])          


                # do H or not
                Q_H = round(random.random())
                if Q_H == 1:
                    ns.qubits.operate(qubits[0], ns.H)
                    self.counts.append(1)
                else:
                    self.counts.append(0)
                # measurement
                m, b = ns.qubits.measure(qubits[0], observable=ns.Z)
                self.mRtp.append(m)
                # make sure A&B&C receive q
                for i in range(1, self.num):
                    yield self.await_port_input(self.node.ports["Cin"+str(self.allnode[i].name)+"2"+str(self.allnode[0].name)])
                    self.node.ports["Cin"+str(self.allnode[i].name)+"2"+str(self.allnode[0].name)].rx_input().items[0]
                # ack
                for i in range(1, self.num):
                    self.node.ports["Cout"+str(self.allnode[0].name)+"2"+str(self.allnode[i].name)].tx_output("123")
                l += 1
            
            

            X_times = [0]*rounds        
            # receive X-basis times
            for i in range(1, self.num):
                yield self.await_port_input(self.node.ports["Cin"+str(self.allnode[i].name)+"2"+str(self.allnode[0].name)])
                tmp = self.node.ports["Cin"+str(self.allnode[i].name)+"2"+str(self.allnode[0].name)].rx_input().items
                for i in range(rounds):
                    X_times[i] += tmp[i]
            for i in range(rounds):
                X_times[i] += self.counts[i]

            # if X-basis is odd then store its position and send to A&B
            position = []
            for i in range(rounds):
                if X_times[i]%2 == 1:
                    x = (X_times[i]-1) // 2
                    if x%2 == 1:
                        self.c.append(1)
                    else:
                        self.c.append(0)                    
                    position.append(1)
                    self.mRtp2.append(self.mRtp[i])
                else:
                    position.append(0)
            # send position to user
            for i in range(1, self.num):
                self.node.ports["Cout"+str(self.allnode[0].name)+"2"+str(self.allnode[i].name)].tx_output(position)
        ##############################################
        global text
        time.sleep(13) 
        page0.pack_forget()
        text = '1'
        for client_socket in client_sockets:
            client_socket.send(text.encode())
        print(f"sending qubits to users...")
        page1.pack()
        update_progress(progress1, 0, 30)
        # 延时一段时间
        time.sleep(5)  # 这里可以根据需要设置发送字符的间隔时间
        ####################################################
        
        # delete when len is over num   
        del self.mRtp2[n:]
        del self.c[n:]
        # receive XOR result
        U = []
        for i in range(1, self.num):
            yield self.await_port_input(self.node.ports["Cin"+str(self.allnode[i].name)+"2"+str(self.allnode[0].name)])
            tmp = self.node.ports["Cin"+str(self.allnode[i].name)+"2"+str(self.allnode[0].name)].rx_input().items
            U.append(tmp)

        ##############################################
        text = '2'
        for client_socket in client_sockets:
            client_socket.send(text.encode())
        print(f"receiving info from users...")
        page1.pack_forget()
        page2.pack()
        update_progress(progress2, 30, 65)
        # 延时一段时间
        time.sleep(5)  # 这里可以根据需要设置发送字符的间隔时间
        ##################################################

        # ack
        for i in range(1, self.num):
            self.node.ports["Cout"+str(self.allnode[0].name)+"2"+str(self.allnode[i].name)].tx_output("TP receive!")
        # receice cw
        Ucw = []
        for i in range(1, self.num):
            yield self.await_port_input(self.node.ports["Cin"+str(self.allnode[i].name)+"2"+str(self.allnode[0].name)])
            tmp = self.node.ports["Cin"+str(self.allnode[i].name)+"2"+str(self.allnode[0].name)].rx_input().items[0]
            Ucw.append(tmp)
        for i in range(self.num-1):
            U[i] = list(rsc.decode(bytearray(U[i]) + Ucw[i])[0])
        # XOR
        UU = [0]*n
        for i in range(self.num-1):
            for j in range(n):
                UU[j] = UU[j] ^ U[i][j]
        ans = []
        flag = True
        for i in range(n):
            tmp = UU[i] ^ self.mRtp2[i] ^ self.c[i]
            if tmp != 0 :
                flag = False
            ans.append(tmp)

        ##############################################
        text = '3'
        for client_socket in client_sockets:
            client_socket.send(text.encode())
        print(f"sending result of XOR from users...")
        page2.pack_forget()
        page3.pack()
        update_progress(progress3, 65, 95)
        # 延时一段时间
        time.sleep(5)  # 这里可以根据需要设置发送字符的间隔时间
        ##################################################

        #print(f"ans:     {ans}")
        if flag == True:
            ##############################################
            text = '4'
            for client_socket in client_sockets:
                client_socket.send(text.encode())
            print(f"EQUAL...")
            page3.pack_forget()
            page4.pack()
            update_progress_fast(progress4)
            # 延时一段时间
            time.sleep(5)  # 这里可以根据需要设置发送字符的间隔时间
            ##################################################
        else:
            ##############################################
            text = '5'
            for client_socket in client_sockets:
                client_socket.send(text.encode())
            print(f"NOT EQUAL...")
            page3.pack_forget()
            page5.pack()
            update_progress_fast(progress5)
            # 延时一段时间
            time.sleep(5)  # 这里可以根据需要设置发送字符的间隔时间
            ##################################################
        ##############################################
        text = '6'
        for client_socket in client_sockets:
            client_socket.send(text.encode())
        page4.pack_forget()
        page5.pack_forget()
        page6.pack()
        # 延时一段时间
        time.sleep(5)  # 这里可以根据需要设置发送字符的间隔时间
        ##################################################

class UserProtocol(NodeProtocol):
    def __init__(self, node, id, allnode, message):
        super().__init__(node)
        self.mRu = []
        self.mRu2 = []
        self.counts = []
        self.id = id
        self.allnode = allnode
        self.message = message

    def run(self):
        ack = False
        while len(self.mRu2) < n:
            self.mRu.clear()
            self.counts.clear()
            l = 0
            while l < rounds:
                yield self.await_port_input(self.node.ports["Qin" + str(self.allnode[0].name) + "2" + str(self.allnode[self.id].name)])
                q = self.node.ports["Qin" + str(self.allnode[0].name) + "2" + str(self.allnode[self.id].name)].rx_input().items[0]
                #do H or not
                Q_H = round(random.random())
                if Q_H == 1:
                    ns.qubits.operate(q, ns.H)
                    self.counts.append(1)
                else:
                    self.counts.append(0)
                # measurement
                m, prob = ns.qubits.measure(q, observable=ns.Z)
                self.mRu.append(m)
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
            for i in range(rounds):
                if p[i] == 1:
                    self.mRu2.append(self.mRu[i])   
        # delete when len is over num  
        del self.mRu2[n:]
        # XOR
        u =[]
        for i in range(n):
            tmp = int(self.message[i]) ^ self.mRu2[i]
            u.append(tmp)
        # ECC
        codeword = rsc.encode(u)
        self.node.ports["Cout"+str(self.allnode[self.id].name)+"2"+str(self.allnode[0].name)].tx_output(u)
        yield self.await_port_input(self.node.ports["Cin"+str(self.allnode[0].name)+"2"+str(self.allnode[self.id].name)])
        tmp = self.node.ports["Cin"+str(self.allnode[0].name)+"2"+str(self.allnode[self.id].name)].rx_input().items[0]
        # send CWa to tp
        self.node.ports["Cout"+str(self.allnode[self.id].name)+"2"+str(self.allnode[0].name)].tx_output(codeword[n:])
        

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

def run():
    while flag==0:
        pass
    num = 3 # input how many nodes
    ns.sim_reset()
    network = example_network_setup(num)   # set up network

    node = []
    protocol = []
    for i in range(num):
        node.append(network.get_node("node" + str(i)))
    for i in range(num):
        if i == 0:
            protocol.append(TpProtocol(node[i], num, node))
        else:
            if i == 1:
                protocol.append(UserProtocol(node[i], i, node,"00000000000000000000"))
            else:
                protocol.append(UserProtocol(node[i], i, node,"00000000000000000001"))
    for i in range(num):
        protocol[i].start()
    ns.sim_run(500)

def conn():
    # 创建 Socket
    global text, flag
    global server_socket, client_socket, client_sockets 
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # 绑定地址和端口
    server_address = ('192.168.14.148', 8000)
    server_socket.bind(server_address)

    # 监听连接
    clients = 1
    server_socket.listen(clients)

    print('WAITING CONNECTION...')
    client_sockets = []  # 存储客户端套接字
    connected_client = 0
    # # 接受树莓派连接
    client_socket, client_address = server_socket.accept()
    print('SUCCESSFULLY CONNECTED:', client_address)
    # 接受树莓派连接
    while True:
        client_socket, client_address = server_socket.accept()
        print('SUCCESSFULLY CONNECTED:', client_address)
        client_sockets.append(client_socket)
        connected_client += 1
        if connected_client >= clients:
            break
    
    text = '1'
    flag = 1

# 設定新的尺寸
new_size = (400, 400)

def load_and_resize_gif(gif_path):
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

flag = 0
text = '0'
# 建立畫面
root = tk.Tk()
root.title("client 1")
root.geometry("800x600")

page0 = tk.Frame(root)
page1 = tk.Frame(root)
page2 = tk.Frame(root)
page3 = tk.Frame(root)
page4 = tk.Frame(root)
page5 = tk.Frame(root)
page6 = tk.Frame(root)

page0.pack()
page1.pack_forget()
page2.pack_forget()
page3.pack_forget()
page4.pack_forget()
page5.pack_forget()
page6.pack_forget()

# 載入和縮小GIF圖像
frames_photo0 = load_and_resize_gif("wait.gif")
frames_photo1 = load_and_resize_gif("t.gif")
frames_photo2 = load_and_resize_gif("j.gif")
frames_photo3 = load_and_resize_gif("t.gif")
frames_photo4 = load_and_resize_gif("page4.gif")
frames_photo5 = load_and_resize_gif("page5.gif")
frames_photo6 = load_and_resize_gif("tk.gif")

# 顯示縮小後的GIF圖像
gif_label0 = tk.Label(page0)
gif_label0.pack()
update_gif_frame(gif_label0, frames_photo0, 0)
text0 = tk.Label(page0, text="\nWAITING...\n", font=("Arial", 20))
text0.pack()

gif_label1 = tk.Label(page1)
gif_label1.pack()
update_gif_frame(gif_label1, frames_photo1, 0)
text1 = tk.Label(page1, text="receiving qubits from server...\n", font=("Arial", 20))
text1.pack()
progress1 = ttk.Progressbar(page1, orient=tk.HORIZONTAL, length=600, mode='determinate')
progress1.pack()
progress1['value'] = 0

gif_label2 = tk.Label(page2)
gif_label2.pack()
update_gif_frame(gif_label2, frames_photo2, 0)
text2 = tk.Label(page2, text="sending info to server...\n", font=("Arial", 20))
text2.pack()
progress2 = ttk.Progressbar(page2, orient=tk.HORIZONTAL, length=600, mode='determinate')
progress2.pack()
progress2['value'] = 0

gif_label3 = tk.Label(page3)
gif_label3.pack()
update_gif_frame(gif_label3, frames_photo3, 0)
text3 = tk.Label(page3, text="receiving result from server...\n", font=("Arial", 20))
text3.pack()
progress3 = ttk.Progressbar(page3, orient=tk.HORIZONTAL, length=600, mode='determinate')
progress3.pack()
progress3['value'] = 0

gif_label4 = tk.Label(page4)
gif_label4.pack()
update_gif_frame(gif_label4, frames_photo4, 0)
text4 = tk.Label(page4, text="EQUAL\n", font=("Arial", 20))
text4.pack()
progress4 = ttk.Progressbar(page4, orient=tk.HORIZONTAL, length=600, mode='determinate')
progress4.pack()
progress4['value'] = 0

gif_label5 = tk.Label(page5)
gif_label5.pack()
update_gif_frame(gif_label5, frames_photo5, 0)
text5 = tk.Label(page5, text="NOT EQUAL\n", font=("Arial", 20))
text5.pack()
progress5 = ttk.Progressbar(page5, orient=tk.HORIZONTAL, length=600, mode='determinate')
progress5.pack()
progress5['value'] = 0

gif_label6 = tk.Label(page6)
gif_label6.pack()
update_gif_frame(gif_label6, frames_photo6, 0)
text6 = tk.Label(page6, text="\nFINISHED", font=("Arial", 20))
text6.pack()


run_thread = threading.Thread(target=run)
conn_thread = threading.Thread(target=conn)


run_thread.start()
conn_thread.start()

root.mainloop()

run_thread.join()
conn_thread.join()


client_socket.close()
server_socket.close()