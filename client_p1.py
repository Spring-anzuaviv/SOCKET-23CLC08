import socket
import os
import pickle

size = 102400
host = input("Enter the server IP address: ")
port = 12345
format = "utf-8"
client_folder = os.path.join(os.getcwd(), "output")
input_file = os.path.join(os.getcwd(), "input.txt")


def read_input_file():
    if os.path.exists(input_file):
        with open(input_file, 'r') as f:
            return [line.strip() for line in f]
    return []

def get_file_list(conn):
    data = conn.recv(4096)
    file_list = pickle.loads(data)
    return file_list

def download_file (conn, filename):
    try:
        conn.send(filename.encode(format))
     
        response = conn.recv(size).decode(format)

        if response.startswith("Sending file..."):
            file_size = int(response.split()[2])
            file_path = os.path.join(client_folder, filename)
            if not os.path.exists(file_path):
                conn.send("Client is receiving file...".encode(format))
                
                downloaded_size = 0
                with open(file_path, 'wb') as f:
                    while downloaded_size < file_size:
                        data = conn.recv(size)
                        if not data:
                            break
                        f.write(data)
                        downloaded_size += len(data)

                        # progress
                        progress = (downloaded_size / file_size) * 100
                        print(f"\rDownloading {filename} .... {int(progress)}%", end="")
                print("\n")
                print(f"File '{filename}' downloaded successfully. \n")
            else:
                conn.send("File is already downloaded.".encode(format))
                print(f"{filename} is already downloaded. \n")
        else:
            print(response)
            
    except Exception as e:
        print(f"Error downloading file '{filename}': {e}")

def monitor_input_file(client):
    downloaded_files = set()
    
    while True:
        try:
            cur_files = set(read_input_file())
            new_files = list(cur_files - downloaded_files)
            
            for filename in new_files:
                download_file(client, filename)
                downloaded_files.add(filename)
            
        except FileNotFoundError:
            print(f"File {input_file} does not exist.\n")
        except Exception as e:
            print(f"An error occurred: {e}")
            break
    
def main ():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((host, port))   
    print(f"Connected to server {(host, port)}. \n")
    
    try:
        file_list = get_file_list(client)
        
        print("Files available for download:")
        for filename, filesize in file_list:
            print(f"{filename} ({filesize})")
            
        monitor_input_file(client)
        
    except KeyboardInterrupt:
        print("Closing the connection ...\n")
        client.close()
        print("Disconnected.\n")
        
if __name__ == "__main__":
    main()