import socket
import time
import collections
import threading
import os
import sys

# Request=collections.namedtuple('Request', 'name priority status')
# lưu trữ thông tin về các yêu cầu tải file.
class Request:
    def __init__(self, name, priority, size, progress):
        self.name = name
        self.priority = priority
        self.size = size
        self.progress = progress #tiến độ tải file


#lưu trữ thông tin về các file có sẵn trên server.
class menu:
    def __init__(self, name, size):
        self.name = name
        self.size = size

preRequest = [] #Danh sách lưu trữ các yêu cầu tải file từ phía client (là input.txt), nó chỉ là mảng xử lí trước khi xử lí cho request của client
NumberOfFile_Menu = 0   #Biến lưu trữ số lượng file có sẵn trong menu của server.

#lấy địa chỉ cục bộ mà ko cần phải kết nối trực tiếp đến máy chủ từ xa 
def get_local_ip(s:socket.socket):
    # s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0) # mục đích của hàm là lấy địa chỉ IP cục bộ nên không cần kết nối đến máy chủ từ xa -> timeout = 0 để tránh chờ đợi nếu máy chủ không phản hồi
    try:
        # Doesn't even have to be reachable
        s.connect(('10.254.254.254', 1)) #một địa chỉ không tồn tại hoặc không cần thiết kết nối đến
        #mục đích chỉ là lấy địa chỉ IP cục bộ mà socket sẽ sử dụng
        local_ip = s.getsockname()[0] 
    except Exception:
        local_ip = '127.0.0.1' #nếu có bất kì lỗi nào sẽ lấy địa chỉ IP mặc định
    finally:
        s.close()
    return local_ip


# kiểm tra xem yêu cầu tải file với tên file cụ thể đã tồn tại trong danh sách preRequest hay chưa
def checkPrevious(preRequest, request):
    for i in range(0, len(preRequest)):
        if preRequest[i].name == request:
            return True
    return False


#Hàm này đọc file input.txt mỗi 2 giây để cập nhật các yêu cầu tải file mới. 
#Nếu file yêu cầu tồn tại trong menu của server, nó sẽ được thêm vào danh sách preRequest với các thông tin chi tiết.
def readInputFile(s, Menu):
    try:
        while True:   #đọc liên tục để lấy các yêu cầu mới từ file
            f = open("input.txt", "r") #mở file txt
            lines = f.readlines() #đọc từng dòng

            for line in lines:
                line = line.strip().split() #xóa khoảng trắng đầu/cuối dòng và phân tách dòng thành danh sách từ
                if len(line) == 2 and not checkPrevious(preRequest, line[0]) and line[1] in {"HIGH", "CRITICAL", "NORMAL"}:
                    #kiểm tra điều kiên:
                        #dòng phải có đúng 2 phần
                        #phần đầu tiên (tên) chưa có trong preRequest
                        #phần thứ 2 phải là một mức độ ưu tiên hợp lệ
                    check = True    

                    for i in range(0, len(Menu)):
                        if Menu[i].name == line[0]: #Kiểm tra xem tên file trong mục hiện tại của Menu có khớp với tên file trong dòng yêu cầu (line[0]) hay không.
                            preRequest.append(Request(line[0], line[1], Menu[i].size, 0)) 
                            check = False
                            break
                    if check == True: preRequest.append(Request(line[0], line[1], 0, 0))

            f.close()
            time.sleep(2) # mỗi 2s quét 1 lần
    except KeyboardInterrupt:
        return
    finally:
        return
    

def PrintStatus(preRequest,n):
    for i in range(0, n):
        if preRequest[i].size == 0:
            print(preRequest[i].name + " "+ " " + "File not found")
        elif preRequest[i].progress == 1:
            print(preRequest[i].name + " "+ " " + "Downloaded Successfully")
        else:
            print(preRequest[i].name + " "+ " " + str(int(preRequest[i].progress * 100)) + "%")

    #điều chỉnh vị trí con trỏ đầu ra và đảm bảo rằng các thông báo không bị ghi đè lên nhau.
    sys.stdout.write("\033[" + str(n) + "A")
    sys.stdout.flush()  
    

