import socket
import threading
import collections



menu = collections.namedtuple('menu', 'name size')  # lấy file.txt bỏ vô mảng menu gồm tên và kích thước mỗi file
Request = collections.namedtuple('Request', 'name size priority')  # lấy file input.txt bỏ vô mảng này để lưu tên file nào ưu tiên tải
Rawmenu = str  # chuỗi (string)để lưu trữ nội dung của file.txt thô trước khi được phân tich, sau đó chuyển đổi thành các phần tử trong danh sách Menu.
Menu = []  # list rỗng để lưu trữ các mục menu sau khi chúng được phân tích từ Rawmenu. Mỗi mục trong Menu là một namedtuple menu chứa tên file và size file
NumberOfFile: int
ClientRequest: list

#kết nối 2 máy
def initServer():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    hostname = socket.gethostname()
    dns_resolved_addr = socket.gethostbyname(hostname)
    print("Server IP Address: ", dns_resolved_addr)
    print("Server is listening on port 12345...")
    s.bind(('0.0.0.0', 12345))  # listen trên tất cả các địa chỉ IP
    s.listen(100)
    return s

#Phân tích chuỗi menu, lấy kích thước của từng tệp tin và thêm vào danh sách Menu.
def takeMenu(Rawmenu):
    for i in range(0, len(Rawmenu.split()), 2): #split() sẽ tách chuỗi Rawmenu thành danh sách các từ theo các space
        size = 0
        f = open(Rawmenu.split()[i], "rb") #Mở từng file txt r đọc file bin để lấy file size của mỗi file 
        f.seek(0, 2)  # di chuyển con trỏ tới cuối file
        size = f.tell()  # lấy kích thước của tệp tin.
        f.close()
        # Tạo một namedtuple menu với tên file và kích thước của nó, sau đó thêm vào danh sách Menu
        Menu.append(menu(Rawmenu.split()[i], size))
    Menu.sort(key=lambda x: x.name)  # sort Menu_List

#Đọc nội dung của menu từ file file.txt và trả về dưới dạng chuỗi.
def getRawMenu():
    with open("file.txt") as f:
        return f.read()

# Gửi danh sách các file (tên và kích thước) tới client.
def sendMenu(conn, Menu):
    # gửi số lượng file trong menu
    NumberOfFile = len(Menu)
    conn.sendall(NumberOfFile.to_bytes(4, byteorder='big'))  # gửi số lượng file trong menu
    #gửi từng mục trong menu
    for item in Menu:
        name_bytes = item.name.encode('utf-8')
        conn.sendall(len(name_bytes).to_bytes(4, byteorder='big'))  # gửi độ dài của tên file
        conn.sendall(name_bytes)  # gửi tên file
        conn.sendall(item.size.to_bytes(4, byteorder='big'))  # gửi kích thước file

#tìm file theo tên trong Menu
def binarySearch(Menu, key):
    left = 0
    right = len(Menu) - 1
    while left <= right:
        mid = (left + right) // 2
        if Menu[mid].name == key:
            return mid
        elif Menu[mid].name > key:
            right = mid - 1
        else:
            left = mid + 1
    return -1

#Kiểm tra xem yêu cầu đã tồn tại trong danh sách yêu cầu trước đó chưa.
def checkPrevious(preRequest, request):
    return request in preRequest

#Xử lý yêu cầu từ client, kiểm tra và thêm vào danh sách yêu cầu nếu hợp lệ, sau đó gửi phản hồi tới client.
def handleClientRequest(str_data, clientRequest, Menu, conn):
    msg = []  #Danh sách để lưu trữ các tin nhắn phản hồi mà sẽ được gửi lại cho client.
    for i in range(0, len(str_data.split()), 2):
        index = binarySearch(Menu, str_data.split()[i])
        reply = str_data.split()[i]  # bắt đầu tạo tin nhắn phản hồi với tên của mục mà client yêu cầu.
        if index != -1:
            tmp = Request(str_data.split()[i], Menu[index].size, str_data.split()[i + 1])
            if not checkPrevious(clientRequest, tmp):  # check xem có tồn tại hay không
                clientRequest.append(tmp)  # nếu chưa tồn tại, thêm yêu cầu này vào clientRequest.
                reply = reply + " IS AVAILABLE in the menu!"
            else:
                reply = reply + " IS ALREADY REQUESTED!"
        else:
            reply = reply + " DOESN'T EXIST!!!"
        msg.append(reply)
    conn.sendall(bytes('\n'.join(msg) + '\n', "utf8"))  # gửi phản hồi đến client
    #'\n'.join(msg): Nối tất cả các tin nhắn trong msg thành một chuỗi duy nhất, với mỗi tin nhắn trên một dòng mới.
    return clientRequest

