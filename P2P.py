import hashlib
import os
import sys
import pickle
import random
import math
import time
import socket
import requests
import re
import glob
import _thread
from threading import Thread
from socketserver import ThreadingMixIn
from enum import Enum
from os import walk
from threading import Timer


RECV_BUFFER_SIZE = 1024  # Const receive buffer size for socket


class Opcodes(Enum):
    PEER_UPDATE = 0
    REQUEST_CHUNK = 1
    FILE_LIST = 2
    QUERY_FILE = 3
    POST_FILE = 4
    UPDATE_AVAIL = 5
    SAVE_CHUNK = 6


class FileData:  # Stores file metadata
    filename = ""
    numChunks = 0
    chunkSize = 1
    checkSums = []

metadataFolder = ""
downloadFolder = ""
fileData = {}
chunkAvail = {}
isHost = False
threads = []
ipPortMap = {}

# IP stuff
IP = "127.0.0.1"
trackerIP = "127.0.0.1"
listenPort = 5000
trackerPort = 5001
need = None
busy = False
sockets = {}
hostSockIP = None

peerInfo = {
    # (ip-port) : {file : [chunkAvail]}
    # including host itself
}
peerList = [
    #{
    #   "IP" : <peerIP1>,
    #   "chunkID" : <chunkID>
    #}
]


class ClientThread(Thread):  # Setup client threat
    def __init__(self, ip, port, conn):
        Thread.__init__(self)
        self.ip = ip
        self.port = port
        self.conn = conn
        ipPortMap[ip] = str(port)
        print("\nNew thread started - " + ip + ":" + str(port) + "\n")

    def run(self):
        try:
            while True:
                packet = pickle.loads(self.conn.recv(RECV_BUFFER_SIZE))
                print("Receive packet: \n" + str(packet) + "\n")
                handlePacket(self.conn, packet)
        except Exception as e:
            print(e)
            print("Closed\n")


def getPublicIP():
    #return "127.0.0.1"
    response = requests.get('http://checkip.dyndns.org/')
    m = re.findall('[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}', str(response.content))
    print(m[0])
    return m[0]


'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
'                                                                           '
'This part is for chunking data & create metadata file between Host and Peer'
'                                                                           '
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
def initMetadata(filePath):
    # read all this from filepath
    fd = FileData()
    in_file = open(filePath, "r")  # opening for [r]eading
    data = in_file.read()  # read and store as string
    in_file.close()  # closing file
    fd.filename, numChunks, chunkSize, checkSums = data.split()  # split by " "
    fd.numChunks = int(numChunks)
    fd.chunkSize = int(chunkSize)
    fd.checkSums = checkSums.split(",")  # split by ","
    return fd


def getChecksum(filePath):
    return hashlib.md5(open(filePath, 'rb').read()).hexdigest()


def chunk(folderPath, filePath, chunkSize):
    # chunkSize in bytes
    in_file = open(filePath, "r")  # opening for [r]eading
    i = 0
    owd = os.getcwd()
    if not os.path.exists(folderPath):
        os.mkdir(folderPath)
    os.chdir(folderPath)
    if not os.path.exists("chunk"):
        os.mkdir("chunk")
    for data in iter(lambda: in_file.read(chunkSize), ""):    # Create file chunks
        out_file = open("chunk/" + filePath + "-" + str(i) + ".part", "w")  # a1.txt -> out/a1.txt-0.part out/a1.txt-1.part
        out_file.write(data)
        out_file.close()
        i += 1
    os.chdir(owd)
    in_file.close()
    return


def generateMetaData(folderPath, filePath, chunkSize):  # Write to file metadata
    filesize = os.path.getsize(filePath)
    numChunks = int(math.ceil(filesize * 1.0 / chunkSize))
    chunk(folderPath, filePath, chunkSize)

    metadataPath = metadataFolder + "/" + filePath + ".metadata"
    out_file = open(metadataPath, "w")  # open for [w]riting
    out_file.write(filePath + " ")
    out_file.write(str(numChunks) + " ")
    out_file.write(str(chunkSize) + " ")
    for i in range(0, numChunks):
        if i < numChunks:
            out_file.write(getChecksum(getChunkPath(folderPath, filePath, i)) + ",")
        else:
            out_file.write(getChecksum(getChunkPath(folderPath, filePath, i)))
    out_file.close()
    return metadataPath


