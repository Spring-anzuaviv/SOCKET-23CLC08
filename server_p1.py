import socket
import os
import pickle

host = socket.gethostbyname(socket.gethostname())
#host = "127.0.0.1"
print(host)
port = 12345
format = "utf-8"
size = 102400
server_folder = os.path.join(os.getcwd(), "server_folder")
file_list_path = os.path.join(os.getcwd(), "file.txt")

def get_file_list ():
    file_list = []
    if os.path.exists(file_list_path):
        with open(file_list_path, 'r') as f:
            for line in f:
                filename, size = line.split()
                
                file_list.append((filename, size))
        return file_list
    else:
        return file_list

def send_file_list (conn):
    data = get_file_list()
    serialized_data = pickle.dumps(data)
    conn.send(serialized_data)   

def check_file_exist (filename):
    file_list = get_file_list()
    for file, size in file_list:
        if file == filename:
            return True
    return False

def handle_client (conn, addr):
    while True:
        try:
            filename = conn.recv(size).decode(format)
            
            if filename:
                if check_file_exist(filename):
                    print(f'[{addr}]: Downloading file {filename} \n')
                            
                    file_path = os.path.join(server_folder, filename)
                    file_size = os.path.getsize(file_path)
                    conn.send(f"Sending file... {file_size}".encode(format))
                    response = conn.recv(size).decode(format)
                            
                    if response == "Client is receiving file...":
                        file = os.path.join(server_folder, filename)
                        with open(file, 'rb') as f:
                            while True:
                                data = f.read(size)
                                if not data:
                                    break
                                conn.send(data)
                                
                        print(f"[{addr}]: Complete sending file. \n")
                    elif response == "File is already downloaded.":
                        print(f"[{addr}]: " + str(response) + "\n")
                else:
                    print(f'[{addr}]: File not found. \n')
                    conn.send("File not found".encode(format))
            else:
                print(f"[{addr}]: Disconnect. \n")
                break
                      
        except Exception as e:
            print(f"Exception occurred with client: {e}")
            break
        
def start_server ():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    print("[START] server is starting ...\n")
    server.listen()
    print("Server is listening on " + str(port) + ". \n")
    
    try:
        while True:
            conn, addr = server.accept()
            print(f"[NEW CONNECTION]: Client {addr} connected. \n")
            send_file_list(conn)
            
            handle_client(conn, addr)
            conn.close()
            
            
    except KeyboardInterrupt:
        print('Shutting down the server...')
        print('Server is shut down')
    finally:
        server.close()
        
if __name__ == "__main__":
    start_server()