#nhận toàn bộ data từ socket, Đảm bảo rằng tất cả dữ liệu có độ dài length đều được nhận.
def recv_all(sock, length):
    data = b''
    #Vòng lặp để nhận dữ liệu cho đến khi đạt đủ số lượng byte yêu cầu
    while len(data) < length:
        more = sock.recv(length - len(data))
        if not more:
            raise EOFError('Was expecting %d bytes but only received %d bytes before the socket closed' % (length, len(data)))
            #Nếu điều này xảy ra, một ngoại lệ EOFError sẽ được ném ra với thông báo rằng bạn đang kỳ vọng nhận về length byte 
            #nhưng chỉ nhận được len(data) byte trước khi socket đóng.
        data += more
    return data

#Xử lý kết nối và yêu cầu của từng client (gửi danh sách menu, nhận yêu cầu và gửi dữ liệu file tới client.)
def process(conn, addr, count, Menu):
    try:
        print("Client",count, "CONNECTED")
        print('Connected by', addr)
        sendMenu(conn, Menu)
        while True:
            #nhận tên file yêu cầu từ client (input.txt)
            name_length = int.from_bytes(recv_all(conn, 4), byteorder='big') #nhận độ dài của tên file (4 byte)
            name = recv_all(conn, name_length).decode('utf-8') #Nhận tên file tương ứng với độ dài đã nhận.

            # client ko gửi tín hiệu cho server để server thông báo
            if name == "DONE":
                print("Client has finished downloading all files.")
                break

             # nhận độ ưu tiên từ client        
            priority_length = int.from_bytes(recv_all(conn, 4), byteorder='big')  #Nhận độ dài của chuỗi priority (4 byte).
            priority = recv_all(conn, priority_length).decode('utf-8') #Nhận chuỗi priority tương ứng với độ dài đã nhận.
            #nhận kích thước hiện tại của file từ client (4 byte)
            cur_size = int.from_bytes(recv_all(conn, 4), byteorder='big')

           #đặt độ ưu tiên rồi truyền data theo tốc độ đó
            if priority == "CRITICAL":
                prio = 10000
            elif priority == "HIGH":
                prio = 4000
            else:
                prio = 1000

            f = open(name, "rb")
            f.seek(cur_size) #Di chuyển con trỏ file đến vị trí cur_size (vị trí mà client muốn tiếp tục đọc từ đó).
            data = f.read(1024 * prio)  #số byte đọc tùy thuộc vào độ ưu tiên

            #Gửi dữ liệu vừa đọc từ file đến client qua socket.
            conn.sendall(data) 
            f.close()
    except KeyboardInterrupt and ConnectionResetError:
        print("CLIENT",count, "DISCONNECTED")
        count[0] -= 1   #giảm số lượng client kết nối 
    finally:
        conn.close()
        return

def main():
    s = initServer()
    print("Waiting for Client !!!")
    Rawmenu = getRawMenu()
    takeMenu(Rawmenu)
    print("Menu List: ", Menu)
    clients = [] #chứa các client
    i = 0

    #đảm bảo rằng server liên tục lắng nghe và xử lý các kết nối từ client. Server chỉ ngừng hoạt động khi bị tắt thủ công.
    while True:
        conn, addr = s.accept()
        #tạo thread để xử lí kết nối client bằng cách gọi hàm process; len(clients) + 1: STT client
        clients.append(threading.Thread(target=process, args=(conn, addr, len(clients) + 1, Menu), daemon=True))
        #sau khi thêm vào client list --> khởi tạo process để xử lí yêu cầu
        clients[i].start()
        i += 1

main()


# 1. Khởi tạo và thiết lập server
# Khởi tạo một server socket và lắng nghe kết nối từ các client.
# Hiển thị địa chỉ IP của server để các client có thể kết nối.
# 2. Quản lý menu của các tệp tin
# Đọc menu từ file (file.txt) để lấy danh sách các tệp tin cần chia sẻ.
# Phân tích và sắp xếp menu theo tên tệp tin.
# 3. Xử lý kết nối từ client
# Chấp nhận kết nối từ client và tạo một luồng (thread) để xử lý từng kết nối riêng biệt.
# Gửi danh sách menu tới client khi kết nối được thiết lập.
# Nhận yêu cầu từ client, kiểm tra yêu cầu có hợp lệ không và gửi dữ liệu tệp tin tương ứng.
# 4. Xử lý và gửi dữ liệu tệp tin
# Nhận yêu cầu tệp tin từ client và kiểm tra xem tệp tin có tồn tại trong menu hay không.
# Gửi dữ liệu tệp tin tới client dựa trên yêu cầu và mức độ ưu tiên