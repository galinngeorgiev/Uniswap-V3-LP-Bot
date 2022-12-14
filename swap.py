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


#N.B. Size-split swapping: if amount_to_swap_token0 > 0, swap token0 to token1; if amount_to_swap_token0 < 0, swap token1 to token0;
def size_split_swap(network='mumbai', price=1000., amount_to_swap_token0=0.001, max_fee_per_gas=MAX_FEE_PER_GAS, max_priority_fee_per_gas=MAX_PRIORITY_FEE_PER_GAS, address=ADDRESS_TESTNET, private_key=PRIVATE_KEY, init=None, nonce=None):
    
    flag_swap, flag_failed_tx, count_failed_tx, gas_fee, slippage_and_pool_fee_token1 = True, False, 0, 0., 0.
    slippage_per = SLIPPAGE_PER
    abs_amount_to_swap = abs(amount_to_swap_token0)
    #N.B. num_swap_iteration includes the remainder
    j, num_swap_iteration = 0, int(abs_amount_to_swap // MAX_QUANTITY0_SWAP_ITERATION + 1)

    while j < num_swap_iteration:
        #N.B. Increase gas, if swap tx failed
        if flag_failed_tx and  max_fee_per_gas / MAX_FEE_PER_GAS <= MAX_MULT_FACTOR_GAS_REPLACE:
            max_fee_per_gas, max_priority_fee_per_gas  = int(MULT_GAS_FACTOR_REPLACE * max_fee_per_gas), int(MULT_GAS_FACTOR_REPLACE * max_priority_fee_per_gas)
        else:
            max_fee_per_gas, max_priority_fee_per_gas = MAX_FEE_PER_GAS, MAX_PRIORITY_FEE_PER_GAS
        
        #N.B. Increase slippage, if swap tx failed
        if not flag_swap and slippage_per <= MAX_SLIPPAGE_PER:
            slippage_per += SLIPPAGE_PER
        else:
            slippage_per = SLIPPAGE_PER

        logger.info(network + ', num swap iteration = ' + str(num_swap_iteration) + ', swap iteration = ' + str(j))

        if j < num_swap_iteration - 1:
            #N.B. amount_to_swap_iteration = MAX_QUANTITY0_SWAP
            amount_to_swap_iteration = MAX_QUANTITY0_SWAP_ITERATION #N.B. > 0
        else:
            #N.B. amount_to_swap_iteration = remainder
            amount_to_swap_iteration = abs_amount_to_swap % MAX_QUANTITY0_SWAP_ITERATION #N.B. > 0
        
        ##N.B. Get sometimes 'nonce too low' error for j > 1!
        #if j > 0:
        #    nonce = None
                        
        if count_failed_tx < MAX_ATTEMPS_FAILED_TX:
            #N.B. If .wait_for_transaction_receipt() is pending, it exits after TIMEOUT_SEC with web3.exceptions.TimeExhausted (tx fails with 'Transaction too old' on Polygonscan)
            #N.B. and 2nd tx is submitted on the next j-iteration with higher gas and the same nonce i.e. the 1st tx is cancelled (if the 1st tx does not succeed by then); 
            #N.B. nonce does not include 'pending' and it is very unlikely that the 1st tx succeeds before next j-iteration for TIMEOUT_SEC >> 0;
              
            #N.B. input: token0 amount_to_swap_token0
            if amount_to_swap_token0 > 0:
                amount_out_min_iteration = amount_to_swap_iteration / price * (1 - slippage_per / 100)
                    
                result = swap(network, amount0=amount_to_swap_iteration, amount1=0., amount_out_min=amount_out_min_iteration,\
                            max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas,\
                                address=address, private_key=private_key, init=init, nonce=nonce)
                if isinstance(result, tuple):
                    gas, pool_liquidity, pool_price, swap_price, slippage_and_pool_fee, nonce = result
                    gas_fee += gas
                    slippage_and_pool_fee_token1 += slippage_and_pool_fee
                    flag_failed_tx, flag_swap = False, True
                    count_failed_tx = 0
                else:
                    if isinstance(result, list):
                        [gas, status] = result
                        gas_fee += gas
                    #N.B. nonce=None triggers web3 getting a nonce
                    flag_failed_tx, flag_swap, nonce = True, False, None
                    count_failed_tx += 1
                    continue #N.B. j is not increased!
                                        
            #N.B. input: token1 amount_to_swap_token0 / price
            elif amount_to_swap_token0 < 0:
                amount_out_min_iteration = amount_to_swap_iteration * (1 - slippage_per / 100)
                amount_to_swap_iteration /= price
                    
                result = swap(network, amount0=0., amount1=amount_to_swap_iteration, amount_out_min=amount_out_min_iteration,\
                            max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas, \
                                address=address, private_key=private_key, init=init, nonce=nonce)
                if isinstance(result, tuple):
                    gas, pool_liquidity, pool_price, swap_price, slippage_and_pool_fee, nonce = result
                    gas_fee += gas
                    slippage_and_pool_fee_token1 += slippage_and_pool_fee
                    flag_failed_tx, flag_swap = False, True
                    count_failed_tx = 0
                else:
                    if isinstance(result, list):
                        [gas, status] = result
                        gas_fee += gas
                    #N.B. nonce=None triggers web3 getting a nonce
                    flag_failed_tx, flag_swap, nonce = True, False, None
                    count_failed_tx += 1
                    logger.error(network + ", swap() failed for amount_to_swap_token0 " + str(amount_to_swap_token0) +\
                                                    ", count_failed_tx = " + str(count_failed_tx))
                    continue #N.B. j is not increased!
            else:
                logger.error(network + ", amount_to_swap_token0 = 0, continue with next main() iteration...")
                return True

            #swap iteration delay
            time.sleep(DELAY_SWAP_ITERATION_SEC)
            logger.info('')
            j += 1
        else:
            return [gas_fee, False]
                    
    return gas_fee, pool_liquidity, pool_price, swap_price, slippage_and_pool_fee_token1, nonce


################################################################################
#N.B. amountI=0 indicates swapping to tokenI
#swap(network, address, amount0, amount1, amount_out_min)
def swap(network='mumbai', amount0=0.001, amount1=0., amount_out_min=0., max_fee_per_gas=MAX_FEE_PER_GAS, max_priority_fee_per_gas=MAX_PRIORITY_FEE_PER_GAS, address=ADDRESS_TESTNET, private_key=PRIVATE_KEY, init=None, nonce=None):

    swap_price, slippage_and_pool_fee_token1 = None, None
    if amount0 != 0 and amount1 != 0:
        logger.error(network + ", error in swap() inputs: amount0 != 0 and amount1 != 0 Stop main()!")
        return False

    if init is None:
        init = Initialization(network)
    #N.B. Setting up a gas strategy turns tx-s into 'Legacy'
    #init.w3.eth.set_gas_price_strategy(medium_gas_price_strategy) #N.B. Only used for legacy tx-s: https://web3py.readthedocs.io/en/stable/gas_price.html
    c = Contract(network, init.w3, 'LT')
    c_pool = Contract(network, init.w3, 'Pool')

    #N.B. Speed-up by saving another call to the blockchain (it is possible but very unlikely that block is delayed)
    expiryDate = int(time.time()) + EXPIRY_SEC
    #expiryDate = init.w3.eth.get_block('latest')["timestamp"] + TIMEOUT_SEC
   
    #N.B. Omitting deadline i.e. using SwapRouter02.sol, can save gas: https://github.com/Uniswap/interface/issues/2924
    if amount1 == 0.:
        amount_to_swap_token0 = int(amount0 * 10**init.token0_decimal)
        amount_out_min = int(amount_out_min * 10**init.token1_decimal)
        
        params = (
            init.token0_address, # TokenIn
            init.token1_address, # TokenOut
            init.pool_fee,  # fee
            address, # recipient
            expiryDate, #deadline
            amount_to_swap_token0,  # amountIn
            amount_out_min,  # amountOutMinimum
            0  # sqrtPriceLimitX96
            )
    elif amount0 == 0.:
        amount_to_swap_token0 = int(amount1 * 10**init.token1_decimal)
        amount_out_min = int(amount_out_min * 10**init.token0_decimal)
        params = (
            init.token1_address, # TokenIn
            init.token0_address, # TokenOut
            init.pool_fee,  # fee
            address, # recipient
            expiryDate, #deadline
            amount_to_swap_token0,  # amountIn
            amount_out_min,  # amountOutMinimum
            0  # sqrtPriceLimitX96
            )

    #N.B. The nonce does not use 'pending', so the 2nd tx (with higher gas) replaces a pending tx
    if nonce is None:
        try:
            nonce = init.w3.eth.get_transaction_count(address)
        except:
            logger.error(network + ', get_transaction_count() in swap() failed. Next main() iteration (with higher gas)!')
            return False
        time.sleep(DELAY_NONCE_SEC) #N.B. Sometimes get 'nonce too low' error
    else:
        nonce += 1
    swap_tx = c.contract.functions.exactInputSingle(params).build_transaction({
        "chainId": init.networkId,
        "from": address,
        "maxFeePerGas": init.w3.toHex(max_fee_per_gas), 
        "maxPriorityFeePerGas": init.w3.toHex(max_priority_fee_per_gas),
        #"gasPrice": w3.toHex(int(5e9)), #N.B. Commenting out gasPrice uses market GasPrice & makes the tx "Type 2: EIP-1559" (as opposed to "Legacy" when un-commented) 
        "gas": init.w3.toHex(MAX_GAS_UNITS),
        "nonce": nonce
    })

    signed_tx = init.w3.eth.account.sign_transaction(swap_tx, private_key)
    try:
        tx_hash = init.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    except Exception as e:
        #N.B. The error 'connection closed abnormally' delays execution but the tx executes!
        #if 'connection closed abnormally' in traceback.format_exc(limit=0):
        #    logger.error(network + ', send_raw_transaction() in swap() failed with error ' + traceback.format_exc(limit=0))
        #    tx_hash = delay_error(network, init, 'hash', signed_tx.rawTransaction)
        #else:
        logger.error(network + ', send_raw_transaction() in swap() failed with error ' +\
            traceback.format_exc(limit=0) + '. Try again with higher gas! ')
        return False
    
   
    #N.B. tx receipt
    tx_receipt = {'status': -1} #N.B. tx_receipt['status'] is not recognised sometimes

    #N.B. wait_for_transaction_receipt() exits sometimes with traceback which contains:
    #N.B.   i) 'Unable to complete request at this time.' or 
    #N.B.   ii) 'CancelledError' (I assume, with NODE_WEBSOCKET = True): https://docs.python.org/3/library/asyncio-exceptions.html
    #N.B. but succeeds anyway!

    #N.B. If .wait_for_transaction_receipt() is pending, it exits after TIMEOUT_SEC with web3.exceptions.TimeExhausted (tx fails with 'Transaction too old' on Polygonscan)
    #N.B. and 2nd tx is submitted on the next i-iteration with higher gas and the same nonce i.e. the 1st tx is cancelled (if the 1st tx does not succeed by then); 
    #N.B. nonce does not include 'pending' and it is very unlikely that the 1st tx succeeds before next i-iteration for TIMEOUT_SEC >> 0;
  
    try:
        #N.B. Tx cancels after deadline: used for MAX_ATTEMPS_FAILED_TX-th tx! https://docs.uniswap.org/contracts/v3/guides/swaps/single-swaps
        tx_receipt = init.w3.eth.wait_for_transaction_receipt(tx_hash, timeout = TIMEOUT_SEC)
    except Exception as e: # TimeExhausted as e:
        if "Unable to complete request at this time" in traceback.format_exc() or 'CancelledError' in traceback.format_exc():
            #N.B. wait!
            logger.error(network + ', wait_for_transaction_receipt() in swap() failed with error ' + traceback.format_exc(limit=0))
            tx_receipt = delay_error(network, init, 'receipt', tx_hash)
        else:
            logger.error(network + ', wait_for_transaction_receipt() in swap() failed after TIMEOUT_SEC = ' + str(TIMEOUT_SEC) + ' with error ' + traceback.format_exc(limit=0) + '. Try again with higher gas!')
            return False
       
    if tx_receipt['status'] == 0:
        logger.error(network + ', swap() failed with tx_receipt[status] == 0! Tx receipt %s. Try again with higher gas! ', tx_receipt)
        gas_fee = tx_receipt['effectiveGasPrice'] * tx_receipt['gasUsed'] / 10**init.token1_decimal
        return [gas, False]
    else:
        gas_fee = tx_receipt['effectiveGasPrice'] * tx_receipt['gasUsed'] / 10**init.token1_decimal
        #N.B. Router contract does not have events in the ABI.  Decoding the Swap() event of the Pool contract
        event_dict = c_pool.contract.events.Swap().processReceipt(tx_receipt, errors=DISCARD)
        #N.B. For the general case (without tx), connecting through websocket to watch events is required!
        #c_pool.contract.events.Swap().createFilter(fromBlock='latest').get_new_entries()
        amount0, amount1, sqrtPriceX96, pool_liquidity, tick = event_dict[0]['args']['amount0'], event_dict[0]['args']['amount1'], event_dict[0]['args']['sqrtPriceX96'], event_dict[0]['args']['liquidity'], event_dict[0]['args']['tick']
        #N.B. According to the docs, price = (sqrtPrice / 2^96)^2 https://docs.uniswap.org/sdk/guides/fetching-prices & rounded price = 1.0001^tick
        #price = 1.0001 ** tick
        pool_price = 1. / (sqrtPriceX96 / 2**96)**2 / 10**init.token0_decimal * 10**init.token1_decimal
        swap_price =  -(amount0 / 10**init.token0_decimal) / (amount1 / 10**init.token1_decimal)
        if amount1 < 0: #N.B. token0 is supplied in i.e. longShort = 1
            #N.B. swap price before pool fees
            swap_price *= 1. - init.pool_fee / 1000000
            slippage_and_pool_fee_token1 = - (amount0 / 10**init.token0_decimal / pool_price + amount1 / 10**init.token1_decimal) # < 0
            logger.info(network + ', swap() succedeed: block=' + str(tx_receipt["blockNumber"]) +\
                       ', amountIn=' + "{:1.4f}".format(amount0 / 10**init.token0_decimal) + ' ' + init.token0_symbol +\
                       ', amountOut=' + "{:1.4f}".format(amount1 / 10**init.token1_decimal) + ' ' + init.token1_symbol +\
                       ', slippage & pool fee=' + "{:1.4f}".format(slippage_and_pool_fee_token1) + ' ' + init.token1_symbol +\
                       ', pool price=' + "{:1.5f}".format(pool_price) +\
                        ', swap price=' + "{:1.5f}".format(swap_price) + ', pool liq-at-tick=' +\
                        '{:1.0f}'.format(pool_liquidity / 10 ** (0.5 * (init.token0_decimal + init.token1_decimal))))
        elif amount0 < 0: #N.B. token1 is supplied in i.e. longShort = -1
            #N.B. swap price before pool fees
            swap_price /= 1. - init.pool_fee / 1000000
            slippage_and_pool_fee_token1 = - (amount1 / 10**init.token1_decimal + amount0 / 10**init.token0_decimal / pool_price) # < 0
            logger.info(network + ', swap() succedeed: block=' + str(tx_receipt["blockNumber"]) +\
                       ', amountIn=' + "{:1.4f}".format(amount1 / 10**init.token1_decimal) + ' ' + init.token1_symbol +\
                       ', amountOut=' + "{:1.4f}".format(amount0 / 10**init.token0_decimal) + ' ' + init.token0_symbol +\
                       ', slippage & pool fee=' + "{:1.4f}".format(slippage_and_pool_fee_token1) + ' ' + init.token1_symbol +\
                       ', pool price=' + "{:1.5f}".format(pool_price) +\
                       ', swap price=' + "{:1.5f}".format(swap_price) + ', pool liq-at-tick=' +\
                       '{:1.0f}'.format(pool_liquidity / 10 ** (0.5 * (init.token0_decimal + init.token1_decimal))) )


    return gas_fee, pool_liquidity, pool_price, swap_price, slippage_and_pool_fee_token1, nonce

#N.B. Size-split swapping: if amount_to_swap_token0 > 0, swap token0 to token1; if amount_to_swap_token0 < 0, swap token1 to token0;
def swap_wrapped(network='mumbai',price=1000., amount_to_swap_token0=0.001, amount_out_min=0., max_fee_per_gas=MAX_FEE_PER_GAS, max_priority_fee_per_gas=MAX_PRIORITY_FEE_PER_GAS):

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

    swap(network, price, amount_to_swap_token0, max_fee_per_gas, max_priority_fee_per_gas, address=Address, private_key=privateKey)

import sys
if __name__ == '__main__':
    if len(sys.argv) == 2: #network
        swap_wrapped(amount0=str(sys.argv[1]))
    elif len(sys.argv) == 4: # network, amount0, amount1
        swap_wrapped(network=str(sys.argv[1]), amount0=eval(sys.argv[2]), amount1=eval(sys.argv[3]))
    elif len(sys.argv) == 6: # network, amount0, amount1, max_fee_per_gas, max_priority_fee_per_gas
        swap_wrapped(network=str(sys.argv[1]), amount0=eval(sys.argv[2]), amount1=eval(sys.argv[3]), amount_out_min=0., max_fee_per_gas=eval(sys.argv[4]), max_priority_fee_per_gas=eval(sys.argv[5]))
    else:
        print("Wrong number of inputs!")

