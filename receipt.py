__author__ = "Alexandre Chirouze"
__copyright__ = "Copyright 2022, GammaDynamics, LLC"
__version__ = "1.1.0.0"


from toolbox import *
from global_params import *



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


#N.B. wait_for_transaction_receipt() exits sometimes with traceback which contains:
#N.B.   i) 'Unable to complete request at this time.' or 
#N.B.   ii) 'CancelledError' (I assume, with NODE_WEBSOCKET = True): https://docs.python.org/3/library/asyncio-exceptions.html
#N.B. but succeeds anyway!
#N.B. If .wait_for_transaction_receipt() is pending, it exits after TIMEOUT_SEC with web3.exceptions.TimeExhausted (tx fails with 'Transaction too old' on Polygonscan)
#N.B. and 2nd tx is submitted on the next i-iteration with higher gas and the same nonce i.e. the 1st tx is cancelled (if the 1st tx does not succeed by then); 
#N.B. nonce does not include 'pending' and it is very unlikely that the 1st tx succeeds before next i-iteration for TIMEOUT_SEC >> 0;

def wait_for_transaction_receipt(network, tx_hash, timeout=TIMEOUT_SEC, polling=RECEIPT_POLLING_SEC, init=None):
    
    timeout = time.time() + timeout
    while True:
        try:
            receipt = init.w3.eth.get_transaction_receipt(tx_hash)
            return vars(receipt)
        except Exception as e: # If the function does not succeed, it means that the tx is not included in a block yet or tx_hash doesn't exist.
            if "Unable to complete request at this time" in traceback.format_exc() or 'CancelledError' in traceback.format_exc() or 'IncompleteReadError' in traceback.format_exc():
	            #N.B. wait!
                logger.error(network + ', .get_transaction_receipt() in wait_for_transaction_receipt() failed with error ' +\
                        traceback.format_exc(limit=0) + '. Run delay_error()')
                tx_receipt = delay_error(network, init, 'receipt', tx_hash)
            elif time.time() >= timeout:
	            logger.error(network + ', wait_for_transaction_receipt() failed because it exceeded timeout = ' + str(TIMEOUT_SEC) + '. Try again with higher gas!')
	            return False
            time.sleep(polling) # wait polling seconds before trying to get the receipt again.

#######################################################
##N.B. using w3.eth.wait_for_transaction_receipt()
#    try:
#        #N.B. Tx cancels after deadline: used for MAX_ATTEMPS_FAILED_TX-th tx! https://docs.uniswap.org/contracts/v3/guides/swaps/single-swaps
#        tx_receipt = init.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=TIMEOUT_SEC)
#    except Exception as e: # TimeExhausted as e:
#        if "Unable to complete request at this time" in traceback.format_exc() or 'CancelledError' in traceback.format_exc() or 'IncompleteReadError' in traceback.format_exc():
#            logger.error(network + ', wait_for_transaction_receipt() in decreaseLiquidity() for tokenId=' + str(tokenId) + ' failed with error ' + traceback.format_exc(limit=0))
#            tx_receipt = delay_error(network, init, 'receipt', tx_hash)
#        else:
#           logger.error(network + ', wait_for_transaction_receipt() in decreaseLiquidity()  for tokenId=' + str(tokenId) + ' failed after TIMEOUT_SEC = ' + str(TIMEOUT_SEC) + ' with error ' + traceback.format_exc(limit=0) + '. Try again with higher gas!')
#           return False
#    #print(tx_receipt)
