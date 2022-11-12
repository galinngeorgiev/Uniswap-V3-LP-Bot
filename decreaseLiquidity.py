__author__ = "Galin Georgiev"
__copyright__ = "Copyright 2022, GammaDynamics, LLC"
__version__ = "1.1.0.0"




from toolbox import *
from global_params import *
from encryption import decrypt_file


############################################################
#logger
logger_fname = os.path.join(DATA_PATH, 'log','main_' + str(time.strftime("%Y%m%d")) + '.log')
import logging
import time
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# create a file handler
handler = logging.FileHandler(logger_fname, mode='a')
handler.setLevel(logging.INFO)
# create a logging format
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)20.20s - %(message)s')
handler.setFormatter(formatter)
# add the handlers to the logger
if not len(logger.handlers):
	logger.addHandler(handler)

##############################################################

def decreaseLiquidity(network, tokenId, liquidity, max_fee_per_gas=MAX_FEE_PER_GAS, max_priority_fee_per_gas=MAX_PRIORITY_FEE_PER_GAS,\
                        address=ADDRESS_TESTNET, private_key=PRIVATE_KEY, init=None, nonce=None):

    if init is None:
        init = Initialization(network)
    c = Contract(network, init.w3, 'LP')
    #N.B. Setting up a gas strategy turns tx-s into 'Legacy'
    #init.w3.eth.set_gas_price_strategy(medium_gas_price_strategy) #N.B. Only used for legacy tx-s: https://web3py.readthedocs.io/en/stable/gas_price.html
    
    #N.B. Speed-up by saving another call to the blockchain (it is possible but very unlikely that block is delayed)
    expiryDate = int(time.time()) + EXPIRY_SEC
    #try:
    #    expiryDate = init.w3.eth.get_block('latest')["timestamp"] + EXPIRY_SEC
    #except:
    #    logger.error(network + ', expiryDate in decreaseLiquidity() failed. Next main() iteration (with higher gas)!')
    #    return False

    params = (
                tokenId, #: tokenId, in decimal
                liquidity, #liquidity,
                0, #amount0Min
                0, #amount1Min,
                expiryDate #deadline
                
       )
   
    if nonce is None:
        #N.B. The nonce does not use 'pending', so the 2nd tx (with higher gas) replaces a pending tx
        try:
            nonce = init.w3.eth.get_transaction_count(address)
        except:
            logger.error(network + ', get_transaction_count() in decreaseLiquidity() failed. Next main() iteration (with higher gas)!')
            return False
        time.sleep(DELAY_NONCE_SEC) #N.B. Sometimes get 'nonce too low' error
    else:
        nonce += 1
    remove_lp_tx = c.contract.functions.decreaseLiquidity(params).build_transaction({
        "chainId": init.networkId,
        "from": address,
        "maxFeePerGas": init.w3.toHex(max_fee_per_gas),
        "maxPriorityFeePerGas": init.w3.toHex(max_priority_fee_per_gas),
        #"gasPrice": w3.toHex(int(5e11)), #N.B. Commenting out gasPrice uses market GasPrice & makes the tx "Type 2: EIP-1559" (as opposed to "Legacy" when un-commented) 
        "gas": init.w3.toHex(MAX_GAS_UNITS),
        "nonce": nonce
    })

    signed_tx = init.w3.eth.account.sign_transaction(remove_lp_tx, private_key)
    try:
        tx_hash = init.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    except Exception as e:
        #N.B. The error 'connection closed abnormally' delays execution but the tx executes!
        #if 'connection closed abnormally' in traceback.format_exc(limit=0):
        #    logger.error(network + ', send_raw_transaction() in decreaseLiquidity() failed with error ' + traceback.format_exc(limit=0))
        #    tx_hash = delay_error(network, init, 'hash', signed_tx.rawTransaction)
        #else:
        logger.error(network + ', send_raw_transaction() in decreaseLiquidity() for tokenId ' + str(tokenId) + ' failed with error ' +\
            traceback.format_exc(limit=0) + '. Try again with higher gas! ')
        return False

    #N.B. tx receipt
    tx_receipt = {'status': -1} #N.B. tx_receipt['status'] is not recognised sometimes
   
    #N.B. wait_for_transaction_receipt() exits sometimes with traceback which contains:
    #N.B.   i) 'Unable to complete request at this time.' or 
    #N.B.   ii) 'asyncio.exceptions.CancelledError' (I assume, with NODE_WEBSOCKET = True): https://docs.python.org/3/library/asyncio-exceptions.html
    #N.B. but succeeds anyway!
    #N.B. If .wait_for_transaction_receipt() hangs (tx is pending), it exits after TIMEOUT_SEC with web3.exceptions.TimeExhausted and succeddes on the next iteration 
    #N.B. (nonce does not include 'pending' and it is very unlikely that the 1st tx succeeds before next iteration for TIMEOUT_SEC >> 0)
    try:
        #N.B. Tx cancels after deadline, so no point of waitning TIMEOUT_SEC!
        tx_receipt = init.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=EXPIRY_SEC)
    except Exception as e: # TimeExhausted as e:
        if "Unable to complete request at this time" in traceback.format_exc() or 'CancelledError' in traceback.format_exc() or 'IncompleteReadError' in traceback.format_exc():
            logger.error(network + ', wait_for_transaction_receipt() in decreaseLiquidity() for tokenId=' + str(tokenId) + ' failed with error ' + traceback.format_exc(limit=0))
            tx_receipt = delay_error(network, init, 'receipt', tx_hash)
        else:
           logger.error(network + ', wait_for_transaction_receipt() in decreaseLiquidity()  for tokenId=' + str(tokenId) + ' failed after TIMEOUT_SEC = ' + str(TIMEOUT_SEC) + ' with error ' + traceback.format_exc(limit=0) + '. Try again with higher gas!')
           return False
    #print(tx_receipt)

    if tx_receipt['status'] == 0:
        logger.error(network + ', decreaseLiquidity() failed with tx_receipt[status] == 0 for tokenId=' + str(tokenId) + ', liquidity=' + str(liquidity) +\
                                '. Tx receipt %s. Try again with higher gas! ', tx_receipt)
        return False
    else:
        #N.B. Decoding the DecreaseLiquidity() event in the receipt
        event_dict = c.contract.events.DecreaseLiquidity().processReceipt(tx_receipt, errors=DISCARD)
        liquidity, amount0, amount1 = event_dict[0]['args']['liquidity'], event_dict[0]['args']['amount0'], event_dict[0]['args']['amount1']
        #tokenId_decreaseLiquidity = tokenId
        logger.info(network + ', decreaseLiquidity() succedeed: block=' + str(tx_receipt["blockNumber"]) + ', tokenId=' + str(tokenId) +\
                    ': liquidity removed=' + str(liquidity) +\
                    ', amount0 removed=' + str(amount0 / 10**init.token0_decimal) +\
                   ', amount1 removed=' + str(amount1 / 10**init.token1_decimal))
        #print('liquidity removed =' +  "{:1.0f}".format(liquidity) + ', amount0 removed =' +  "{:1.5f}".format(amount0 / 10**18) + ', amount1 removed =' +  "{:1.5f}".format(amount1 / 10**18))


    return amount0, amount1, nonce


