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
from threading import Thread
from enum import Enum
from os import walk

RECV_BUFFER_SIZE = 1024  # Const receive buffer size for socket


class Opcodes(Enum):
    PEER_UPDATE = 0
    REQUEST_CHUNK = 1
    FILE_LIST = 2

metadataFolder = ""
downloadFolder = ""
class FileData:  # Stores file metadata
    filename = ""
    numChunks = 0
    chunkSize = 1
    checkSums = []
fileData = {}

peerInfo = {
    # ip : {file : [chunkAvail]}
    # including host itself
}
peerList = [
    #{
    #   "IP" : <peerIP1>,
    #   "chunkID" : <chunkID>
    #}
]
chunkAvail = {}
isHost = False

# IP stuff
IP = "127.0.0.1"
trackerIP = "127.0.0.1"
listenPort = 5000
trackerPort = 5001


def getPublicIP():
    return "127.0.0.1"
    '''
    response = requests.get('http://checkip.dyndns.org/')
    m = re.findall('[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}', str(response.content))
    print(m[0])
    return m[0]
    '''


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


def generateMetaData(folderPath, filePath, chunkSize):
    filesize = os.path.getsize(filePath)
    numChunks = int(math.ceil(filesize * 1.0 / chunkSize))
    chunk(folderPath, filePath, chunkSize)

    # Write to file matadata
    out_file = open(metadataFolder + "/" + filePath + ".metadata", "w")  # open for [w]riting
    out_file.write(filePath + " ")
    out_file.write(str(numChunks) + " ")
    out_file.write(str(chunkSize) + " ")
    for i in range(0, numChunks):
        if i < numChunks:
            out_file.write(getChecksum(getChunkPath(folderPath, filePath, i)) + ",")
        else:
            out_file.write(getChecksum(getChunkPath(folderPath, filePath, i)))
    out_file.close()


def tryReassemble(fd):
    # reassemble chunks into file
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


def checkAvail(fd):
    # looks in the folder for chunks
    # filename = test.txt
    # folderPath = out
    # checksums = ["ansnns", "jsak111", "3jjwn"]

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


def loadChunk(fd, chunkID):
    filepath = getChunkPath(downloadFolder, fd.filename, chunkID) # loads file #chunkID from the file path
    in_file = open(filepath, "r")  # opening for [r]eading
    data = in_file.read()  # if you only wanted to read 512 bytes, do .read(512)  # returns a byte string
    in_file.close()
    return data


def saveData(fd, chunkID, data):
    print("Saving data to " + getChunkPath(downloadFolder, fd.filename, chunkID))
    if not os.path.exists(downloadFolder):
        os.mkdir(downloadFolder)
    if not os.path.exists(downloadFolder + "/chunk"):
        os.mkdir(downloadFolder + "/chunk")
    with open(getChunkPath(downloadFolder, fd.filename, chunkID), 'w') as output:
        output.write(data)


# Sends an arbitrary packet to IP/port and receives a response
def sendPacket(IP, port, packet):
    sendSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sendSocket.settimeout(5000)
    print("Sending to " + str(IP) + " " + str(port))
    sendSocket.connect((IP, port))
    sendData = pickle.dumps(packet)
    sendSocket.send(sendData)
    recvData = pickle.loads(sendSocket.recv(RECV_BUFFER_SIZE))
    sendSocket.close()
    print("Response: " + str(recvData))
    return recvData


# Send Thread
def sendThread():
    global peerList
    global chunkAvail
    need = None
    while True:
        if need is None:
            time.sleep(1)
            continue

        if len(peerList) == 0:

            # Temporary code to stop the program from sending indefinitely
            chunkAvail = checkAvail(need)
            if tryReassemble(need):
                print("Reassembly successful.")
                need = None

            # 1. PEER: Send Peer Update to Host
            print("Peer list empty, send peer update to tracker")
            packet = {
                "opcode": Opcodes.PEER_UPDATE,
                "IP": IP,
                "need": need.filename,
                "chunkAvail": chunkAvail
            }
            try:
                response = sendPacket(trackerIP, trackerPort, packet)
                peerList = response["peers"]
            except:
                print("Timeout on SEND_PEER_UPDATE")
        else:
            print("Send peer request")
            print("Peer list: " + str(peerList))

            # 7. Send peer request to first IP in peerList

            # Remove very first peer
            peer = peerList.pop(0)

            packet = {
                "need": need.filename,
                "opcode" : Opcodes.REQUEST_CHUNK,
                "chunkID" : peer["chunkID"]
            }

            print("Requesting chunk " + str(peer["chunkID"]) + " from " + peer["IP"])

            port = listenPort
            if peer["IP"] == "tracker":
                peer["IP"] = trackerIP
                port = trackerPort

            response = sendPacket(peer["IP"], port, packet)
            data = response["data"]
            saveData(need, peer["chunkID"], data)
            chunkAvail[peer["chunkID"]] = True


