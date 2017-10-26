import hashlib
import os
import sys
import pickle
import random
import math
import time
import socket
from threading import Thread
from enum import Enum

RECV_BUFFER_SIZE = 1024  # Const receive buffer size for socket


class Opcodes(Enum):
    PEER_UPDATE = 0
    REQUEST_CHUNK = 1


class FileData:  # Stores file metadata
    filename = ""
    numChunks = 0
    chunkSize = 1
    checkSums = []
    trackerIP = ""
    downloadFolder = ""
fileData = FileData()

peerInfo = {
    # peer IP : chunkAvail
    # including host itself
}
peerList = [
    #{
    #   "IP" : <peerIP1>,
    #   "chunkID" : <chunkID>
    #}
]
chunkAvail = [False, False, False] # python bitarray
isHost = False

# IP stuff
IP = "127.0.0.1"
listenPort = 5000
trackerPort = 5001

# PEER_UPDATE
'''
Sample:
{
    "opcode" : 1,
    "IP" : <Public IP>,
    "chunkAvail" : <chunkAvail>
}
'''
# TRACKER_RESPONSE
'''
Sample:
{
    "opcode" : 2,
    "peers" : [
        {
            "IP" : <peerIP1>,
            "chunkID" : <chunkID>
        }, # do one chunk per peer first
        {
            "IP" : <peerIP2>,
            "chunkID" : <chunkID>
        },
    ]
}
'''
# REQUEST_CHUNK
'''
Sample:
{
    "opcode" : 3,
    "chunkID" : <chunkID>
}
'''
# CHUNK_DATA
'''
Sample:
{
    "data" : <byte array data>
}
'''


def getPublicIP():
    return "127.0.0.1"


def initMetadata(filePath):
    # read all this from filepath
    in_file = open(filePath, "r")  # opening for [r]eading
    data = in_file.read()  # read and store as string
    in_file.close()  # closing file
    fileData.filename, numChunks, chunkSize, checkSums = data.split()  # split by " "
    fileData.numChunks = int(numChunks)
    fileData.chunkSize = int(chunkSize)
    fileData.checkSums = checkSums.split(",")  # split by ","
    return


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
    for data in iter(lambda: in_file.read(chunkSize), ""):    # Create file chunks
        out_file = open(filePath + "-" + str(i) + ".part", "w")  # a1.txt -> out/a1.txt-0.part out/a1.txt-1.part
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
    out_file = open(filePath + ".metadata", "w")  # open for [w]riting
    out_file.write(filePath + " ")
    out_file.write(str(numChunks) + " ")
    out_file.write(str(chunkSize) + " ")
    for i in range(0, numChunks):
        if i < numChunks:
            out_file.write(getChecksum(getChunkPath(folderPath, filePath, i)) + ",")
        else:
            out_file.write(getChecksum(getChunkPath(folderPath, filePath, i)))
    out_file.close()


def tryReassemble():
    # reassemble chunks into file
    for hasChunk in checkAvail():
        if not hasChunk:
            return False

    out_file = open(fileData.downloadFolder + "/" + fileData.filename, "w")
    for i in range(0, fileData.numChunks):
        in_file = open(getChunkPath(fileData.downloadFolder, fileData.filename, i), "r")
        out_file.write(in_file.read())
        in_file.close()
    out_file.close()

    return True


def checkAvail():
    # looks in the folder for chunks
    # filename = test.txt
    # folderPath = out
    # checksums = ["ansnns", "jsak111", "3jjwn"]

    checkAvailArr = []
    for i in range(0, fileData.numChunks):
        chunkPath = getChunkPath(fileData.downloadFolder, fileData.filename, i)
        if not os.path.exists(chunkPath):
            checkAvailArr.append(False)
        else:
            checkAvailArr.append(fileData.checkSums[i] == getChecksum(chunkPath))
    return checkAvailArr