#xử lý việc tải file từ server. 
#Nó liên tục kiểm tra danh sách preRequest, gửi yêu cầu tải file với tên và độ ưu tiên tới server
#nhận dữ liệu file và ghi vào ổ đĩa cục bộ, cập nhật tiến độ và in ra trạng thái tải.
def mainProcess(s):
    time.sleep(0.5) #Chờ 0.5 giây trước khi bắt đầu xử lý, có thể để đảm bảo rằng tất cả các thiết lập ban đầu đã hoàn tất.
    try:

        while True:
            n = len(preRequest)
            for i in range(0, n):
                if preRequest[i].size == 0 or preRequest[i].progress == 1: #kiểm tra file không tồn tại hoặc không xác định kích thước hay file đã tải 100%
                    PrintStatus(preRequest,n) #in ra trạng thái hiện tại của file
                    continue

                # xử lí download file cho yêu cầu hiện tại,
                # preRequest[i].name tên tệp tin mà đang tải xuống từ server (đường dẫn đầy đủ là "output/example.txt").
                RealName = "output/" + preRequest[i].name

                f = open(RealName, "ab") #ghi vào cuối file
                cur_size = f.tell() #Lấy kích thước hiện tại của tệp (vị trí con trỏ file).

                if cur_size >= preRequest[i].size:
                    preRequest[i].progress = 1 #tải đầy đủ 100%
                    PrintStatus(preRequest, n)
                    continue

                #gửi yêu cầu cần download file tới server
                # gửi size tên file và tên file tới server
                # Gửi độ dài của độ ưu tiên và độ ưu tiên tới server
                # Gửi kích thước hiện tại của file tới server
                name_bytes = preRequest[i].name.encode('utf-8')     # Chuyển tên tệp sang dạng bytes để gửi đi.
                s.sendall(len(name_bytes).to_bytes(4, byteorder = 'big'))
                s.sendall(name_bytes)
                priority_bytes = preRequest[i].priority.encode('utf-8')
                s.sendall(len(priority_bytes).to_bytes(4, byteorder = 'big'))
                s.sendall(priority_bytes)
                s.sendall(cur_size.to_bytes(4, byteorder = 'big'))


                data = s.recv(1024 * 10000)     # Nhận dữ liệu từ server, với kích thước tối đa là 10 MB.

                #Kiểm tra nếu không nhận được dữ liệu (kết nối bị đóng)
                if not data:
                    break


                f.write(data)
                cur_size = f.tell()     #Cập nhật kích thước hiện tại của tệp
                preRequest[i].progress = cur_size / preRequest[i].size
                f.close()

                PrintStatus(preRequest,n)

                #nếu tất cả các file đã download xong
                if preRequest[i].progress < 1: 
                    all_done = False
                
            if all_done:
                # send "DONE" msg to server
                done_msg = "DONE".encode('utf-8')
                s.sendall(len(done_msg).to_bytes(4, byteorder= 'big'))
                s.sendall(done_msg)
                break

    except KeyboardInterrupt: 
        return
    finally: 
        return
    

def main():
    server_ip = input("Enter the server IP address: ")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (server_ip, 12345)
    print('Connecting to port ' + str(server_address))


    Menu = []
    
    try: 
        s.connect(server_address)
        print ("SERVER CONNECTED 🤝 \n")
        NumberOfFile_Menu = int.from_bytes(s.recv(4), byteorder = 'big')
        print('NUMBER OF FILES: ' + str(NumberOfFile_Menu) + '\n')
        
        for i in range(NumberOfFile_Menu):
            name_length = int.from_bytes(s.recv(4), byteorder = 'big')
            name = s.recv(name_length).decode('utf-8')
            size = int.from_bytes(s.recv(4), byteorder = 'big')
            Menu.append(menu(name, size))
        print("AVAILABLE FILES:")

        for i in range(0,NumberOfFile_Menu):
            print(Menu[i].name + " " + str(Menu[i].size))

            #Một thread để đọc file đầu vào input.txt và cập nhật danh sách yêu cầu.
            #Một thread để xử lý việc tải file từ server.
        read_input = threading.Thread(target=readInputFile, args=(s, Menu ),daemon=True).start()
        main_process = threading.Thread(target=mainProcess, args=(s, ),daemon=True).start()

        

        while True:
            pass
    except KeyboardInterrupt or ConnectionResetError:
        print("\nCtrl+C pressed.")
    finally:
        print('Closing socket !')
        s.close()

main()