# Listen Thread
def listenThread(IP, port):
    receiveSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    receiveSocket.bind((IP, port))
    receiveSocket.listen(1)
    # print("Listening on " + str(IP) + " " + str(port))
    while True:
        # receive packet

        conn, addr = receiveSocket.accept()
        packet = pickle.loads(conn.recv(RECV_BUFFER_SIZE))
        print("Receive packet: " + str(packet))
        handlePacket(conn, packet)


# Called by listenThread when a packet is received
def handlePacket(conn, packet):
    if isHost and packet["opcode"] == Opcodes.PEER_UPDATE:
        # Handle peer update
        # 2. HOST: Host receives PEER_UPDATE
        # 3. HOST: Update peer info database
        peerInfo[conn.getpeername()[0]] = packet["chunkAvail"]
        print("Received peer update request from " + conn.getpeername()[0])

        # 4. HOST: Look for chunks for peer
        peers = []

        need = packet["need"]
        for i in range(0, len(packet["chunkAvail"])):
            if not packet["chunkAvail"][i]:
                for ip, peerFiles in peerInfo.items():
                    if need in peerFiles and peerFiles[need][i]:
                        hasChunk = {"IP": ip, "chunkID": i}
                        peers.append(hasChunk)
                        break;

        print(peers)
        trackerResponse = { "peers" : peers };
        # 5. HOST: Send Tracker response
        packet = pickle.dumps(trackerResponse)
        conn.send(packet)
        return
    elif packet["opcode"] == Opcodes.REQUEST_CHUNK:
        # Handle request chunk

        # 8. PEER: Receive chunk request
        # 9. PEER: Send chunk

        chunkID = packet["chunkID"]
        need = packet["need"]
        print("Received request for chunk " + str(chunkID) + " from " + conn.getpeername()[0])

        dataResponse = {
            "data": loadChunk(fileData[need], chunkID)
        }

        packet = pickle.dumps(dataResponse)
        conn.send(packet)
    elif packet["opcode"] == Opcodes.FILE_LIST:
        dataResponse = {
            "filelist": fileList()
        }
        packet = pickle.dumps(dataResponse)
        conn.send(packet)
        return


def printUsageAndExit():
    print("Usage:")
    print("Host: ./p2p host <metadata_folder> <download_folder>")
    print("Peer: ./p2p peer <metadata_folder> <download_folder> <tracker_IP>")
    exit()

if len(sys.argv) < 2:
    printUsageAndExit()

command = sys.argv[1]

#if command == "init" and len(sys.argv) >= 5:
#    generateMetaData(sys.argv[2], sys.argv[3], int(sys.argv[4]))
#    exit()
#el
if command == "host" and len(sys.argv) >= 2:
    #initMetadata(sys.argv[2])
    #downloadFolder = sys.argv[3]
    #trackerIP = getPublicIP()
    isHost = True

elif command == "peer" and len(sys.argv) >= 5:
    #fileData.downloadFolder = sys.argv[3]
    trackerIP = sys.argv[4]
else:
    printUsageAndExit()

metadataFolder = sys.argv[2]
downloadFolder = sys.argv[3]

for file in glob.glob(os.getcwd() + "/" + metadataFolder + "/*.metadata"):
    fd = initMetadata(file)
    fileData[fd.filename] = fd

for file in fileData:
    chunkAvail[file] = checkAvail(fileData[file])
print("Chunk avail: " + str(chunkAvail))
IP = getPublicIP()


if not isHost:
    Thread(target=sendThread, args=()).start()
    Thread(target=listenThread, args=(IP, listenPort)).start()
else:
    peerInfo["tracker"] = chunkAvail # host inserts itself into peer list
    Thread(target=listenThread, args=(IP, trackerPort)).start()

def fileList():
    f = []
    for (dirpath, dirnames, filenames) in walk (metadataFolder):
        f.extend(filenames)
        break
    return f

def printCommands():
    print("Commands available: ")
    print("1. Initialise Chunk size: [init <file> <chunk size>]")
    print("2. Query the centralised server for list of files available: [files]")
    print("3. Query centalised server for a specific file: [query <file path>]")
    print("4. Download a file by specifying the filaname: [download <file path> <folder>]")
    print("5. Create metadata file: [post <metadata file>]\n")

while(1):
    printCommands()
    cmd = input('Enter command: ').split(' ')

    if cmd[0] == "init" and len(cmd) >= 3:
        filePath = cmd[1]
        chunkSize = int(cmd[2])
        generateMetaData(downloadFolder, filePath, chunkSize)
        pass
    elif cmd[0] == "files":
        packet = {
            "opcode": Opcodes.FILE_LIST
        }
        response = sendPacket(trackerIP, trackerPort, packet)

        for file in response["filelist"]:
            print(file)

    elif cmd[0] == "query":
        pass
    elif cmd[0] == "download":
        pass
    elif cmd[0] == "post":
        pass
    else:
        printCommands()