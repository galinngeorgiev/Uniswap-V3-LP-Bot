__author__ = "Galin Georgiev"
__copyright__ = "Copyright 2022, GammaDynamics, LLC"
__version__ = "1.1.0.0"


from toolbox import *
from global_params import *

from receipt import wait_for_transaction_receipt
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

def collect(network, tokenId, max_fee_per_gas=MAX_FEE_PER_GAS, max_priority_fee_per_gas=MAX_PRIORITY_FEE_PER_GAS, address=ADDRESS_TESTNET, private_key=PRIVATE_KEY, init=None, nonce=None):

    if init is None:
        init = Initialization(network)
    c = Contract(network, init.w3, 'LP')

    uint128_max = 2**128 - 1 #N.B. collect() takes uint128 as amountMax: https://docs.uniswap.org/protocol/reference/core/interfaces/pool/IUniswapV3PoolActions
    params = (
                tokenId, #tokenId
                address, #recipient
                uint128_max, #amount0Max
                uint128_max #amount1Max
            )
     
    #N.B. The nonce does not use 'pending', so the 2nd tx (with higher gas) replaces a pending tx
    if nonce is None:
        try:
            nonce = init.w3.eth.get_transaction_count(address)
        except:
            logger.error(network + ', get_transaction_count() in collect() failed. Next main() iteration (with higher gas)!')
            return False
        time.sleep(DELAY_NONCE_SEC) #N.B. Sometimes get 'nonce too low' error
    else:
        nonce += 1
    collect_tx = c.contract.functions.collect(params).build_transaction({
        "chainId": init.networkId,
        "from": address,
        "maxFeePerGas": init.w3.toHex(max_fee_per_gas),
        "maxPriorityFeePerGas": init.w3.toHex(max_priority_fee_per_gas),
        #"gasPrice": w3.toHex(int(5e11)), #N.B. Commenting out gasPrice uses market GasPrice & makes the tx "Type 2: EIP-1559" (as opposed to "Legacy" when un-commented) 
        "gas": init.w3.toHex(MAX_GAS_UNITS),
        "nonce": nonce
    })

    signed_tx = init.w3.eth.account.sign_transaction(collect_tx, private_key)
    try:
        tx_hash = init.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    except Exception as e:
        #N.B. The error 'connection closed abnormally' delays execution but the tx executes!
        #if 'connection closed abnormally' in traceback.format_exc(limit=0):
        #    logger.error(network + ', send_raw_transaction() in colllect() failed with error ' + traceback.format_exc(limit=0))
        #    tx_hash = delay_error(network, init, 'hash', signed_tx.rawTransaction)
        #else:
        logger.error(network + ', send_raw_transaction() in collect() for tokenId ' + str(tokenId) + ' failed with error ' +\
            traceback.format_exc(limit=0) + '. Try again with higher gas! ')
        return False
        
    #N.B. tx receipt
    tx_receipt = {'status': -1} #N.B. tx_receipt['status'] is not recognised sometimes
    result = wait_for_transaction_receipt(network, tx_hash, timeout=TIMEOUT_SEC, polling=RECEIPT_POLLING_SEC, init=init)
    if isinstance(result, dict):
        tx_receipt = result
        if tx_receipt['status'] == 0:
            logger.error(network + ', collect() for tokenId = ' + str(tokenId) + ' failed with tx_receipt[status] == 0. Tokens are not collected! Try again with higher gas! ', tx_receipt)
            gas_fee = tx_receipt['effectiveGasPrice'] * tx_receipt['gasUsed'] / 10**init.token1_decimal
            return [gas_fee, False]
        else:
            gas_fee = tx_receipt['effectiveGasPrice'] * tx_receipt['gasUsed'] / 10**init.token1_decimal
            #N.B. Decoding the Collect() event in the receipt
            event_dict = c.contract.events.Collect().processReceipt(tx_receipt, errors=DISCARD)
            recipient, amount0, amount1 = event_dict[0]['args']['recipient'], event_dict[0]['args']['amount0'], event_dict[0]['args']['amount1']
            logger.info(network + ', collect() succedeed: block=' + str(tx_receipt["blockNumber"]) + ', tokenId=' + str(tokenId) +\
                     ', amount0 collected=' + str(amount0 / 10**init.token0_decimal) +\
                        ', amount1 collected=' + str(amount1 / 10**init.token1_decimal) +\
                        ', recipient=' + str(recipient))
        return gas_fee, amount0, amount1, nonce
    else:
        logger.error(network + ', collect() for tokenId = ' + str(tokenId) + ' failed because wait_for_transaction_receipt() failed')
        return False


def collect_wrapped(network, tokenId, max_fee_per_gas=MAX_FEE_PER_GAS, max_priority_fee_per_gas=MAX_PRIORITY_FEE_PER_GAS):

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

    collect(network, tokenId, max_fee_per_gas, max_priority_fee_per_gas, address=Address, private_key=privateKey)



if __name__ == '__main__':
    if len(sys.argv) == 3:  # network, tokenId
        collect_wrapped(network=str(sys.argv[1]), tokenId=eval(sys.argv[2]))
    elif len(sys.argv) == 5:  # tokenId, network, max_fee_per_gas, max_priority_fee_per_gas
        collect_wrapped(network=str(sys.argv[1]), tokenId=eval(sys.argv[2]), max_fee_per_gas=eval(sys.argv[3]), max_priority_fee_per_gas=eval(sys.argv[4]))
    else:
        print("Wrong number of inputs!")

