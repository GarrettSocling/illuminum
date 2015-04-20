#!/usr/bin/env python
 
import socket, struct,  threading, cgi, time
from base64 import b64encode
from hashlib import sha1

#******************************************************#
def recv_data (client, length):
	#print("Wait on data")
	data = bytearray(client.recv(512))
	#print("[ws] -> Incoming")
	if(len(data)==0):
		print("[ws] -> len=0 ==> disconnect")
		return -1
	elif(data[0]!=129):
		print("[ws] -> regular disconnect")
		return -1
	elif(len(data) < 6):
		print("[ws] -> Error reading data")
	else:
		datalen = (0x7F & data[1])
		
		if(datalen > 6): #fin,length,4xmask,?
			print("datalen: %d"%datalen)
			indexFirstMask=2
			if(datalen==126):
				indexFirstMask+=2
			elif(datalen==127):
				indexFirstMask+=8

			mask_key = data[indexFirstMask:indexFirstMask+4]
			masked_data = data[indexFirstMask+4:(indexFirstMask+4+datalen)]
			unmasked_data=""
			for i in range(0,len(masked_data),1):
				unmasked_data+=(chr(masked_data[i] ^ mask_key[i%4]))
		
			#print("Message:")
			#print(str_data)
			#print("EOM")
			for callb in callback_msg:
				callb(unmasked_data,client)
		return 0
	return -3
	#end
 

def send_data(client, data):
	msg= bytearray()
	# header = text
	msg.extend([0b10000001])
	# add length
	if(len(data)<=125):
		msg.extend([len(data)])
	elif(len(data)<=65535):
		msg.extend(bytes([126]))
		for i in range(8,-1,-8):
			msg.extend([len(data)>>i & 255])
	else:
		msg.extend(bytes([127]))	
		for i in range(56,-1,-8):
			msg.extend([len(data)>>i & 255])

	# add payload
	#msg.extend(data.encode('utf-8'))
	for d in bytearray(data):
            msg.append(d)

	try:
		client.send(msg)
	except:
		print("failed")
		return -1

	return 0

def send_data_all_clients(data):
	rem_clients = []
	id_max=len(clients)
	for i in clients:
		if(send_data(i,data)!=0):
			rem_clients.append(i)

	lock = threading.Lock()
	lock.acquire()
	for i in rem_clients:
		if(i in clients):
			clients.remove(i)
	lock.release()
	

 
def parse_headers (data):
	headers = {}
	lines = data.splitlines()
	for l in lines:
		parts = l.split(": ", 1)
		if len(parts) == 2:
			headers[parts[0]] = parts[1]
	headers['code'] = lines[len(lines) - 1]
	return headers

def handshake (client):
	#print('[ws] -> Handshaking...')
	data = str(client.recv(1024))
	headers = parse_headers(data)
	#print('Got headers:')
	#print('===========')
	#for k, v in headers.items():
	#	print(k+':'+v)
	#print('===========')
	shake = "HTTP/1.1 101 Switching Protocols\r\n"
	for k, v in headers.items():
		if(k=='Connection' and v=='Upgrade'):
			shake += "Upgrade: websocket\r\n"
			shake += "Connection: Upgrade\r\n"
		elif(k=='Origin'):
			shake += "Sec-WebSocket-Origin: %s\r\n" % (headers['Origin'])
		elif(k=='Host'):
			shake += "Sec-WebSocket-Location: ws://%s\r\n" % (headers['Host'])
		elif(k=='Sec-WebSocket-Protocol'):
			shake += "Sec-WebSocket-Protocol: sample\r\n\r\n"
		elif(k=='Sec-WebSocket-Key'):
			GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
			response_key = b64encode(sha1(v.encode('utf-8') + GUID.encode('utf-8')).digest())
			shake +="Sec-WebSocket-Accept:%s\r\n"%response_key.decode()
	shake+="\r\n"
	#print('Response: [%s]' % (shake.encode()))
	return client.send(shake.encode())
 
def handle (client, addr):
	handshake(client)
	lock = threading.Lock()
	while 1:
		#time.sleep(5)
		#print("Sending...")
		#msg="hi"
		#print("Done")
		res = recv_data(client, 1024)
		if res<0:
			#print("returned:%d"%res)
			break
		#print("recv_data!!")
		#if not data: break
		#data = cgi.escape(data)
		#lock.acquire()
		#[send_data(c, data) for c in clients]
		#lock.release()
	print("[ws] -> Client closed:"+str(addr))
	lock.acquire()
	if(client in clients):
		clients.remove(client)
	lock.release()
	client.close()
	
def start_server ():
	s = socket.socket()
	s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	s.bind(('', 9876))
	s.listen(5)
	print("[ws] -> Waiting on clients")
	while 1:
		conn, addr = s.accept()
		clients.append(conn)
		print("[ws] -> Connection from:"+ str(addr)+" Serving "+str(len(clients))+" clients now")
		threading.Thread(target = handle, args = (conn, addr)).start()
		# send every subscr
		for callb in callback_con:
			callb(conn)

 
def start():
	threading.Thread(target = start_server, args = ()).start()

def subscribe_callback(fun,method):
	if(method=="msg"):
		if callback_msg[0]==subscribe_callback:
			callback_msg[0]=fun
		else:
			callback_msg.append(fun)
	elif(method=="con"):
		if callback_con[0]==subscribe_callback:
			callback_con[0]=fun
		else:
			callback_con.append(fun)
#******************************************************#

callback_con = [subscribe_callback]
callback_msg = [subscribe_callback]
clients = []


