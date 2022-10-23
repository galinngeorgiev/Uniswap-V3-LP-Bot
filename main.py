__author__ = "Galin Georgiev"
__copyright__ = "Copyright 2022, GammaDynamics, LLC"
__version__ = "1.1.0.0"


import numpy as np

from toolbox import *
from global_params import *
from swap import size_split_swap
from mint import mint
from increaseLiquidity import increaseLiquidity
from decreaseLiquidity import decreaseLiquidity
from collect import collect
from burn import burn
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

def main(network='mumbai'):
    import time

    #initialize tx
    i, block_num, price_list, price, price_median, price_mad, max_price_mad_time, swap_price, max_price_mad =\
        0, None, [], None, 0., 0., 0., 0., 0.
    blockNumber_init, price_init = None, None
    pool_liquidity_list, pool_liquidity_median, pool_liquidity_LP = [], 0., 0.
    tokenIds, tokenIds_burned, liquidities = [], [],  NUM_LP * [None]
    priceLower, tickLower, priceUpper, tickUpper, priceLP, swap_volume_token1, rel_swap_volume_token1, swap_flow_token1 =\
            NUM_LP * [None], NUM_LP * [None], NUM_LP * [None], NUM_LP * [None], NUM_LP * [None], NUM_LP * [0.], NUM_LP * [0.], NUM_LP * [0.]
    amount0_invested, amount1_invested, asset_ratio_01_LP, asset_ratio_01, asset0_ratio, asset1_ratio =\
            NUM_LP * [None], NUM_LP * [None], NUM_LP * [None], NUM_LP * [None], NUM_LP * [None], NUM_LP * [None]
    tx_invested_token1, tx_borrow_invested_token1, tx_collected_token1, tx_borrow_pl_bp = NUM_LP * [0.], NUM_LP * [0.], NUM_LP * [0.], NUM_LP * [0.]                  
    RL_v2_bp, delta_RL_v2, v3_v2_mult_factor, RL_v3_bp, delta_RL_v3, LP_fees_bp = NUM_LP * [0.], NUM_LP * [0.], NUM_LP * [0.], NUM_LP * [0.], NUM_LP * [0.],  NUM_LP * [0.]
    tx_count_hedge_RL, tx_hedge_RL_amount, last_RL_bp, tx_hedge_RL_pl_bp, hedge_RL_pl_bp = NUM_LP * [0], NUM_LP * [0.], NUM_LP * [0.], NUM_LP * [0.], NUM_LP * [0.]
    tx_amount_to_swap = 0.
    mint_time, ITM_duration, OTM_duration, decreaseLiquidity_time = NUM_LP * [None], NUM_LP * [0], NUM_LP * [0], NUM_LP * [None]
    #unwind_distance_to_bound = UNWIND_DIST_TO_BOUND_PER / 100

    #initialize session
    session_count_LP, session_count_mint, session_count_LP_SWAP, session_count_unwind_stop, session_count_unwind_pool_liq, session_count_unwind_max_price_mad,\
            session_count_unwind_signed_quantity, session_count_unwind_distance, session_count_hedge_RL, session_count_swaps, session_count_unwind_flow =\
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    session_LP_fees_bp, session_RL_bp, session_pl_token1, session_pl_bp, session_borrow_pl_token1, session_borrow_pl_bp =\
            NUM_LP * [0.], NUM_LP * [0.], NUM_LP * [0.], NUM_LP * [0.], NUM_LP * [0.], NUM_LP * [0.]
    session_hedge_RL_pl_bp, session_slippage_and_pool_fee_pl_bp, session_res_num_token0, session_res_num_token1 = 0., 0., 0., 0.
    session_ITM_duration, session_OTM_duration = NUM_LP * [0], NUM_LP * [0]

    #initialize flags
    flag_change_tokenIds, flag_mint, flag_increaseLiquidity, flag_hedgeRL, flag_decreaseLiquidity, flag_collect, flag_burn =\
        False, False, True, True, True, True, True
    flag_failed_tx, count_failed_tx = False, 0
    max_fee_per_gas, max_priority_fee_per_gas, slippage_per = MAX_FEE_PER_GAS, MAX_PRIORITY_FEE_PER_GAS, SLIPPAGE_PER
    

    logger.info('')
    logger.info(network + ', START session')
    start_time, iteration_time = time.time(), time.time()
    global HEDGE_RL
    hedge_RL = HEDGE_RL
    init = Initialization(network)

    #get private key with a password
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

    

   #main loop
    while i <= int(RUNTIME_SEC / DELAY_LOOP_SEC):
        #N.B. Increase gas, if tx failed
        if flag_failed_tx and  max_fee_per_gas / MAX_FEE_PER_GAS <= MAX_MULT_FACTOR_GAS_REPLACE:
            max_fee_per_gas, max_priority_fee_per_gas  = int(MULT_GAS_FACTOR_REPLACE * max_fee_per_gas), int(MULT_GAS_FACTOR_REPLACE * max_priority_fee_per_gas)
        else:
            max_fee_per_gas, max_priority_fee_per_gas = MAX_FEE_PER_GAS, MAX_PRIORITY_FEE_PER_GAS
        
        #loop delay
        if not flag_failed_tx:
            time.sleep(DELAY_LOOP_SEC)
        logger.info('')
        logger.info(network + ', main iteration = ' + str(i))
        #print(i)

        ######################################################################
        #1. obtain the current LP positions: do not run (incurs >= 0.5s delay) if not flag_change_tokenIds (changed only on mint() or burn())
        if (not flag_failed_tx) and flag_change_tokenIds:
            flag_change_tokenIds = False

            result = current_LP_positions(network, address=Address, init=init) 
            if isinstance(result, list):
                tokenIds = result
                #N.B. Sometimes Alchemy API returns already burned tokens, so check for that!
                tokenIds = [i for i in tokenIds if i not in tokenIds_burned]
                    

            else:
                i += 1
                continue


        #######################################################################
        #1a. Checks
        if i == 0 and len(tokenIds) > 0:
            logger.error(network + ', there are NFTs in this account with ID-s ' + str(tokenIds) + ', burn them with burn(tokenId) in burn.py! Stop main()!')
            logger.info('network, END session')
       
        #####################################################################
        #2. obtain the current pool price: the fuction returns False if no updates!
        if (not flag_failed_tx) and i < int(RUNTIME_SEC / DELAY_LOOP_SEC) - MAX_ATTEMPS_FAILED_TX:
            result = current_pool_price(network, block_num, price_list, price_median, pool_liquidity_list, pool_liquidity_median, \
                        price_mad, max_price_mad, priceLower, priceUpper, swap_volume_token1, rel_swap_volume_token1, swap_flow_token1, init=init)      
            if isinstance(result, list):
                GMTtimeStamp, block_num, txIx, price_list, price_median, pool_liquidity_list, pool_liquidity_median, signed_token1_quantity,\
                                price_mad, max_price_mad, swap_volume_token1, rel_swap_volume_token1, swap_flow_token1 = result
                if len(price_list) > 0:
                    price = price_list[-1]
                    if price_median == 0.:
                        price_median = price
                else:
                    logger.info(network + ', price_list = [], next iteration...')
                    i += 1
                    continue
                #if price_mad > PRICE_MAD[-1]:
                #    max_price_mad_time = time.time()

                #N.B. Too many tx-s in current_pool_price()
                if price is None:
                    logger.info(network + ', price is None, remove None from price_list, next iteration...')
                    price_list.pop()
                    i += 1
                    continue
                else:
                    price_DECIMAL = price * 10**init.token0_decimal / 10**init.token1_decimal
                    price_median_DECIMAL = price_median * 10**init.token0_decimal / 10**init.token1_decimal
            else:
                i += 1
                continue             
        
        ######################################################################
        #3. add LP position
        #N.B. There is a check above that price is not None
        #N.B. The last condition allows only NUM_LP initiations of LP positions!
        if len(tokenIds) < NUM_LP and i < int(RUNTIME_SEC / DELAY_LOOP_SEC) - MAX_ATTEMPS_FAILED_TX:
            flag_mint = False

            ##N.B. LP_SWAP unfinished: requires 'chasing' the market!
            #if LP_SWAP:
            #    amount0_LP = session_res_num_token0 * 10**init.token0_decimal if session_res_num_token0 > 0 else 0
            #    amount1_LP = session_res_num_token1 * 10**init.token1_decimal if session_res_num_token1 > 0 else 0
            #    priceLower = price_DECIMAL * (1. - LP_SWAP_DISTANCE_TO_BOUND_PER[0] / 100)
            #    priceUpper = price_DECIMAL * (1. - LP_SWAP_DISTANCE_TO_BOUND_PER[-1] / 100)
            #    if amount0_LP > 0 or amount1_LP > 0:
            #        flag_mint = True
            #else:
            amount0_LP = MAX_NUM_TOKEN0_LP * 10**init.token0_decimal
            amount1_LP = np.min([MAX_NUM_TOKEN1_LP, MAX_NUM_TOKEN0_LP / price]) * 10**init.token1_decimal
            #N.B. LP_distance_to_bound from beginning to end of quiet hours
            if (int(time.strftime('%w', time.gmtime())) != 6 and int(time.strftime('%w', time.gmtime())) != 0 and\
                    (int(time.strftime('%H', time.gmtime())) >= QUIET_HOURS_START[0] and int(time.strftime('%H', time.gmtime())) < QUIET_HOURS_END[-1])):
                LP_distance_to_bound = LP_DISTANCE_TO_BOUND_PER[-1] / 100
                #unwind_distance_to_bound = UNWIND_DIST_TO_BOUND_MIN_PER / 100 * LP_distance_to_bound
                logger.info(network + ", LP_distance_to_bound = " +\
                    "{:1.2f}".format(LP_distance_to_bound * 100) + "% from beginning to end of quiet hours!")
            else:
                LP_distance_to_bound = LP_DISTANCE_TO_BOUND_PER[0] / 100

            #N.B. Do not initiate during quiet hours
            if not (int(time.strftime('%w', time.gmtime())) != 6 and int(time.strftime('%w', time.gmtime())) != 0 and\
                    ((int(time.strftime('%H', time.gmtime())) >= QUIET_HOURS_START[0] and int(time.strftime('%H', time.gmtime())) < QUIET_HOURS_END[0]) or\
                    (int(time.strftime('%H', time.gmtime())) >= QUIET_HOURS_START[1] and int(time.strftime('%H', time.gmtime())) < QUIET_HOURS_END[1]))):
                flag_mint = True
            
                #N.B. Do not initiate if liquidity decreases!
                if EVENT_LOGS and len(pool_liquidity_list) > 0 and\
                    pool_liquidity_list[-1] >= np.min([pool_liquidity_median, pool_liquidity_list[-1]]) * MIN_POOL_LIQUIDITY_PER[0] / 100:
                    flag_mint = flag_mint and True
                else:
                    logger.info('')
                    logger.info("NO LP INITIALIZATION because EVENT_LOGS=F or pool liq = " +\
                                    "{:1.0f}".format(pool_liquidity_list[-1] / 10 ** (0.5 * (init.token0_decimal + init.token1_decimal))) +\
                                    " < pool liq median * threshold= " + "{:1.0f}".format(pool_liquidity_median  / 10 ** (0.5 * (init.token0_decimal + init.token1_decimal)) * MIN_POOL_LIQUIDITY_PER[0] / 100))
                    flag_mint = False

                #N.B. Do not initiate if price_mad too high!
                if price_mad <= PRICE_MAD[0]: # and (time.time() - max_price_mad_time) / 60 >= PRICE_MAD_WAIT_TIME_MIN:
                    flag_mint = flag_mint and True
                else:
                    logger.info('')
                    logger.info("NO LP INITIALIZATION because price_mad = " + "{:1.5f}".format(price_mad) +\
                                " > " + str(PRICE_MAD[0]) )
                    flag_mint = False

                #N.B. Do not initiate if abs(signed_token1_quantity) is too small &
                #N.B.  MIN_INIT_AFTER_BLOCKS or MIN_INIT_AFTER_PRICE_RET_BP is not passed!
                if blockNumber_init is None:
                    if i != 0 and abs(signed_token1_quantity) / pool_liquidity_list[-1] *\
                        10 ** (0.5 * (init.token0_decimal + init.token1_decimal)) >= MIN_INIT_TOKEN1_QUANTITY_TO_TVL_BP / 10000:
                        blockNumber_init, price_init = block_num, price #if signed_token1_quantity > 0 else -price
                        logger.info(network + ", blockNumber_init = " + str(blockNumber_init) + ", price_init = " +\
                            "{:1.5f}".format(price_init) + ", scaled abs(signed_token1_quantity) / pool_liquidity_list[-1] = " +\
                            "{:1.3f}".format(abs(signed_token1_quantity) / pool_liquidity_list[-1] * 10 ** (0.5 * (init.token0_decimal + init.token1_decimal)) * 10000) +\
                            " >=  MIN_INIT_TOKEN1_QUANTITY_TO_TVL_BP = " + str(MIN_INIT_TOKEN1_QUANTITY_TO_TVL_BP))
                    else:
                        logger.info(network + ", NO LP INITIALIZATION because blockNumber_init/price_init is not set yet: " +\
                            "scaled abs(signed_token1_quantity) / pool_liquidity_list[-1] = " +\
                            "{:1.3f}".format(abs(signed_token1_quantity) / pool_liquidity_list[-1] * 10 ** (0.5 * (init.token0_decimal + init.token1_decimal)) * 10000) +\
                            " <  MIN_INIT_TOKEN1_QUANTITY_TO_TVL_BP = " + str(MIN_INIT_TOKEN1_QUANTITY_TO_TVL_BP))
    
                    flag_mint = False
                else:
                    if  block_num >= blockNumber_init + MIN_INIT_AFTER_BLOCKS:
                        if abs(price - price_init) / price_init * 10000 >= MIN_INIT_AFTER_PRICE_RET_BP: # and (price - price_init) * price_init > 0:
                            flag_mint = flag_mint and True
                        else: 
                            #logger.info('')
                            logger.info(network + ", blockNumber_init = " + str(blockNumber_init) + ", price_init = " + "{:1.5f}".format(price_init))
                            logger.info(network + ", NO LP INITIALIZATION because abs(price - price_init) / price_init = " +\
                                    "{:1.2f}".format(abs(price - price_init) / price_init * 10000) +\
                                    " bp < MIN_INIT_AFTER_PRICE_RET_BP = " + str(MIN_INIT_AFTER_PRICE_RET_BP) + " bp")
                            flag_mint = False
                        blockNumber_init, price_init = None, None
                    else:
                        logger.info(network + ", blockNumber_init = " + str(blockNumber_init) + ", price_init = " + "{:1.5f}".format(price_init))
                        logger.info(network + ", NO LP INITIALIZATION because current block number = " +\
                                    str(block_num) + " <  blockNumber_init = " + str(blockNumber_init) +\
                                    " + MIN_INIT_AFTER_BLOCKS = " + str(MIN_INIT_AFTER_BLOCKS) )
                        flag_mint = False
            else:
                flag_mint = False
                logger.info(network + ", NO LP INITIALIZATION during quiet hours!")
            
            #N.B. Do not mint if end of iterations: the last MAX_ATTEMPS_FAILED_TX iterations reserved for unwinding
            if i >= int(RUNTIME_SEC / DELAY_LOOP_SEC) - MAX_ATTEMPS_FAILED_TX:
                flag_mint = False

            if flag_mint:
                #N.B. middle LP is always symmetric in-the-money
                priceLower[int((NUM_LP - 1) / 2)] = price_DECIMAL * (1. - LP_distance_to_bound)
                priceUpper[int((NUM_LP - 1) / 2)] = price_DECIMAL * (1. + LP_distance_to_bound)
                #N.B. Assure the the price ranges are adjacent!
                for k in reversed(range(int((NUM_LP - 1) / 2))):
                     priceLower[k] = price_DECIMAL * (1. + (2 * k - NUM_LP) * LP_distance_to_bound)
                     priceUpper[k] = priceLower[k + 1]
                for k in range(int((NUM_LP - 1) / 2) + 1, NUM_LP):
                     priceLower[k] = priceUpper[k - 1]
                     priceUpper[k] = price_DECIMAL * (1. + (2 * (k + 1) - NUM_LP) * LP_distance_to_bound)

                if count_failed_tx < MAX_ATTEMPS_FAILED_TX:

                    if not flag_failed_tx:
                        j = 0
                    while j < NUM_LP:
                        #N.B. Re-compute priceLower, priceUpper
                        #N.B. tick = log(price) / log(1.0001): (6.1) in https://uniswap.org/whitepaper-v3.pdf
                        tickLower[j] = np.log(priceLower[j]) / np.log(1.0001)
                        tickUpper[j] = np.log(priceUpper[j]) / np.log(1.0001)
                        #tick spacing >> 1, depending on the pool fee: section 4 in https://uniswap.org/whitepaper-v3.pdf
                        if init.pool_fee == 500:
                            tickLower[j], tickUpper[j] = int(tickLower[j] - tickLower[j] % 10), int(tickUpper[j] + (10 - tickUpper[j] % 10))
                        elif init.pool_fee == 3000:
                            tickLower[j], tickUpper[j] = int(tickLower[j] - tickLower[j] % 60), int(tickUpper[j] + (60 - tickUpper[j] % 60))
                        elif init.pool_fee == 10000:
                            tickLower[j], tickUpper[j] = int(tickLower[j] - tickLower[j] % 200), int(tickUpper[j] + (200 - tickUpper[j] % 200))
                    
                        #N.B. Compute nonce in mint() in order to keep the order of mints()
                        result = mint(network, amount0ToMint=amount0_LP, amount1ToMint=amount1_LP, tickLower=tickLower[j], tickUpper=tickUpper[j], \
                                        max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas, \
                                        address=Address, private_key=privateKey, init=init)
                        priceLower[j], priceUpper[j] = 1.0001 ** tickLower[j], 1.0001 ** tickUpper[j]
                    
                        if isinstance(result, tuple):
                            tokenId, liquidity, amount0, amount1, blockNumber, nonce = result

                            #if LP_SWAP:
                            #    LP_SWAP_price_LP = (amount0  / liquidity + np.sqrt(priceLower)) ** 2
                            #    session_count_LP_SWAP += 1
                            #    logger.info(network + ", " +\
                            #                ", LP_SWAP priceLP = " + "{:1.5f}".format(LP_SWAP_price_LP / 10**init.token0_decimal * 10**init.token1_decimal) +\
                            #                ", LP_SWAP priceLower = " + "{:1.5f}".format(priceLower / 10**init.token0_decimal * 10**init.token1_decimal) +\
                            #                ", LP_SWAP priceUpper = " + "{:1.5f}".format(priceUpper / 10**init.token0_decimal * 10**init.token1_decimal) +\
                            #                ", session count LP swap tx_s = " + str(session_count_LP_SWAP) )
                            #else:
                                #N.B. Can not use '+=' on a list!
                            liquidities[j] = liquidity
                            #N.B. priceLP from line (71) in https://github.com/Uniswap/v3-periphery/blob/main/contracts/libraries/LiquidityAmounts.sol
                            #N.B. When price range is out-of-the-money, priceLP equals one of the price bound!
                            priceLP[j] = (amount0  / liquidities[j] + np.sqrt(priceLower[j])) ** 2
                            pool_liquidity_LP = pool_liquidity_list[-1]
                            hedge_RL = HEDGE_RL
                            #tx_hedge_RL_pl_bp[j], hedge_RL_pl_bp[j], last_RL_bp[j], tx_hedge_RL_amount[j], last_hedge_RL_price[j] = 0., 0., 0., 0., None
                            flag_change_tokenIds, swap_volume_token1[j], rel_swap_volume_token1[j], swap_flow_token1[j] = True, 0., 0., 0.
                            amount0_invested[j], amount1_invested[j] = amount0, amount1
                            session_count_mint += 1
                            session_count_LP += 1
                            blockNumber_init, price_init = None, None
                            tx_slippage_and_pool_fee_pl_bp, tx_count_hedge_RL[j] = 0., 0
                            tx_invested_token1[j] = amount0 / 10**init.token0_decimal / price + amount1 / 10**init.token1_decimal
                            tx_borrow_invested_token1[j] = tx_invested_token1[j]
                            mint_time[j], iteration_time, ITM_duration[j], OTM_duration[j] = time.time(), time.time(), 0, 0
                            if amount1 != 0:
                                asset_ratio_01_LP[j] = amount0 / price / amount1
                            else:
                                asset_ratio_01_LP[j] = np.inf
                                    
                            logger.info(network + ", " + str(j) + "-th LP: " +
                                        " invested " + str(tx_invested_token1[j]) +\
                                        " token1, asset0/asset1 = " +  "{:1.3f}".format(asset_ratio_01_LP[j]) +\
                                        ", priceLP = " + "{:1.5f}".format(priceLP[j] / 10**init.token0_decimal * 10**init.token1_decimal) +\
                                        ", priceLower = " + "{:1.5f}".format(priceLower[j] / 10**init.token0_decimal * 10**init.token1_decimal) +\
                                        ", priceUpper = " + "{:1.5f}".format(priceUpper[j] / 10**init.token0_decimal * 10**init.token1_decimal) +\
                                        ", session count LP tx_s = " + str(session_count_LP) )
                        
                            flag_failed_tx = False
                            count_failed_tx = 0

                            #N.B. run current pool price again: the fuction returns False if no updates!
                            result = current_pool_price(network, block_num, price_list, price_median, pool_liquidity_list, pool_liquidity_median,\
                                price_mad, max_price_mad, priceLower, priceUpper, swap_volume_token1, rel_swap_volume_token1, swap_flow_token1, init=init)      
                            if isinstance(result, list):
                                GMTtimeStamp, block_num, txIx, price_list, price_median, pool_liquidity_list, pool_liquidity_median, signed_token1_quantity,\
                                    price_mad, max_price_mad, swap_volume_token1_output, rel_swap_volume_token1_output, swap_flow_token1_output = result
                                #N.B. Sometimes curent_pool_price() reports tx-s with block numbers not exceeding LP block and hence not earning fees!
                                if block_num > blockNumber:
                                    swap_volume_token1, rel_swap_volume_token1, swap_flow_token1=\
                                        swap_volume_token1_output, rel_swap_volume_token1_output, swap_flow_token1_output

                            j += 1
                            continue
                        else:
                            nonce = None
                            if not result:
                                #N.B. nonce=None triggers web3 getting a nonce
                                priceLP[j], nonce = None, None
                                flag_failed_tx = True
                                count_failed_tx += 1
                                break #N.B. Break the inner loop
                else:
                    logger.error(network + ', mint() for ' + str(j) + '-th LP failed MAX_ATTEMPS_FAILED_TX = ' + str(MAX_ATTEMPS_FAILED_TX) + ' times, stop main()!')
                    #logger.info(network + ", session p&l = " + str(session_pl_token1[j]) + " token1" +\
                    #                ", " + "{:1.2f}".format(session_pl_bp[j]) + " bp")
                    logger.info(network + ", session (w/o possible swap) for " + str(j) + "-th LP borrow p&l " +\
                            #": i) w/o hedge RL=" + str(session_borrow_pl_token1[j]) + " token1" +\
                            "{:1.2f}".format(session_borrow_pl_bp[j]) + " bp" ) # +\
                            #", iii) slippage & pool fee=" + "{:1.2f}".format(session_slippage_and_pool_fee_pl_bp) + " bp" +\
                            #", iv) hedge RL=" + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
                    logger.info('network, END session')
                    return False

                    
               
        #######################################################################    
        else:
            unwind_condition = False
            unwind_distance_to_bound = UNWIND_DIST_TO_BOUND_PER / 100 * LP_distance_to_bound
            logger.info(network + ", LP unwind dist-to-bound = " + "{:1.2f}".format(unwind_distance_to_bound * 100) + "%")
            ###################################################################################
            #N.B. Reporting in log
            if not flag_failed_tx:
                j = 0

                while j < NUM_LP and i < int(RUNTIME_SEC / DELAY_LOOP_SEC) - MAX_ATTEMPS_FAILED_TX:
                    #N.B. 3a. Estimate quantities to report: RL, asset ratio, LP fees
                    #N.B. Rebalancing Loss (RL)
                    #N.B. see my Crypto doc, Defi Swaps > Uniswap > RL > Uniswap V2 & V3 > RL or > Greeks: https://docs.google.com/document/d/1K83HF3-A9NqFKtjF-wcf6Kduz0r-J0yYchiyOCfaKgo/edit
                    tx_borrow_invested_token1[j] = amount0_invested[j] / 10**init.token0_decimal / price + amount1_invested[j] / 10**init.token1_decimal
                    if priceLower[j] is not None and priceUpper[j] is not None:
                        if price_DECIMAL >= priceLower[j] and price_DECIMAL <= priceUpper[j]:
                            #if priceLP[j] > priceUpper[j]:
                            #    RL_v2_bp[j] = 10000 * (2 * np.sqrt(price_DECIMAL / priceUpper[j]) / (price_DECIMAL / priceUpper[j] + 1) - 1)
                            #    delta_RL_v2[j] = (1 - price_DECIMAL / priceUpper[j]) / np.sqrt(price_DECIMAL / priceUpper[j]) / (price_DECIMAL / priceUpper[j] + 1)**2
                            #    v3_v2_mult_factor[j] = (price_DECIMAL / priceUpper[j] + 1) / (1 - np.sqrt(priceLower[j] / priceUpper[j]))
                            #elif priceLP[j] < priceLower[j]:
                            #    RL_v2_bp[j] = 10000 * (2 * np.sqrt(price_DECIMAL / priceLower[j]) / (price_DECIMAL / priceLower[j] + 1) - 1)
                            #    delta_RL_v2[j] = (1 - price_DECIMAL / priceLower[j]) / np.sqrt(price_DECIMAL / priceLower[j]) / (price_DECIMAL / priceLower[j] + 1)**2
                            #    v3_v2_mult_factor[j] = (price_DECIMAL / priceLower[j] + 1) / (price_DECIMAL / priceLower[j] * (1 - np.sqrt(priceLower[j] / priceUpper[j])))
                            #else:
                            RL_v2_bp[j] = 10000 * (2 * np.sqrt(price_DECIMAL / priceLP[j]) / (price_DECIMAL / priceLP[j] + 1) - 1)
                            delta_RL_v2[j] = (1 - price_DECIMAL / priceLP[j]) / np.sqrt(price_DECIMAL / priceLP[j]) / (price_DECIMAL / priceLP[j] + 1)**2
                            v3_v2_mult_factor[j] = (price_DECIMAL / priceLP[j] + 1) / \
                                    (price_DECIMAL / priceLP[j] * (1 - np.sqrt(priceLP[j] / priceUpper[j])) + (1 - np.sqrt(priceLower[j] / priceLP[j])))
                            RL_v3_bp[j] = RL_v2_bp[j] * v3_v2_mult_factor[j] 
                            #N.B. True only if Price_LP is geometric average of priceUpper & priceLower 
                            delta_RL_v3[j] = delta_RL_v2[j] * v3_v2_mult_factor[j]

                            #N.B. adjust for multiple LP-s
                            RL_v2_bp[j] *= tx_borrow_invested_token1[j] / sum(tx_borrow_invested_token1)
                            RL_v3_bp[j] *= tx_borrow_invested_token1[j] / sum(tx_borrow_invested_token1)

                            #time
                            ITM_duration[j] += time.time() - iteration_time
                        else:
                            OTM_duration[j] += time.time() - iteration_time
                        
                        #N.B. Asset ratio
                        if price_DECIMAL < priceLower[j] or priceLP[j] == priceUpper[j]:
                            asset_ratio_01[j] = 0.
                            asset0_ratio[j], asset1_ratio[j] = 0., 1.
                        elif price_DECIMAL > priceUpper[j] or priceLP[j] == priceLower[j]:
                            asset_ratio_01[j] = np.inf
                            asset0_ratio[j], asset1_ratio[j] = 1., 0.
                        else:
                            #N.B. see my Crypto doc, Defi Swaps > Uniswap > V3 > Balances: https://docs.google.com/document/d/1K83HF3-A9NqFKtjF-wcf6Kduz0r-J0yYchiyOCfaKgo/edit
                            asset_ratio_01[j] = (np.sqrt(price_DECIMAL) - np.sqrt(priceLower[j])) / (np.sqrt(priceLP[j]) - np.sqrt(priceLower[j])) \
                                        / ((1 / np.sqrt(price_DECIMAL) - 1 / np.sqrt(priceUpper[j])) / (1 / np.sqrt(priceLP[j]) - 1 / np.sqrt(priceUpper[j]))) \
                                        / price_DECIMAL * priceLP[j] \
                                        #* asset_ratio_01_LP[j]
                            asset0_ratio[j], asset1_ratio[j] = asset_ratio_01[j] / (asset_ratio_01[j] + 1), 1 / (asset_ratio_01[j] + 1.)
                       
                        #N.B. LP Fees
                        #N.B. Alchemy transfer tx-s API does not report txIx, tx order in the same block is unknown & rel_swap_volume_token1 is wrong!
                        #N.B. If collect() or burn() return False (swap() does not return False), liquidities=[]
                        #N.B. swap_volume_token1[j] & rel_swap_volume_token1[j] are computed in current_pool_price(), using priceLower, priceUpper
                        if PRICE_ALCHEMY and (not EVENT_LOGS):
                            if pool_liquidity_median is not None:
                                LP_fees_bp[j] = liquidities[j] / pool_liquidity_median * swap_volume_token1[j] * init.pool_fee / 1000000 / sum(tx_borrow_invested_token1) * 10000
                            else:
                                #N.B. Triggers STOP_LOSS!
                                LP_fees_bp[j] = 0. #-np.infty
                        else:
                            LP_fees_bp[j] = liquidities[j] * rel_swap_volume_token1[j] * init.pool_fee / 1000000 / sum(tx_borrow_invested_token1) * 10000
                        
                        #N.B. Triggers STOP_LOSS!
                        #else:
                        #    LP_fees_bp = -np.infty

                        ##N.B. Hedge RL p&l
                        #tx_borrow_invested_token1[j] = amount0_invested[j] / 10**init.token0_decimal / price + amount1_invested[j] / 10**init.token1_decimal
                        ##N.B. If last_hedge_RL_price is not set
                        #if last_hedge_RL_price[j] is None:
                        #    last_hedge_RL_price[j] = price
                        ##N.B. tx_hedge_RL_amount / price is the tx hedge RL amount in token1
                        ##N.B. tx hedge RL P&L is a sum tx_hedge_RL_pl_bp + hedge_RL_pl_bp:  hedge_RL_pl_bp measure hedge RL P&L only from the last hedge!
                        #hedge_RL_pl_bp[j] = (price - last_hedge_RL_price[j]) * tx_hedge_RL_amount[j] / price / tx_borrow_invested_token1[j] * 10000
                
                
                        ##N.B. First-passage time density does not change if distance varies proportionally to vol: https://en.wikipedia.org/wiki/First-hitting-time_model
                        #if price_mad != 0.:
                        #    #N.B. if tx time elapsed is too small (volume is too small) or the market is mean-reverting, decrease only (no increase) of unwind distance to bound
                        #    if (time.time() - mint_time) / 60 < DECREASE_ONLY_UNWIND_DIST_TIME_MIN or\
                        #        (swap_volume_token1 == 0. or abs(swap_flow_token1) /  swap_volume_token1 < SWAP_FLOW_THRESHOLD_PER / 100):
                        #        unwind_distance_to_bound = np.min([unwind_distance_to_bound, \
                        #                                       UNWIND_DIST_TO_BOUND_PER / 100 * LP_distance_to_bound / (price_mad * init.unwind_dist_price_mad_mult)])
                        #    else:
                        #        unwind_distance_to_bound = UNWIND_DIST_TO_BOUND_PER / 100 * LP_distance_to_bound  / (price_mad * init.unwind_dist_price_mad_mult)
                        #else:
                        #    #N.B. if tx time elapsed is too small (volume is too small) or the market is mean-reverting, decrease only (no increase) of unwind distance to bound
                        #    if (time.time() - mint_time) / 60 < DECREASE_ONLY_UNWIND_DIST_TIME_MIN or\
                        #        (swap_volume_token1 == 0. or abs(swap_flow_token1) /  swap_volume_token1 < SWAP_FLOW_THRESHOLD_PER / 100):
                        #        unwind_distance_to_bound = np.min([unwind_distance_to_bound, \
                        #                                        UNWIND_DIST_TO_BOUND_PER / 100 * LP_distance_to_bound])
                        #    else:
                        #        unwind_distance_to_bound = UNWIND_DIST_TO_BOUND_PER / 100 * LP_distance_to_bound

                        ##N.B. unwind_distance_to_bound can not be out of the range (UNWIND_DIST_TO_BOUND_MIN_PER, UNWIND_DIST_TO_BOUND_MAX_PER) / 100 * LP_distance_to_bound
                        #unwind_distance_to_bound = np.min([UNWIND_DIST_TO_BOUND_MAX_PER / 100 * LP_distance_to_bound, unwind_distance_to_bound])
                        #unwind_distance_to_bound = np.max([UNWIND_DIST_TO_BOUND_MIN_PER / 100 * LP_distance_to_bound, unwind_distance_to_bound])

                        logger.info(network + ", " + str(j) + "-th LP" +\
                                            ": dist-to-lower-bound = " + "{:1.2f}".format((1. - priceLower[j] / price_DECIMAL) * 100) + "%" +\
                                            ", dist-to-upper-bound = " + "{:1.2f}".format((priceUpper[j] / price_DECIMAL - 1.) * 100) + "%" +\
                                            #", unwind dist-to-bound = " + "{:1.2f}".format(unwind_distance_to_bound * 100) + "%" +\
                                            "; ITM dur = " + "{:1.1f}".format(ITM_duration[j] / 60) + " min" +\
                                            "; OTM dur = " + "{:1.1f}".format(OTM_duration[j] / 60) + " min" +\
                                            "; dur = " + "{:1.1f}".format((time.time() - mint_time[j]) / 60) + " min" +\
                                            #", initial asset0/asset1 = " +  "{:1.3f}".format(asset_ratio_01_LP[j]) +\
                                            ", current rel asset0/asset1 = " +  "{:1.3f}".format(asset_ratio_01[j]) )

                        logger.info(network + ", " + str(j) + "-th LP" +\
                                                ": LP fees = " +  "{:1.2f}".format(LP_fees_bp[j]) + " bp" +\
                                                ", RL_v2 = " +  "{:1.2f}".format(RL_v2_bp[j]) + " bp" +\
                                                #", delta_RL_v2 = " +  "{:1.4f}".format(delta_RL_v2[j]) +\
                                                ", RL_v3 = " +  "{:1.2f}".format(RL_v3_bp[j]) + " bp" +\
                                                #", delta_RL_v3 = " +  "{:1.4f}".format(delta_RL_v3[j])+\
                                                #", hedge RL p&l = " +  "{:1.2f}".format(tx_hedge_RL_pl_bp[j] + hedge_RL_pl_bp[j]) + " bp" +\
                                                ", total p&l = " +  "{:1.2f}".format(LP_fees_bp[j] + RL_v3_bp[j] + tx_hedge_RL_pl_bp[j] + hedge_RL_pl_bp[j]) + " bp")
                    
                    j += 1
                    continue
                iteration_time = time.time()
                

            if (not flag_decreaseLiquidity) or (not flag_collect) or (not flag_burn):
                unwind_condition = True
            #N.B. Last MAX_ATTEMPS_FAILED_TX iterations reserved for unwinding
            elif i >= int(RUNTIME_SEC / DELAY_LOOP_SEC) - MAX_ATTEMPS_FAILED_TX:
                unwind_condition = True 
            #N.B. Unwind during quiet hours
            elif (int(time.strftime('%w', time.gmtime())) != 6 and int(time.strftime('%w', time.gmtime())) != 0 and\
                ((int(time.strftime('%H', time.gmtime())) >= QUIET_HOURS_START[0] and int(time.strftime('%H', time.gmtime())) < QUIET_HOURS_END[0]) or\
                (int(time.strftime('%H', time.gmtime())) >= QUIET_HOURS_START[1] and int(time.strftime('%H', time.gmtime())) < QUIET_HOURS_END[1]))):
                unwind_condition = True
                logger.info(network + ", decreaseLiquidity() during quiet hours!")
            else:
                #N.B. not working properly: after execution, has to go straight to mint(), without decreaseLiquidity(), but not otherwise!
                #if INCREASE_LIQUIDITY:
                ######################################################################################
                ##N.B. 3b. IncreaseLiquidity()
                ##N.B. Determine unwind_distance_to_bound
                #    ##N.B. If last LP tx P&L < 0, increase price bounds, otherwise desrease price bounds
                #    #if tx_borrow_pl_bp > 0.:
                #    #    LP_distance_to_bound -= LP_distance_to_bound_STEP_PER / 100
                #    #elif tx_borrow_pl_bp < 0.:
                #    #    LP_distance_to_bound += LP_distance_to_bound_STEP_PER / 100
                #    ##N.B. LP_distance_to_bound can not < LP_DISTANCE_TO_BOUND_MIN_PER / 100 or > LP_DISTANCE_TO_BOUND_MAX_PER / 100
                #    #LP_distance_to_bound = np.max([LP_distance_to_bound, LP_DISTANCE_TO_BOUND_MIN_PER / 100])
                #    #LP_distance_to_bound = np.min([LP_distance_to_bound, LP_DISTANCE_TO_BOUND_MAX_PER / 100])
                #    #if tx_borrow_pl_bp > 0.:
                #    #    logger.info("last LP borrow tx P&L: " + "{:1.2f}".format(tx_borrow_pl_bp) +\
                #    #        " bp, decrease range; current LP distance to bound = " + "{:1.2f}".format(LP_distance_to_bound * 100) + "%")
                #    #elif tx_borrow_pl_bp < 0.:
                #    #    logger.info("last LP borrow tx P&L: " + "{:1.2f}".format(tx_borrow_pl_bp) +\
                #    #        " bp, increase range; current LP distance to bound = " + "{:1.2f}".format(LP_distance_to_bound * 100) + "%")
                
                
                    
                #    if min([1. - priceLower / price_DECIMAL, priceUpper / price_DECIMAL - 1.]) > unwind_distance_to_bound:
                #        logger.info(network + ", dist-to-lower-bound = " + "{:1.2f}".format((1. - priceLower / price_DECIMAL) * 100) + "%" +\
                #                        ", dist-to-upper-bound = " + "{:1.2f}".format((priceUpper / price_DECIMAL - 1.) * 100) + "%" +\
                #                        ", unwind dist-to-bound = " + "{:1.2f}".format(unwind_distance_to_bound * 100) + "%" )

                #        if blockNumber_init is not None:
                #            if block_num >= blockNumber_init + MIN_INIT_AFTER_BLOCKS:

                #                if abs(price - price_init) / price_init * 10000 >= MIN_INIT_AFTER_PRICE_RET_BP: # and (price - price_init) * price_init > 0:
                #                    if count_failed_tx < MAX_ATTEMPS_FAILED_TX:
                  
                #                        result = increaseLiquidity(network, tokenIds[-1],\
                #                                amount0ToMint=tx_res_num_token0, amount1ToMint=tx_res_num_token1, \
                #                                max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas, \
                #                                address=Address, private_key=privateKey, init=init)

                #                        if isinstance(result, tuple):
                #                            liquidity, amount0, amount1, blockNumber, nonce = result

                #                            #N.B. Can not use '+=' on a list!
                #                            liquidities.append(liquidity)
                                                                       
                #                            #N.B. priceLP from line (71) in https://github.com/Uniswap/v3-periphery/blob/main/contracts/libraries/LiquidityAmounts.sol
                #                            priceLP = (amount0  / liquidities[-1] + np.sqrt(priceLower)) ** 2
                #                            pool_liquidity_LP = pool_liquidity_list[-1]
                #                            hedge_RL = HEDGE_RL
                #                            tx_hedge_RL_pl_bp, hedge_RL_pl_bp, last_RL_bp, tx_hedge_RL_amount, last_hedge_RL_price = 0., 0., 0., 0., None
                #                            flag_change_tokenIds, swap_volume_token1, rel_swap_volume_token1, swap_flow_token1 = True, 0., 0., 0.
                #                            amount0_invested, amount1_invested = amount0, amount1
                #                            blockNumber_init, price_init = None, None
                #                            session_count_LP += 1
                #                            tx_slippage_and_pool_fee_pl_bp, tx_count_hedge_RL = 0., 0
                #                            tx_invested_token1 = (amount0 / priceLP + amount1) / 10**init.token1_decimal
                #                            mint_time = time.time()
                #                            if amount1 != 0:
                #                                asset_ratio_01_LP = amount0 / priceLP / amount1
                #                            else:
                #                                asset_ratio_01_LP = 1
                                    
                #                            logger.info(network + ", tx invested " + str(tx_invested_token1) +\
                #                                        " token1, LP asset0/asset1 = " +  "{:1.3f}".format(asset_ratio_01_LP) +\
                #                                        ", priceLP = " + "{:1.5f}".format(priceLP / 10**init.token0_decimal * 10**init.token1_decimal) +\
                #                                        ", priceLower = " + "{:1.5f}".format(priceLower / 10**init.token0_decimal * 10**init.token1_decimal) +\
                #                                        ", priceUpper = " + "{:1.5f}".format(priceUpper / 10**init.token0_decimal * 10**init.token1_decimal) +\
                #                                        ", session count LP tx_s = " + str(session_count_LP) )
                        
                #                            flag_failed_tx, flag_increaseLiquidity = False, True
                #                            count_failed_tx = 0

                #                            #N.B. run current pool price again: the fuction returns False if no updates!
                #                            result = current_pool_price(network, block_num, price_list, price_median, pool_liquidity_list, pool_liquidity_median,\
                #                                price_mad, max_price_mad, priceLower, priceUpper, swap_volume_token1, rel_swap_volume_token1, swap_flow_token1, init=init)      
                #                            if isinstance(result, list):
                #                                GMTtimeStamp, block_num, txIx, price_list, price_median, pool_liquidity_list, pool_liquidity_median, signed_token1_quantity,\
                #                                    price_mad, max_price_mad, swap_volume_token1_output, rel_swap_volume_token1_output, swap_flow_token1_output = result
                #                                #N.B. Sometimes curent_pool_price() reports tx-s with block numbers not exceeding LP block and hence not earning fees!
                #                                if block_num > blockNumber:
                #                                    swap_volume_token1, rel_swap_volume_token1, swap_flow_token1=\
                #                                        swap_volume_token1_output, rel_swap_volume_token1_output, swap_flow_token1_output
                #                        else:
                #                            nonce = None
                #                            if not result:
                #                                #N.B. nonce=None triggers web3 getting a nonce
                #                                priceLP, nonce = None, None
                #                                flag_failed_tx, flag_increaseLiquidity = True, False
                #                                count_failed_tx += 1
                #                                i += 1
                #                                continue
                #                    else:
                #                        if (flag_hedgeRL and flag_decreaseLiquidity and flag_collect and flag_burn) or not flag_increaseLiquidity:
                #                            logger.error(network + ', increaseLiquidity() failed MAX_ATTEMPS_FAILED_TX = ' + str(MAX_ATTEMPS_FAILED_TX) + ' times, stop main()!')
                #                            logger.info(network + ", session p&l = " + str(session_pl_token1[j]) + " token1" +\
                #                                                    ", " + "{:1.2f}".format(session_pl_bp[j]) + " bp")
                #                           
                #                            return False


                #                else: 
                #                    #logger.info('')
                #                    logger.info(network + ", blockNumber_init = " + str(blockNumber_init) + ", price_init = " + "{:1.5f}".format(price_init))
                #                    logger.info(network + ", NO increaseLiquidity() because abs(price - price_init) / price_init = " +\
                #                            "{:1.2f}".format(abs(price - price_init) / price_init * 10000) +\
                #                            " bp < MIN_INIT_AFTER_PRICE_RET_BP = " + str(MIN_INIT_AFTER_PRICE_RET_BP) + " bp")
                                    
                #            else:
                #                logger.info(network + ", blockNumber_init = " + str(blockNumber_init) + ", price_init = " + "{:1.5f}".format(price_init))
                #                logger.info(network + ", NO increaseLiquidity() because current block number = " +\
                #                            str(block_num) + " <  blockNumber_init = " + str(blockNumber_init) +\
                #                            " + MIN_INIT_AFTER_BLOCKS = " + str(MIN_INIT_AFTER_BLOCKS) )
                            
                ####################################################################
                ##N.B. hedge RL (only mint())
                #if hedge_RL and price_mad >= PRICE_MAD[1]: # and (not LP_SWAP):
                #    if abs(RL_v3_bp - last_RL_bp) > HEDGE_RL_THRESHOLD_BP:
                        
                #        tx_borrow_invested_token1 = amount0_invested / 10**init.token0_decimal / price + amount1_invested / 10**init.token1_decimal
                #        #N.B. The final goal is tx_hedge_RL_amount = - delta_RL_v3 * tx_borrow_invested_token1
                #        amount_to_swap = - delta_RL_v3 * tx_borrow_invested_token1 - tx_hedge_RL_amount 

                #        logger.info('')
                #        logger.info(network + ", RL diff = " + "{:1.2f}".format(RL_v3_bp - last_RL_bp) + " bp" +\
                #                                ", hedge RL amount_to_swap = " + str(amount_to_swap) )
                #        #N.B. amount_to_swap > or < 0: swap amount_to_swap token0 into token1 if > 0 or swap -amount_to_swap token1 into token0 if < 0
                #        result = size_split_swap(network, price, amount_to_swap,\
                #                                max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas,\
                #                                 address=Address, private_key=privateKey, init=init, nonce=nonce)
                #        if isinstance(result, tuple):
                #            pool_liquidity, pool_price, swap_price, slippage_and_pool_fee_token1, nonce = result
                #            last_RL_bp = RL_v3_bp
                            
                #            #N.B. swap_price is wrong for small amounts, using pool_price for P&L!
                #            swap_price  = pool_price
                #            #N.B. pool_fee creates wrong p&l in the next iteration
                #            #if amount_to_swap > 0:
                #            #    swap_price *= (1. + init.pool_fee / 1000000)
                #            #else:
                #            #    swap_price /= (1. + init.pool_fee / 1000000) 
                #            #N.B. If last_hedge_RL_price is not set
                #            if last_hedge_RL_price is None:
                #                last_hedge_RL_price = price
                #            #N.B. tx_hedge_RL_amount / price is the tx accumulated hedge RL amount in token1
                #            hedge_RL_pl_bp = (swap_price - last_hedge_RL_price) * tx_hedge_RL_amount / price / tx_borrow_invested_token1 * 10000
                #            logger.info(network + ', this hedge RL p&l = ' + "{:1.4f}".format(hedge_RL_pl_bp) + 'bp' +\
                #                                  ', tx hedge RL amount = ' + str(tx_hedge_RL_amount) +\
                #                                  ', price change from prev hedge = ' + "{:1.4f}".format(swap_price - last_hedge_RL_price) +\
                #                                  ', tx_borrow_invested_token1 = ' + str(tx_borrow_invested_token1) )
                #            logger.info('')

                #            last_hedge_RL_price = swap_price
                #            #N.B. The final goal is tx_hedge_RL_amount = - delta_RL_v3 * tx_borrow_invested_token1
                #            tx_hedge_RL_amount = - delta_RL_v3 * tx_borrow_invested_token1
                #            tx_hedge_RL_pl_bp += hedge_RL_pl_bp
                #            #N.B. hedge_RL_pl_bp measure P&L only from the last hedge!
                #            hedge_RL_pl_bp = 0.
                #            tx_count_hedge_RL += 1
                #            session_count_hedge_RL += 1

                #            tx_slippage_and_pool_fee_pl_bp += slippage_and_pool_fee_token1 / tx_borrow_invested_token1 * 10000
                #            session_slippage_and_pool_fee_pl_bp += tx_slippage_and_pool_fee_pl_bp
                #            session_borrow_pl_bp[j] += tx_slippage_and_pool_fee_pl_bp
                #        else:
                #            #N.B. nonce=None triggers web3 getting a nonce
                #            nonce = None
                #            if not result:
                #                #N.B. If something is not changed, the attemps to swap will continue forever!
                #                #hedge_RL = False
                #                last_RL_bp = RL_v3_bp
                #                logger.error(network + ', hedge RL swap failed MAX_ATTEMPS_FAILED_TX = ' + str(MAX_ATTEMPS_FAILED_TX) +\
                #                           ' times, hedge RL unchanged until the next hedge RL, continue...')
                #elif price_mad <= PRICE_MAD[0]:
                #    if tx_hedge_RL_amount != 0.:
                #        amount_to_swap = tx_hedge_RL_amount

                #        #N.B. amount_to_swap > or < 0: swap amount_to_swap token0 into token1 if > 0 or swap -amount_to_swap token1 into token0 if < 0
                #        result = size_split_swap(network, price, amount_to_swap,\
                #                                max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas,\
                #                                 address=Address, private_key=privateKey, init=init, nonce=nonce)
                #        if isinstance(result, tuple):
                #            pool_liquidity, pool_price, swap_price, slippage_and_pool_fee_token1, nonce = result
                #            last_RL_bp = RL_v3_bp
                            
                #            #N.B. swap_price is wrong for small amounts, using pool_price for P&L!
                #            swap_price  = pool_price
                #            #N.B. pool_fee creates wrong p&l in the next iteration
                #            #if amount_to_swap > 0:
                #            #    swap_price *= (1. + init.pool_fee / 1000000)
                #            #else:
                #            #    swap_price /= (1. + init.pool_fee / 1000000) 
                #            #N.B. last_hedge_RL_price is not None because tx_hedge_RL_amount != 0.
                #            #if last_hedge_RL_price is None:
                #            #    last_hedge_RL_price = price
                #            #N.B. tx_hedge_RL_amount / price is the tx accumulated hedge RL amount in token1
                #            hedge_RL_pl_bp = (swap_price - last_hedge_RL_price) * tx_hedge_RL_amount / price / tx_borrow_invested_token1 * 10000
                #            logger.info(network + ', this hedge RL p&l = ' + "{:1.4f}".format(hedge_RL_pl_bp) + 'bp' +\
                #                                  ', no hedging RL because price_mad = '+ str(price_mad) + " <= PRICE_MAD[0] = " + str(PRICE_MAD[0]) +\
                #                                  ', price change from prev hedge = ' + "{:1.4f}".format(swap_price - last_hedge_RL_price) +\
                #                                  ', tx_borrow_invested_token1 = ' + str(tx_borrow_invested_token1) )
                #            logger.info('')

                #            last_hedge_RL_price = swap_price
                #            tx_hedge_RL_pl_bp += hedge_RL_pl_bp
                #            #N.B. hedge_RL_pl_bp measures P&L only from the last hedge!
                #            tx_hedge_RL_amount, hedge_RL_pl_bp = 0., 0.
                #            tx_count_hedge_RL += 1
                #            session_count_hedge_RL += 1

                #            tx_slippage_and_pool_fee_pl_bp += slippage_and_pool_fee_token1 / tx_borrow_invested_token1 * 10000
                #            session_slippage_and_pool_fee_pl_bp += tx_slippage_and_pool_fee_pl_bp
                #            session_borrow_pl_bp[j] += tx_slippage_and_pool_fee_pl_bp
                #        else:
                #            #N.B. nonce=None triggers web3 getting a nonce
                #            nonce = None
                #            if result:
                #                #N.B. unwind the LP position (if something is not changed, the attemps to swap will continue forever!)
                #                unwind_distance_to_bound = np.inf
                #                logger.error(network + ', UNWINDING open LP position: hedge RL swap failed MAX_ATTEMPS_FAILED_TX = ' + str(MAX_ATTEMPS_FAILED_TX) +\
                #                           ' times for price_mad = '+ str(price_mad) + " < PRICE_MAD[0] = " + str(PRICE_MAD[0]) + ', continue...')



                ###########################################################################
                #N.B. Unwind condition
                if price_mad > PRICE_MAD[-1]:
                    logger.info('')
                    logger.info(network + ", LP UNWIND because price_mad = " + str(price_mad) +\
                                                " > PRICE_MAD[-1] = " + str(PRICE_MAD[-1]))
                    unwind_condition = True
                    session_count_unwind_max_price_mad += 1

                if EVENT_LOGS and abs(signed_token1_quantity) / pool_liquidity_list[-1]  *\
                                        10 ** (0.5 * (init.token0_decimal + init.token1_decimal)) * 10000 > MAX_UNWIND_TOKEN1_QUANTITY_TO_TVL_BP:
                    logger.info('')
                    logger.info(network + ", LP UNWIND because abs(signed_token1_quantity) / pool_liquidity * 10000 = " +\
                                        "{:1.4f}".format(abs(signed_token1_quantity) / pool_liquidity_list[-1] *\
                                                10 ** (0.5 * (init.token0_decimal + init.token1_decimal)) * 10000) +\
                                        " > MAX_UNWIND_TOKEN1_QUANTITY_TO_TVL_BP = " + str(MAX_UNWIND_TOKEN1_QUANTITY_TO_TVL_BP))
                    unwind_condition = True
                    session_count_unwind_signed_quantity += 1

                if EVENT_LOGS and pool_liquidity_list[-1] < pool_liquidity_LP * MIN_POOL_LIQUIDITY_PER[-1] / 100:
                    logger.info('')
                    logger.info(network + ", LP UNWIND because pool liq = " +\
                                "{:1.0f}".format(pool_liquidity_list[-1] / 10 ** (0.5 * (init.token0_decimal + init.token1_decimal))) +\
                                " < initiation LP pool liq * threshold = " +\
                                "{:1.0f}".format(pool_liquidity_LP  / 10 ** (0.5 * (init.token0_decimal + init.token1_decimal)) * MIN_POOL_LIQUIDITY_PER[-1] / 100))
                    unwind_condition = True
                    session_count_unwind_pool_liq += 1

                while j < NUM_LP:
                    if priceLower[j] is not None and priceUpper[j] is not None:
                        if min([1. - priceLower[j] / price_DECIMAL, priceUpper[j] / price_DECIMAL - 1.]) <= unwind_distance_to_bound:
                            #asset_ratio_01 <= UNWIND_ASSET_RATIO_PER / 100 or asset_ratio_01 >= 1. / (UNWIND_ASSET_RATIO_PER / 100)
                            logger.info('')
                            logger.info(network + ", LP UNWIND because unwind_distance_to_bound = " + str(unwind_distance_to_bound) + " is reached!")
                            unwind_condition = True
                            session_count_unwind_distance += 1

                        #N.B. Stop-profit / stop-loss
                        if LP_fees_bp[j] + RL_v3_bp[j] + tx_hedge_RL_pl_bp[j] + hedge_RL_pl_bp[j] < - STOP_LOSS_BP or\
                            LP_fees_bp[j] + RL_v3_bp[j] + tx_hedge_RL_pl_bp[j] + hedge_RL_pl_bp[j] > STOP_PROFIT_BP:
                            logger.info('')
                            logger.info(network + ", LP UNWIND because tx p&l < - " + str(STOP_LOSS_BP) + " bp or > " + str(STOP_PROFIT_BP) + " bp")
                            unwind_condition = True
                            session_count_unwind_stop += 1

                    if swap_volume_token1[j] > MIN_UNWIND_SWAP_VOLUME_TOKEN1 and swap_flow_token1[j] > MIN_UNWIND_SWAP_FLOW_PER / 100 * swap_volume_token1[j]:
                        logger.info('')
                        logger.info(network + ", LP UNWIND because swap_volume_token1 = " + "{:1.0f}".format(swap_volume_token1) +\
                                    " > MIN_UNWIND_SWAP_VOLUME_TOKEN1 = " + str(MIN_UNWIND_SWAP_VOLUME_TOKEN1) +\
                                    " and swap_flow / swap_volume= " + "{:1.2f}".format(swap_flow_token1 / swap_volume_token1 * 100) + "%" +\
                                    " > MIN_UNWIND_SWAP_FLOW_PER = " + str(MIN_UNWIND_SWAP_FLOW_PER) + "%")
                        logger.info('')
                        unwind_condition = True
                        session_count_unwind_flow += 1

                    j += 1
                    continue

            if TEST:
                unwind_condition = unwind_condition or i % 2 == 1

            #N.B. Run decreaseLiquidity(), collect() only if unwind_condition!
            if unwind_condition and len(tokenIds) > 0:
            #####################################################################
            #4. Delete the above LP position
                if (flag_increaseLiquidity and flag_hedgeRL and flag_collect and flag_burn) or not flag_decreaseLiquidity:
                    if count_failed_tx < MAX_ATTEMPS_FAILED_TX:
                        if not flag_failed_tx: #N.B. If the specific flag is used, j does not reset because the default is True
                            j = 0
                        while j < NUM_LP:
                            #N.B. If decreaseLiquidity() tx fails, run only the failed decreaseLiquidity() in the next iteration!
                            #N.B. Passing nonce speeds up execution
                            result = decreaseLiquidity(network, tokenIds[j], liquidities[j],\
                                            max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas, \
                                                        address=Address, private_key=privateKey, init=init, nonce=nonce)
                            if isinstance(result, tuple):
                                amount0, amount1, nonce = result
                                flag_failed_tx, flag_decreaseLiquidity = False, True
                                count_failed_tx = 0
                                #del liquidities[j]
                                hedge_RL = HEDGE_RL
                                decreaseLiquidity_time[j] = time.time()
                                j += 1
                                continue
                            else:
                                nonce = None
                                if not result:
                                    #N.B. nonce=None triggers web3 getting a nonce
                                    flag_failed_tx, flag_decreaseLiquidity, nonce = True, False, None
                                    count_failed_tx += 1
                                    break #N.B. Break the inner loop
                    else:
                        logger.error(network + ', decreaseLiquidity() for ' + str(j) + '-th LP failed MAX_ATTEMPS_FAILED_TX = ' + str(MAX_ATTEMPS_FAILED_TX) + ' times, stop main()!')
                        #logger.info(network + ", session p&l = " + str(session_pl_token1[j]) + " token1" +\
                        #                        ", " + "{:1.2f}".format(session_pl_bp[j]) + " bp")
                        logger.info(network + ", session (w/o possible swap) for " + str(j) + "-th LP borrow p&l " +\
                            #": i) w/o hedge RL=" + str(session_borrow_pl_token1[j]) + " token1" +\
                            "{:1.2f}".format(session_borrow_pl_bp[j]) + " bp" ) # +\
                            #", iii) slippage & pool fee=" + "{:1.2f}".format(session_slippage_and_pool_fee_pl_bp) + " bp" +\
                            #", iv) hedge RL=" + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
                        logger.info('network, END session')
                        return False

                #####################################################################
                #5. Collect tokens from the deleted LP position
                #N.B. If collect() tx fails, run only the failed collect() in the next iteration!
                #time.sleep(3)
                if (flag_increaseLiquidity and flag_hedgeRL and flag_decreaseLiquidity and flag_burn) or not flag_collect:
                    if count_failed_tx < MAX_ATTEMPS_FAILED_TX:
                        #N.B. If the specific flag is used, j does not reset because the default is True
                        if not flag_failed_tx:
                            j = 0
                        tx_amount_to_swap = 0.
                        while j < NUM_LP:
                            result = collect(tokenIds[j], network, max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas, \
                                                address=Address, private_key=privateKey, init=init, nonce=nonce)
                            if isinstance(result, tuple):
                                amount0, amount1, nonce = result
                                blockNumber_init, price_init = block_num, price #if signed_token1_quantity > 0 else -price
                            
                                #N.B. tx
                                tx_collected_token1 = amount0 / 10**init.token0_decimal / price + amount1 / 10**init.token1_decimal
                                tx_borrow_invested_token1[j] = amount0_invested[j] / 10**init.token0_decimal / price + amount1_invested[j] / 10**init.token1_decimal
                                tx_borrow_pl_bp[j] = (tx_collected_token1 - tx_borrow_invested_token1[j]) / sum(tx_borrow_invested_token1) * 10000
                                #N.B. tx hedge RL P&L is a sum tx_hedge_RL_pl_bp + hedge_RL_pl_bp:  hedge_RL_pl_bp measures hedge RL  P&L only from the last hedge!
                                tx_borrow_pl_bp[j] += tx_hedge_RL_pl_bp[j] + hedge_RL_pl_bp[j]
                                tx_res_num_token0,  tx_res_num_token1 = (amount0 - amount0_invested[j]) / 10**init.token0_decimal, (amount1 - amount1_invested[j]) / 10**init.token1_decimal
                                priceLower[j], priceUpper[j], priceLP[j] = None, None, None
                                #N.B. tx_amount_to_swap: swap tx_amount_to_swap token0 into token1 if > 0 or -tx_amount_to_swap token1 into token0 if < 0
                                if amount0_invested[j] == 0.:
                                    tx_amount_to_swap +=  amount0 / 10**init.token0_decimal
                                elif amount1_invested[j] == 0.:
                                    tx_amount_to_swap +=  -amount1 / 10**init.token1_decimal
                                else:
                                    #N.B. formula : amount0/10**init.token0_decimal - tx_amount_to_swap = price*amount1/10**init.token1_decimal + tx_amount_to_swap
                                    tx_amount_to_swap += 0.5 * (amount0 / 10**init.token0_decimal - price * amount1 / 10**init.token1_decimal)

                                #N.B. tx P&L log report
                                #logger.info('')
                                #logger.info(network + ", LP tx (w/o possible swap) for " + str(j) + "-th LP p&l = " +\
                                #                str(tx_collected_token1 - tx_invested_token1[j]) + " token1" +\
                                #                ", " + "{:1.2f}".format((tx_collected_token1 - tx_invested_token1[j]) / sum(tx_invested_token1) * 10000) + " bp" +\
                                #                ", tx_borrow_invested_token1 = " + str(tx_borrow_invested_token1[j]))
                                logger.info(network + ", LP tx (w/o possible swap) for " + str(j) + "-th LP borrow p&l" +\
                                                ", i) " + str(tx_collected_token1 - tx_borrow_invested_token1[j]) + " token1" +\
                                                ", ii) " + "{:1.2f}".format(tx_borrow_pl_bp[j]) + " bp" +\
                                                #", iii) hedge RL=" + "{:1.2f}".format(tx_hedge_RL_pl_bp[j] + hedge_RL_pl_bp[j]) + " bp" +\
                                                #"; num hedge RL=" + str(tx_count_hedge_RL[j]) +\
                                                "; ITM duration=" + "{:1.1f}".format(ITM_duration[j] / 60) + " min" +\
                                                "; OTM duration=" + "{:1.1f}".format(OTM_duration[j] / 60) + " min" +\
                                                "; duration=" + "{:1.1f}".format((decreaseLiquidity_time[j] - mint_time[j]) / 60) + " min" +\
                                                "; tx amount_to_swap=" + "{:1.5f}".format(tx_amount_to_swap) )
                                                #"; tx swap flow token1 = " + "{:1.1f}".format(swap_flow_token1))

                                
                                #N.B. session
                                session_pl_token1[j] += tx_collected_token1 - tx_invested_token1[j]
                                session_borrow_pl_token1[j] += tx_collected_token1 - tx_borrow_invested_token1[j]
                                session_pl_bp[j] +=  (tx_collected_token1 - tx_invested_token1[j]) / sum(tx_invested_token1) * 10000
                                session_borrow_pl_bp[j] += tx_borrow_pl_bp[j] 
                                session_hedge_RL_pl_bp += tx_hedge_RL_pl_bp[j] + hedge_RL_pl_bp[j]

                                session_res_num_token0 += tx_res_num_token0
                                session_res_num_token1 += tx_res_num_token1

                                session_LP_fees_bp[j] += LP_fees_bp[j]
                                session_RL_bp[j] += RL_v3_bp[j]
                                session_ITM_duration[j] += ITM_duration[j]
                                session_OTM_duration[j] += OTM_duration[j]

                                #N.B. session P&L report
                                #logger.info(network + ", session (w/o possible) swap p&l= " + str(session_pl_token1[j]) + " token1" +\
                                #                       ", " + "{:1.2f}".format(session_pl_bp[j]) + " bp")
                                logger.info(network + ", session (w/o possible swap) for " + str(j) + "-th LP borrow" +\
                                        #": i) w/o hedge RL=" + str(session_borrow_pl_token1[j]) + " token1" +\
                                        ": p&l = " + "{:1.2f}".format(session_borrow_pl_bp[j]) + " bp"  +\
                                        "; ITM duration=" + "{:1.1f}".format(session_ITM_duration[j] / 60) + " min" +\
                                        "; OTM duration=" + "{:1.1f}".format(session_OTM_duration[j] / 60) + " min")
                                        #", iii) slippage & pool fee=" + "{:1.2f}".format(session_slippage_and_pool_fee_pl_bp) + " bp" +\
                                        #", iv) hedge RL=" + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
                                #logger.info(network + ", session" +\
                                #                ": LP fees  for " + str(j) + "-th LP = " + "{:1.2f}".format(session_LP_fees_bp[j]) + " bp" +\
                                #                ", RL  for " + str(j) + "-th LP= " + "{:1.2f}".format(session_RL_bp[j]) + " bp")


                                flag_failed_tx, flag_collect = False, True
                                count_failed_tx = 0
                                j += 1
                                continue
                            else:
                                if not result:
                                    nonce = None
                                #N.B. nonce=None triggers web3 getting a nonce
                                flag_failed_tx, flag_collect, nonce = True, False, None
                                count_failed_tx += 1
                                break #N.B. Break the inner loop
                    else:
                        logger.error(network + ', collect() for ' + str(j) + '-th LP failed MAX_ATTEMPS_FAILED_TX = ' + str(MAX_ATTEMPS_FAILED_TX) +  ' times, stop main()!')
                        #logger.info(network + ", session p&l = " + str(session_pl_token1[j]) + " token1" +\
                        #                    ", " + "{:1.2f}".format(session_pl_bp[j]) + " bp")
                        logger.info(network + ", session (w/o possible swap) for " + str(j) + "-th LP borrow p&l " +\
                            #": i) w/o hedge RL=" + str(session_borrow_pl_token1[j]) + " token1" +\
                            "{:1.2f}".format(session_borrow_pl_bp[j]) + " bp" ) # +\
                            #", iii) slippage & pool fee=" + "{:1.2f}".format(session_slippage_and_pool_fee_pl_bp) + " bp" +\
                            #", iv) hedge RL=" + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
                        logger.info('network, END session')
                        return False

                    
                    #N.B. session log report
                    logger.info(network + ", session: res num token0 = " + str(session_res_num_token0) +\
                                                    ", res num token1 = " + str(session_res_num_token1) )
                    logger.info(network + ', session' +\
                        ': count LP=' + str(session_count_LP) +\
                        ', count mint=' + str(session_count_mint) +\
                        ', count swaps=' + str(session_count_swaps) +\
                        ', count LP swap =' + str(session_count_LP_SWAP) +\
                        ', count unwind distance=' + str(session_count_unwind_distance) +\
                        ', count unwind flow=' + str(session_count_unwind_flow) +\
                        ', count unwind signed q=' + str(session_count_unwind_signed_quantity) +\
                        ', count unwind stop=' + str(session_count_unwind_stop) +\
                        ', count unwind pool liq=' + str(session_count_unwind_pool_liq) +\
                        ', count unwind price_mad=' + str(session_count_unwind_max_price_mad) +\
                        ', count hedge RL = ' + str(session_count_hedge_RL) )
                    logger.info(network + ", session: duration = " + "{:1.1f}".format((time.time() - start_time) / 3600) + " h" +\
                                            ", max price_mad = " + "{:1.5f}".format(max_price_mad))
                            

                
                ###################################################
                #6. Burn the NFT correponding to tokenIds[-1]: otherwise the NFT stays in the wallet & can be seen running current_LP_positions()
                #N.B. From the docs: "The token must have 0 liquidity and all tokens must be collected first.": https://docs.uniswap.org/protocol/reference/periphery/NonfungiblePositionManager
                #N.B. If tokens not collected first, burn() tx produces error on Etherscan "Fail with error 'Not cleared'"
                #N.B. If burn() tx fails, run only the failed burn() in the next iteration!
                #N.B. swap() is after burn() because swap() does not depend on unwind_condition or len(tokenIds): if burn() fails, swap() is delayed or fails!
                if (flag_increaseLiquidity and flag_hedgeRL and flag_decreaseLiquidity and flag_collect) or not flag_burn:
                    if count_failed_tx < MAX_ATTEMPS_FAILED_TX:
                        #N.B. If the specific flag is used, j does not reset because the default is True
                        if not flag_failed_tx:
                            j = 0
                        while j < NUM_LP:
                            if burn(tokenIds[j], network, max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas, \
                                            address=Address, private_key=privateKey, init=init, nonce=nonce):
                                tokenIds_burned += [tokenIds[j]]
                                nonce += 1
                                flag_change_tokenIds = True
                                flag_failed_tx, flag_burn = False, True
                                count_failed_tx = 0
                                j += 1
                                continue
                            else:
                                #N.B. nonce=None triggers web3 getting a nonce
                                flag_failed_tx, flag_burn, nonce = True, False, None
                                count_failed_tx += 1
                                break #N.B. Break the inner loop
                    else:
                        logger.error(network + ', burn() for ' + str(j) + '-th LP failed MAX_ATTEMPS_FAILED_TX = ' + str(MAX_ATTEMPS_FAILED_TX) + ' times, stop main()!')
                        #logger.info(network + ", session p&l = " + str(session_pl_token1[j]) + " token1" +\
                        #                    ", " + "{:1.2f}".format(session_pl_bp[j]) + " bp")
                        logger.info(network + ", session (w/o possible swap) for " + str(j) + "-th LP borrow p&l " +\
                            #": i) w/o hedge RL=" + str(session_borrow_pl_token1[j]) + " token1" +\
                            "{:1.2f}".format(session_borrow_pl_bp[j]) + " bp" ) # +\
                            #", iii) slippage & pool fee=" + "{:1.2f}".format(session_slippage_and_pool_fee_pl_bp) + " bp" +\
                            #", iv) hedge RL=" + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
                        logger.info('network, END session')
                        return False
                
                 
            ######################################################################
            #7. Swap the collected amounts difference to achieve parity of the amounts
            #N.B. If slippage is too low, get error 'Too little received'
            #N.B. If swap() tx fails, run only the failed swap() in the next swap iteration!
            if flag_increaseLiquidity and flag_hedgeRL and flag_decreaseLiquidity and flag_collect and flag_burn:
                #logger.info('')
                    
                #N.B. tx
                #N.B. swap tx_amount_to_swap token0 into token1 if > 0 or -tx_amount_to_swap token1 into token0 if < 0
                amount_to_swap = 0.
                flag_swap = False

                if abs(tx_amount_to_swap) > MIN_TX_SWAP_PER / 100 * sum(tx_borrow_invested_token1):
                    amount_to_swap = tx_amount_to_swap
                    tx_amount_to_swap = 0.
                    flag_swap = True
                else:
                    logger.info(network + ", no tx swap: abs(tx_amount_to_swap) = " + str(abs(tx_amount_to_swap)) + " <= min tx swap threshold = " +\
                            str(MIN_TX_SWAP_PER / 100 * sum(tx_borrow_invested_token1)) + ", continue...")
                    flag_swap = False

                #N.B. session
                #N.B. amount_to_swap from session is used!
                if abs(session_res_num_token1) > MIN_SESSION_SWAP_PER / 100 * sum(tx_borrow_invested_token1):
                    if session_res_num_token0 > 0:
                        amount_to_swap = session_res_num_token0
                    elif session_res_num_token1 > 0:
                        amount_to_swap = -session_res_num_token1 * price
                    session_res_num_token0, session_res_num_token1 = 0., 0.
                    flag_swap = flag_swap or True
                else:
                    logger.info(network + ", no session swap: abs(session_res_num_token1)=" + str(abs(session_res_num_token1)) +\
                            " <= min session swap token1=" + str(MIN_SESSION_SWAP_PER / 100 * sum(tx_borrow_invested_token1)) + ", continue...")
                    flag_swap = flag_swap or False

                if flag_swap and abs(amount_to_swap) >= SWAP_EPSILON_PER / 100  * sum(tx_borrow_invested_token1):
                    #if LP_SWAP:
                    #    #N.B. Get fresh price before LP swap
                    #    i += 1
                    #    continue
                    #else:
                    #N.B. Size-split swap: if tx_amount_to_swap > 0, swap tx_amount_to_swap token0 to token1; if < 0, swap -tx_amount_to_swap token1 to token0;
                    #N.B. Passing nonce speeds up execution
                    result = size_split_swap(network, price, amount_to_swap,\
                        max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas,\
                        address=Address, private_key=privateKey, init=init, nonce=nonce)
                    if isinstance(result, tuple):
                        pool_liquidity, pool_price, swap_price, slippage_and_pool_fee_token1, nonce = result
                        session_count_swaps += 1
                        #N.B. tx
                        tx_slippage_and_pool_fee_pl_bp += slippage_and_pool_fee_token1 / sum(tx_borrow_invested_token1) * 10000 if\
                                sum(tx_borrow_invested_token1) > 0 else 0.
                        logger.info(network + ", swap slippage & pool fee=" +\
                                        "{:1.2f}".format(tx_slippage_and_pool_fee_pl_bp) + " bp" )#+\
                                        #"; tx swap flow token1 = " + "{:1.1f}".format(swap_flow_token1))
                        #N.B. session
                        session_slippage_and_pool_fee_pl_bp += tx_slippage_and_pool_fee_pl_bp
                        #session_borrow_pl_bp[j] += tx_slippage_and_pool_fee_pl_bp
                        logger.info(network + ', session: count swaps=' + str(session_count_swaps) +\
                                    #" i) " + "{:1.2f}".format(session_borrow_pl_bp[j]) + " bp"  +\
                                    ", slippage & pool fee=" + "{:1.2f}".format(session_slippage_and_pool_fee_pl_bp) + " bp")
                    else:
                        nonce = None
                        if not result:
                            if flag_increaseLiquidity and flag_hedgeRL and flag_decreaseLiquidity and flag_collect and flag_burn:
                                logger.error(network + ', hedge size_split_swap() failed MAX_ATTEMPS_FAILED_TX = ' + str(MAX_ATTEMPS_FAILED_TX) +\
                                    ' times for swap iteration, stop main()!')
                                #logger.info(network + ", session p&l = " + str(session_pl_token1[j]) + " token1" +\
                                #                    ", " + "{:1.2f}".format(session_pl_bp[j]) + " bp")
                                logger.info(network + ", session " +\
                                #": i) w/o hedge RL=" + str(session_borrow_pl_token1[j]) + " token1" +\
                                ": i) w/o possible swap " + "{:1.2f}".format(sum(session_borrow_pl_bp)) + " bp" +\
                                ", ii) slippage & pool fee=" + "{:1.2f}".format(session_slippage_and_pool_fee_pl_bp) + " bp") # +\
                                #", iv) hedge RL=" + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
                                logger.info('network, END session')
                                return False
                       
                

        if i == int(RUNTIME_SEC / DELAY_LOOP_SEC):
            #logger.info(network + ", session p&l = " + str(sum(session_pl_token1)) + " token1" +\
            #                ", " + "{:1.2f}".format(sum(session_pl_bp)) + " bp")
            logger.info(network + ", session: borrow p&l (w/o possible swap)" +\
                            #": i) w/o hedge RL=" + str(sum(session_borrow_pl_token1)) + " token1" +\
                            " = " + "{:1.2f}".format(sum(session_borrow_pl_bp)) + " bp" +\
                            ", slippage & pool fee=" + "{:1.2f}".format(session_slippage_and_pool_fee_pl_bp) + " bp") #  +\
                            #", iv) hedge RL = " + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
            logger.info(network + ", session: res num token0 = " + str(session_res_num_token0) +\
                                                        ", res num token1 = " + str(session_res_num_token1) )
            logger.info(network + ', session' +\
                                ': count LP=' + str(session_count_LP) +\
                                ', count mint=' + str(session_count_mint) +\
                                ', count swaps=' + str(session_count_swaps) +\
                                ', count LP swap =' + str(session_count_LP_SWAP) +\
                                ', count unwind distance=' + str(session_count_unwind_distance) +\
                                ', count unwind flow=' + str(session_count_unwind_flow) +\
                                ', count unwind signed q=' + str(session_count_unwind_signed_quantity) +\
                                ', count unwind stop=' + str(session_count_unwind_stop) +\
                                ', count unwind pool liq=' + str(session_count_unwind_pool_liq) +\
                                ', count unwind price_mad=' + str(session_count_unwind_max_price_mad) +\
                                ', count hedge RL = ' + str(session_count_hedge_RL) )
            logger.info(network + ", session: duration = " + "{:1.1f}".format((time.time() - start_time) / 3600) + " h" +\
                                                    ", max price_mad = " + "{:1.5f}".format(max_price_mad) +\
                                                    ", LP fees = " + "{:1.2f}".format(sum(session_LP_fees_bp)) + " bp" +\
                                                    ", RL = " + "{:1.2f}".format(sum(session_RL_bp)) + " bp" )
            logger.info('network, END session')
                 
                
        i += 1

    return True




import sys
if __name__ == '__main__':
    if len(sys.argv) == 1: #no inputs
        main()
    elif len(sys.argv) == 2: #network
        main(str(sys.argv[1]))
    else:
        print("Wrong number of inputs!")




