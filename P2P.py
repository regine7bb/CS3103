peerInfo = {
    # peer IP : chunkAvail
}
chunkAvail = [True, True, False] # python bitarray
isHost = False
peerList = {
    # peer IP : chunkID
}
peerState = {
    "SEND_PEER_UPDATE" : 0,
    "WAIT_TRACKER_RESPONSE" : 1,
    "SEND_PEER_REQUEST" : 4,
    "WAIT_PEER_RESPONSE" : 2,
    "REMOVE_PEER" : 3

}
opcodes = {
    "PEER_UPDATE" : 0,
    "TRACKER_RESPONSE" : 1,
    "REQUEST_CHUNK" : 2,
    "CHUNK_DATA" : 3
}

peerStatus = peerState.SEND_PEER_UPDATE

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
        <peerIP1> : [chunkID1, chunkID2 ...],
        <peerIP2> : [chunkID1, chunkID2 ...]
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

def chunk(filePath, chunkSize):
    # chunkSize in bytes
    # Create file chunks
    # a1.txt -> out/a1.txt-1.part out/a1.txt-2.part
    return

def getChecksum(filePath):
    # MD5 Checksum
    return "checksum"

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
        if peerStatus == peerState.SEND_PEER_UPDATE:
            # 1. PEER: Send Peer Update to Host
            peerStatus = peerState.WAIT_TRACKER_RESPONSE
        elif peerStatus == peerState.WAIT_TRACKER_RESPONSE:
            # Wait for tracker response
            if <timeout>:
                peerStatus = peerState.SEND_PEER_UPDATE
        elif peerStatus == peerState.SEND_PEER_REQUEST:

            if peerList.keys().count() == 0:
                peerStatus = peerState.SEND_PEER_UPDATE
            else:
                # 7. Send peer request to first IP in peerList
                peerStatus = peerState.WAIT_PEER_RESPONSE

        elif peerStatus == peerState.WAIT_PEER_RESPONSE:
            if <timeout>:
                # Remove first IP from peer list
                peerStatus = peerState.SEND_PEER_UPDATE
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
    if isHost and packet.opcode == opcodes.PEER_UPDATE:
        # Handle peer update

        # 2. HOST: Host receives PEER_UPDATE
        # 3. HOST: Update peer info database
        # 4. HOST: Look for chunks for peer
        # 5. HOST: Send Tracker response
        return
    elif packet.opcode == opcodes.TRACKER_RESPONSE:
        # Handle tracker response

        peerList = packet.peers
        peerStatus = peerState.SEND_PEER_RESPONSE
        # 6. PEER: Receive tracker response
        return
    elif packet.opcode == opcodes.REQUEST_CHUNK:
        # Handle request chunk

        # 8. PEER: Receive chunk request
        # 9. PEER: Send chunk
        return
    elif packet.opcode == opcodes.CHUNK_DATA:
        # Handle receive data

        # 10. PEER: Receive data from packet and save to file
        # 11. PEER: Update chunk avail
        peerStatus = peerState.SEND_PEER_REQUEST
        return
