import sys
import socket
import ssl
import threading
 

class MsgExchange:
    def __init__(self): 
        self.cond = threading.Condition()  # nodification from within exch
        self.server_msg_sock = ""          # start        from within exch  29002
        self.server_obj_sock = ""          # start        from within exch  29003

        self.send_data    = ""
        self.send_pos     = -1
        self.send_txt_lst = []
        self.send_obj_lst = []
        self.threads1     = []
        self.threads2     = []


    def server_msg_sock_start(self):
        try:
            host    = socket.gethostname()
            host_id = socket.gethostbyname(host)
            port    = 29002
            address = (host_id, port)

            self.server_msg_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_msg_sock.bind(address)
            self.server_msg_sock.listen()
            print("        In server_msg_sock_start(), connect to ", address, "  success")
        except:
            print("        In server_msg_sock_start(), connect to ", address, "  failed")


    def server_obj_sock_start(self):
        try:
            host    = socket.gethostname()
            host_id = socket.gethostbyname(host)
            port    = 29003
            address = (host_id, port)

            self.server_obj_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_obj_sock.bind(address)
            self.server_obj_sock.listen()
            print("        In server_obj_sock_start(), connect to ", address, "  success")
        except:
            print("        In server_obj_sock_start(), connect to ", address, "  failed")


    def NotifyAll(self):
        if self.cond.acquire():
            self.cond.notifyAll()
            self.cond.release()


class ClientIn:
    def __init__(self):
        i = 1

    def client_in(self, conn, exch, my_pos, nick):
        while True: 
            try: 
                temp = conn.recv(1024)                                   # receive text
                exch.send_pos  = my_pos
                exch.send_data = temp.decode()

                if exch.send_data:
                    exch.send_txt_lst    = exch.send_data.split('|||')
                    exch.send_txt_lst[0] = exch.send_txt_lst[0].strip()

                    print("    client_in, 111    nick=", nick, ",    read text message=", exch.send_txt_lst)

                    if exch.send_txt_lst[6] == 'xxxcccxxx':
                        exch.send_obj_lst = self.obj_read(exch)
                        print("    client_in, 222    nick=", nick, "     read obj file ................ done")
                    exch.NotifyAll()
                else:
                    print("    client_in, send_data is empty")
            except:
                print("    client_in()    444 ", my_pos, nick, " closed")
                exch.send_pos  = my_pos
                exch.send_data = "disconnected"
                exch.NotifyAll()
                self._is_running = False
                return


    def obj_read(self, exch): 
        print("")
        print("                In obj_read(), 111 waitng for an obj client connection")
        client_sock, client_addr = exch.server_obj_sock.accept()
        print("                In obj_read(), 222 obtained an obj client connection")
        client_file  = client_sock.makefile('rb')
        send_obj_lst = []
        data = 'empty'
        while data and data != '': 
            data = client_file.read()
            send_obj_lst.append(data)
            print("                In obj_read(), 333 read obj data loop")
        client_file.close()
        print("                In obj_read(), 444 read file   closed")
        client_sock.close()
        print("                In obj_read(), 555 read socket closed")
        print("")
        return send_obj_lst


class ClientOut:
    def __init__(self):
        i = 1

    def client_out(self, conn, my_pos, nick, exch): 
        while True: 
            if exch.cond.acquire():                                    # get lock
                exch.cond.wait()                                       # release lock, wait

                if exch.send_pos == my_pos and exch.send_data == "disconnected":
                    self.close_actions(exch, my_pos, nick, "close_in() closed, close_out() should close")
                    return

                if exch.send_pos != my_pos and exch.send_data == "disconnected":
                    continue

                if exch.send_pos == my_pos:
                    continue

                if exch.send_pos != my_pos: 
                    send_msg = exch.send_data.encode()
                    if len(exch.send_txt_lst) > 1:

                        print("    client_out  111 nick=", nick, ",    text message=", exch.send_txt_lst)

                        if exch.send_txt_lst[0] == "Group" or exch.send_txt_lst[0] == nick:
                            try:
                                print("    client_out  222 nick=", nick, ",     text data",  exch.send_data, "  try send to ", nick)
                                conn.send(send_msg)                    # actually send text msg
                            except:
                                self.close_actions(exch, my_pos, nick, "text msg send() doesn't work, this close_out() should be closed")
                                return

                            if exch.send_txt_lst[6] == 'xxxcccxxx': 
                                print("    client_out,  333 nick=", nick, "  send objects")
                                self.obj_send(exch)
                                print("    client_out, 444 nick=", nick, "  objects .............. sent")
                exch.cond.release()


    def close_actions(self, exch, my_pos, nick, msg):
        print("    client_out()   333 ", my_pos, nick, "     ", msg)
        exch.send_pos  = my_pos
        exch.send_data = "disconnected"
        exch.cond.release()
        self._is_running = False


    def obj_send(self, exch):
        print("                In obj_send(), 111  waiting for an obj client connection")
        client_sock, addr = exch.server_obj_sock.accept()
        client_file = client_sock.makefile('wb')
        print("                In obj_send(), 222  obj client connected")

        for chunk in exch.send_obj_lst: 
            print("    In obj_send(), write loop")
            client_file.write(chunk)

        client_file.flush()
        client_file.close()
        print("                In obj_send(), 333  write obj file closed")
        client_sock.close()
        print("                In obj_send(), 444  write obj socket closed")

    
def main(): 

    pos  = 0
    exch = MsgExchange()
    exch.server_msg_sock_start()   # server side, a socket is created and listening to client connection for message
    exch.server_obj_sock_start()   # server side, a socket is created and listening to client connection for objects

    while True:
        exch.send_pos = pos
        print("")
        print("main(), ............ server ready to accept a client ............")
        print("")
        newsock, addr = exch.server_msg_sock.accept()     # newsock: a socket from a client, addr: address on other end
        newssl        = ssl.wrap_socket(newsock, server_side=True, certfile="cert.pem", keyfile="cert.pem", 
                                 ssl_version=ssl.PROTOCOL_TLSv1)
        temp = newssl.read()
        data = temp.decode()
        exch.send_data = data
        print("main(),              a client connected, data=", exch.send_data)

        if data != "":                           # 1st data from a client
            comm_partner, comm_me, fullname, fname, fsuffix, filetype, obj = data.split('|||')
            print("main(),                  ", comm_me, "  ------------- to ------------->  ", comm_partner)

            exch.NotifyAll()                              # wake up send thread

            a_client = comm_me.strip()
            #try:
            #    newssl.send(temp)                         # send message back to where it came from
            #except:
            #    print("    cannot send initial message back to ", a_client)

            try:
                m1 = a_client + " thread in"
                ci = ClientIn()
                exch.threads1.append(threading.Thread(name=m1, target=ci.client_in,   args=(newssl, exch, pos, a_client)))
                exch.threads1[pos].start()
            except:
                print("    client_in()  threads for ", a_client, " cannot start")

            try:
                m2 = a_client + " thread out"
                co = ClientOut()
                exch.threads2.append(threading.Thread(name=m2, target=co.client_out, args=(newssl, pos, a_client, exch)))
                exch.threads2[pos].start()
            except:
                print("    client_out() threads for ", a_client, " cannot start")
        pos += 1
    s.close()


if __name__=='__main__':
    main()
    
