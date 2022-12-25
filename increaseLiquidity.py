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

#N.B. price is for token1 w.r.t. token 0
def increaseLiquidity(network, tokenId, \
                     amount0ToMint=0.02*10**TOKEN0_DECIMAL_MUMBAI, amount1ToMint=0.0001*10**TOKEN1_DECIMAL_MUMBAI,\
            max_fee_per_gas=MAX_FEE_PER_GAS, max_priority_fee_per_gas=MAX_PRIORITY_FEE_PER_GAS,\
           address=ADDRESS_TESTNET, private_key=PRIVATE_KEY, init=None): 
    #N.B. Example of succesful tx https://kovan.etherscan.io/tx/0xf18d55baef8f0efd274fe3d4014d177cbc3113f71a6481154c17a9af4a78cc39 > Input Data > Decode
    amount0ToMint = int(amount0ToMint)
    amount1ToMint = int(amount1ToMint)

    if init is None:
        init = Initialization(network)
    #N.B. Setting up a gas strategy turns tx-s into 'Legacy'
    #init.w3.eth.set_gas_price_strategy(medium_gas_price_strategy) #N.B. Only used for legacy tx-s: https://web3py.readthedocs.io/en/stable/gas_price.html

    #N.B. Speed-up by saving another call to the blockchain (it is possible but very unlikely that block is delayed)
    expiryDate = int(time.time()) + EXPIRY_SEC
    #try:
    #    expiryDate = init.w3.eth.get_block('latest')["timestamp"] + EXPIRY_SEC
    #except:
    #    logger.error(network + ', expiryDate in mint() failed. Nexr main() iteration (with higher gas)!')
    #    return False
   
    params = (
                tokenId, #: tokenId, in decimal
                amount0ToMint, #amount0Desired 
                amount1ToMint, # amount1Desired
                0, #amount0Min
                0, #amount1Min: 
                address, #recipient
                expiryDate #deadline
    )
   
    c = Contract(network, init.w3, 'LP')

    #N.B. The nonce does not use 'pending', so the 2nd tx (with higher gas) replaces a pending tx
    try:
        nonce = init.w3.eth.get_transaction_count(address)
    except:
        logger.error(network + ', get_transaction_count() in mint() failed. Next main() iteration (with higher gas)!')
        return False

    time.sleep(DELAY_NONCE_SEC) #N.B. Sometimes get 'nonce too low' error
    lp_tx = c.contract.functions.increaseLiquidity(params).build_transaction({
        "chainId": init.networkId,
        "from": address,
        "maxFeePerGas": init.w3.toHex(max_fee_per_gas),
        "maxPriorityFeePerGas": init.w3.toHex(max_priority_fee_per_gas),
        #"gasPrice": w3.toHex(int(5e9)), #N.B. Commenting out gasPrice uses market GasPrice & makes the tx "Type 2: EIP-1559" (as opposed to "Legacy" when un-commented) 
        "gas": init.w3.toHex(MAX_GAS_UNITS),
        "nonce": nonce
    })

    
    signed_tx = init.w3.eth.account.sign_transaction(lp_tx, private_key)
    try:
        tx_hash = init.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    except Exception as e:
        #N.B. The error 'connection closed abnormally' delays execution but the tx executes!
        #if 'connection closed abnormally' in traceback.format_exc(limit=0):
        #    logger.error(network + ', send_raw_transaction() in increaseLiquidity() failed with error ' + traceback.format_exc(limit=0))
        #    tx_hash = delay_error(network, init, 'hash', signed_tx.rawTransaction)
        #else:
        logger.error(network + ', send_raw_transaction() in increaseLiquidity() for tokenId ' + str(tokenId) + ' failed with error ' +\
            + traceback.format_exc(limit=0) +'. Try again with higher gas! ' )
        return False
   
    #N.B. tx receipt
    tx_receipt = {'status': -1} #N.B. tx_receipt['status'] is not recognised sometimes
    result = wait_for_transaction_receipt(network,tx_hash, timeout=TIMEOUT_SEC, polling=RECEIPT_POLLING_SEC, init=init)
    if isinstance(result, dict):
        tx_receipt = result
        if tx_receipt['status'] == 0:
            logger.error(network + ', increaseLiquidity() failed with tx_receipt[status] == 0! Tx receipt %s. Try again with higher gas!', tx_receipt)
            gas_fee = tx_receipt['effectiveGasPrice'] * tx_receipt['gasUsed'] / 10**init.token1_decimal
            return [gas_fee, False]
        else:
            gas_fee = tx_receipt['effectiveGasPrice'] * tx_receipt['gasUsed'] / 10**init.token1_decimal
            #N.B. Decoding the IncreaseLiquidity() event in the receipt
            event_dict = c.contract.events.IncreaseLiquidity().processReceipt(tx_receipt, errors=DISCARD)
            tokenId, liquidity, amount0, amount1 = event_dict[0]['args']['tokenId'], event_dict[0]['args']['liquidity'], event_dict[0]['args']['amount0'], event_dict[0]['args']['amount1']
            blockNumber = tx_receipt["blockNumber"] 
            logger.info(network + ', increaseLiquidity() succedeed: block=' + str(blockNumber) +\
               ', tokenId=' + str(tokenId) + ', liquidity=' + str(liquidity) +\
               ', amount0=' + str(amount0 / 10**init.token0_decimal) + ', amount1=' + str(amount1 / 10**init.token1_decimal))
            #print('tokenId=' + str(tokenId) + ', liquidity=' + str(liquidity) + ', amount0=' + str(amount0 / 10**18) + ', amount1=' +  str(amount1 / 10**18))

            #N.B. Although the guide https://docs.uniswap.org/protocol/guides/providing-liquidity/mint-a-position
            #N.B. has transfers of residual amounts at the end, 
            # N.B. WETH_balance_after - WETH_balance_before - amount1 (when token1=WETH) appears to be = 0?!
        return gas_fee, liquidity, amount0, amount1, blockNumber, nonce
    else:
        logger.error(network + ', increaseLiquidity() for tokenId = ' + str(tokenId) + ' failed because wait_for_transaction_receipt() failed')
        return False

def increaseLiquidity_wrapped(network, tokenId, amount0ToMint=0.02*10**TOKEN0_DECIMAL_MUMBAI, amount1ToMint=0.0001*10**TOKEN1_DECIMAL_MUMBAI, max_fee_per_gas=MAX_FEE_PER_GAS, max_priority_fee_per_gas=MAX_PRIORITY_FEE_PER_GAS): 

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

    increaseLiquidity(network, tokenId, amount0ToMint, amount1ToMint, max_fee_per_gas, max_priority_fee_per_gas, address=Address, private_key=privateKey)

if __name__ == '__main__':
    if len(sys.argv) == 5:  # network, amount0ToMint, amount1ToMint, price_lower, price_upper
        increaseLiquidity_wrapped(network=str(sys.argv[1]), amount0ToMint=eval(sys.argv[2]), amount1ToMint=eval(sys.argv[3]), price_lower=eval(sys.argv[4]), price_upper=eval(sys.argv[5]))
    elif len(sys.argv) == 7:  # network, max_fee_per_gas, max_priority_fee_per_gas
        increaseLiquidity_wrapped(network=str(sys.argv[1]), amount0ToMint=eval(sys.argv[2]), amount1ToMint=eval(sys.argv[3]), price_lower=eval(sys.argv[4]), price_upper=eval(sys.argv[5]), max_fee_per_gas=eval(sys.argv[6]), max_priority_fee_per_gas=eval(sys.argv[7]))
    else:   
        print("Wrong number of inputs!")