def tryReassemble(fd):  # reassemble chunks into file
    for hasChunk in checkAvail(fd):
        if not hasChunk:
            return False

    out_file = open(downloadFolder + "/" + fd.filename, "w")
    for i in range(0, fd.numChunks):
        in_file = open(getChunkPath(downloadFolder, fd.filename, i), "r")
        out_file.write(in_file.read())
        in_file.close()
    out_file.close()
    return True


def checkAvail(fd):  # looks in the folder for chunks
    checkAvailArr = []
    for i in range(0, fd.numChunks):
        chunkPath = getChunkPath(downloadFolder, fd.filename, i)
        if not os.path.exists(chunkPath):
            checkAvailArr.append(False)
        else:
            checkAvailArr.append(fd.checkSums[i] == getChecksum(chunkPath))
    return checkAvailArr


# Returns a file path given the download folder, the file name, and the chunk ID.
def getChunkPath(downloadFolder, fileName, chunkID):
    return os.getcwd() + "/" + downloadFolder + "/chunk/" + fileName + "-" + str(chunkID) + ".part"


def loadChunk(fd, chunkID): # loads file #chunkID from the file path
    filepath = getChunkPath(downloadFolder, fd.filename, chunkID)
    in_file = open(filepath, "r")  # opening for [r]eading
    data = in_file.read()  # if you only wanted to read 512 bytes, do .read(512)  # returns a byte string
    in_file.close()
    return data


def loadMetadata(filename):  # load metadata file
    filepath = os.getcwd() + "/" + metadataFolder + "/" + filename + ".metadata"
    in_file = open(filepath, "r")  # opening for [r]eading
    data = in_file.read()
    in_file.close()
    return data


def saveData(fd, chunkID, data):  # saving data to download folder
    print("Saving data to " + getChunkPath(downloadFolder, fd.filename, chunkID))
    if not os.path.exists(downloadFolder):
        os.mkdir(downloadFolder)
    if not os.path.exists(downloadFolder + "/chunk"):
        os.mkdir(downloadFolder + "/chunk")
    with open(getChunkPath(downloadFolder, fd.filename, chunkID), 'w') as output:
        output.write(data)


def saveMetadata(filename, data):  # saving data to metadata folder
   print("Saving metadata file to folder " + metadataFolder)
   if not os.path.exists(metadataFolder):
        os.mkdir(metadataFolder)
   finalPath = os.getcwd() + "/" + metadataFolder + "/" + filename + ".metadata"
   with open(finalPath, 'w') as output:
        output.write(data)
   return finalPath


