from Scheduler import Scheduler
from InputsConfig import InputsConfig as p
from Models.Bitcoin.Node import Node
from Statistics import Statistics
from Models.Transaction import LightTransaction as LT, FullTransaction as FT
from Models.Network import Network
from Models.Bitcoin.Consensus import Consensus as c
from Models.BlockCommit import BlockCommit as BaseBlockCommit

class BlockCommit(BaseBlockCommit):

    postpone_next_blk = {}

    # Handling and running Events
    def handle_event(event):
        if event.type == "create_block":
            BlockCommit.generate_block(event)
        elif event.type == "receive_block":
            BlockCommit.receive_block(event)

    # Block Creation Event
    def generate_block (event):
        miner = p.NODES[event.block.miner]
        minerId = miner.id
        eventTime = event.time
        blockPrev = event.block.previous
        postpone_time = BlockCommit.postpone_next_blk.get(minerId, 0)
        if postpone_time > eventTime:
            Scheduler.postpone_create_block_event(event.block, postpone_time)
            return

        if blockPrev == miner.last_block().id:
            Statistics.totalBlocks += 1 # count # of total blocks created!
            if p.hasTrans:
                if p.Ttechnique == "Light": blockTrans,blockSize = LT.execute_transactions()
                elif p.Ttechnique == "Full": blockTrans,blockSize = FT.execute_transactions(miner,eventTime)

                event.block.transactions = blockTrans
                event.block.usedgas= blockSize

            miner.blockchain.append(event.block)

            if p.hasTrans and p.Ttechnique == "Light":LT.create_transactions() # generate transactions

            BlockCommit.propagate_block(event.block)
            BlockCommit.generate_next_block(miner,eventTime)# Start mining or working on the next block

    # Block Receiving Event
    def receive_block (event):

        miner = p.NODES[event.block.miner]
        minerId = miner.id
        currentTime = event.time
        blockPrev = event.block.previous # previous block id

        node = p.NODES[event.node] # recipint
        lastBlockId= node.last_block().id # the id of last block
        postpone_time = BlockCommit.postpone_next_blk.get(minerId, 0)
        if postpone_time > currentTime:
            Scheduler.postpone_receive_block_event(node, event.block, postpone_time)
            return

        BlockCommit.postpone_next_blk[node.id] = currentTime + 2

        #### case 1: the received block is built on top of the last block according to the recipient's blockchain ####
        if blockPrev == lastBlockId:
            node.blockchain.append(event.block) # append the block to local blockchain
            if p.hasTrans and p.Ttechnique == "Full": BlockCommit.update_transactionsPool(node, event.block)
            BlockCommit.generate_next_block(node,currentTime + 2)# Start mining or working on the next block

         #### case 2: the received block is  not built on top of the last block ####
        else:
            depth = event.block.depth + 1
            if (depth > len(node.blockchain)):
                BlockCommit.update_local_blockchain(node,miner,depth)
                BlockCommit.generate_next_block(node,currentTime + 2)# Start mining or working on the next block

            if p.hasTrans and p.Ttechnique == "Full": BlockCommit.update_transactionsPool(node,event.block) # not sure yet.

    # Upon generating or receiving a block, the miner start working on the next block as in POW
    def generate_next_block(node,currentTime):
	    if node.hashPower > 0:
                 blockTime = currentTime + 2 + c.Protocol(node) # time when miner x generate the next block
                 Scheduler.create_block_event(node,blockTime)

    def generate_initial_events():
            currentTime=0
            for node in p.NODES:
            	BlockCommit.generate_next_block(node,currentTime)

    def propagate_block (block):
        for recipient in p.NODES:
            if recipient.id != block.miner:
                blockDelay= Network.block_prop_delay() # draw block propagation delay from a distribution !! or you can assign 0 to ignore block propagation delay
                Scheduler.receive_block_event(recipient,block,blockDelay)
