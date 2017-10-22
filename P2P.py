import hashlib
import os
import sys
import pickle
import random
import time
import socket
from threading import Thread
from enum import Enum

# Const receive buffer size for socket
RECV_BUFFER_SIZE = 1024

class Opcodes(Enum):
    PEER_UPDATE = 0
    REQUEST_CHUNK = 1

# Stores file metadata
class FileData:
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
    # TODO

    # read all this from filepath
    # DUMMY VALUES
    fileData.filename = "test.txt"
    fileData.numChunks = 3
    fileData.chunkSize = 10
    fileData.checkSums = [
        "e11170b8cbd2d74102651cb967fa28e5",
        "3a08fe7b8c4da6ed09f21c3ef97efce2",
        "4aee3e28df37ea1af64bd636eca59dcb",
    ]
    return

def chunk(filePath, chunkSize):
    # TODO

    # chunkSize in bytes
    # Create file chunks
    # a1.txt -> out/a1.txt-0.part out/a1.txt-1.part
    return

def getChecksum(filePath):
    return hashlib.md5(open(filePath, 'rb').read()).hexdigest()

def generateMetaData(filePath, chunkSize):
    # TODO

    chunk(filePath, chunkSize)

    # for i in range(0, numFiles):
    #    getChecksum()
    # generate file
    return

def reassemble(metadata):
    # TODO

    # reassemble chunks into file
    return

def checkAvail(filename, folderPath, checksums):
    # TODO

    # looks in the folder for chunks
    # checks checksums
    # initialize chunkAvail

    chunkAvail = [False, False, False] #...

# Returns a file path given the download folder, the file name, and the chunk ID.
def getChunkPath(downloadFolder, fileName, chunkID):
    return os.getcwd() + "\\" + downloadFolder + "\\" + fileName + "-" + str(chunkID) + ".part"

def loadChunk(downloadFolder, fileName, chunkID):
    # TODO

    # loads file #chunkID from the file path
    # returns a byte string

    # DUMMY VALUES
    print("Loading chunk " + str(chunkID))
    return bytearray([49, 49, 49, 49, 49, 49, 49, 49, 49, 49])

def saveData(downloadFolder, fileName, chunkID, data):
    print("Saving data to " + getChunkPath(downloadFolder, fileName, chunkID))
    with open(getChunkPath(downloadFolder, fileName, chunkID), 'wb') as output:
        output.write(bytearray(data))

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
    while True:
        if len(peerList) == 0:

            # Temporary code to stop the program from sending indefinitely
            if chunkAvail[2]:
                exit()

            # 1. PEER: Send Peer Update to Host
            print("Peer list empty, send peer update to tracker")
            packet = {
                "opcode" : Opcodes.PEER_UPDATE,
                "IP" : IP,
                "chunkAvail" : chunkAvail
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

            response = sendPacket(peer["IP"], trackerPort, packet)
            data = response["data"]
            saveData(fileData.downloadFolder, fileData.filename, peer["chunkID"], data)
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
    return

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
        peerInfoList = peerInfo.items()
        # to randomized the peer being pointed to
        random.shuffle(peerInfoList)
        for i in range(0, len(packet["chunkAvail"])):
            if not packet["chunkAvail"][i]:
                for ip, chunks in peerInfoList:
                    if chunks[i]:
                        hasChunk = {"IP" : ip, "chunkID" : i}
                        peers.append(hasChunk)
                        break;

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
            "data" : loadChunk(fileData.downloadFolder, fileData.filename, chunkID)
        }

        packet = pickle.dumps(dataResponse)
        conn.send(packet)
        return

def printUsageAndExit():
    print("Usage:")
    print("Generate metadata: ./p2p init <file> <chunk_size> <target metadata_file>")
    print("Host: ./p2p host <metadata_file> <download_folder>")
    print("Peer: ./p2p peer <metadata_file> <download_folder> <tracker_IP>")
    exit()

if len(sys.argv) < 2:
    printUsageAndExit()

command = sys.argv[1]

if command == "init" and len(sys.argv) >= 5:
    exit() # TODO change this
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

checkAvail(fileData.filename, fileData.downloadFolder, fileData.checkSums)
IP = getPublicIP()
# host inserts itself into peer list
if isHost:
    peerInfo[IP] = chunkAvail

print("File name " + fileData.filename)

if not isHost:
    Thread(target=sendThread, args=()).start()
else:
    listenPort = trackerPort
Thread(target=listenThread, args=(IP, listenPort)).start()