'''''''''''''''''''''''''''''''''''''''''''''''''''''''''
'                                                       '
'This part is for sending packet between Host and Peer  '
'                                                       '
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''
# Sends an arbitrary packet to IP/port and receives a response
def sendPacketToSocket(receiver, packet, response = True):
    print("Sending packet to socket")
    sendData = pickle.dumps(packet)
    receiver.send(sendData)
    if response:
        recvData = pickle.loads(receiver.recv(RECV_BUFFER_SIZE))
        print("Response: " + str(recvData))
        return recvData
    return None


# Sends an arbitrary packet to IP/port and receives a response
def sendPacket(IP, port, packet, response = True):
    receiver = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    receiver.connect((IP, port))
    print("Sending packet to " + str(IP) + " " + str(port))
    sendData = pickle.dumps(packet)
    receiver.send(sendData)
    if response:
        recvData = pickle.loads(receiver.recv(RECV_BUFFER_SIZE))
        print("Response: " + str(recvData))
        receiver.close()
        return recvData
    return None


def sendThread(): # Send Thread
    global peerList
    global chunkAvail
    global need
    global busy
    while True:
        if busy or need is None:
            time.sleep(1)
            continue
        print("try")
        if len(peerList) == 0:

            # Temporary code to stop the program from sending indefinitely
            chunkAvail = checkAvail(need)

            # 1. PEER: Send Peer Update to Host
            print("\nPeer list empty, send peer update to tracker")
            packet = {
                "opcode": Opcodes.PEER_UPDATE,
                "IP": IP,
                "need": need.filename,
                "chunkAvail": chunkAvail,
                "sockIP": hostSockIP
            }
            try:
                response = sendPacket(trackerIP, trackerPort, packet)
                peerList = response["peers"]
            except:
                print("\nTimeout on SEND_PEER_UPDATE")

            if tryReassemble(need):
                print("\nReassembly successful.")
                need = None
        else:
            print("\nSend peer request")
            print("Peer list: " + str(peerList) + "\n")

            # 7. Send peer request to first IP in peerList
            # Remove very first peer
            peer = peerList.pop(0)

            packet = {
                "need": need.filename,
                "opcode" : Opcodes.REQUEST_CHUNK,
                "chunkID" : peer["chunkID"],
                "IP": peer["IP"],
                "sockIP": hostSockIP
            }

            print("\nRequesting chunk " + str(peer["chunkID"]) + " from " + str(peer["IP"]) + "\n")

            try:
                busy = True
                sendPacket(trackerIP, trackerPort, packet, False)
            except:
                print(str(peer["IP"]) + " not available\n")
                peerList = list(filter(lambda p: p["IP"] != peer["IP"], peerList))


'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
'                                                             '
'This part is for setting up connection between Host and Peer '
'                                                             '
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
def peerListen(IP, port):  # setup peer to host connection
    global sockets
    global hostSockIP
    hostConn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print("\nAttempting to connect to " + str(IP) + " " + str(port))
    hostConn.connect((IP, port))
    sockets[(IP, port)] = hostConn
    packet = {
        "opcode": Opcodes.UPDATE_AVAIL,
        "avail": chunkAvail,
        "persist" : True
    }
    response = sendPacketToSocket(hostConn, packet)
    hostSockIP = response["sockIP"]
    print("My IP: " + str(hostSockIP))
    print("Connection successful. Loading Commands Menu...")
    while True:
        packet = pickle.loads(hostConn.recv(RECV_BUFFER_SIZE))
        print("\nReceive packet: \n" + str(packet))
        handlePacket(hostConn, packet)


def hostListen(IP, port):  # Listen Thread
    receiveSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    receiveSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    receiveSocket.bind((IP, port))
    receiveSocket.listen(8)
    print("Listening on host IP" + str(IP) + " " + str(port))
    while True:  # receive packet
        (conn, (addr, port)) = receiveSocket.accept()
        clientThread = ClientThread(addr, port, conn)
        clientThread.start()
        threads.append(clientThread)


def handlePacket(conn, packet):  # Called by listenThread when a packet is received
    global sockets
    global need
    global busy
    if isHost and packet["opcode"] == Opcodes.PEER_UPDATE:  # Handle peer update
        # 2. HOST: Host receives PEER_UPDATE
        # 3. HOST: Update peer info database
        peerIp = packet["sockIP"]
        if peerIp not in peerInfo:
            peerInfo[peerIp] = {}
        peerInfo[peerIp][packet["need"]] = packet["chunkAvail"]
        print("\nReceived peer update request from " + str(conn.getpeername()))

        # 4. HOST: Look for chunks for peer
        peers = []
        peerInfoList = list(peerInfo.items())
        need = packet["need"]
        for i in range(0, len(packet["chunkAvail"])):
            if not packet["chunkAvail"][i]:
                random.shuffle(peerInfoList)  # to ensure that the tracker is not always the first in the list
                for ip, peerFiles in peerInfoList:
                    if need in peerFiles and peerFiles[need][i]:
                        hasChunk = {"IP": ip, "chunkID": i}
                        peers.append(hasChunk)
                        break

        print(peers)
        print(peerInfo)
        trackerResponse = { "peers" : peers }
        # 5. HOST: Send Tracker response
        packet = pickle.dumps(trackerResponse)
        conn.send(packet)
        return
    elif packet["opcode"] == Opcodes.REQUEST_CHUNK:  # Handle request chunk
        # 8. PEER: Receive chunk request
        # 9. PEER: Send chunk
        chunkID = packet["chunkID"]
        filename = packet["need"]
        ip = packet["IP"]
        sockIp = packet["sockIP"]
        print("\nReceived request for chunk " + str(chunkID) + " from " + str(conn.getpeername()) + " IP " + str(ip))

        if isHost and ip != "tracker":
            sendPacketToSocket(sockets[ip], packet, False)
        else:
            dataResponse = {
                "opcode": Opcodes.SAVE_CHUNK,
                "data": loadChunk(fileData[filename], chunkID),
                "chunkID": chunkID,
                "sockIP": sockIp
            }
            if isHost:
                sendPacketToSocket(sockets[sockIp], dataResponse, False)
            else:
                packet = pickle.dumps(trackerResponse)
                conn.send(dataResponse)
    elif packet["opcode"] == Opcodes.SAVE_CHUNK:  # Handle save chunks
        if isHost:
            sockIp = packet["sockIP"]
            sendPacketToSocket(sockets[sockIp], packet, False)
        else:
            data = packet["data"]
            saveData(need, packet["chunkID"], data)
            chunkAvail[packet["chunkID"]] = True
            busy = False
    elif packet["opcode"] == Opcodes.QUERY_FILE:  # Handle query file
        want = packet["want"]
        print("\nReceived query for file " + want + " from " + str(conn.getpeername()))
        dataResponse = {
            "data": loadMetadata(want)
        }
        packet = pickle.dumps(dataResponse)
        conn.send(packet)
        return
    elif packet["opcode"] == Opcodes.FILE_LIST:  # Handle get file list
        dataResponse = {
            "filelist": fileList()
        }
        packet = pickle.dumps(dataResponse)
        conn.send(packet)
        print(peerInfo)
        return
    elif packet["opcode"] == Opcodes.POST_FILE:  # Handle post file to host
        peerIp = conn.getpeername()
        if peerIp not in peerInfo:
            peerInfo[peerIp] = {}
        peerInfo[peerIp][packet["filename"]] = packet["chunkAvail"]
        metadataPath = saveMetadata(packet["filename"], packet["metadata"])
        fileData[packet["filename"]] = initMetadata(metadataPath)
        trackerResponse = {}
        # 5. HOST: Send Tracker response
        packet = pickle.dumps(trackerResponse)
        conn.send(packet)
        print("Done")
        return
    elif packet["opcode"] == Opcodes.UPDATE_AVAIL:  # Handle update avail peerIP
        peerIp = conn.getpeername()
        if peerIp not in peerInfo:
            peerInfo[peerIp] = {}
        peerInfo[peerIp] = packet["avail"]
        print(peerInfo)
        trackerResponse = {
            "sockIP" : peerIp
        }
        # 5. HOST: Send Tracker response
        packet = pickle.dumps(trackerResponse)
        conn.send(packet)
        sockets[peerIp] = conn
        print(str(sockets))
        return

'''''''''''''''''''''''''''''''''''''''''''''''
'                                             '
'This part is for reading and process commands'
'                                             '
'''''''''''''''''''''''''''''''''''''''''''''''
def fileList():  # get all file names in the folder
    f = []
    for (dirpath, dirnames, filenames) in walk(metadataFolder):
        f.extend(filenames)
        break
    return f


def printUsageAndExit():
    print("Usage:")
    print("Host: ./p2p host <metadata_folder> <download_folder>")
    print("Peer: ./p2p peer <metadata_folder> <download_folder> <tracker_IP>")
    print("Generate metadata & chunk: ./p2p init <metadata_folder> <file_folder_path> <file> <chunk_size>")
    exit()


if len(sys.argv) < 2:
    printUsageAndExit()

command = sys.argv[1]


def initialiseFolders():
    global metadataFolder
    global downloadFolder
    global fileData
    global chunkAvail

    metadataFolder = sys.argv[2]
    downloadFolder = sys.argv[3]
    for file in glob.glob(os.getcwd() + "/" + metadataFolder + "/*.metadata"):
        fd = initMetadata(file)
        fileData[fd.filename] = fd

    for file in fileData:
        chunkAvail[file] = checkAvail(fileData[file])

# Reading command: for host or for peer
if command == "host" and len(sys.argv) >= 2:
    # initMetadata(sys.argv[2])
    # downloadFolder = sys.argv[3]
    # trackerIP = getPublicIP()
    isHost = True
    initialiseFolders()

    print("\nChunk avail: " + str(chunkAvail) + "\n")
elif command == "peer" and len(sys.argv) >= 5:
    # downloadFolder = sys.argv[3]
    trackerIP = sys.argv[4]
    initialiseFolders()

elif command == "init" and len(sys.argv) >= 6:
    filePath = sys.argv[4]
    metadataFolder = sys.argv[2]
    metadataPath = generateMetaData(sys.argv[3], filePath, int(sys.argv[5]))
    exit()
else:
    printUsageAndExit()


IP = getPublicIP()


def printCommands():  # Command Menu
    print("\nCommands Menu: ")
    print("1. Initialise metadata file & chunk file: [init <file name> <chunk size>]")
    print("2. Query the centralised server for list of files available: [files]")
    print("3. Query centalised server for a specific file: [query <file name>]")
    print("4. Download a file by specifying the filename: [download <file name>]")
    print("5. Send metadata file: [post <file name>]")
    print("6. Exit the program: [exit]")


def readCommands():  # read and process commands
    global need
    while (1):
        printCommands()
        cmd = input('\n>Enter Command: ').split(' ')

        if cmd[0] == "init" and len(cmd) >= 3:
            filePath = cmd[1]
            chunkSize = int(cmd[2])
            metadataPath = generateMetaData(downloadFolder, filePath, chunkSize)
            fileData[filePath] = initMetadata(metadataPath)
            pass
        elif cmd[0] == "files":
            packet = {
                "opcode": Opcodes.FILE_LIST
            }
            response = sendPacket(trackerIP, trackerPort, packet)
            for file in response["filelist"]:
                print(file)
        elif cmd[0] == "query" and len(cmd) >= 2:
            filename = cmd[1]
            packet = {
                "opcode": Opcodes.QUERY_FILE,
                "want": filename
            }
            response = sendPacket(trackerIP, trackerPort, packet)
            metadataPath = saveMetadata(filename, response["data"])
            fileData[filename] = initMetadata(metadataPath)
        elif cmd[0] == "download" and len(cmd) >= 2:
            filePath = cmd[1]
            if filePath not in fileData:
                print("Couldn't find metadata. Use query command to retrieve it from server.")
                continue
            print("Downloading...")
            need = fileData[filePath]
        elif cmd[0] == "post" and len(cmd) >= 2:
            filePath = cmd[1]
            if filePath not in fileData:
                print("Couldn't find metadata.")
                continue
            print("Done")
            packet = {
                "opcode": Opcodes.POST_FILE,
                "IP": IP,
                "filename": fileData[filePath].filename,
                "chunkAvail": checkAvail(fileData[filePath]),
                "metadata": loadMetadata(fileData[filePath].filename)
            }
            response = sendPacket(trackerIP, trackerPort, packet)
        elif cmd[0] == "exit":
            print("Exiting...")
            sys.exit()
        else:
            print("Error: Please enter a valid command...")

if not isHost:  # setting up connection for peer
    Thread(target=sendThread, args=()).start()
    Thread(target=peerListen, args=(trackerIP, trackerPort)).start()
    t = Timer(1.5, readCommands)
    t.start()

else:  # setting up connection for host
    peerInfo["tracker"] = chunkAvail # host inserts itself into peer list
    Thread(target=hostListen, args=(IP, trackerPort)).start()