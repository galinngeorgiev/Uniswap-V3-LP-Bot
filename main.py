__author__ = "Galin Georgiev"
__copyright__ = "Copyright 2022, GammaDynamics, LLC"
__version__ = "1.1.0.0"


from ast import Num
from re import I
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
    tokenIds, tokenIds_burned, liquidities = (NUM_LP + 1) * [None], [],  (NUM_LP + 1) * [None]
    amount0_LP, amount1_LP, priceLower, tickLower, priceUpper, tickUpper, priceLP =\
            (NUM_LP + 1) * [None], (NUM_LP + 1) * [None], (NUM_LP + 1) * [None], (NUM_LP + 1) * [None], (NUM_LP + 1) * [None], (NUM_LP + 1) * [None], (NUM_LP + 1) * [None]
    swap_volume_token1, rel_swap_volume_token1, swap_flow_token1 = (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.]
    amount0_invested, amount1_invested, asset_ratio_01_LP, asset_ratio_01, asset0_ratio, asset1_ratio =\
            (NUM_LP + 1) * [None], (NUM_LP + 1) * [None], (NUM_LP + 1) * [None], (NUM_LP + 1) * [None], (NUM_LP + 1) * [None], (NUM_LP + 1) * [None]
    tx_invested_token1, tx_borrow_invested_token1, tx_collected_token1, tx_borrow_pl_bp, tx_estimated_borrow_pl_bp =\
            (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.] , (NUM_LP + 1) * [0.]     
    RL_v2_bp, delta_RL_v2, v3_v2_mult_factor, RL_v3_bp, delta_RL_v3, LP_fees_bp, OTM_loss_bp =\
       (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.],  (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.]
    tx_count_hedge_RL, tx_hedge_RL_amount, last_RL_bp, tx_hedge_RL_pl_bp, hedge_RL_pl_bp =\
        (NUM_LP + 1) * [0], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.]
    tx_batch_amount_to_swap_token1 = 0.
    mint_time, ITM_duration, OTM_duration, decreaseLiquidity_time = (NUM_LP + 1) * [None], (NUM_LP + 1) * [0], (NUM_LP + 1) * [0], (NUM_LP + 1) * [None]
    mint_condition, unwind_condition = (NUM_LP + 1) * [False], (NUM_LP + 1) * [False]
    count_LP_SWAP_attempts = 0

    #initialize session
    session_count_LP, session_count_LP_SWAP, session_count_LP_SWAP_failed, session_count_unwind_stop, session_count_unwind_pool_liq, session_count_unwind_max_price_mad,\
            session_count_unwind_signed_quantity, session_count_unwind_distance, session_count_hedge_RL, session_count_swaps, session_count_unwind_flow =\
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    session_LP_fees_bp, session_RL_bp, session_pl_token1, session_pl_bp, session_borrow_pl_token1, session_borrow_pl_bp, session_OTM_loss_bp =\
            (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.]
    session_hedge_RL_pl_bp, session_swap_cost_bp, session_res_num_token0, session_res_num_token1 = 0., 0., 0., 0.
    session_ITM_duration, session_OTM_duration, session_LP_SWAP_duration = (NUM_LP + 1) * [0], (NUM_LP + 1) * [0], 0
    amount_to_swap_token0 = 0.

    #initialize flags
    #N.B. Individual tx-s flags are needed so the wrong tx is not run when tx fails!
    flag_change_tokenIds, flag_mint, flag_increaseLiquidity, flag_hedgeRL, flag_decreaseLiquidity, flag_collect, flag_burn, flag_LP_SWAP, flag_swap_session =\
        True, True, True, True, True, True, True, False, False
    flag_failed_tx, count_failed_tx = False, 0

    #gas & slippage
    max_fee_per_gas, max_priority_fee_per_gas, slippage_per = MAX_FEE_PER_GAS, MAX_PRIORITY_FEE_PER_GAS, SLIPPAGE_PER
    

    logger.info('')
    logger.info(network + ', START session')
    start_time, iteration_time = time.time(), time.time()
    #global HEDGE_RL
    #hedge_RL = HEDGE_RL
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

    
    ##############################################################################################################
    #main loop
    i = 0
    main_loop_end = int(RUNTIME_SEC / DELAY_LOOP_SEC)
    if LP_SWAP:
        main_loop_end *= LP_SWAP_MULT_RUNTIME
    while i <= main_loop_end:
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
                if len(result) > NUM_LP + 1:
                    logger.error(network + ', at most ' + str(NUM_LP + 1) + ' simulteneous LP positions are allowed, burn the extra with running burn.py! Stop main()!')
                    logger.info('network, END session')
                    return False
                
                #N.B. The list result is sorted in ascending order but to be saf, tokenIds[j] is assigned in mint()!
                for j in range(NUM_LP + 1):
                    if tokenIds[j] not in result:
                        tokenIds[j] = None
                #N.B. Sometimes Alchemy API returns already burned tokens, so check for that!
                for tokenId in tokenIds:
                    if tokenId in tokenIds_burned:
                        tokenId = None 

            else:
                i += 1
                continue

        #######################################################################
        #1a. Checks
        if i == 0 and tokenIds != (NUM_LP + 1) * [None]:
            logger.error(network + ', there are NFTs in this account with ID-s ' + str(tokenIds) + ', burn them with running burn.py! Stop main()!')
            logger.info('network, END session')
            return False

        #####################################################################
        #2. obtain the current pool price: the fuction returns False if no updates!
        if not flag_failed_tx:
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
                #N.B. Loop continues at the end even without data, because tx-s have to be unwound!
                if i < int(RUNTIME_SEC / DELAY_LOOP_SEC) - NUM_LP * MAX_ATTEMPS_FAILED_TX:
                    i += 1
                    continue             
        
        ######################################################################
        #3. mint LP position
        #N.B. if individual flags are not specified here, when unwind tx fails, it triggers infinite mint loop;
        if flag_increaseLiquidity and flag_hedgeRL and flag_decreaseLiquidity and flag_collect and flag_burn:

            #######################
            #N.B. mint_condition
            if not flag_mint:
                mint_condition[j] = True
            else:
                #N.B. LP_SWAP position can be mint(), even if tokenIds[:NUM_LP] != NUM_LP * [None]!
                #N.B. 'priceLP[NUM_LP] is None' condition prevents 2nd LP swap
                if flag_LP_SWAP and priceLP[NUM_LP] is None and amount_to_swap_token0 != 0.:
                    #N.B. amountX_LP = 0 assures that LP is OTM, otherwise mint() fails!
                    amount0_LP[NUM_LP] = amount_to_swap_token0 * 10**init.token0_decimal if amount_to_swap_token0 > 0 else 0.
                    amount1_LP[NUM_LP] = - amount_to_swap_token0 / price * 10**init.token1_decimal if amount_to_swap_token0 < 0 else 0.
                    if amount0_LP[NUM_LP] > 0 or amount1_LP[NUM_LP] > 0:
                        mint_condition[NUM_LP] = True
                    #N.B. Can use amount_to_swap_token0 sign because this is immediately after amount_to_swap_token0 was set up!
                    if amount_to_swap_token0 > 0:
                        priceUpper[NUM_LP] = price_DECIMAL * (1. - LP_SWAP_DISTANCE_TO_BOUND_PER / 100)
                        #N.B. Re-compute priceLower, priceUpper: tick spacing >> 1, depending on the pool fee: section 4 in https://uniswap.org/whitepaper-v3.pdf
                        #N.B. tick = log(price) / log(1.0001): (6.1) in https://uniswap.org/whitepaper-v3.pdf
                        tickUpper[NUM_LP] = np.log(priceUpper[NUM_LP]) / np.log(1.0001)
                        if init.pool_fee == 500:
                            tickLower[NUM_LP] = int(tickUpper[NUM_LP] // 10 * 10 - 10)
                            tickUpper[NUM_LP] = int(tickUpper[NUM_LP] // 10 * 10)
                        elif init.pool_fee == 3000:
                            tickLower[NUM_LP] = int(tickUpper[NUM_LP] // 60 * 60 - 60)
                            tickUpper[NUM_LP] = int(tickUpper[NUM_LP] // 60 * 60)
                        elif init.pool_fee == 10000:
                            tickLower[NUM_LP] = int(tickUpper[NUM_LP] // 200 * 200 - 200)
                            tickUpper[NUM_LP] = int(tickUpper[NUM_LP] // 200 * 200)
                    #N.B. Can use amount_to_swap_token0 sign because this is immediately after amount_to_swap_token0 was set up!
                    elif amount_to_swap_token0 < 0:
                        priceLower[NUM_LP] = price_DECIMAL * (1. + LP_SWAP_DISTANCE_TO_BOUND_PER / 100)
                        #N.B. Re-compute priceLower, priceUpper: tick spacing >> 1, depending on the pool fee: section 4 in https://uniswap.org/whitepaper-v3.pdf
                        #N.B. tick = log(price) / log(1.0001): (6.1) in https://uniswap.org/whitepaper-v3.pdf
                        tickLower[NUM_LP] = np.log(priceLower[NUM_LP]) / np.log(1.0001)
                        if init.pool_fee == 500:
                            tickUpper[NUM_LP] = int(tickLower[NUM_LP] // 10 * 10 + 10)
                            tickLower[NUM_LP] = int(tickLower[NUM_LP] // 10 * 10)
                        elif init.pool_fee == 3000:
                            tickUpper[NUM_LP] = int(tickLower[NUM_LP] // 60 * 60 + 60)
                            tickLower[NUM_LP] = int(tickLower[NUM_LP] // 60 * 60)
                        elif init.pool_fee == 10000:
                            tickUpper[NUM_LP] = int(tickLower[NUM_LP] // 200 * 200 + 200)
                            tickLower[NUM_LP] = int(tickLower[NUM_LP] // 200 * 200)
                
                    priceLower[NUM_LP], priceUpper[NUM_LP] = 1.0001 ** tickLower[NUM_LP], 1.0001 ** tickUpper[NUM_LP]

                #N.B. New LP positions with j < NUM_LP can be mint even if flag_LP_SWAP!
                if tokenIds[:NUM_LP] == NUM_LP * [None] and i < int(RUNTIME_SEC / DELAY_LOOP_SEC) - NUM_LP * MAX_ATTEMPS_FAILED_TX:
                    amount0_LP[:NUM_LP] = NUM_LP * [NUM_TOKEN0_LP / NUM_LP * 10**init.token0_decimal]
                    amount1_LP[:NUM_LP] = NUM_LP * [np.min([NUM_TOKEN1_LP / NUM_LP, NUM_TOKEN0_LP / NUM_LP / price]) * 10**init.token1_decimal]
                    #N.B. LP_distance_to_bound from beginning to end of quiet hours
                    if (int(time.strftime('%w', time.gmtime())) != 6 and int(time.strftime('%w', time.gmtime())) != 0 and\
                            (int(time.strftime('%H', time.gmtime())) >= QUIET_HOURS_START[0] and int(time.strftime('%H', time.gmtime())) < QUIET_HOURS_END[-1])):
                        LP_distance_to_bound = LP_DISTANCE_TO_BOUND_PER[-1] / 100
                        #logger.info(network + ", LP_distance_to_bound = " +\
                        #    "{:1.2f}".format(LP_distance_to_bound * 100) + "% from beginning to end of quiet hours!")
                    else:
                        LP_distance_to_bound = LP_DISTANCE_TO_BOUND_PER[0] / 100

                    #N.B. Do not initiate during quiet hours
                    if not (int(time.strftime('%w', time.gmtime())) != 6 and int(time.strftime('%w', time.gmtime())) != 0 and\
                            ((int(time.strftime('%H', time.gmtime())) >= QUIET_HOURS_START[0] and int(time.strftime('%H', time.gmtime())) < QUIET_HOURS_END[0]) or\
                            (int(time.strftime('%H', time.gmtime())) >= QUIET_HOURS_START[1] and int(time.strftime('%H', time.gmtime())) < QUIET_HOURS_END[1]))):
                        mint_condition[:NUM_LP] = NUM_LP * [True]
                        
                        #N.B. Do not initiate if liquidity decreases!
                        if EVENT_LOGS and len(pool_liquidity_list) > 0 and\
                            pool_liquidity_list[-1] >= np.min([pool_liquidity_median, pool_liquidity_list[-1]]) * MIN_POOL_LIQUIDITY_PER[0] / 100:
                            mint_condition[:NUM_LP] = [mint_condition[k] and True for k in range(NUM_LP)]
                        else:
                            logger.info('')
                            logger.info("NO LP INITIALIZATION because EVENT_LOGS=F or pool liq = " +\
                                            "{:1.0f}".format(pool_liquidity_list[-1] / 10 ** (0.5 * (init.token0_decimal + init.token1_decimal))) +\
                                            " < pool liq median * threshold= " + "{:1.0f}".format(pool_liquidity_median  / 10 ** (0.5 * (init.token0_decimal + init.token1_decimal)) * MIN_POOL_LIQUIDITY_PER[0] / 100))
                            mint_condition[:NUM_LP] = NUM_LP * [False]

                        #N.B. Do not initiate if price_mad too high!
                        if price_mad <= PRICE_MAD[0]: # and (time.time() - max_price_mad_time) / 60 >= PRICE_MAD_WAIT_TIME_MIN:
                            mint_condition[:NUM_LP] = [mint_condition[k] and True for k in range(NUM_LP)]
                        else:
                            logger.info('')
                            logger.info("NO LP INITIALIZATION because price_mad = " + "{:1.5f}".format(price_mad) +\
                                        " > " + str(PRICE_MAD[0]) )
                            mint_condition[:NUM_LP] = NUM_LP * [False]
                        
                        #N.B. Do not initiate if signed_token1_quantity is too small (only in one direction) &
                        #N.B.  MIN_INIT_AFTER_BLOCKS or MIN_INIT_AFTER_PRICE_RET_BP is not passed!
                        if blockNumber_init is None:
                            if i != 0 and signed_token1_quantity / pool_liquidity_list[-1] *\
                                10 ** (0.5 * (init.token0_decimal + init.token1_decimal)) >= MIN_INIT_TOKEN1_QUANTITY_TO_TVL_BP / 10000:
                                blockNumber_init, price_init = block_num, price #if signed_token1_quantity > 0 else -price
                                logger.info(network + ", blockNumber_init = " + str(blockNumber_init) + ", price_init = " +\
                                    "{:1.5f}".format(price_init) + ", scaled signed_token1_quantity / pool_liquidity_list[-1] = " +\
                                    "{:1.3f}".format(abs(signed_token1_quantity) / pool_liquidity_list[-1] * 10 ** (0.5 * (init.token0_decimal + init.token1_decimal)) * 10000) +\
                                    " >=  MIN_INIT_TOKEN1_QUANTITY_TO_TVL_BP = " + str(MIN_INIT_TOKEN1_QUANTITY_TO_TVL_BP))
                            else:
                                logger.info(network + ", NO LP INITIALIZATION because blockNumber_init/price_init is not set yet: " +\
                                    "scaled abs(signed_token1_quantity) / pool_liquidity_list[-1] = " +\
                                    "{:1.3f}".format(abs(signed_token1_quantity) / pool_liquidity_list[-1] * 10 ** (0.5 * (init.token0_decimal + init.token1_decimal)) * 10000) +\
                                    " <  MIN_INIT_TOKEN1_QUANTITY_TO_TVL_BP = " + str(MIN_INIT_TOKEN1_QUANTITY_TO_TVL_BP))
    
                            mint_condition[:NUM_LP] = NUM_LP * [False]
                        else:
                            if  block_num >= blockNumber_init + MIN_INIT_AFTER_BLOCKS:
                                if abs(price - price_init) / price_init * 10000 >= MIN_INIT_AFTER_PRICE_RET_BP: # and (price - price_init) * price_init > 0:
                                    mint_condition[:NUM_LP] = [mint_condition[j] and True for j in range(NUM_LP)]
                                else: 
                                    #logger.info('')
                                    logger.info(network + ", blockNumber_init = " + str(blockNumber_init) + ", price_init = " + "{:1.5f}".format(price_init))
                                    logger.info(network + ", NO LP INITIALIZATION because abs(price - price_init) / price_init = " +\
                                            "{:1.2f}".format(abs(price - price_init) / price_init * 10000) +\
                                            " bp < MIN_INIT_AFTER_PRICE_RET_BP = " + str(MIN_INIT_AFTER_PRICE_RET_BP) + " bp")
                                    mint_condition[:NUM_LP] = NUM_LP * [False]
                                blockNumber_init, price_init = None, None
                            else:
                                logger.info(network + ", blockNumber_init = " + str(blockNumber_init) + ", price_init = " + "{:1.5f}".format(price_init))
                                logger.info(network + ", NO LP INITIALIZATION because current block number = " +\
                                            str(block_num) + " <  blockNumber_init = " + str(blockNumber_init) +\
                                            " + MIN_INIT_AFTER_BLOCKS = " + str(MIN_INIT_AFTER_BLOCKS) )
                                mint_condition[:NUM_LP] = NUM_LP * [False]
                            
                            if mint_condition[:NUM_LP] == NUM_LP * [True]:
                                #N.B. LP positions symmetric around the current price
                                ##N.B. middle LP is always symmetric in-the-money
                                #priceLower[int((NUM_LP - 1) / 2)] = price_DECIMAL * (1. - LP_distance_to_bound)
                                #priceUpper[int((NUM_LP - 1) / 2)] = price_DECIMAL * (1. + LP_distance_to_bound)
                                ##N.B. Assure the the price ranges are adjacent!
                                #for k in reversed(range(int((NUM_LP - 1) / 2))):
                                #        priceLower[k] = price_DECIMAL * (1. + (2 * k - NUM_LP) * LP_distance_to_bound)
                                #        priceUpper[k] = priceLower[k + 1]
                                #for k in range(int((NUM_LP - 1) / 2) + 1, NUM_LP):
                                #        priceLower[k] = priceUpper[k - 1]
                                #        priceUpper[k] = price_DECIMAL * (1. + (2 * (k + 1) - NUM_LP) * LP_distance_to_bound)

                                #N.B. LP positions below the current price
                                priceLower[NUM_LP - 1] = price_DECIMAL * (1. - 2 * LP_distance_to_bound)
                                priceUpper[NUM_LP - 1] = price_DECIMAL * (1. - LP_SWAP_DISTANCE_TO_BOUND_PER / 100)
                                #N.B. Assure the the price ranges are adjacent!
                                for k in reversed(range(NUM_LP - 1)):
                                    priceLower[k] = price_DECIMAL * (1. + 2 * (k - NUM_LP) * LP_distance_to_bound)
                                    priceUpper[k] = priceLower[k + 1]
                            
                                for k in range(NUM_LP):
                                    #N.B. Re-compute priceLower, priceUpper: tick spacing >> 1, depending on the pool fee: section 4 in https://uniswap.org/whitepaper-v3.pdf
                                    #N.B. tick = log(price) / log(1.0001): (6.1) in https://uniswap.org/whitepaper-v3.pdf
                                    tickLower[k] = np.log(priceLower[k]) / np.log(1.0001)
                                    tickUpper[k] = np.log(priceUpper[k]) / np.log(1.0001)
                                    if init.pool_fee == 500:
                                        #N.B. in order to have ITM LP!
                                        #tickLower[k], tickUpper[k] = int(tickLower[k] // 10 * 10), int(tickUpper[k] // 10 * 10 + 6 * 10)
                                        tickLower[k], tickUpper[k] = int(tickLower[k] // 10 * 10), int(tickUpper[k] // 10 * 10 + 10)
                                    elif init.pool_fee == 3000:
                                        tickLower[k], tickUpper[k] = int(tickLower[k] // 60 * 60), int(tickUpper[k] // 60 * 60 + 60)
                                    elif init.pool_fee == 10000:
                                        tickLower[k], tickUpper[k] = int(tickLower[k] // 200 * 200), int(tickUpper[k] // 200 * 200 + 200)
                                    priceLower[k], priceUpper[k] = 1.0001 ** tickLower[k], 1.0001 ** tickUpper[k]
              
                    else:
                        mint_condition[:NUM_LP] = NUM_LP * [False]
                        logger.info(network + ", NO LP INITIALIZATION during quiet hours!")

            #############################
            #N.B. mint() (only if mint_condition[j])
            if not flag_failed_tx:
                j = 0
            while j <= NUM_LP:
                #if j == NUM_LP and not flag_LP_SWAP: #N.B. When j += 1, this line is hit, but if mint_condition[NUM_LP] == False, nothing will happen!
                #    j = 0
                #    break
                if mint_condition[j]:
                    #N.B.  flag_increaseLiquidity and flag_hedgeRL and flag_decreaseLiquidity and flag_collect and flag_burn on the top of mint_condition loop!
                    if count_failed_tx < MAX_ATTEMPS_FAILED_TX:
                        #N.B. Compute nonce in mint() in order to keep the order of mints()
                        result = mint(network, amount0ToMint=amount0_LP[j], amount1ToMint=amount1_LP[j], tickLower=tickLower[j], tickUpper=tickUpper[j], \
                                        max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas, \
                                        address=Address, private_key=privateKey, init=init)
                        if isinstance(result, tuple):
                            tokenId, liquidity, amount0, amount1, blockNumber, nonce = result

                            tokenIds[j], liquidities[j] = tokenId, liquidity
                            #N.B. priceLP from line (71) in https://github.com/Uniswap/v3-periphery/blob/main/contracts/libraries/LiquidityAmounts.sol
                            #N.B. When price range is out-of-the-money, priceLP equals one of the price bound!
                            priceLP[j] = (amount0  / liquidities[j] + np.sqrt(priceLower[j])) ** 2
                            pool_liquidity_LP = pool_liquidity_list[-1]
                            swap_volume_token1[j], rel_swap_volume_token1[j], swap_flow_token1[j] = 0., 0., 0.
                            amount0_invested[j], amount1_invested[j] = amount0, amount1
                            session_count_LP += 1
                            blockNumber_init, price_init = None, None
                            amount0_LP[j], amount1_LP[j] = None, None
                            tx_slippage_and_pool_fee_pl_bp, tx_count_hedge_RL[j] = 0., 0
                            tx_invested_token1[j] = amount0 / 10**init.token0_decimal / price + amount1 / 10**init.token1_decimal
                            tx_borrow_invested_token1[j] = tx_invested_token1[j]
                            mint_time[j], iteration_time, ITM_duration[j], OTM_duration[j] = time.time(), time.time(), 0, 0
                            mint_condition[j] = False

                            if j == NUM_LP and flag_LP_SWAP:
                                session_count_LP_SWAP += 1
                                logger.info(network  +\
                                            ", LP_SWAP priceLP = " + "{:1.5f}".format(priceLP[NUM_LP] / 10**init.token0_decimal * 10**init.token1_decimal) +\
                                            ", LP_SWAP priceLower = " + "{:1.5f}".format(priceLower[NUM_LP] / 10**init.token0_decimal * 10**init.token1_decimal) +\
                                            ", LP_SWAP priceUpper = " + "{:1.5f}".format(priceUpper[NUM_LP] / 10**init.token0_decimal * 10**init.token1_decimal) +\
                                            ", session count LP swap tx_s = " + str(session_count_LP_SWAP) +\
                                            ", session count LP swaps failed =" + str(session_count_LP_SWAP_failed) )
                                LP_SWAP_start_time = time.time()
                            else:
                                #hedge_RL = HEDGE_RL
                                #tx_hedge_RL_pl_bp[j], hedge_RL_pl_bp[j], last_RL_bp[j], tx_hedge_RL_amount[j], last_hedge_RL_price[j] = 0., 0., 0., 0., None
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
                                        
                            flag_change_tokenIds, flag_failed_tx, flag_mint = True, False, True
                            count_failed_tx = 0
                        else:
                            nonce = None
                            if not result:
                                #N.B. nonce=None triggers web3 getting a nonce
                                priceLP[j], nonce = None, None
                                flag_failed_tx, flag_mint = True, False
                                count_failed_tx += 1
                                #N.B. If MAX_ATTEMPS_FAILED_TX > LP_SWAP_MAX_ATTEMPTS_FAILED_TX, this triggers non-LP swap!
                                if j == NUM_LP and flag_LP_SWAP:
                                    count_LP_SWAP_attempts += 1
                                break #N.B. Break the inner loop
                    else:
                        logger.error(network + ', mint() for ' + str(j) + '-th LP failed MAX_ATTEMPS_FAILED_TX = ' + str(MAX_ATTEMPS_FAILED_TX) + ' times, stop main()!')
                        #logger.info(network + ", session p&l = " + str(session_pl_token1[j]) + " token1" +\
                        #                ", " + "{:1.2f}".format(session_pl_bp[j]) + " bp")
                        logger.info(network + ", session" +\
                                #": i) w/o hedge RL=" + str(session_borrow_pl_token1[j]) + " token1" +\
                                ": borrow p&l w/o swaps=" + "{:1.2f}".format(sum(session_borrow_pl_bp)) + " bp" +\
                                ", RL = " + "{:1.2f}".format(sum(session_RL_bp)) + " bp" +\
                                ", OTM loss = " + "{:1.2f}".format(sum(session_OTM_loss_bp)) + " bp"  +\
                                ", swap cost=" + "{:1.2f}".format(session_swap_cost_bp) + " bp") # +\
                                #", iv) hedge RL=" + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
                        logger.info(network + ', session' +\
                            ': count LP=' + str(session_count_LP) +\
                            ', count swaps=' + str(session_count_swaps) +\
                            ', count LP swaps=' + str(session_count_LP_SWAP) +\
                            ', count LP swaps failed=' + str(session_count_LP_SWAP_failed) +\
                            ', count unwind distance=' + str(session_count_unwind_distance) +\
                            ', count unwind flow=' + str(session_count_unwind_flow) +\
                            ', count unwind signed q=' + str(session_count_unwind_signed_quantity) +\
                            ', count unwind stop=' + str(session_count_unwind_stop) +\
                            ', count unwind pool liq=' + str(session_count_unwind_pool_liq) +\
                            ', count unwind price_mad=' + str(session_count_unwind_max_price_mad) +\
                            ', count hedge RL = ' + str(session_count_hedge_RL) )
                        logger.info(network + ", session: duration = " + "{:1.1f}".format((time.time() - start_time) / 3600) + " h" +\
                            ", LP SWAP duration = " + "{:1.1f}".format(session_LP_SWAP_duration / 60) + " min"
                            ", max price_mad = " + "{:1.5f}".format(max_price_mad) +\
                            ", LP fees = " + "{:1.2f}".format(sum(session_LP_fees_bp)) + " bp" +\
                            ", RL = " + "{:1.2f}".format(sum(session_RL_bp)) + " bp" )
                        logger.info('network, END session')
                        return False
                #N.B. 'if not flag_failed_tx' is not needed here, because unwind tx are checked to not have failed and if mint() fails, it breaks the NUM_LP-loop! 
                #if not flag_failed_tx:
                j += 1

        ###################################################################################
        #N.B. Reporting in log
        unwind_distance_to_bound = [(UNWIND_DIST_TO_BOUND_PER[j][0] / 100, UNWIND_DIST_TO_BOUND_PER[j][1] / 100) for j in range(NUM_LP)] +\
                                    [(- LP_SWAP_UNWIND_DISTANCE_PER / 100, - LP_SWAP_UNWIND_DISTANCE_PER / 100)]
        if tokenIds != (NUM_LP + 1) * [None]:
            if not flag_failed_tx:
                j = 0
                while j <= NUM_LP: # and i < int(RUNTIME_SEC / DELAY_LOOP_SEC) - NUM_LP * MAX_ATTEMPS_FAILED_TX:
                    #N.B. 3a. Estimate quantities to report: RL, asset ratio, LP fees
                    #N.B. Rebalancing Loss (RL)
                    #N.B. see my Crypto doc, Defi Swaps > Uniswap > RL > Uniswap V2 & V3 > RL or > Greeks: https://docs.google.com/document/d/1K83HF3-A9NqFKtjF-wcf6Kduz0r-J0yYchiyOCfaKgo/edit
                    if priceLower[j] is not None and priceUpper[j] is not None and priceLP[j] is not None:
                        
                        tx_borrow_invested_token1[j] = amount0_invested[j] / 10**init.token0_decimal / price + amount1_invested[j] / 10**init.token1_decimal
                        if price_DECIMAL >= priceLower[j] and price_DECIMAL <= priceUpper[j]:
                            RL_v2_bp[j] = 10000 * (2 * np.sqrt(price_DECIMAL / priceLP[j]) / (price_DECIMAL / priceLP[j] + 1) - 1)
                            delta_RL_v2[j] = (1 - price_DECIMAL / priceLP[j]) / np.sqrt(price_DECIMAL / priceLP[j]) / (price_DECIMAL / priceLP[j] + 1)**2
                            v3_v2_mult_factor[j] = (price_DECIMAL / priceLP[j] + 1) / \
                                    (price_DECIMAL / priceLP[j] * (1 - np.sqrt(priceLP[j] / priceUpper[j])) + (1 - np.sqrt(priceLower[j] / priceLP[j])))
                            #time
                            ITM_duration[j] += time.time() - iteration_time
                        else:
                            OTM_duration[j] += time.time() - iteration_time
                            #N.B. Price can change dramatically within DELAY_LOOP_SEC and not be reflected in RL_v3!
                            if price_DECIMAL < priceLower[j]:
                                RL_v2_bp[j] = 10000 * (2 * np.sqrt(priceLower[j] / priceLP[j]) / (priceLower[j] / priceLP[j] + 1) - 1)
                                delta_RL_v2[j] = (1 - priceLower[j] / priceLP[j]) / np.sqrt(priceLower[j] / priceLP[j]) / (priceLower[j] / priceLP[j] + 1)**2
                                v3_v2_mult_factor[j] = (priceLower[j] / priceLP[j] + 1) / \
                                    (priceLower[j] / priceLP[j] * (1 - np.sqrt(priceLP[j] / priceUpper[j])) + (1 - np.sqrt(priceLower[j] / priceLP[j])))
                            elif price_DECIMAL > priceUpper[j]:
                                RL_v2_bp[j] = 10000 * (2 * np.sqrt(priceUpper[j] / priceLP[j]) / (priceUpper[j] / priceLP[j] + 1) - 1)
                                delta_RL_v2[j] = (1 - priceUpper[j] / priceLP[j]) / np.sqrt(priceUpper[j] / priceLP[j]) / (priceUpper[j] / priceLP[j] + 1)**2
                                v3_v2_mult_factor[j] = (priceUpper[j] / priceLP[j] + 1) / \
                                    (priceUpper[j] / priceLP[j] * (1 - np.sqrt(priceLP[j] / priceUpper[j])) + (1 - np.sqrt(priceLower[j] / priceLP[j])))
                        #N.B. adjust for multiple LP-s
                        RL_v2_bp[j] *= tx_borrow_invested_token1[j] / sum(tx_borrow_invested_token1)
                        RL_v3_bp[j] = RL_v2_bp[j] * v3_v2_mult_factor[j] 
                        #N.B. True only if Price_LP is geometric average of priceUpper & priceLower 
                        delta_RL_v3[j] = delta_RL_v2[j] * v3_v2_mult_factor[j]
                        
                        #N.B. Asset ratio
                        if price_DECIMAL < priceLower[j] or min([abs(price_DECIMAL - priceLower[j]), abs(priceLP[j] - priceUpper[j])]) <= EPSILON:
                            asset_ratio_01[j] = 0.
                            asset0_ratio[j], asset1_ratio[j] = 0., 1.
                        elif price_DECIMAL > priceUpper[j] or min([abs(price_DECIMAL - priceUpper[j]), abs(priceLP[j] - priceLower[j])]) <= EPSILON:
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

                        #N.B. OTM loss
                        if price_DECIMAL < priceLower[j]:
                            #N.B. Only approximate because amount0_invested token0 is converted to token1
                            #N.B. Using token0 correctly does not generate OTM_loss for up OTM LP positions (they have amount0_invested = 0)!
                            OTM_loss_bp[j] = amount0_invested[j] / 10**init.token0_decimal * (price_DECIMAL / priceLower[j] - 1.) / price
                        elif price_DECIMAL > priceUpper[j]:
                            #N.B. Only approximate because amount1_invested token1 is converted to token0
                            #N.B. Using token1 correctly does not generate OTM_loss for dows OTM LP positions (they have amount1_invested = 0)!
                            OTM_loss_bp[j] = - amount1_invested[j] / 10**init.token1_decimal * (price_DECIMAL / priceUpper[j] - 1.)
                        else:
                            OTM_loss_bp[j] = 0.
                        OTM_loss_bp[j] *= 10000 / sum(tx_borrow_invested_token1)

                        #logger.info('')
                        logger.info(network + ", " + str(j) + "-th LP" +\
                                            ": dist-to-lower-bound / unwind per = " + "{:1.2f}".format((1. - priceLower[j] / price_DECIMAL) * 100) + "%" +\
                                            " / " + "{:1.2f}".format(unwind_distance_to_bound[j][0] * 100) + "%" +\
                                            ", dist-to-upper-bound / unwind per = " + "{:1.2f}".format((priceUpper[j] / price_DECIMAL - 1.) * 100) + "%" +\
                                            " / " + "{:1.2f}".format(unwind_distance_to_bound[j][1] * 100) + "%" +\
                                            "; ITM dur = " + "{:1.1f}".format(ITM_duration[j] / 60) + " min" +\
                                            "; OTM dur = " + "{:1.1f}".format(OTM_duration[j] / 60) + " min" +\
                                            "; dur = " + "{:1.1f}".format((time.time() - mint_time[j]) / 60) + " min") # +\
                                            #", initial asset0/asset1 = " +  "{:1.3f}".format(asset_ratio_01_LP[j]) +\
                                            #", current rel asset0/asset1 = " +  "{:1.3f}".format(asset_ratio_01[j]) )
                            
                        #N.B. If price_DECIMAL < priceLP[j], RL & OTM loss contribution to borrow p&l is 0, because borrowed token0 converts to token1 which is the bench!
                        tx_estimated_borrow_pl_bp[j] = LP_fees_bp[j] + tx_hedge_RL_pl_bp[j] + hedge_RL_pl_bp[j]
                        #N.B. For LP swaps, RL & OTM loss are 0 in a relative to ETH scale!
                        if abs(amount1_invested[j]) > 0 and price_DECIMAL > priceLP[j] and j != NUM_LP:
                                tx_estimated_borrow_pl_bp[j] += RL_v3_bp[j] + OTM_loss_bp[j]

                        logger.info(network + ", " + str(j) + "-th LP" +\
                                                ": LP fees = " +  "{:1.2f}".format(LP_fees_bp[j]) + " bp" +\
                                                ", RL_v2 = " +  "{:1.2f}".format(RL_v2_bp[j]) + " bp" +\
                                                #", delta_RL_v2 = " +  "{:1.4f}".format(delta_RL_v2[j]) +\
                                                ", RL_v3 = " +  "{:1.2f}".format(RL_v3_bp[j]) + " bp" +\
                                                #", delta_RL_v3 = " +  "{:1.4f}".format(delta_RL_v3[j])+\
                                                #", hedge RL p&l = " +  "{:1.2f}".format(tx_hedge_RL_pl_bp[j] + hedge_RL_pl_bp[j]) + " bp" +\
                                                ", OTM loss = " +  "{:1.2f}".format(OTM_loss_bp[j]) + " bp" +\
                                                ", estimated borrow p&l = " +  "{:1.2f}".format(tx_estimated_borrow_pl_bp[j]) + "bp")
                    
                    j += 1
                    continue
                iteration_time = time.time()
                j = 0
            
            ###########################################################################
            #N.B. Unwind condition
            if flag_mint:
                unwind_condition = (NUM_LP + 1) * [False]
            
                #N.B. Unwind failed tx-s; use specific flags to avoid failed mint() which will trigger unwind_condition!
                if (not flag_increaseLiquidity) or (not flag_hedgeRL) or (not flag_decreaseLiquidity) or (not flag_collect) or (not flag_burn):
                    unwind_condition[j] = True
                #N.B. Unwind during quiet hours
                elif (int(time.strftime('%w', time.gmtime())) != 6 and int(time.strftime('%w', time.gmtime())) != 0 and\
                    ((int(time.strftime('%H', time.gmtime())) >= QUIET_HOURS_START[0] and int(time.strftime('%H', time.gmtime())) < QUIET_HOURS_END[0]) or\
                    (int(time.strftime('%H', time.gmtime())) >= QUIET_HOURS_START[1] and int(time.strftime('%H', time.gmtime())) < QUIET_HOURS_END[1]))):
                    unwind_condition[:NUM_LP] = NUM_LP * [True]
                    logger.info(network + ", UNWIND all LP positions during quiet hours!")
                else:
                    #N.B. Allow for any j to be unwound!
                    #N.B. Treat flag_LP_SWAP
                    if flag_LP_SWAP:
                        #N.B. unwinding at the end!
                        if i >= main_loop_end - MAX_ATTEMPS_FAILED_TX:
                            logger.info('')
                            logger.info(network + ", UNWIND failing LP swap because of the end of main loop!")
                            count_LP_SWAP_attempts += 1
                            #N.B. If not flag_LP_SWAP, non-LP swap is not triggered!
                            #flag_LP_SWAP = False
                            unwind_condition[NUM_LP] = True

                        #N.B. Need lower price!
                        #N.B. Can use amount_to_swap_token0 sign despite the fact that this is not immediately after amount_to_swap_token0 was set up:
                        #N.B. because flag_LP_SWAP and there is only one LP swap, amount_to_swap_token0 has not changed!
                        if amount_to_swap_token0 > 0:
                            #N.B. Unwinding successfully LP swap (price is small enough): token0 is converted into token1
                            if priceLower[NUM_LP] is not None and 1. - priceLower[NUM_LP] / price_DECIMAL <= - LP_SWAP_DISTANCE_TO_BOUND_PER / 100:
                                logger.info('')
                                logger.info(network + ", UNWIND successful LP swap because price = " + str(price) +\
                                   " is LP_SWAP_DISTANCE_TO_BOUND_PER / 100 = " + str(LP_SWAP_DISTANCE_TO_BOUND_PER / 100) + "%" +\
                                   " below priceLower[NUM_LP] = " + str(priceLower[NUM_LP] / 10**init.token0_decimal * 10**init.token1_decimal) + ". flagLP_SWAP = False.")
                                #N.B. Adjustment is only done if tx batch swap; if session swap, session_res_tokenX are zeroed!
                                if not flag_swap_session:
                                    session_res_num_token0 -= amount0_invested[NUM_LP] / 10**init.token0_decimal
                                    session_res_num_token1 += amount0_invested[NUM_LP] / price / 10**init.token0_decimal
                                flag_LP_SWAP = False
                                unwind_condition[NUM_LP] = True
                            #N.B. unwinding failed LP swap: price is too large!
                            if priceUpper[NUM_LP] is not None and priceUpper[NUM_LP] / price_DECIMAL - 1. <= - LP_SWAP_UNWIND_DISTANCE_PER / 100:
                                count_LP_SWAP_attempts += 1
                                logger.info('')
                                logger.info(network + ", UNWIND failing LP swap because price = " + str(price) +\
                                   " is LP_SWAP_UNWIND_DISTANCE_PER / 100 = " + str(LP_SWAP_UNWIND_DISTANCE_PER / 100) + "%" +\
                                   " above priceUpper[NUM_LP] = " + str(priceUpper[NUM_LP] / 10**init.token0_decimal * 10**init.token1_decimal) +\
                                   "; count_LP_SWAP_attempts = " + str(count_LP_SWAP_attempts))
                                unwind_condition[NUM_LP] = True

                            
                        #N.B. Need higher price!
                        #N.B. Can use amount_to_swap_token0 sign despite the fact that this is not immediately after amount_to_swap_token0 was set up:
                        #N.B. because flag_LP_SWAP and there is only one LP swap, amount_to_swap_token0 has not changed!
                        if amount_to_swap_token0 < 0:
                            #N.B. Unwinding successfully LP swap (price is big enough):  token1 is converted into token0
                            if priceUpper[NUM_LP] is not None and priceUpper[NUM_LP] / price_DECIMAL - 1. <= - LP_SWAP_DISTANCE_TO_BOUND_PER / 100:
                                logger.info('')
                                logger.info(network + ", UNWIND successful LP swap because price = " + str(price) +\
                                   " is LP_SWAP_DISTANCE_TO_BOUND_PER / 100 = " + str(LP_SWAP_DISTANCE_TO_BOUND_PER / 100) + "%" +\
                                   " above priceUpper[NUM_LP] = " + str(priceUpper[NUM_LP] / 10**init.token0_decimal * 10**init.token1_decimal) + ". flagLP_SWAP = False.")
                                #N.B. Adjustment is only done if tx batch swap; if session swap, session_res_tokenX are zeroed!
                                if not flag_swap_session:
                                    session_res_num_token0 += amount1_invested[NUM_LP] * price / 10**init.token1_decimal
                                    session_res_num_token1 -= amount1_invested[NUM_LP] / 10**init.token1_decimal
                                flag_LP_SWAP = False
                                unwind_condition[NUM_LP] = True
                            #N.B. unwinding failed LP swap: price is too small!
                            if priceLower[NUM_LP] is not None and 1. - priceLower[NUM_LP] / price_DECIMAL <= -LP_SWAP_UNWIND_DISTANCE_PER /100:
                                count_LP_SWAP_attempts += 1
                                logger.info('')
                                logger.info(network + ", UNWIND failing LP swap because price = " + str(price) +\
                                   " is LP_SWAP_UNWIND_DISTANCE_PER / 100 = " + str(LP_SWAP_UNWIND_DISTANCE_PER / 100) + "%" +\
                                   " below priceLower[NUM_LP] = " + str(priceLower[NUM_LP] / 10**init.token0_decimal * 10**init.token1_decimal) +\
                                   "; count_LP_SWAP_attempts = " + str(count_LP_SWAP_attempts))
                                unwind_condition[NUM_LP] = True
            
                    #N.B. Treat non-LP_SWAP LP tx-s
                    if price_mad > PRICE_MAD[-1]:
                        logger.info('')
                        logger.info(network + ", UNWIND all LP positions because price_mad = " + str(price_mad) +\
                                                    " > PRICE_MAD[-1] = " + str(PRICE_MAD[-1]))
                        unwind_condition[:NUM_LP] = NUM_LP * [True]
                        session_count_unwind_max_price_mad += 1

                    if EVENT_LOGS and signed_token1_quantity / pool_liquidity_list[-1]  *\
                                            10 ** (0.5 * (init.token0_decimal + init.token1_decimal)) * 10000 > MAX_UNWIND_TOKEN1_QUANTITY_TO_TVL_BP:
                        logger.info('')
                        logger.info(network + ", UNWIND all LP positions because signed_token1_quantity / pool_liquidity * 10000 = " +\
                                            "{:1.4f}".format(signed_token1_quantity / pool_liquidity_list[-1] *\
                                                    10 ** (0.5 * (init.token0_decimal + init.token1_decimal)) * 10000) +\
                                            " > MAX_UNWIND_TOKEN1_QUANTITY_TO_TVL_BP = " + str(MAX_UNWIND_TOKEN1_QUANTITY_TO_TVL_BP))
                        unwind_condition[:NUM_LP] = NUM_LP * [True]
                        session_count_unwind_signed_quantity += 1

                    if EVENT_LOGS and pool_liquidity_list[-1] < pool_liquidity_LP * MIN_POOL_LIQUIDITY_PER[-1] / 100:
                        logger.info('')
                        logger.info(network + ", UNWIND all LP positions because pool liq = " +\
                                    "{:1.0f}".format(pool_liquidity_list[-1] / 10 ** (0.5 * (init.token0_decimal + init.token1_decimal))) +\
                                    " < initiation LP pool liq * threshold = " +\
                                    "{:1.0f}".format(pool_liquidity_LP  / 10 ** (0.5 * (init.token0_decimal + init.token1_decimal)) * MIN_POOL_LIQUIDITY_PER[-1] / 100))
                        unwind_condition[:NUM_LP] = NUM_LP * [True]
                        session_count_unwind_pool_liq += 1

                    #N.B. failed tx-s are hadled in the top condition!
                    j = 0
                    while j < NUM_LP:

                        #N.B. Stop-profit / stop-loss
                        if LP_fees_bp[j] + RL_v3_bp[j] + tx_hedge_RL_pl_bp[j] + hedge_RL_pl_bp[j] < - STOP_LOSS_BP or\
                            LP_fees_bp[j] + RL_v3_bp[j] + tx_hedge_RL_pl_bp[j] + hedge_RL_pl_bp[j] > STOP_PROFIT_BP:
                            #logger.info('')
                            logger.info(network + ", UNWIND " + str(j) + "-th LP position because tx p&l < - " + str(STOP_LOSS_BP) + " bp or > " + str(STOP_PROFIT_BP) + " bp")
                            unwind_condition[j] = True
                            session_count_unwind_stop += 1
                
                        if priceLower[j] is not None and 1. - priceLower[j] / price_DECIMAL <= unwind_distance_to_bound[j][0]:
                                #asset_ratio_01 <= UNWIND_ASSET_RATIO_PER / 100 or asset_ratio_01 >= 1. / (UNWIND_ASSET_RATIO_PER / 100)
                                logger.info('')
                                logger.info(network + ", UNWIND " + str(j) + "-th LP position because lower unwind_distance_to_bound[" + str(j) + "] = " +\
                                        str(unwind_distance_to_bound[j][0]) + " is reached!")
                                unwind_condition[j] = True
                                session_count_unwind_distance += 1

                        if priceUpper[j] is not None and priceUpper[j] / price_DECIMAL - 1. <= unwind_distance_to_bound[j][1]:
                            #asset_ratio_01 <= UNWIND_ASSET_RATIO_PER / 100 or asset_ratio_01 >= 1. / (UNWIND_ASSET_RATIO_PER / 100)
                            logger.info('')
                            logger.info(network + ", UNWIND " + str(j) + "-th LP position because upper unwind_distance_to_bound[" + str(j) + "] = " +\
                                        str(unwind_distance_to_bound[j][1]) + " is reached!")
                            unwind_condition[j] = True
                            session_count_unwind_distance += 1

                        if swap_volume_token1[j] > MIN_UNWIND_SWAP_VOLUME_TOKEN1 and swap_flow_token1[j] > MIN_UNWIND_SWAP_FLOW_PER / 100 * swap_volume_token1[j]:
                            logger.info('')
                            logger.info(network + ", UNWIND " + str(j) + "-th LP position because swap_volume_token1[" + str(j) + "] = " + "{:1.0f}".format(swap_volume_token1[j]) +\
                                        " > MIN_UNWIND_SWAP_VOLUME_TOKEN1 = " + str(MIN_UNWIND_SWAP_VOLUME_TOKEN1) +\
                                        " and swap_flow[" + str(j) + "] / swap_volume[" + str(j) + "]= " +\
                                        "{:1.2f}".format(swap_flow_token1[j] / swap_volume_token1[j] * 100) + "%" +\
                                        " > MIN_UNWIND_SWAP_FLOW_PER = " + str(MIN_UNWIND_SWAP_FLOW_PER) + "%")
                            logger.info('')
                            unwind_condition[j] = True
                            session_count_unwind_flow += 1

                        j += 1
                        continue

                #N.B. Last iterations reserved for unwinding non-LP_SWAP tx-s
                if i >= int(RUNTIME_SEC / DELAY_LOOP_SEC) - NUM_LP * MAX_ATTEMPS_FAILED_TX:
                    unwind_condition[:NUM_LP] = NUM_LP * [True]
            
                if TEST:
                    unwind_condition = [unwind_condition[j] or i % 2 == 1 for j in range(NUM_LP)] + [False]

                ###########################################################################
                #N.B. decreaseLiquidity(), collect(), burn() (only if unwind_condition[j])
                tx_batch_amount_to_swap_token1 = 0.
                if not flag_failed_tx:
                    j = 0
                while j <= NUM_LP:
                    #if j == NUM_LP and not flag_LP_SWAP: #N.B. When j += 1, this line is hit but if unwind_condition[NUM_LP] == False, nothing will happen!
                    #    j = 0
                    #    break
                    if unwind_condition[j] and tokenIds[j] is not None and liquidities[j] is not None:

                        #############################
                        #4. decreaseLiquidity()
                        #N.B. If decreaseLiquidity() tx fails, run only the failed decreaseLiquidity() in the next iteration!
                        if flag_mint and flag_increaseLiquidity and flag_hedgeRL and flag_collect and flag_burn:
                        
                            if count_failed_tx < MAX_ATTEMPS_FAILED_TX:
                                #N.B. If decreaseLiquidity() tx fails, run only the failed decreaseLiquidity() in the next main loop iteration!
                                #N.B. Passing nonce speeds up execution
                                result = decreaseLiquidity(network, tokenIds[j], liquidities[j],\
                                                max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas, \
                                                            address=Address, private_key=privateKey, init=init, nonce=nonce)
                                if isinstance(result, tuple):
                                    amount0, amount1, nonce = result
                                    flag_failed_tx, flag_decreaseLiquidity = False, True
                                    count_failed_tx = 0
                                    liquidities[j] = None
                                    unwind_condition[j] = False
                                    #hedge_RL = HEDGE_RL
                                    decreaseLiquidity_time[j] = time.time()
                                else:
                                    nonce = None
                                    if not result:
                                        #N.B. nonce=None triggers web3 getting a nonce
                                        flag_failed_tx, flag_decreaseLiquidity, nonce = True, False, None
                                        count_failed_tx += 1
                                        break #N.B. Break the NUM_LP-loop and continue with code
                            else:
                                logger.error(network + ', decreaseLiquidity() for ' + str(j) + '-th LP failed MAX_ATTEMPS_FAILED_TX = ' + str(MAX_ATTEMPS_FAILED_TX) + ' times, stop main()!')
                                #logger.info(network + ", session p&l = " + str(session_pl_token1[j]) + " token1" +\
                                #                        ", " + "{:1.2f}".format(session_pl_bp[j]) + " bp")
                                logger.info(network + ", session" +\
                                    #": i) w/o hedge RL=" + str(session_borrow_pl_token1[j]) + " token1" +\
                                    ": borrow p&l w/o swaps=" + "{:1.2f}".format(sum(session_borrow_pl_bp)) + " bp" +\
                                    ", RL = " + "{:1.2f}".format(sum(session_RL_bp)) + " bp" +\
                                    ", OTM loss = " + "{:1.2f}".format(sum(session_OTM_loss_bp)) + " bp"  +\
                                    ", swap cost=" + "{:1.2f}".format(session_swap_cost_bp) + " bp") # +\
                                    #", iv) hedge RL=" + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
                                logger.info(network + ', session' +\
                                    ': count LP=' + str(session_count_LP) +\
                                    ', count swaps=' + str(session_count_swaps) +\
                                    ', count LP swaps=' + str(session_count_LP_SWAP) +\
                                    ', count LP swaps failed=' + str(session_count_LP_SWAP_failed) +\
                                    ', count unwind distance=' + str(session_count_unwind_distance) +\
                                    ', count unwind flow=' + str(session_count_unwind_flow) +\
                                    ', count unwind signed q=' + str(session_count_unwind_signed_quantity) +\
                                    ', count unwind stop=' + str(session_count_unwind_stop) +\
                                    ', count unwind pool liq=' + str(session_count_unwind_pool_liq) +\
                                    ', count unwind price_mad=' + str(session_count_unwind_max_price_mad) +\
                                    ', count hedge RL = ' + str(session_count_hedge_RL) )
                                logger.info(network + ", session: duration = " + "{:1.1f}".format((time.time() - start_time) / 3600) + " h" +\
                                    ", LP SWAP duration = " + "{:1.1f}".format(session_LP_SWAP_duration / 60) + " min"
                                    ", max price_mad = " + "{:1.5f}".format(max_price_mad) +\
                                    ", LP fees = " + "{:1.2f}".format(sum(session_LP_fees_bp)) + " bp" +\
                                    ", RL = " + "{:1.2f}".format(sum(session_RL_bp)) + " bp" )
                                logger.info('network, END session')
                                return False

                        #####################################################################
                        #5. collect()
                        #N.B. If collect() tx fails, run only the failed collect() in the next iteration!
                        #time.sleep(3)
                        if flag_mint and flag_increaseLiquidity and flag_hedgeRL and flag_decreaseLiquidity and flag_burn:
                            if count_failed_tx < MAX_ATTEMPS_FAILED_TX:
                                                  
                                result = collect(tokenIds[j], network, max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas, \
                                                    address=Address, private_key=privateKey, init=init, nonce=nonce)
                                if isinstance(result, tuple):
                                    amount0, amount1, nonce = result
                                    blockNumber_init, price_init = block_num, price #if signed_token1_quantity > 0 else -price
                            
                                    #N.B. tx
                                    tx_collected_token1 = amount0 / 10**init.token0_decimal / price + amount1 / 10**init.token1_decimal
                                    tx_borrow_invested_token1[j] = amount0_invested[j] / 10**init.token0_decimal / price + amount1_invested[j] / 10**init.token1_decimal
                                    tx_borrow_pl_bp[j] = (tx_collected_token1 - tx_borrow_invested_token1[j]) / sum(tx_borrow_invested_token1) * 10000
                                    #N.B. If price < priceLP, RL & OTM loss contribution to borrow p&l is 0, because borrowed token0 converts to token1 which is the bench!
                                    if price_DECIMAL <= priceLP[j]:
                                        tx_borrow_pl_bp[j] -= RL_v3_bp[j] + OTM_loss_bp[j]
                                    #N.B. tx hedge RL P&L is a sum tx_hedge_RL_pl_bp + hedge_RL_pl_bp:  hedge_RL_pl_bp measures hedge RL  P&L only from the last hedge!
                                    tx_borrow_pl_bp[j] += tx_hedge_RL_pl_bp[j] + hedge_RL_pl_bp[j]
                                    tickLower[j], priceLower[j], tickUpper[j], priceUpper[j], priceLP[j] = None, None, None, None, None
                                    if j < NUM_LP:
                                    #N.B. tx_batch_amount_to_swap_token1: swap tx_batch_amount_to_swap_token1*price token0 into token1 if > 0 or -tx_batch_amount_to_swap_token1 token1 into token0 if < 0
                                        tx_batch_amount_to_swap_token1 += -(amount1 - amount1_invested[j]) / 10**init.token1_decimal
                                        tx_res_num_token0,  tx_res_num_token1 = (amount0 - amount0_invested[j]) / 10**init.token0_decimal, (amount1 - amount1_invested[j]) / 10**init.token1_decimal
                                

                                        #N.B. tx P&L log report
                                        #logger.info('')
                                        #logger.info(network + ", LP tx (w/o possible swap) for " + str(j) + "-th LP p&l = " +\
                                        #                str(tx_collected_token1 - tx_invested_token1[j]) + " token1" +\
                                        #                ", " + "{:1.2f}".format((tx_collected_token1 - tx_invested_token1[j]) / sum(tx_invested_token1) * 10000) + " bp" +\
                                        #                ", tx_borrow_invested_token1 = " + str(tx_borrow_invested_token1[j]))
                                        logger.info(network + ", LP tx (w/o possible swap) for " + str(j) + "-th LP borrow p&l" +\
                                                        #", i) " + str(tx_collected_token1 - tx_borrow_invested_token1[j]) + " token1" +\
                                                        ", ii) " + "{:1.2f}".format(tx_borrow_pl_bp[j]) + " bp" +\
                                                        #", iii) hedge RL=" + "{:1.2f}".format(tx_hedge_RL_pl_bp[j] + hedge_RL_pl_bp[j]) + " bp" +\
                                                        #"; num hedge RL=" + str(tx_count_hedge_RL[j]) +\
                                                        "; ITM duration=" + "{:1.1f}".format(ITM_duration[j] / 60) + " min" +\
                                                        "; OTM duration=" + "{:1.1f}".format(OTM_duration[j] / 60) + " min" +\
                                                        "; duration=" + "{:1.1f}".format((decreaseLiquidity_time[j] - mint_time[j]) / 60) + " min" +\
                                                        "; tx batch amount_to_swap_token1=" + "{:1.5f}".format(tx_batch_amount_to_swap_token1) + " token1" )
                                                        #"; tx swap flow token1 = " + "{:1.1f}".format(swap_flow_token1))

                                
                                        #N.B. session
                                        session_pl_token1[j] += tx_collected_token1 - tx_invested_token1[j]
                                        session_borrow_pl_token1[j] += tx_collected_token1 - tx_borrow_invested_token1[j]
                                        session_pl_bp[j] +=  (tx_collected_token1 - tx_invested_token1[j]) / sum(tx_invested_token1) * 10000
                                        session_borrow_pl_bp[j] += tx_borrow_pl_bp[j]
                                        session_OTM_loss_bp[j] += OTM_loss_bp[j]
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
                                                ": borrow p&l = " + "{:1.2f}".format(session_borrow_pl_bp[j]) + " bp"  +\
                                                ", RL = " + "{:1.2f}".format(session_RL_bp[j]) + " bp" +\
                                                ", OTM loss = " + "{:1.2f}".format(session_OTM_loss_bp[j]) + " bp"  +\
                                                "; ITM duration=" + "{:1.1f}".format(session_ITM_duration[j] / 60) + " min" +\
                                                "; OTM duration=" + "{:1.1f}".format(session_OTM_duration[j] / 60) + " min")
                                        
                                                #", iv) hedge RL=" + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
                                
                                        #logger.info(network + ", session" +\
                                        #                ": LP fees  for " + str(j) + "-th LP = " + "{:1.2f}".format(session_LP_fees_bp[j]) + " bp" +\
                                        #                ", RL  for " + str(j) + "-th LP= " + "{:1.2f}".format(session_RL_bp[j]) + " bp")
                                    else:
                                        #session_swap_cost_bp += (tx_collected_token1 - tx_invested_token1[NUM_LP]) / sum(tx_invested_token1) * 10000
                                        logger.info(network + ", LP swap tx p&l = " + "{:1.2f}".format(tx_borrow_pl_bp[NUM_LP]) + " bp" +\
                                                            ", session swap cost=" + "{:1.2f}".format(session_swap_cost_bp) + " bp" )
                                    flag_failed_tx, flag_collect = False, True
                                    count_failed_tx = 0
                                else:
                                    if not result:
                                        nonce = None
                                    #N.B. nonce=None triggers web3 getting a nonce
                                    flag_failed_tx, flag_collect, nonce = True, False, None
                                    count_failed_tx += 1
                                    break #N.B. Break the NUM_LP-loop and continue with code
                            else:
                                logger.error(network + ', collect() for ' + str(j) + '-th LP failed MAX_ATTEMPS_FAILED_TX = ' + str(MAX_ATTEMPS_FAILED_TX) +  ' times, stop main()!')
                                #logger.info(network + ", session p&l = " + str(session_pl_token1[j]) + " token1" +\
                                #                    ", " + "{:1.2f}".format(session_pl_bp[j]) + " bp")
                                logger.info(network + ", session" +\
                                    #": i) w/o hedge RL=" + str(session_borrow_pl_token1[j]) + " token1" +\
                                    ": borrow p&l w/o swaps=" + "{:1.2f}".format(sum(session_borrow_pl_bp)) + " bp" +\
                                    ", RL = " + "{:1.2f}".format(sum(session_RL_bp)) + " bp" +\
                                    ", OTM loss = " + "{:1.2f}".format(sum(session_OTM_loss_bp)) + " bp"  +\
                                    ", swap cost=" + "{:1.2f}".format(session_swap_cost_bp) + " bp" ) #+\
                                    #", iv) hedge RL=" + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
                                logger.info(network + ', session' +\
                                    ': count LP=' + str(session_count_LP) +\
                                    ', count swaps=' + str(session_count_swaps) +\
                                    ', count LP swaps=' + str(session_count_LP_SWAP) +\
                                    ', count LP swaps failed=' + str(session_count_LP_SWAP_failed) +\
                                    ', count unwind distance=' + str(session_count_unwind_distance) +\
                                    ', count unwind flow=' + str(session_count_unwind_flow) +\
                                    ', count unwind signed q=' + str(session_count_unwind_signed_quantity) +\
                                    ', count unwind stop=' + str(session_count_unwind_stop) +\
                                    ', count unwind pool liq=' + str(session_count_unwind_pool_liq) +\
                                    ', count unwind price_mad=' + str(session_count_unwind_max_price_mad) +\
                                    ', count hedge RL = ' + str(session_count_hedge_RL) )
                                logger.info(network + ", session: duration = " + "{:1.1f}".format((time.time() - start_time) / 3600) + " h" +\
                                    ", LP SWAP duration = " + "{:1.1f}".format(session_LP_SWAP_duration / 60) + " min"
                                    ", max price_mad = " + "{:1.5f}".format(max_price_mad) +\
                                    ", LP fees = " + "{:1.2f}".format(sum(session_LP_fees_bp)) + " bp" +\
                                    ", RL = " + "{:1.2f}".format(sum(session_RL_bp)) + " bp" )
                                logger.info('network, END session')
                                return False

                    
                            #N.B. session log report
                            logger.info(network + ", session: res num token0 = " + str(session_res_num_token0) +\
                                                            ", res num token1 = " + str(session_res_num_token1) )
                            logger.info(network + ', session' +\
                                ': count mint=' + str(session_count_LP) +\
                                ', count swaps=' + str(session_count_swaps) +\
                                ', count LP swaps =' + str(session_count_LP_SWAP) +\
                                ', count LP swaps failed=' + str(session_count_LP_SWAP_failed) +\
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
                        #6. burn(): otherwise the NFT (corresponding to the LP) stays in the wallet & can be seen running current_LP_positions()
                        #N.B. From the docs: "The token must have 0 liquidity and all tokens must be collected first.": https://docs.uniswap.org/protocol/reference/periphery/NonfungiblePositionManager
                        #N.B. If tokens not collected first, burn() tx produces error on Etherscan "Fail with error 'Not cleared'"
                        #N.B. If burn() tx fails, run only burn() in the next iteration!
                        #N.B. swap() is after burn() because swap() does not depend on unwind_condition: if burn() fails, swap() is delayed!
                        if flag_mint and flag_increaseLiquidity and flag_hedgeRL and flag_decreaseLiquidity and flag_collect:
                            if count_failed_tx < MAX_ATTEMPS_FAILED_TX:                        
                                if burn(tokenIds[j], network, max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas, \
                                                address=Address, private_key=privateKey, init=init, nonce=nonce):
                                    tokenIds_burned += [tokenIds[j]]
                                    nonce += 1
                                    flag_change_tokenIds = True
                                    tokenIds[j] = None
                                    if j == NUM_LP: #N.B. flag_LP_SWAP = False above!
                                        session_LP_SWAP_duration += time.time() - LP_SWAP_start_time
                                    flag_failed_tx, flag_burn = False, True
                                    count_failed_tx = 0
                                else:
                                    #N.B. nonce=None triggers web3 getting a nonce
                                    flag_failed_tx, flag_burn, nonce = True, False, None
                                    count_failed_tx += 1
                                    break #N.B. Break the NUM_LP-loop and continue with code
                            else:
                                logger.error(network + ', burn() for ' + str(j) + '-th LP failed MAX_ATTEMPS_FAILED_TX = ' + str(MAX_ATTEMPS_FAILED_TX) + ' times, stop main()!')
                                #logger.info(network + ", session p&l = " + str(session_pl_token1[j]) + " token1" +\
                                #                    ", " + "{:1.2f}".format(session_pl_bp[j]) + " bp")
                                logger.info(network + ", session" +\
                                    #": i) w/o hedge RL=" + str(session_borrow_pl_token1[j]) + " token1" +\
                                    ": borrow p&l w/o swaps=" + "{:1.2f}".format(sum(session_borrow_pl_bp)) + " bp" +\
                                    ", RL = " + "{:1.2f}".format(sum(session_RL_bp)) + " bp" +\
                                    ", OTM loss = " + "{:1.2f}".format(sum(session_OTM_loss_bp)) + " bp"  +\
                                    ", swap cost=" + "{:1.2f}".format(session_swap_cost_bp) + " bp" ) #+\
                                    #", iv) hedge RL=" + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
                                logger.info(network + ', session' +\
                                    ': count LP=' + str(session_count_LP) +\
                                    ', count swaps=' + str(session_count_swaps) +\
                                    ', count LP swaps=' + str(session_count_LP_SWAP) +\
                                    ', count LP swaps failed=' + str(session_count_LP_SWAP_failed) +\
                                    ', count unwind distance=' + str(session_count_unwind_distance) +\
                                    ', count unwind flow=' + str(session_count_unwind_flow) +\
                                    ', count unwind signed q=' + str(session_count_unwind_signed_quantity) +\
                                    ', count unwind stop=' + str(session_count_unwind_stop) +\
                                    ', count unwind pool liq=' + str(session_count_unwind_pool_liq) +\
                                    ', count unwind price_mad=' + str(session_count_unwind_max_price_mad) +\
                                    ', count hedge RL = ' + str(session_count_hedge_RL) )
                                logger.info(network + ", session: duration = " + "{:1.1f}".format((time.time() - start_time) / 3600) + " h" +\
                                    ", LP SWAP duration = " + "{:1.1f}".format(session_LP_SWAP_duration / 60) + " min"
                                    ", max price_mad = " + "{:1.5f}".format(max_price_mad) +\
                                    ", LP fees = " + "{:1.2f}".format(sum(session_LP_fees_bp)) + " bp" +\
                                    ", RL = " + "{:1.2f}".format(sum(session_RL_bp)) + " bp" )
                                logger.info('network, END session')
                                return False

                    #N.B. 'if not flag_failed_tx' is not needed here because mint() is checked to not have failed and if the uwind tx-s fail, they break the NUM_LP-loop!
                    #if not flag_failed_tx:         
                    j += 1

                if (not flag_failed_tx):
                    if amount_to_swap_token0 is not None and priceLower[NUM_LP] is not None and priceUpper[NUM_LP] is not None:
                        logger.info(network + ", LP SWAP tx with amount_to_swap_token0 = " + str(amount_to_swap_token0) +\
                            ", priceLower = " + "{:1.5f}".format(priceLower[NUM_LP] / 10**init.token0_decimal * 10**init.token1_decimal) +\
                            ", priceUpper = " + "{:1.5f}".format(priceUpper[NUM_LP] / 10**init.token0_decimal * 10**init.token1_decimal) +\
                            ", duration = " + "{:1.1f}".format((time.time() - LP_SWAP_start_time) / 60) + " min")
                    if unwind_condition[:NUM_LP] != NUM_LP * [None] and i <= int(RUNTIME_SEC / DELAY_LOOP_SEC):
                        logger.info(network + ", session" +\
                                #": i) w/o hedge RL=" + str(session_borrow_pl_token1[j]) + " token1" +\
                                ": borrow p&l w/o swaps= " + "{:1.2f}".format(sum(session_borrow_pl_bp)) + " bp"  +\
                                ", RL = " + "{:1.2f}".format(sum(session_RL_bp)) + " bp" +\
                                ", OTM loss = " + "{:1.2f}".format(sum(session_OTM_loss_bp)) + " bp"  +\
                                ", swap cost=" + "{:1.2f}".format(session_swap_cost_bp) + " bp" +\
                                ", duration = " + "{:1.1f}".format((time.time() - start_time) / 3600) + " h")
                    #else:
                    #    logger.info(network + ", session LP SWAP duration = " + "{:1.1f}".format(session_LP_SWAP_duration / 60) + " min")

                
            
                 
        ######################################################################
        #7. Swap the collected amounts difference to achieve the original amounts
        #N.B. If slippage is too low, get error 'Too little received'
        #N.B. If swap() tx fails, run only the failed swap() in the next swap iteration!
        if flag_mint and flag_increaseLiquidity and flag_hedgeRL and flag_decreaseLiquidity and flag_collect and flag_burn and\
            (not flag_LP_SWAP or count_LP_SWAP_attempts >= LP_SWAP_MAX_ATTEMPTS_FAILED_TX or i == main_loop_end - MAX_ATTEMPS_FAILED_TX):
            #logger.info('')
            
            #swap_condition
            #N.B. If a failed LP swap or the end of main loop, standard swap is executed!
            if flag_LP_SWAP and (count_LP_SWAP_attempts >= LP_SWAP_MAX_ATTEMPTS_FAILED_TX or i == main_loop_end - MAX_ATTEMPS_FAILED_TX):
                if count_LP_SWAP_attempts >= LP_SWAP_MAX_ATTEMPTS_FAILED_TX:
                    logger.info(network + ", LP SWAP tx with tokenId = " + str(tokenIds[NUM_LP]) + " failed " +\
                            str(count_LP_SWAP_attempts) + " times, standard swap is executed with amount_to_swap_token0 = " + str(amount_to_swap_token0))
                if i == main_loop_end - MAX_ATTEMPS_FAILED_TX:
                    logger.info(network + ", LP SWAP tx with tokenId = " + str(tokenIds[NUM_LP]) + " failed because i = " +\
                            str(main_loop_end - MAX_ATTEMPS_FAILED_TX) + ", standard swap is executed with amount_to_swap_token0 = " + str(amount_to_swap_token0))
                session_count_LP_SWAP_failed += 1
                flag_LP_SWAP = False #N.B. Affects the end of the loop
                swap_condition = True
            else:
                amount_to_swap_token0 = 0.
                swap_condition = False

                #N.B. session swap: overwrites tx batch swap because session_res_num_token1 includes tx_batch_amount_to_swap_token1
                if abs(session_res_num_token1) > MIN_SESSION_SWAP_PER / 100 * sum(tx_borrow_invested_token1) or\
                        i >= int(RUNTIME_SEC / DELAY_LOOP_SEC):
                    if session_res_num_token0 > 0:
                        amount_to_swap_token0 = session_res_num_token0
                    elif session_res_num_token1 > 0:
                        amount_to_swap_token0 = -session_res_num_token1 * price
                    session_res_num_token0, session_res_num_token1 = 0., 0.
                    logger.info(network + ", session swap: amount_to_swap_token0 = " + str(amount_to_swap_token0))
                    swap_condition, flag_swap_session = True, True
                else:
                    flag_swap_session = False
                    logger.info(network + ", no session swap: abs(session_res_num_token1)=" + str(abs(session_res_num_token1)) +\
                            " <= min session swap token1=" + str(MIN_SESSION_SWAP_PER / 100 * sum(tx_borrow_invested_token1)))
                    #N.B. tx batch swap
                    #N.B. swap tx_batch_amount_to_swap_token1 token0 into token1 if > 0 or -tx_batch_amount_to_swap_token1 token1 into token0 if < 0
                    if abs(tx_batch_amount_to_swap_token1) > MIN_TX_BATCH_SWAP_PER / 100 * sum(tx_borrow_invested_token1):
                        amount_to_swap_token0 = tx_batch_amount_to_swap_token1 * price
                        session_res_num_token0 -= tx_batch_amount_to_swap_token1 * price
                        session_res_num_token1 += tx_batch_amount_to_swap_token1
                        tx_batch_amount_to_swap_token1 = 0.
                        logger.info(network + ", tx batch swap: amount_to_swap_token0 = " + str(amount_to_swap_token0))
                        swap_condition = True
                    else:
                        logger.info(network + ", no tx batch swap either: abs(tx_batch_amount_to_swap_token1) = " + str(abs(tx_batch_amount_to_swap_token1)) +\
                           " <= min tx swap threshold = " + str(MIN_TX_BATCH_SWAP_PER / 100 * sum(tx_borrow_invested_token1)) + ", continue with next iter...")
                        swap_condition = False
                    

            #swap()
            if swap_condition and abs(amount_to_swap_token0) > SWAP_EPSILON_PER / 100  * sum(tx_borrow_invested_token1) * price :
                logger.info(network + ", swap_condition is raised and amount_to_swap_token0 = " + str(amount_to_swap_token0) + " with abs(amount_to_swap_token0) > " +\
                        str(SWAP_EPSILON_PER / 100  * sum(tx_borrow_invested_token1) * price) )
                if LP_SWAP and count_LP_SWAP_attempts < LP_SWAP_MAX_ATTEMPTS_FAILED_TX and i < main_loop_end - MAX_ATTEMPS_FAILED_TX:
                    flag_LP_SWAP = True
                    logger.info(network + ", flag_LP_SWAP is raised! count_LP_SWAP_attempts = " + str(count_LP_SWAP_attempts))
                    #N.B. Get fresh price before LP swap
                    i += 1
                    continue
                else:
                    flag_LP_SWAP, count_LP_SWAP_attempts = False, 0
                    #N.B. Size-split swap: if amount_to_swap_token0 > 0, swap amount_to_swap_token0 token0 to token1; if < 0, swap -amount_to_swap_token0 token1 to token0;
                    #N.B. Passing nonce speeds up execution
                    result = size_split_swap(network, price, amount_to_swap_token0,\
                        max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas,\
                        address=Address, private_key=privateKey, init=init, nonce=nonce)
                    if isinstance(result, tuple):
                        pool_liquidity, pool_price, swap_price, slippage_and_pool_fee_token1, nonce = result
                        session_count_swaps += 1
                        #N.B. tx
                        tx_slippage_and_pool_fee_pl_bp += slippage_and_pool_fee_token1 / sum(tx_borrow_invested_token1) * 10000 if\
                                sum(tx_borrow_invested_token1) > 0 else 0.
                        logger.info(network + ", non-LP swap tx slippage & pool fee cost = " +\
                                        "{:1.2f}".format(tx_slippage_and_pool_fee_pl_bp) + " bp" )#+\
                                        #"; tx swap flow token1 = " + "{:1.1f}".format(swap_flow_token1))
                        #N.B. session
                        session_swap_cost_bp += tx_slippage_and_pool_fee_pl_bp
                        #session_borrow_pl_bp[j] += tx_slippage_and_pool_fee_pl_bp
                        logger.info(network + ', session: count swaps=' + str(session_count_swaps) +\
                                    #" i) " + "{:1.2f}".format(session_borrow_pl_bp[j]) + " bp"  +\
                                    ", swap cost=" + "{:1.2f}".format(session_swap_cost_bp) + " bp")
                    else:
                        nonce = None
                        if result:
                            break #N.B. continue with code!
                        else:
                            if flag_increaseLiquidity and flag_hedgeRL and flag_decreaseLiquidity and flag_collect and flag_burn:
                                logger.error(network + ', hedge size_split_swap() failed MAX_ATTEMPS_FAILED_TX = ' + str(MAX_ATTEMPS_FAILED_TX) +\
                                    ' times for swap iteration, stop main()!')
                                #logger.info(network + ", session p&l = " + str(session_pl_token1[j]) + " token1" +\
                                #                    ", " + "{:1.2f}".format(session_pl_bp[j]) + " bp")
                                logger.info(network + ", session" +\
                                #": i) w/o hedge RL=" + str(session_borrow_pl_token1[j]) + " token1" +\
                                ": borrow p&l w/o swaps=" + "{:1.2f}".format(sum(session_borrow_pl_bp)) + " bp" +\
                                ", RL = " + "{:1.2f}".format(sum(session_RL_bp)) + " bp" +\
                                ", OTM loss = " + "{:1.2f}".format(sum(session_OTM_loss_bp)) + " bp"  +\
                                ", swap cost=" + "{:1.2f}".format(session_swap_cost_bp) + " bp") # +\
                                #", iv) hedge RL=" + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
                                logger.info(network + ', session' +\
                                    ': count LP=' + str(session_count_LP) +\
                                    ', count swaps=' + str(session_count_swaps) +\
                                    ', count LP swaps=' + str(session_count_LP_SWAP) +\
                                    ', count LP swaps failed=' + str(session_count_LP_SWAP_failed) +\
                                    ', count unwind distance=' + str(session_count_unwind_distance) +\
                                    ', count unwind flow=' + str(session_count_unwind_flow) +\
                                    ', count unwind signed q=' + str(session_count_unwind_signed_quantity) +\
                                    ', count unwind stop=' + str(session_count_unwind_stop) +\
                                    ', count unwind pool liq=' + str(session_count_unwind_pool_liq) +\
                                    ', count unwind price_mad=' + str(session_count_unwind_max_price_mad) +\
                                    ', count hedge RL = ' + str(session_count_hedge_RL) )
                                logger.info(network + ", session: duration = " + "{:1.1f}".format((time.time() - start_time) / 3600) + " h" +\
                                        ", LP SWAP duration = " + "{:1.1f}".format(session_LP_SWAP_duration / 60) + " min"
                                        ", max price_mad = " + "{:1.5f}".format(max_price_mad) +\
                                        ", LP fees = " + "{:1.2f}".format(sum(session_LP_fees_bp)) + " bp" +\
                                        ", RL = " + "{:1.2f}".format(sum(session_RL_bp)) + " bp" )
                                logger.info('network, END session')
                                return False
                       
                
        #N.B. End
        if i >= int(RUNTIME_SEC / DELAY_LOOP_SEC):
            if main_loop_end % 50 == 0:
                #logger.info(network + ", session p&l = " + str(sum(session_pl_token1)) + " token1" +\
                #                ", " + "{:1.2f}".format(sum(session_pl_bp)) + " bp")
                logger.info(network + ", session" +\
                                #": i) w/o hedge RL=" + str(sum(session_borrow_pl_token1)) + " token1" +\
                                ": borrow p&l w/o swaps=" + "{:1.2f}".format(sum(session_borrow_pl_bp)) + " bp" +\
                                ", RL = " + "{:1.2f}".format(sum(session_RL_bp)) + " bp" +\
                                ", OTM loss = " + "{:1.2f}".format(sum(session_OTM_loss_bp)) + " bp"  +\
                                ", swap cost=" + "{:1.2f}".format(session_swap_cost_bp) + " bp") #  +\
                                #", iv) hedge RL = " + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
                logger.info(network + ", session: res num token0 = " + str(session_res_num_token0) +\
                                                            ", res num token1 = " + str(session_res_num_token1) )
                logger.info(network + ', session' +\
                                    ': count LP=' + str(session_count_LP) +\
                                    ', count swaps=' + str(session_count_swaps) +\
                                    ', count LP swaps=' + str(session_count_LP_SWAP) +\
                                    ', count LP swaps failed=' + str(session_count_LP_SWAP_failed) +\
                                    ', count unwind distance=' + str(session_count_unwind_distance) +\
                                    ', count unwind flow=' + str(session_count_unwind_flow) +\
                                    ', count unwind signed q=' + str(session_count_unwind_signed_quantity) +\
                                    ', count unwind stop=' + str(session_count_unwind_stop) +\
                                    ', count unwind pool liq=' + str(session_count_unwind_pool_liq) +\
                                    ', count unwind price_mad=' + str(session_count_unwind_max_price_mad) +\
                                    ', count hedge RL = ' + str(session_count_hedge_RL) )
                logger.info(network + ", session: duration = " + "{:1.1f}".format((time.time() - start_time) / 3600) + " h" +\
                                            ", LP SWAP duration = " + "{:1.1f}".format(session_LP_SWAP_duration / 60) + " min"
                                            ", max price_mad = " + "{:1.5f}".format(max_price_mad) +\
                                            ", LP fees = " + "{:1.2f}".format(sum(session_LP_fees_bp)) + " bp" +\
                                            ", RL = " + "{:1.2f}".format(sum(session_RL_bp)) + " bp" )

            #N.B. If flag_LP_SWAP, loop continues
            if not flag_LP_SWAP:
                logger.info('network, END session')
                return True
                 
                
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