def decreaseLiquidity_wrapped(network, tokenId, liquidity, max_fee_per_gas=MAX_FEE_PER_GAS, max_priority_fee_per_gas=MAX_PRIORITY_FEE_PER_GAS):

    if network == 'ethereum':
        Address = ADDRESS_MAINNET
        file_name = os.path.join(DATA_PATH,'accounts','MM_account1.txt')
        privateKey = decrypt_file(file_name)
    elif network == 'polygon':
        Address = ADDRESS_POLYGON
        file_name = os.path.join(DATA_PATH,'accounts','MM_account3.txt')
        privateKey = decrypt_file(file_name)
    elif network == 'mumbai' or network == 'kovan' or network == 'goerli':
        Address = ADDRESS_TESTNET
        privateKey = PRIVATE_KEY

    decreaseLiquidity(network, tokenId, liquidity, max_fee_per_gas, max_priority_fee_per_gas, address=Address, private_key=privateKey)

if __name__ == '__main__':
    #print(len(sys.argv), sys.argv)
    if len(sys.argv) == 3:  #tokenId, liquidity
        decreaseLiquidity_wrapped('mumbai', tokenId=eval(sys.argv[1]), liquidity=eval(sys.argv[2]))
    elif len(sys.argv) == 4:  # network, tokenId, liquidity
        decreaseLiquidity_wrapped(network=str(sys.argv[1]), tokenId=eval(sys.argv[2]), liquidity=eval(sys.argv[3]))
    elif len(sys.argv) == 6:  # network, tokenId, liquidity, max_fee_per_gas, max_priority_fee_per_gas
        decreaseLiquidity_wrapped(network=str(sys.argv[1]), tokenId=eval(sys.argv[2]), liquidity=eval(sys.argv[3]), max_fee_per_gas=eval(sys.argv[4]), max_priority_fee_per_gas=eval(sys.argv[5]))
    else:
        print("Wrong number of inputs!")