# Returns a file path given the download folder, the file name, and the chunk ID.
def getChunkPath(downloadFolder, fileName, chunkID):
    return os.getcwd() + "/" + downloadFolder + "/" + fileName + "-" + str(chunkID) + ".part"


def loadChunk(chunkID):
    filepath = getChunkPath(fileData.downloadFolder, fileData.filename, chunkID) # loads file #chunkID from the file path
    in_file = open(filepath, "r")  # opening for [r]eading
    data = in_file.read()  # if you only wanted to read 512 bytes, do .read(512)  # returns a byte string
    in_file.close()
    return data


def saveData(chunkID, data):
    print("Saving data to " + getChunkPath(fileData.downloadFolder, fileData.filename, chunkID))
    with open(getChunkPath(fileData.downloadFolder, fileData.filename, chunkID), 'w') as output:
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
    while True:
        if len(peerList) == 0:

            # Temporary code to stop the program from sending indefinitely
            chunkAvail = checkAvail()
            if tryReassemble():
                print("Reassembly successful.")
                exit()

            # 1. PEER: Send Peer Update to Host
            print("Peer list empty, send peer update to tracker")
            packet = {
                "opcode": Opcodes.PEER_UPDATE,
                "IP": IP,
                "chunkAvail": chunkAvail
            }
            try:
                response = sendPacket(fileData.trackerIP, trackerPort, packet)
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
                "opcode" : Opcodes.REQUEST_CHUNK,
                "chunkID" : peer["chunkID"]
            }

            print("Requesting chunk " + str(peer["chunkID"]) + " from " + peer["IP"])

            if peer["IP"] == "tracker":
                peer["IP"] = fileData.trackerIP

            response = sendPacket(peer["IP"], trackerPort, packet)
            data = response["data"]
            saveData(peer["chunkID"], data)
            chunkAvail[peer["chunkID"]] = True


# Listen Thread
def listenThread(IP, port):
    receiveSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    receiveSocket.bind((IP, port))
    receiveSocket.listen(1)
    print("Listening on " + str(IP) + " " + str(port))
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

        for i in range(0, len(packet["chunkAvail"])):
            if not packet["chunkAvail"][i]:
                for ip, chunks in peerInfo.items():
                    if chunks[i]:
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
        print("Received request for chunk " + str(chunkID) + " from " + conn.getpeername()[0])

        dataResponse = {
            "data": loadChunk(chunkID)
        }

        packet = pickle.dumps(dataResponse)
        conn.send(packet)
        return


def printUsageAndExit():
    print("Usage:")
    print("Generate metadata: ./p2p init <folder_path> <file> <chunk_size>")
    print("Host: ./p2p host <metadata_file> <download_folder>")
    print("Peer: ./p2p peer <metadata_file> <download_folder> <tracker_IP>")
    exit()

if len(sys.argv) < 2:
    printUsageAndExit()

command = sys.argv[1]

if command == "init" and len(sys.argv) >= 5:
    generateMetaData(sys.argv[2], sys.argv[3], int(sys.argv[4]))
    exit()
elif command == "host" and len(sys.argv) >= 4:
    initMetadata(sys.argv[2])
    fileData.downloadFolder = sys.argv[3]
    fileData.trackerIP = getPublicIP()
    isHost = True
elif command == "peer" and len(sys.argv) >= 5:
    initMetadata(sys.argv[2])
    fileData.downloadFolder = sys.argv[3]
    fileData.trackerIP = sys.argv[4]
else:
    printUsageAndExit()

chunkAvail = checkAvail()
print("Chunk avail: " + str(chunkAvail))
IP = getPublicIP()

print("File name " + fileData.filename)

if not isHost:
    Thread(target=sendThread, args=()).start()
else:
    peerInfo["tracker"] = chunkAvail # host inserts itself into peer list
    listenPort = trackerPort
Thread(target=listenThread, args=(IP, listenPort)).start()