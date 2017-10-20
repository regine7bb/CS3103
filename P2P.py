import hashlib
import os
from enum import Enum

class PeerState(Enum):
    SEND_PEER_UPDATE = 0
    WAIT_TRACKER_RESPONSE = 1
    SEND_PEER_REQUEST = 2
    WAIT_PEER_RESPONSE = 3
    REMOVE_PEER = 4

class Opcodes(Enum):
    PEER_UPDATE = 0
    TRACKER_RESPONSE = 1
    REQUEST_CHUNK = 2
    CHUNK_DATA = 3

# file metadata
class FileData:
    filename = ""
    numChunks = 0
    chunkSize = 1
    checkSums = []


peerInfo = {
    # peer IP : chunkAvail
}
chunkAvail = [True, True, False] # python bitarray
isHost = False
peerList = {
    # peer IP : chunkID
}
fileData = FileData()
peerStatus = PeerState.SEND_PEER_UPDATE

# PEER_UPDATE
'''
Sample:
{
    "opcode" : 1,
    "IP" : <Public IP>,
    "availability" : <chunkAvail>
}
'''
# TRACKER_RESPONSE
'''
Sample:
{
    "opcode" : 2,
    "peers" : {
        <peerIP1> : chunkID, # do one chunk per peer first
        <peerIP2> : chunkID
    }
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
    "opcode" : 4,
    "chunkID" : <chunkID>,
    "data" : byte[]
}
'''

def getPublicIP():
    return "127.0.0.1"

def initMetadata(filePath):
    # read all this from filepath
    # DUMMY CODE
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
    # chunkSize in bytes
    # Create file chunks
    # a1.txt -> out/a1.txt-1.part out/a1.txt-2.part
    return

def getChecksum(filePath):
    return hashlib.md5(open(filePath, 'rb').read()).hexdigest()

def generateMetaData(filePath, chunkSize):
    chunk(filePath, chunkSize)

    # for i in range(0, numFiles):
    #    getChecksum()
    # generate file
    return

def reassemble(metadata):
    # reassemble chunks into file
    return

def checkAvail(filename, folderPath, checksums):
    # looks in the folder for chunks
    # checks checksums
    # initialize chunkAvail

    chunkAvail = [True, False] #...

# Thread (async)
def sendChunk(IP, port, chunkID):
    # sends file chunkID to IP and port
    return

def sendThread(IP, port, packet):
    while True:
        if peerStatus == PeerState.SEND_PEER_UPDATE:
            # 1. PEER: Send Peer Update to Host
            peerStatus = PeerState.WAIT_TRACKER_RESPONSE
        elif peerStatus == PeerState.WAIT_TRACKER_RESPONSE:
            # Wait for tracker response
            if True:
                peerStatus = PeerState.SEND_PEER_UPDATE
        elif peerStatus == PeerState.SEND_PEER_REQUEST:

            if peerList.keys().count() == 0:
                peerStatus = PeerState.SEND_PEER_UPDATE
            else:
                # 7. Send peer request to first IP in peerList
                peerStatus = PeerState.WAIT_PEER_RESPONSE

        elif peerStatus == PeerState.WAIT_PEER_RESPONSE:
            if True:
                # Remove first IP from peer list
                peerStatus = PeerState.SEND_PEER_UPDATE
        return
    return

def listenThread(IP, port):
    while True:
        # receive packet
        handlePacket(packet)
        return
    return

# Called by listenThread when a packet is received
def handlePacket(packet):
    if isHost and packet.opcode == Opcodes.PEER_UPDATE:
        # Handle peer update

        # 2. HOST: Host receives PEER_UPDATE
        # 3. HOST: Update peer info database
        # 4. HOST: Look for chunks for peer
        # 5. HOST: Send Tracker response
        return
    elif packet.opcode == Opcodes.TRACKER_RESPONSE:
        # Handle tracker response

        peerList = packet.peers
        peerStatus = PeerState.SEND_PEER_RESPONSE
        # 6. PEER: Receive tracker response
        return
    elif packet.opcode == Opcodes.REQUEST_CHUNK:
        # Handle request chunk

        # 8. PEER: Receive chunk request
        # 9. PEER: Send chunk
        return
    elif packet.opcode == Opcodes.CHUNK_DATA:
        # Handle receive data

        # 10. PEER: Receive data from packet and save to file
        # 11. PEER: Update chunk avail
        peerStatus = PeerState.SEND_PEER_REQUEST
        return
