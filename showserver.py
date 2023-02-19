import sys
import socket
import ssl
import threading
 

class MsgExchange:
    def __init__(self): 
        self.cond = threading.Condition()  # nodification from within exch
        self.server_msg_sock = ""          # start        from within exch  29002

        self.send_data    = ""
        self.send_pos     = -1
        self.send_txt_lst = []
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
                print("    client_in  111  send_data=", exch.send_data)

                if exch.send_data:
                    exch.send_txt_lst = exch.send_data.split('|||')
                    exch.NotifyAll()
                else:
                    print("    client_in, send_data is empty")
            except:
                print("    client_in()    333 ", my_pos, nick, " closed")
                exch.send_pos  = my_pos
                exch.send_data = "disconnected"
                exch.NotifyAll()
                self._is_running = False
                return


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

                if exch.send_pos == my_pos:
                    continue

                if exch.send_pos != my_pos and exch.send_data == "disconnected":
                    continue

                if exch.send_pos != my_pos: 
                    print("    client_out  111  nick=", nick, "    exch.send_txt_lst=", exch.send_txt_lst)

                    send_msg = exch.send_data.encode()
                    if len(exch.send_txt_lst) > 1:
                        if exch.send_txt_lst[0] == "Group" or exch.send_txt_lst[0] == nick:
                            try:
                                print("    client_out  222 ", exch.send_data, "     send to ", nick)
                                conn.send(send_msg)                    # send text
                            except:
                                self.close_actions(exch, my_pos, nick, "send() doesn't work, so, this close_out() should close")
                                return
                exch.cond.release()


    def close_actions(self, exch, my_pos, nick, msg):
        print("    client_out()   333 ", my_pos, nick, "     ", msg)
        exch.send_pos  = my_pos
        exch.send_data = "disconnected"
        exch.cond.release()
        self._is_running = False


    
def main(): 

    pos = 0
    exch = MsgExchange()
    exch.server_msg_sock_start()   # server side, a socket is created and listening to client connection for message

    while True:
        exch.send_pos = pos
        print("")
        print("main(), ............ communication exchange server is running, wait for a msg connect to accept ............")
        print("")
        newsock, addr = exch.server_msg_sock.accept()  # newsock: a socket from a client, addr: address on other end
        newssl        = ssl.wrap_socket(newsock, server_side=True, certfile="cert.pem", keyfile="cert.pem", 
                                 ssl_version=ssl.PROTOCOL_TLSv1)
        temp          = newssl.read()
        exch.send_data = temp.decode()

        if temp.decode() != "":                        # 1st data from a client
            comm_partner, comm_me, fullname, fname, fsuffix, filetype, obj = exch.send_data.split('|||')
            print("main(), connection from  ", comm_me, "  ---------------------->  ", comm_partner)

            exch.NotifyAll()                           # wake up send thread

            try:
                newssl.send(temp)                      # send message back to where it came from
                clientin  = ClientIn()
                clientout = ClientOut()
                exch.threads1.append(threading.Thread(name=comm_me + " threadin", target=clientin.client_in,   args=(newssl, exch, pos, comm_me)))
                exch.threads1[pos].start()
                exch.threads2.append(threading.Thread(name=comm_me + " threadout",target=clientout.client_out, args=(newssl, pos, comm_me, exch)))
                exch.threads2[pos].start()
            except:
                print("    threads for ", comm_me, " cannot start")
        pos += 1
    s.close()


if __name__=='__main__':
    main()
    
