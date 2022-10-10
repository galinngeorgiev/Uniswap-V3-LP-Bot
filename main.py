__author__ = "Galin Georgiev"
__copyright__ = "Copyright 2022, GammaDynamics, LLC"
__version__ = "1.1.0.0"

from ast import Or
import numpy as np

from toolbox import *
from global_params import *
from swap import size_split_swap
from mint import mint
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

    #Initialization
    i, block_num, price_list, price, price_median, price_LP, price_mad, max_price_mad_time, swap_price, max_price_mad,\
        swap_volume_token1, rel_swap_volume_token1, swap_flow_token1 = 0, None, [], None, 0., None, 0., 0., 0., 0., 0., 0., 0.
    pool_liquidity_list, pool_liquidity_median, pool_liquidity_LP = [], 0., 0.
    LP_price_distance_to_bound, unwind_distance_to_bound = LP_PRICE_DISTANCE_TO_BOUND_MIN_PER / 100, UNWIND_DIST_TO_BOUND_PER / 100
    session_count_LP, session_count_unwind_stop, session_count_unwind_pool_liq, session_count_unwind_max_price_mad,\
       session_count_unwind_signed_quantity, session_count_unwind_distance, session_count_hedge_RL, session_count_swaps =\
            0, 0, 0, 0, 0, 0, 0, 0
    session_LP_fees_bp, session_RL_bp, session_pl_token1, session_pl_bp, session_borrow_pl_token1, session_borrow_pl_bp,\
        session_hedge_RL_pl_bp, session_slippage_and_pool_fee_pl_bp, session_res_num_token0, session_res_num_token1 =\
       0., 0., 0., 0., 0., 0., 0., 0., 0., 0.
    tx_invested_token1, tx_collected_token1, tx_borrow_pl_bp = 0., 0., 0.
    tx_count_hedge_RL, tx_hedge_RL_amount, last_RL_bp, tx_hedge_RL_pl_bp, hedge_RL_pl_bp = 0, 0., 0., 0., 0.
    
    flag_change_tokenIds, flag_mint, flag_hedgeRL, flag_decreaseLiquidity, flag_collect, flag_burn = False, False, True, True, True, True
    flag_more_than_one_LP, flag_failed_tx, count_failed_tx = False, False, 0
    max_fee_per_gas, max_priority_fee_per_gas, slippage_per = MAX_FEE_PER_GAS, MAX_PRIORITY_FEE_PER_GAS, SLIPPAGE_PER
    
    tokenIds, tokenIds_burned, liquidities = [], [], []
    logger.info('')
    logger.info(network + ', START session')
    start_time = time.time()
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
        if not flag_failed_tx:
            if flag_change_tokenIds:
                flag_change_tokenIds = False

                result = current_LP_positions(network, address=Address, init=init) 
                if isinstance(result, list):
                    tokenIds = result
                    #N.B. Sometimes Alchemy API returns already burned tokens, so check for that!
                    tokenIds = [i for i in tokenIds if i not in tokenIds_burned]

                    if len(tokenIds) == 0:
                        flag_more_than_one_LP = False
                    elif len(tokenIds) > 1:
                        flag_more_than_one_LP = True

                else:
                    i += 1
                    continue


            #######################################################################
            #1a. Checks
            if i == 0 and len(tokenIds) > 0:
                logger.error(network + ', there are NFTs in this account with ID-s ' + str(tokenIds) + ', burn them with burn(tokenId) in burn.py! Stop main()!')
                logger.info('network, END session')
                return False

            #N.B. If collect() or burn() have .TimeExhausted event, this triggers!
            #if len(tokenIds) != len(liquidities):
            #    logger.error(network + ', len(tokenIds) = ' + str(len(tokenIds)) + ' != len(liquidities) = ' + str(len(liquidities)) +  ', stop main()!')
            #    logger.info(network + ", session p&l = " + str(session_pl_token1) + " token1" +\
            #                            ", " + "{:1.2f}".format(session_pl_bp) + " bp")
            #    logger.info(network + ", session borrow p&l = " + str(session_borrow_pl_token1) + " token1" +\
            #                            ", " + "{:1.2f}".format(session_borrow_pl_bp) + " bp")
            #    logger.info(network + ", session LP fees = " + "{:1.2f}".format(session_LP_fees_bp) + " bp" +\
            #                            ", session RL = " + "{:1.2f}".format(session_RL_bp) + " bp" +\
            #                            "; session time elapsed = " + "{:1.1f}".format((time.time() - start_time) / 3600) + " h; session num LP tx_s = " + str(session_count_LP))
            #    logger.info(network + ", session max price_mad = " + str(max_price_mad))
            #    logger.info('network, END session')
            #    return False


            #####################################################################
            #2. obtain the current pool price: the fuction returns False if no updates!
            if i < int(RUNTIME_SEC / DELAY_LOOP_SEC) - END_NUM_ITERATIONS:
                result = current_pool_price(network, block_num, price_list, price_median, pool_liquidity_list, pool_liquidity_median, \
                            price_mad, max_price_mad, swap_volume_token1, rel_swap_volume_token1, swap_flow_token1, init=init)      
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
                    #if price_mad > MAX_PRICE_MAD[-1]:
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
                    #N.B. Current pool price was not generated: if result is True, set price_LP=None, which triggers decreaseLiquidity()
                    if result and len(tokenIds) > 0: #N.B. requests() in current_pool_price() returns True with open LP position!
                        price_LP = None
                    else:
                        i += 1
                        continue           

        ######################################################################
        #3. add LP position
        #N.B. There is a check above that price is not None
        if len(tokenIds) == 0:

            #N.B. Determine unwind_distance_to_bound
            #N.B. Higher LP_price_distance_to_bound from beginning to end of quiet hours
            if (int(time.strftime('%w', time.gmtime())) != 6 and int(time.strftime('%w', time.gmtime())) != 0 and\
                (int(time.strftime('%H', time.gmtime())) >= QUIET_HOURS_START[0] and int(time.strftime('%H', time.gmtime())) < QUIET_HOURS_END[-1])):

                LP_price_distance_to_bound = LP_PRICE_DISTANCE_TO_BOUND_MAX_PER / 100
                #unwind_distance_to_bound = UNWIND_DIST_TO_BOUND_MIN_PER / 100 * LP_price_distance_to_bound
                logger.info(network + ", Higher LP_price_distance_to_bound = " +\
                    "{:1.2f}".format(LP_price_distance_to_bound * 100) + "% from beginning to end of quiet hours!")
            else:
                LP_price_distance_to_bound = LP_PRICE_DISTANCE_TO_BOUND_MIN_PER / 100
                ##N.B. If last LP tx P&L < 0, increase price bounds, otherwise desrease price bounds
                #if tx_borrow_pl_bp > 0.:
                #    LP_price_distance_to_bound -= LP_PRICE_DISTANCE_TO_BOUND_STEP_PER / 100
                #elif tx_borrow_pl_bp < 0.:
                #    LP_price_distance_to_bound += LP_PRICE_DISTANCE_TO_BOUND_STEP_PER / 100
                ##N.B. LP_price_distance_to_bound can not < LP_PRICE_DISTANCE_TO_BOUND_MIN_PER / 100 or > LP_PRICE_DISTANCE_TO_BOUND_MAX_PER / 100
                #LP_price_distance_to_bound = np.max([LP_price_distance_to_bound, LP_PRICE_DISTANCE_TO_BOUND_MIN_PER / 100])
                #LP_price_distance_to_bound = np.min([LP_price_distance_to_bound, LP_PRICE_DISTANCE_TO_BOUND_MAX_PER / 100])
                #if tx_borrow_pl_bp > 0.:
                #    logger.info("last LP borrow tx P&L: " + "{:1.2f}".format(tx_borrow_pl_bp) +\
                #        " bp, decrease range; current LP distance to bound = " + "{:1.2f}".format(LP_price_distance_to_bound * 100) + "%")
                #elif tx_borrow_pl_bp < 0.:
                #    logger.info("last LP borrow tx P&L: " + "{:1.2f}".format(tx_borrow_pl_bp) +\
                #        " bp, increase range; current LP distance to bound = " + "{:1.2f}".format(LP_price_distance_to_bound * 100) + "%")
            unwind_distance_to_bound = UNWIND_DIST_TO_BOUND_PER / 100 * LP_price_distance_to_bound

            #N.B. Do not initiate during quiet hours
            if not (int(time.strftime('%w', time.gmtime())) != 6 and int(time.strftime('%w', time.gmtime())) != 0 and\
                    ((int(time.strftime('%H', time.gmtime())) >= QUIET_HOURS_START[0] and int(time.strftime('%H', time.gmtime())) < QUIET_HOURS_END[0]) or\
                    (int(time.strftime('%H', time.gmtime())) >= QUIET_HOURS_START[1] and int(time.strftime('%H', time.gmtime())) < QUIET_HOURS_END[1]))):
                flag_mint = True
            else:
                flag_mint = False
                logger.info(network + ", NO INITIATION during quiet hours!")

            #N.B. Do not initiate if abs(signed_token1_quantity) too large!
            if abs(signed_token1_quantity) / pool_liquidity_list[-1] *\
                                                10 ** (0.5 * (init.token0_decimal + init.token1_decimal)) * 10000 <= MAX_TOKEN1_QUANTITY_TO_TVL_BP[0]:
                flag_mint = flag_mint and True
            else:
                logger.info('')
                logger.info(network + ", NO INITIATION because abs(signed_token1_quantity) / pool_liquidity * 10000 = " +\
                                    "{:1.4f}".format(abs(signed_token1_quantity) / pool_liquidity_list[-1] *\
                                             10 ** (0.5 * (init.token0_decimal + init.token1_decimal)) * 10000) +\
                                    " > MAX_TOKEN1_QUANTITY_TO_TVL_BP[0] = " + str(MAX_TOKEN1_QUANTITY_TO_TVL_BP[0]))
                flag_mint = False
            
            #N.B. Do not initiate if liquidity decreases!
            if PRICE_API_LOGS and len(pool_liquidity_list) > 0 and\
                pool_liquidity_list[-1] >= np.min([pool_liquidity_median, pool_liquidity_list[-1]]) * POOL_LIQUIDITY_THRESHOLD_PER[0] / 100:
                flag_mint = flag_mint and True
            else:
                logger.info('')
                logger.info("NO INITIATION because PRICE_API_LOGS=F or pool liq = " +\
                                "{:1.0f}".format(pool_liquidity_list[-1] / 10 ** (0.5 * (init.token0_decimal + init.token1_decimal))) +\
                                " < pool liq median * threshold= " + "{:1.0f}".format(pool_liquidity_median  / 10 ** (0.5 * (init.token0_decimal + init.token1_decimal)) * POOL_LIQUIDITY_THRESHOLD_PER[0] / 100))
                flag_mint = False
                
            #N.B. Do not initiate if price_mad too high!
            if price_mad <= MAX_PRICE_MAD[0]: # and (time.time() - max_price_mad_time) / 60 >= PRICE_MAD_WAIT_TIME_MIN:
                flag_mint = flag_mint and True
            else:
                logger.info('')
                logger.info("NO INITIATION because price_mad = " + "{:1.5f}".format(price_mad) +\
                            " > " + str(MAX_PRICE_MAD[0]) )
                flag_mint = False

            #N.B. Do not initiate if end of iterations: the last END_NUM_ITERATIONS iterations reserved for unwinding
            if i >= int(RUNTIME_SEC / DELAY_LOOP_SEC) - END_NUM_ITERATIONS:
                flag_mint = False

            if flag_failed_tx:
                if count_failed_tx < MAX_ATTEMPS_FAILED_TX:
                    flag_mint = True
                else:
                    logger.error(network + ', mint() failed MAX_ATTEMPS_FAILED_TX = ' + str(MAX_ATTEMPS_FAILED_TX) + ' times, stop main()!')
                    logger.info(network + ", session p&l = " + str(session_pl_token1) + " token1" +\
                                    ", " + "{:1.2f}".format(session_pl_bp) + " bp")
                    logger.info(network + ", session borrow p&l: i) w/o hedge RL=" + str(session_borrow_pl_token1) + " token1" +\
                                    ", ii) " + "{:1.2f}".format(session_borrow_pl_bp) + " bp" +\
                                    ", iii) slippage & pool fee=" + "{:1.2f}".format(session_slippage_and_pool_fee_pl_bp) + " bp"  +\
                                    ", iv) hedge RL=" + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
                    logger.info(network + ", session: res num token0 = " + str(session_res_num_token0) +\
                                                ", res num token1 = " + str(session_res_num_token1) )
                    logger.info(network + ', session: count LP=' + str(session_count_LP) +\
                        ', count swaps=' + str(session_count_swaps) +\
                        ', count unwind distance=' + str(session_count_unwind_distance) +\
                        ', count unwind signed q=' + str(session_count_unwind_signed_quantity) +\
                        ', count unwind stop=' + str(session_count_unwind_stop) +\
                        ', count unwind pool liq=' + str(session_count_unwind_pool_liq) +\
                        ', count unwind price_mad=' + str(session_count_unwind_max_price_mad) +\
                        ', count hedge RL = ' + str(session_count_hedge_RL) )
                    logger.info(network + ", session: time = " + "{:1.1f}".format((time.time() - start_time) / 3600) + " h" +\
                                            ", max price_mad = " + "{:1.5f}".format(max_price_mad) +\
                                            ", LP fees = " + "{:1.2f}".format(session_LP_fees_bp) + " bp" +\
                                            ", RL = " + "{:1.2f}".format(session_RL_bp) + " bp" )
                    logger.info('network, END session')
                    return False

            if flag_mint:
                amount0_LP = MAX_NUM_TOKEN0_LP * 10**init.token0_decimal
                amount1_LP = np.min([MAX_NUM_TOKEN1_LP, MAX_NUM_TOKEN0_LP / price]) * 10**init.token1_decimal
                #N.B. Formula for delta_RL_v3 simplifies a lot if Price_LP is a geometric average of priceUpper & priceLower 
                priceLower = price_DECIMAL * (1. - LP_price_distance_to_bound)
                priceUpper = price_DECIMAL / (1. - LP_price_distance_to_bound)

                #N.B. Compute nonce in mint() in order to keep the order of mints()
                result = mint(network, amount0ToMint=amount0_LP, amount1ToMint=amount1_LP, price_lower=priceLower, price_upper=priceUpper, \
                                max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas, \
                                address=Address, private_key=privateKey, init=init)

                ##########################
                #N.B. Re-compute priceLower, priceUpper, as in mint()
                #N.B. tick = log(price) / log(1.0001): (6.1) in https://uniswap.org/whitepaper-v3.pdf
                tickLower = np.log(priceLower) / np.log(1.0001)
                tickUpper = np.log(priceUpper) / np.log(1.0001)
                #tick spacing >> 1, depending on the pool fee: section 4 in https://uniswap.org/whitepaper-v3.pdf
                if init.pool_fee == 500:
                    tickLower, tickUpper = int(tickLower - tickLower % 10), int(tickUpper + (10 - tickUpper % 10))
                elif init.pool_fee == 3000:
                    tickLower, tickUpper = int(tickLower - tickLower % 60), int(tickUpper + (60 - tickUpper % 60))
                elif init.pool_fee == 10000:
                    tickLower, tickUpper = int(tickLower - tickLower % 200), int(tickUpper + (200 - tickUpper % 200))
                priceLower, priceUpper = 1.0001 ** tickLower, 1.0001 ** tickUpper
                ###########################
                    
                if isinstance(result, tuple):
                    tokenId, liquidity, amount0, amount1, blockNumber, nonce = result

                    #N.B. Can not use '+=' on a list!
                    liquidities.append(liquidity)
                                                                       
                    #N.B. price_LP from line (71) in https://github.com/Uniswap/v3-periphery/blob/main/contracts/libraries/LiquidityAmounts.sol
                    price_LP = (amount0  / liquidities[-1] + np.sqrt(priceLower)) ** 2
                    pool_liquidity_LP = pool_liquidity_list[-1]
                    hedge_RL = HEDGE_RL
                    tx_hedge_RL_pl_bp, hedge_RL_pl_bp, last_RL_bp, tx_hedge_RL_amount, last_hedge_RL_price = 0., 0., 0., 0., None
                    flag_change_tokenIds, swap_volume_token1, rel_swap_volume_token1, swap_flow_token1 = True, 0., 0., 0.
                    amount0_invested, amount1_invested = amount0, amount1
                    session_count_LP += 1
                    tx_slippage_and_pool_fee_pl_bp, tx_count_hedge_RL = 0., 0
                    tx_invested_token1 = (amount0 / price_LP + amount1) / 10**init.token1_decimal
                    mint_time = time.time()
                    if amount1 != 0:
                        asset_ratio_01_LP = amount0 / price_LP / amount1
                    else:
                        asset_ratio_01_LP = 1
                                    
                    logger.info(network + ", tx invested " + str(tx_invested_token1) +\
                                " token1, LP asset0/asset1 = " +  "{:1.3f}".format(asset_ratio_01_LP) +\
                                ", price_LP = " + "{:1.5f}".format(price_LP / 10**init.token0_decimal * 10**init.token1_decimal) +\
                                ", priceLower = " + "{:1.5f}".format(priceLower / 10**init.token0_decimal * 10**init.token1_decimal) +\
                                ", priceUpper = " + "{:1.5f}".format(priceUpper / 10**init.token0_decimal * 10**init.token1_decimal) +\
                                ", session count LP tx_s = " + str(session_count_LP) )
                        
                    flag_failed_tx = False
                    count_failed_tx = 0

                    #N.B. run current pool price again: the fuction returns False if no updates!
                    result = current_pool_price(network, block_num, price_list, price_median, pool_liquidity_list, pool_liquidity_median,\
                        price_mad, max_price_mad, swap_volume_token1, rel_swap_volume_token1, swap_flow_token1, init=init)      
                    if isinstance(result, list):
                        GMTtimeStamp, block_num, txIx, price_list, price_median, pool_liquidity_list, pool_liquidity_median, signed_token1_quantity,\
                            price_mad, max_price_mad, swap_volume_token1_output, rel_swap_volume_token1_output, swap_flow_token1_output = result
                        #N.B. Sometimes curent_pool_price() reports tx-s with block numbers not exceeding LP block and hence not earning fees!
                        if block_num > blockNumber:
                            swap_volume_token1, rel_swap_volume_token1, swap_flow_token1=\
                                swap_volume_token1_output, rel_swap_volume_token1_output, swap_flow_token1_output
                else:
                    nonce = None
                    if not result:
                        #N.B. nonce=None triggers web3 getting a nonce
                        price_LP, nonce = None, None
                        flag_failed_tx = True
                        count_failed_tx += 1
                        i += 1
                        continue                
        #######################################################################    
        else:
            #N.B. price_LP is None if: - requests() in current_pool_price() fails and len(tokenIds) > 0;
            #N.B. If there is > 1 LP position, remove instantly all!
            
            if price_LP is None or flag_failed_tx or flag_more_than_one_LP:
                unwind_condition = True
            else:
                ###################################################################################
                #N.B. 3a. Estimate RL, asset ratio, LP fees, unwind distance
                #N.B. Rebalancing Loss (RL)
                #N.B. see my Crypto doc, Defi Swaps > Uniswap > RL > Uniswap V2 & V3 > RL or > Greeks: https://docs.google.com/document/d/1K83HF3-A9NqFKtjF-wcf6Kduz0r-J0yYchiyOCfaKgo/edit
                RL_v2_bp = 10000 * (2 * np.sqrt(price_DECIMAL / price_LP) / (price_DECIMAL / price_LP + 1) - 1)
                delta_RL_v2 = (1 - price_DECIMAL / price_LP) / np.sqrt(price_DECIMAL / price_LP) / (price_DECIMAL / price_LP + 1)**2
                v3_v2_mult_factor = (price_DECIMAL / price_LP + 1) / \
                    (price_DECIMAL / price_LP * (1 - np.sqrt(price_LP / priceUpper)) + (1 - np.sqrt(priceLower / price_LP)))
                RL_v3_bp = RL_v2_bp * v3_v2_mult_factor 
                #N.B. True only if Price_LP is geometric average of priceUpper & priceLower 
                delta_RL_v3 = delta_RL_v2 * v3_v2_mult_factor

                #N.B. Asset ratio
                if price_DECIMAL <= priceLower:
                    asset_ratio_01 = 0.
                    asset0_ratio, asset1_ratio = 0., 1.
                elif price_DECIMAL < priceUpper:
                    #N.B. see my Crypto doc, Defi Swaps > Uniswap > V3 > Balances: https://docs.google.com/document/d/1K83HF3-A9NqFKtjF-wcf6Kduz0r-J0yYchiyOCfaKgo/edit
                    asset_ratio_01 = (np.sqrt(price_DECIMAL) - np.sqrt(priceLower)) / (np.sqrt(price_LP) - np.sqrt(priceLower)) \
                                / ((1 / np.sqrt(price_DECIMAL) - 1 / np.sqrt(priceUpper)) / (1 / np.sqrt(price_LP) - 1 / np.sqrt(priceUpper))) \
                                / price_DECIMAL * price_LP \
                                * asset_ratio_01_LP
                    asset0_ratio, asset1_ratio = asset_ratio_01 / (asset_ratio_01 + 1), 1 / (asset_ratio_01 + 1.)
                else:
                    asset_ratio_01 = np.inf
                    asset0_ratio, asset1_ratio = 1., 0.

                #N.B. LP Fees
                #N.B. Alchemy transfer tx-s API does not report txIx, tx order in the same block is unknown & rel_swap_volume_token1 is wrong!
                #N.B. When flag_more_than_one_LP = True, need liquidities[-1], not liquidity!
                #N.B. If collect() or burn() return False (swap() does not return False), liquidities=[]
                if len(liquidities) > 0:
                    if PRICE_ALCHEMY and (not PRICE_API_LOGS):
                        if pool_liquidity_median is not None:
                            LP_fees_bp = liquidities[-1] / pool_liquidity_median * swap_volume_token1 * init.pool_fee / 1000000 / tx_invested_token1 * 10000
                            session_LP_fees_bp += LP_fees_bp
                        else:
                            #N.B. Triggers STOP_LOSS!
                            LP_fees_bp = -np.infty
                    else:
                        LP_fees_bp = liquidities[-1] * rel_swap_volume_token1 * init.pool_fee / 1000000 / tx_invested_token1 * 10000
                        session_LP_fees_bp += LP_fees_bp
                #N.B. Triggers STOP_LOSS!
                #else:
                #    LP_fees_bp = -np.infty

                #N.B. Hedge RL p&l
                tx_borrow_invested_token1 = amount0_invested / 10**init.token0_decimal / price + amount1_invested / 10**init.token1_decimal
                #N.B. If last_hedge_RL_price is not set
                if last_hedge_RL_price is None:
                    last_hedge_RL_price = price
                #N.B. tx_hedge_RL_amount / price is the tx hedge RL amount in token1
                #N.B. tx hedge RL P&L is a sum tx_hedge_RL_pl_bp + hedge_RL_pl_bp:  hedge_RL_pl_bp measure hedge RL P&L only from the last hedge!
                hedge_RL_pl_bp = (price - last_hedge_RL_price) * tx_hedge_RL_amount / price / tx_borrow_invested_token1 * 10000
                 
                ##N.B. First-passage time density does not change if distance varies proportionally to vol: https://en.wikipedia.org/wiki/First-hitting-time_model
                #if price_mad != 0.:
                #    #N.B. if tx time elapsed is too small (volume is too small) or the market is mean-reverting, decrease only (no increase) of unwind distance to bound
                #    if (time.time() - mint_time) / 60 < DECREASE_ONLY_UNWIND_DIST_TIME_MIN or\
                #        (swap_volume_token1 == 0. or abs(swap_flow_token1) /  swap_volume_token1 < SWAP_FLOW_THRESHOLD_PER / 100):
                #        unwind_distance_to_bound = np.min([unwind_distance_to_bound, \
                #                                       UNWIND_DIST_TO_BOUND_PER / 100 * LP_price_distance_to_bound / (price_mad * init.unwind_dist_price_mad_mult)])
                #    else:
                #        unwind_distance_to_bound = UNWIND_DIST_TO_BOUND_PER / 100 * LP_price_distance_to_bound  / (price_mad * init.unwind_dist_price_mad_mult)
                #else:
                #    #N.B. if tx time elapsed is too small (volume is too small) or the market is mean-reverting, decrease only (no increase) of unwind distance to bound
                #    if (time.time() - mint_time) / 60 < DECREASE_ONLY_UNWIND_DIST_TIME_MIN or\
                #        (swap_volume_token1 == 0. or abs(swap_flow_token1) /  swap_volume_token1 < SWAP_FLOW_THRESHOLD_PER / 100):
                #        unwind_distance_to_bound = np.min([unwind_distance_to_bound, \
                #                                        UNWIND_DIST_TO_BOUND_PER / 100 * LP_price_distance_to_bound])
                #    else:
                #        unwind_distance_to_bound = UNWIND_DIST_TO_BOUND_PER / 100 * LP_price_distance_to_bound

                ##N.B. unwind_distance_to_bound can not be out of the range (UNWIND_DIST_TO_BOUND_MIN_PER, UNWIND_DIST_TO_BOUND_MAX_PER) / 100 * LP_price_distance_to_bound
                #unwind_distance_to_bound = np.min([UNWIND_DIST_TO_BOUND_MAX_PER / 100 * LP_price_distance_to_bound, unwind_distance_to_bound])
                #unwind_distance_to_bound = np.max([UNWIND_DIST_TO_BOUND_MIN_PER / 100 * LP_price_distance_to_bound, unwind_distance_to_bound])

                logger.info(network + ", dist-to-lower-bound = " + "{:1.2f}".format((1. - priceLower / price_median_DECIMAL) * 100) + "%" +\
                                    ", dist-to-upper-bound = " + "{:1.2f}".format((priceUpper / price_median_DECIMAL - 1.) * 100) + "%" +\
                                    ", unwind dist-to-bound = " + "{:1.2f}".format(unwind_distance_to_bound * 100) + "%" +\
                                    ", initial asset0/asset1 = " +  "{:1.3f}".format(asset_ratio_01_LP) +\
                                    ", current asset0/asset1 = " +  "{:1.3f}".format(asset_ratio_01) )

                logger.info(network + ", tx: fees = " +  "{:1.2f}".format(LP_fees_bp) + " bp" +\
                                      ", RL_v2 = " +  "{:1.2f}".format(RL_v2_bp) + " bp" +\
                                      ", delta_RL_v2 = " +  "{:1.4f}".format(delta_RL_v2) +\
                                      ", RL_v3 = " +  "{:1.2f}".format(RL_v3_bp) + " bp" +\
                                      ", delta_RL_v3 = " +  "{:1.4f}".format(delta_RL_v3)+\
                                      ", hedge RL p&l = " +  "{:1.2f}".format(tx_hedge_RL_pl_bp + hedge_RL_pl_bp) + " bp" +\
                                      ", total p&l = " +  "{:1.2f}".format(LP_fees_bp + RL_v3_bp + tx_hedge_RL_pl_bp + hedge_RL_pl_bp) + " bp")
                ####################################################################
                #N.B. hedge RL
                if hedge_RL and price_mad >= MAX_PRICE_MAD[1] and (not LP_SWAP):
                    if abs(RL_v3_bp - last_RL_bp) > HEDGE_RL_THRESHOLD_BP:
                        
                        tx_borrow_invested_token1 = amount0_invested / 10**init.token0_decimal / price + amount1_invested / 10**init.token1_decimal
                        #N.B. The final goal is tx_hedge_RL_amount = - delta_RL_v3 * tx_borrow_invested_token1
                        amount_to_swap = - delta_RL_v3 * tx_borrow_invested_token1 - tx_hedge_RL_amount 

                        logger.info('')
                        logger.info(network + ", RL diff = " + "{:1.2f}".format(RL_v3_bp - last_RL_bp) + " bp" +\
                                                ", hedge RL amount_to_swap = " + str(amount_to_swap) )
                        #N.B. amount_to_swap > or < 0: swap amount_to_swap token0 into token1 if > 0 or swap -amount_to_swap token1 into token0 if < 0
                        result = size_split_swap(network, price, amount_to_swap,\
                                                max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas,\
                                                 address=Address, private_key=privateKey, init=init, nonce=nonce)
                        if isinstance(result, tuple):
                            pool_liquidity, pool_price, swap_price, slippage_and_pool_fee_token1, nonce = result
                            last_RL_bp = RL_v3_bp
                            
                            #N.B. swap_price is wrong for small amounts, using pool_price for P&L!
                            swap_price  = pool_price
                            #N.B. pool_fee creates wrong p&l in the next iteration
                            #if amount_to_swap > 0:
                            #    swap_price *= (1. + init.pool_fee / 1000000)
                            #else:
                            #    swap_price /= (1. + init.pool_fee / 1000000) 
                            #N.B. If last_hedge_RL_price is not set
                            if last_hedge_RL_price is None:
                                last_hedge_RL_price = price
                            #N.B. tx_hedge_RL_amount / price is the tx accumulated hedge RL amount in token1
                            hedge_RL_pl_bp = (swap_price - last_hedge_RL_price) * tx_hedge_RL_amount / price / tx_borrow_invested_token1 * 10000
                            logger.info(network + ', this hedge RL p&l = ' + "{:1.4f}".format(hedge_RL_pl_bp) + 'bp' +\
                                                  ', tx hedge RL amount = ' + str(tx_hedge_RL_amount) +\
                                                  ', price change from prev hedge = ' + "{:1.4f}".format(swap_price - last_hedge_RL_price) +\
                                                  ', tx_borrow_invested_token1 = ' + str(tx_borrow_invested_token1) )
                            logger.info('')

                            last_hedge_RL_price = swap_price
                            #N.B. The final goal is tx_hedge_RL_amount = - delta_RL_v3 * tx_borrow_invested_token1
                            tx_hedge_RL_amount = - delta_RL_v3 * tx_borrow_invested_token1
                            tx_hedge_RL_pl_bp += hedge_RL_pl_bp
                            #N.B. hedge_RL_pl_bp measure P&L only from the last hedge!
                            hedge_RL_pl_bp = 0.
                            tx_count_hedge_RL += 1
                            session_count_hedge_RL += 1

                            tx_slippage_and_pool_fee_pl_bp += slippage_and_pool_fee_token1 / tx_borrow_invested_token1 * 10000
                            session_slippage_and_pool_fee_pl_bp += tx_slippage_and_pool_fee_pl_bp
                            session_borrow_pl_bp += tx_slippage_and_pool_fee_pl_bp
                        else:
                            #N.B. nonce=None triggers web3 getting a nonce
                            nonce = None
                            if not result:
                                #N.B. If something is not changed, the attemps to swap will continue forever!
                                #hedge_RL = False
                                last_RL_bp = RL_v3_bp
                                logger.error(network + ', hedge RL swap failed MAX_ATTEMPS_FAILED_TX = ' + str(MAX_ATTEMPS_FAILED_TX) +\
                                           ' times, hedge RL unchanged until the next hedge RL, continue...')
                elif price_mad <= MAX_PRICE_MAD[0]:
                    if tx_hedge_RL_amount != 0.:
                        amount_to_swap = tx_hedge_RL_amount

                        #N.B. amount_to_swap > or < 0: swap amount_to_swap token0 into token1 if > 0 or swap -amount_to_swap token1 into token0 if < 0
                        result = size_split_swap(network, price, amount_to_swap,\
                                                max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas,\
                                                 address=Address, private_key=privateKey, init=init, nonce=nonce)
                        if isinstance(result, tuple):
                            pool_liquidity, pool_price, swap_price, slippage_and_pool_fee_token1, nonce = result
                            last_RL_bp = RL_v3_bp
                            
                            #N.B. swap_price is wrong for small amounts, using pool_price for P&L!
                            swap_price  = pool_price
                            #N.B. pool_fee creates wrong p&l in the next iteration
                            #if amount_to_swap > 0:
                            #    swap_price *= (1. + init.pool_fee / 1000000)
                            #else:
                            #    swap_price /= (1. + init.pool_fee / 1000000) 
                            #N.B. last_hedge_RL_price is not None because tx_hedge_RL_amount != 0.
                            #if last_hedge_RL_price is None:
                            #    last_hedge_RL_price = price
                            #N.B. tx_hedge_RL_amount / price is the tx accumulated hedge RL amount in token1
                            hedge_RL_pl_bp = (swap_price - last_hedge_RL_price) * tx_hedge_RL_amount / price / tx_borrow_invested_token1 * 10000
                            logger.info(network + ', this hedge RL p&l = ' + "{:1.4f}".format(hedge_RL_pl_bp) + 'bp' +\
                                                  ', no hedging RL because price_mad = '+ str(price_mad) + " <= MAX_PRICE_MAD[0] = " + str(MAX_PRICE_MAD[0]) +\
                                                  ', price change from prev hedge = ' + "{:1.4f}".format(swap_price - last_hedge_RL_price) +\
                                                  ', tx_borrow_invested_token1 = ' + str(tx_borrow_invested_token1) )
                            logger.info('')

                            last_hedge_RL_price = swap_price
                            tx_hedge_RL_pl_bp += hedge_RL_pl_bp
                            #N.B. hedge_RL_pl_bp measures P&L only from the last hedge!
                            tx_hedge_RL_amount, hedge_RL_pl_bp = 0., 0.
                            tx_count_hedge_RL += 1
                            session_count_hedge_RL += 1

                            tx_slippage_and_pool_fee_pl_bp += slippage_and_pool_fee_token1 / tx_borrow_invested_token1 * 10000
                            session_slippage_and_pool_fee_pl_bp += tx_slippage_and_pool_fee_pl_bp
                            session_borrow_pl_bp += tx_slippage_and_pool_fee_pl_bp
                        else:
                            #N.B. nonce=None triggers web3 getting a nonce
                            nonce = None
                            if result:
                                #N.B. unwind the LP position (if something is not changed, the attemps to swap will continue forever!)
                                unwind_distance_to_bound = np.inf
                                logger.error(network + ', UNWINDING open LP position: hedge RL swap failed MAX_ATTEMPS_FAILED_TX = ' + str(MAX_ATTEMPS_FAILED_TX) +\
                                           ' times for price_mad = '+ str(price_mad) + " < MAX_PRICE_MAD[0] = " + str(MAX_PRICE_MAD[0]) + ', continue...')



                ###########################################################################
                #N.B. Unwind condition
                unwind_condition =\
                  min([1. - priceLower / price_DECIMAL, priceUpper / price_DECIMAL - 1.]) <= unwind_distance_to_bound
                 #asset_ratio_01 <= UNWIND_ASSET_RATIO_PER / 100 or asset_ratio_01 >= 1. / (UNWIND_ASSET_RATIO_PER / 100)
                if unwind_condition:
                    session_count_unwind_distance += 1

                #N.B. Stop-profit / stop-loss
                if LP_fees_bp + RL_v3_bp + tx_hedge_RL_pl_bp + hedge_RL_pl_bp < - STOP_LOSS_BP or LP_fees_bp + RL_v3_bp + tx_hedge_RL_pl_bp + hedge_RL_pl_bp > STOP_PROFIT_BP:
                    logger.info('')
                    logger.info(network + ", UNWINDING open LP position because tx p&l < - " + str(STOP_LOSS_BP) + " bp or > " + str(STOP_PROFIT_BP) + " bp")
                    logger.info('')
                    unwind_condition = True
                    session_count_unwind_stop += 1
                
            if TEST:
                unwind_condition = unwind_condition or i % 2 == 1
           
            #N.B. Last END_NUM_ITERATIONS iterations reserved for unwinding
            if i >= int(RUNTIME_SEC / DELAY_LOOP_SEC) - END_NUM_ITERATIONS:
                unwind_condition = True 

            #N.B. Unwind during quiet hours
            if (int(time.strftime('%w', time.gmtime())) != 6 and int(time.strftime('%w', time.gmtime())) != 0 and\
                ((int(time.strftime('%H', time.gmtime())) >= QUIET_HOURS_START[0] and int(time.strftime('%H', time.gmtime())) < QUIET_HOURS_END[0]) or\
                (int(time.strftime('%H', time.gmtime())) >= QUIET_HOURS_START[1] and int(time.strftime('%H', time.gmtime())) < QUIET_HOURS_END[1]))):
                unwind_condition = True
                logger.info(network + ", UNWINDING open LP position during quiet hours!")
                
            #N.B. If any of the unwind tx-s fail, set unwind_condition=True
            if (not flag_hedgeRL) or (not flag_decreaseLiquidity) or (not flag_collect) or (not flag_burn):
                unwind_condition = True

            if price_mad > MAX_PRICE_MAD[-1]:
                logger.info('')
                logger.info(network + ", UNWINDING open LP position because price_mad = " + str(price_mad) +\
                                            " > MAX_PRICE_MAD[-1] = " + str(MAX_PRICE_MAD[-1]))
                logger.info('')
                unwind_condition = True
                session_count_unwind_max_price_mad += 1

            if PRICE_API_LOGS and abs(signed_token1_quantity) / pool_liquidity_list[-1]  *\
                                    10 ** (0.5 * (init.token0_decimal + init.token1_decimal)) * 10000 > MAX_TOKEN1_QUANTITY_TO_TVL_BP[-1]:
                logger.info('')
                logger.info(network + ", UNWINDING open LP position because abs(signed_token1_quantity) / pool_liquidity * 10000 = " +\
                                    "{:1.4f}".format(abs(signed_token1_quantity) / pool_liquidity_list[-1] *\
                                         10 ** (0.5 * (init.token0_decimal + init.token1_decimal)) * 10000) +\
                                    " > MAX_TOKEN1_QUANTITY_TO_TVL_BP[-1] = " + str(MAX_TOKEN1_QUANTITY_TO_TVL_BP[-1]))
                logger.info('')
                unwind_condition = True
                session_count_unwind_signed_quantity += 1

            if PRICE_API_LOGS and pool_liquidity_list[-1] < pool_liquidity_LP * POOL_LIQUIDITY_THRESHOLD_PER[-1] / 100:
                logger.info('')
                logger.info(network + ", UNWINDING open LP position because pool liq = " +\
                            "{:1.0f}".format(pool_liquidity_list[-1] / 10 ** (0.5 * (init.token0_decimal + init.token1_decimal))) +\
                            " < initiation LP pool liq * threshold = " +\
                            "{:1.0f}".format(pool_liquidity_LP  / 10 ** (0.5 * (init.token0_decimal + init.token1_decimal)) * POOL_LIQUIDITY_THRESHOLD_PER[-1] / 100))
                logger.info('')
                unwind_condition = True
                session_count_unwind_pool_liq += 1

            #N.B. Run decreaseLiquidity(), collect(), swap(), burn() only if this condition!
            if unwind_condition:
                #####################################################################
                #4. Delete the above LP position
                #N.B. If len(tokenIds) ==2, delete only the 1st one, otherwise, delete the last!
                if flag_more_than_one_LP:
                    tokenId = tokenIds[0]
                else:
                    tokenId = tokenIds[-1]

                #N.B. If decreaseLiquidity() tx fails, run only the failed decreaseLiquidity() in the next iteration!
                #N.B. Passing nonce speeds up execution
                if count_failed_tx < MAX_ATTEMPS_FAILED_TX:
                    #N.B. When flag_more_than_one_LP = True, need liquidities[-1], not liquidity!
                    if (flag_hedgeRL and flag_collect and flag_burn) or not flag_decreaseLiquidity:
                        result = decreaseLiquidity(network, tokenId, liquidities[-1],\
                                        max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas, \
                                                    address=Address, private_key=privateKey, init=init, nonce=nonce)
                        if isinstance(result, tuple):
                            amount0, amount1, nonce = result
                            flag_failed_tx, flag_decreaseLiquidity = False, True
                            count_failed_tx = 0
                            liquidities.pop()
                            hedge_RL = HEDGE_RL
                            decreaseLiquidity_time = time.time()
                        else:
                            nonce = None
                            if not result:
                                #N.B. nonce=None triggers web3 getting a nonce
                                flag_failed_tx, flag_decreaseLiquidity, nonce = True, False, None
                                count_failed_tx += 1
                                i += 1
                                continue
                else:
                    if (flag_hedgeRL and flag_collect and flag_burn) or not flag_decreaseLiquidity:
                        logger.error(network + ', decreaseLiquidity() failed MAX_ATTEMPS_FAILED_TX = ' + str(MAX_ATTEMPS_FAILED_TX) + ' times, stop main()!')
                        logger.info(network + ", session p&l = " + str(session_pl_token1) + " token1" +\
                                                ", " + "{:1.2f}".format(session_pl_bp) + " bp")
                        logger.info(network + ", session borrow p&l: i) w/o hedge RL=" + str(session_borrow_pl_token1) + " token1" +\
                                                ", ii) " + "{:1.2f}".format(session_borrow_pl_bp) + " bp" +\
                                                ", iii) slippage & pool fee=" + "{:1.2f}".format(session_slippage_and_pool_fee_pl_bp) + " bp"  +\
                                                ", iv) hedge RL=" + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
                        logger.info(network + ", session: res num token0 = " + str(session_res_num_token0) +\
                                                        ", res num token1 = " + str(session_res_num_token1) )
                        logger.info(network + ', session: count LP=' + str(session_count_LP) +\
                                ', count swaps=' + str(session_count_swaps) +\
                                ', count unwind distance=' + str(session_count_unwind_distance) +\
                                ', count unwind signed q=' + str(session_count_unwind_signed_quantity) +\
                                ', count unwind stop=' + str(session_count_unwind_stop) +\
                                ', count unwind pool liq=' + str(session_count_unwind_pool_liq) +\
                                ', count unwind price_mad=' + str(session_count_unwind_max_price_mad) +\
                                ', count hedge RL = ' + str(session_count_hedge_RL) )
                        logger.info(network + ", session: time = " + "{:1.1f}".format((time.time() - start_time) / 3600) + " h" +\
                                                    ", max price_mad = " + "{:1.5f}".format(max_price_mad) +\
                                                    ", LP fees = " + "{:1.2f}".format(session_LP_fees_bp) + " bp" +\
                                                    ", RL = " + "{:1.2f}".format(session_RL_bp) + " bp" )
                        return False

                #####################################################################
                #5. Collect tokens from the deleted LP position
                #N.B. If collect() tx fails, run only the failed collect() in the next iteration!
                #time.sleep(3)
                if count_failed_tx < MAX_ATTEMPS_FAILED_TX:
                    if (flag_hedgeRL and flag_decreaseLiquidity and flag_burn) or not flag_collect:
                        result = collect(tokenId, network,max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas, \
                                            address=Address, private_key=privateKey, init=init, nonce=nonce)
                        if isinstance(result, tuple):
                            amount0, amount1, nonce = result
                            
                            #N.B. tx
                            tx_collected_token1 = amount0 / 10**init.token0_decimal / price + amount1 / 10**init.token1_decimal
                            tx_borrow_invested_token1 = amount0_invested / 10**init.token0_decimal / price + amount1_invested / 10**init.token1_decimal
                            tx_borrow_pl_bp = (tx_collected_token1 - tx_borrow_invested_token1) / tx_borrow_invested_token1 * 10000
                            #N.B. tx hedge RL P&L is a sum tx_hedge_RL_pl_bp + hedge_RL_pl_bp:  hedge_RL_pl_bp measures hedge RL  P&L only from the last hedge!
                            tx_borrow_pl_bp += tx_hedge_RL_pl_bp + hedge_RL_pl_bp
                            tx_res_num_token0,  tx_res_num_token1 = (amount0 - amount0_invested) / 10**init.token0_decimal, (amount1 - amount1_invested) / 10**init.token1_decimal
                            #N.B. tx P&L log report
                            logger.info('')
                            logger.info(network + ", LP tx (w/o possible swap) p&l = " + str(tx_collected_token1 - tx_invested_token1) + " token1" +\
                                            ", " + "{:1.2f}".format((tx_collected_token1 - tx_invested_token1) / tx_invested_token1 * 10000) + " bp" +\
                                            ", tx_borrow_invested_token1 = " + str(tx_borrow_invested_token1))
                            logger.info(network + ", LP tx (w/o possible swap) borrow p&l: i) w/o hedge RL=" + str(tx_collected_token1 - tx_borrow_invested_token1) + " token1" +\
                                            ", ii) " + "{:1.2f}".format(tx_borrow_pl_bp) + " bp" +\
                                            ", iii) hedge RL=" + "{:1.2f}".format(tx_hedge_RL_pl_bp + hedge_RL_pl_bp) + " bp" +\
                                            "; num hedge RL=" + str(tx_count_hedge_RL) +\
                                            "; time=" + "{:1.1f}".format((decreaseLiquidity_time - mint_time) / 60) + " min" ) #+\
                                            #"; tx swap flow token1 = " + "{:1.1f}".format(swap_flow_token1))
                            #N.B. session
                            session_pl_token1 += tx_collected_token1 - tx_invested_token1
                            session_borrow_pl_token1 += tx_collected_token1 - tx_borrow_invested_token1
                            session_pl_bp +=  (tx_collected_token1 - tx_invested_token1) / tx_invested_token1 * 10000
                            session_borrow_pl_bp += tx_borrow_pl_bp 
                            session_RL_bp += RL_v3_bp
                            session_hedge_RL_pl_bp += tx_hedge_RL_pl_bp + hedge_RL_pl_bp
                            session_res_num_token0 += tx_res_num_token0
                            session_res_num_token1 += tx_res_num_token1
                            #N.B. session P&L log report
                            logger.info(network + ", session (w/o possible) swap p&l= " + str(session_pl_token1) + " token1" +\
                                                    ", " + "{:1.2f}".format(session_pl_bp) + " bp")
                            logger.info(network + ", session (w/o possible swap) borrow p&l: i) w/o hedge RL=" + str(session_borrow_pl_token1) + " token1" +\
                                        ", ii) " + "{:1.2f}".format(session_borrow_pl_bp) + " bp"  +\
                                        ", iii) slippage & pool fee=" + "{:1.2f}".format(session_slippage_and_pool_fee_pl_bp) + " bp"  +\
                                        ", iv) hedge RL=" + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
                            logger.info(network + ", session: res num token0 = " + str(session_res_num_token0) +\
                                                            ", res num token1 = " + str(session_res_num_token1) )
                            logger.info(network + ', session: count LP=' + str(session_count_LP) +\
                                ', count swaps=' + str(session_count_swaps) +\
                                ', count unwind distance=' + str(session_count_unwind_distance) +\
                                ', count unwind signed q=' + str(session_count_unwind_signed_quantity) +\
                                ', count unwind stop=' + str(session_count_unwind_stop) +\
                                ', count unwind pool liq=' + str(session_count_unwind_pool_liq) +\
                                ', count unwind price_mad=' + str(session_count_unwind_max_price_mad) +\
                                ', count hedge RL = ' + str(session_count_hedge_RL) )
                            logger.info(network + ", session: time = " + "{:1.1f}".format((time.time() - start_time) / 3600) + " h" +\
                                                    ", max price_mad = " + "{:1.5f}".format(max_price_mad) +\
                                                        ", LP fees = " + "{:1.2f}".format(session_LP_fees_bp) + " bp" +\
                                                        ", RL = " + "{:1.2f}".format(session_RL_bp) + " bp" )
                            
                            flag_failed_tx, flag_collect = False, True
                            count_failed_tx = 0
                        else:
                            
                            if not result:
                                nonce = None
                            #N.B. nonce=None triggers web3 getting a nonce
                            flag_failed_tx, flag_collect, nonce = True, False, None
                            count_failed_tx += 1
                            i += 1
                            continue
                else:
                    if (flag_hedgeRL and flag_decreaseLiquidity and flag_burn) or not flag_collect:
                        logger.error(network + ', collect() failed MAX_ATTEMPS_FAILED_TX = ' + str(MAX_ATTEMPS_FAILED_TX) +  ' times, stop main()!')
                        logger.info(network + ", session p&l = " + str(session_pl_token1) + " token1" +\
                                            ", " + "{:1.2f}".format(session_pl_bp) + " bp")
                        logger.info(network + ", session borrow p&l: i) w/o hedge RL=" + str(session_borrow_pl_token1) + " token1" +\
                                            ", ii) " + "{:1.2f}".format(session_borrow_pl_bp) + " bp" +\
                                            ", iii) slippage & pool fee=" + "{:1.2f}".format(session_slippage_and_pool_fee_pl_bp) + " bp"  +\
                                            ", iv) hedge RL=" + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
                        logger.info(network + ", session: res num token0 = " + str(session_res_num_token0) +\
                                                        ", res num token1 = " + str(session_res_num_token1) )
                        logger.info(network + ', session: count LP=' + str(session_count_LP) +\
                                ', count swaps=' + str(session_count_swaps) +\
                                ', count unwind distance=' + str(session_count_unwind_distance) +\
                                ', count unwind signed q=' + str(session_count_unwind_signed_quantity) +\
                                ', count unwind stop=' + str(session_count_unwind_stop) +\
                                ', count unwind pool liq=' + str(session_count_unwind_pool_liq) +\
                                ', count unwind price_mad=' + str(session_count_unwind_max_price_mad) +\
                                ', count hedge RL = ' + str(session_count_hedge_RL) )
                        logger.info(network + ", session: time = " + "{:1.1f}".format((time.time() - start_time) / 3600) + " h" +\
                                                    ", max price_mad = " + "{:1.5f}".format(max_price_mad) +\
                                                    ", LP fees = " + "{:1.2f}".format(session_LP_fees_bp) + " bp" +\
                                                    ", RL = " + "{:1.2f}".format(session_RL_bp) + " bp" )
                        logger.info('network, END session')
                        return False     

                                           
                ###################################################
                #6. Burn the NFT correponding to tokenIds[-1]: otherwise the NFT stays in the wallet & can be seen running current_LP_positions()
                #N.B. From the docs: "The token must have 0 liquidity and all tokens must be collected first.": https://docs.uniswap.org/protocol/reference/periphery/NonfungiblePositionManager
                #N.B. If tokens not collected first, burn() tx produces error on Etherscan "Fail with error 'Not cleared'"
                #N.B. If burn() tx fails, run only the failed burn() in the next iteration!
                #N.B. When LP_SWAP = False, swap() is before burn() because, if burn() fails, swap() is delayed, but when LP_SWAP = True, burn() has to be before swap()!
                if count_failed_tx < MAX_ATTEMPS_FAILED_TX:
                    if (flag_hedgeRL and flag_decreaseLiquidity and flag_collect) or not flag_burn:
                        if burn(tokenId, network,max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas, \
                                    address=Address, private_key=privateKey, init=init, nonce=nonce):
                            tokenIds_burned += [tokenIds[-1]]
                            nonce += 1
                            flag_change_tokenIds = True
                            flag_failed_tx, flag_burn = False, True
                            count_failed_tx = 0
                        else:
                            if not result:
                                #N.B. nonce=None triggers web3 getting a nonce
                                flag_failed_tx, flag_burn, nonce = True, False, None
                                count_failed_tx += 1
                                i += 1
                                continue
                else:
                    if (flag_hedgeRL and flag_decreaseLiquidity and flag_collect) or not flag_burn:
                        logger.error(network + ', burn() failed MAX_ATTEMPS_FAILED_TX = ' + str(MAX_ATTEMPS_FAILED_TX) + ' times, stop main()!')
                        logger.info(network + ", session p&l = " + str(session_pl_token1) + " token1" +\
                                            ", " + "{:1.2f}".format(session_pl_bp) + " bp")
                        logger.info(network + ", session borrow p&l: i) w/o hedge RL=" + str(session_borrow_pl_token1) + " token1" +\
                                             ", ii) " + "{:1.2f}".format(session_borrow_pl_bp) + " bp" +\
                                             ", iii) slippage & pool fee=" + "{:1.2f}".format(session_slippage_and_pool_fee_pl_bp) + " bp"  +\
                                             ", iv) hedge RL=" + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
                        logger.info(network + ", session: res num token0 = " + str(session_res_num_token0) +\
                                                        ", res num token1 = " + str(session_res_num_token1) )
                        logger.info(network + ', session: count LP=' + str(session_count_LP) +\
                                ', count swaps=' + str(session_count_swaps) +\
                                ', count unwind distance=' + str(session_count_unwind_distance) +\
                                ', count unwind signed q=' + str(session_count_unwind_signed_quantity) +\
                                ', count unwind stop=' + str(session_count_unwind_stop) +\
                                ', count unwind pool liq=' + str(session_count_unwind_pool_liq) +\
                                ', count unwind price_mad=' + str(session_count_unwind_max_price_mad) +\
                                ', count hedge RL = ' + str(session_count_hedge_RL) )
                        logger.info(network + ", session: time = " + "{:1.1f}".format((time.time() - start_time) / 3600) + " h" +\
                                                    ", max price_mad = " + "{:1.5f}".format(max_price_mad) +\
                                                    ", LP fees = " + "{:1.2f}".format(session_LP_fees_bp) + " bp" +\
                                                    ", RL = " + "{:1.2f}".format(session_RL_bp) + " bp" )
                        logger.info('network, END session')
                        return False

                ######################################################################
                #7. Swap the collected amounts difference to achieve parity of the amounts
                #N.B. If slippage is too low, get error 'Too little received'
                #N.B. If swap() tx fails, run only the failed swap() in the next swap iteration!
                if flag_hedgeRL and flag_decreaseLiquidity and flag_collect and flag_burn:
                    logger.info('')
                    #N.B. tx
                    #N.B. tx_amount_to_swap formula (tx_amount_to_swap > or < 0):
                    #N.B. amount0/10**init.token0_decimal - tx_amount_to_swap = price*amount1/10**init.token1_decimal + tx_amount_to_swap
                    #N.B. swap tx_amount_to_swap token0 into token1 if > 0 or -tx_amount_to_swap token1 into token0 if < 0
                    tx_amount_to_swap = 0.5 * (amount0 / 10**init.token0_decimal - price * amount1 / 10**init.token1_decimal)

                    if abs(tx_amount_to_swap) > 2 * MIN_TX_SWAP_PER / 100 * np.max([MAX_NUM_TOKEN0_LP, price * MAX_NUM_TOKEN1_LP]):
                        amount_to_swap = tx_amount_to_swap
                        flag_swap = True
                    else:
                        logger.info(network + ", no tx swap: abs(tx_amount_to_swap) = " + str(abs(tx_amount_to_swap)) + " <= min tx swap threshold = " +\
                               str(2 * MIN_TX_SWAP_PER / 100 * np.max([MAX_NUM_TOKEN0_LP, price * MAX_NUM_TOKEN1_LP])) + ", continue...")
                        flag_swap = False

                    #N.B. session
                    #N.B. amount_to_swap from session is used!
                    if abs(session_res_num_token0) > 2 * MIN_SESSION_SWAP_PER / 100 * MAX_NUM_TOKEN0_LP or\
                            abs(session_res_num_token1) > 2 * MIN_SESSION_SWAP_PER / 100 * MAX_NUM_TOKEN1_LP or\
                            i >= int(RUNTIME_SEC / DELAY_LOOP_SEC) - END_NUM_ITERATIONS:
                        if session_res_num_token0 > 0:
                            amount_to_swap = session_res_num_token0
                        elif session_res_num_token1 > 0:
                            amount_to_swap = -session_res_num_token1 * price
                        session_res_num_token0, session_res_num_token1 = 0., 0.
                        flag_swap = flag_swap or True
                    else:
                        logger.info(network + ", no session swap: abs(session_res_num_token0)=" + str(abs(session_res_num_token0)) +\
                                " <= min session swap token0=" + str(2 * MIN_SESSION_SWAP_PER / 100 * MAX_NUM_TOKEN0_LP) +\
                               " or abs(session_res_num_token1)=" + str(abs(session_res_num_token1)) +\
                                " <= min session swap token1=" + str(2 * MIN_SESSION_SWAP_PER / 100 * MAX_NUM_TOKEN1_LP) + ", continue...")
                        flag_swap = flag_swap or False

                    if flag_swap:
                        if LP_SWAP:
                            #N.B. Get fresh price before LP swap
                            i += 1
                            continue
                        else:
                            #N.B. Size-split swap: if tx_amount_to_swap > 0, swap tx_amount_to_swap token0 to token1; if < 0, swap -tx_amount_to_swap token1 to token0;
                            #N.B. Passing nonce speeds up execution
                            result = size_split_swap(network, price, amount_to_swap,\
                                max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas,\
                                address=Address, private_key=privateKey, init=init, nonce=nonce)
                            if isinstance(result, tuple):
                                pool_liquidity, pool_price, swap_price, slippage_and_pool_fee_token1, nonce = result
                                session_count_swaps += 1
                                #N.B. tx
                                tx_slippage_and_pool_fee_pl_bp += slippage_and_pool_fee_token1 / tx_borrow_invested_token1 * 10000
                                tx_borrow_pl_bp += tx_slippage_and_pool_fee_pl_bp
                                logger.info(network + ", LP tx (with swap) borrow p&l:" +\
                                                " i) " + "{:1.2f}".format(tx_borrow_pl_bp) + " bp" +\
                                                ", ii) slippage & pool fee=" + "{:1.2f}".format(tx_slippage_and_pool_fee_pl_bp) + " bp" )#+\
                                                #"; tx swap flow token1 = " + "{:1.1f}".format(swap_flow_token1))
                                #N.B. session
                                session_slippage_and_pool_fee_pl_bp += tx_slippage_and_pool_fee_pl_bp
                                session_borrow_pl_bp += tx_slippage_and_pool_fee_pl_bp
                                logger.info(network + ', session count swaps=' + str(session_count_swaps) +\
                                            ", session (with swap) borrow p&l:" +\
                                            " i) " + "{:1.2f}".format(session_borrow_pl_bp) + " bp"  +\
                                            ", ii) slippage & pool fee=" + "{:1.2f}".format(session_slippage_and_pool_fee_pl_bp) + " bp")
                            else:
                                nonce = None
                                if not result:
                                    if flag_hedgeRL and flag_decreaseLiquidity and flag_collect and flag_burn:
                                        logger.error(network + ', hedge size_split_swap() failed MAX_ATTEMPS_FAILED_TX = ' + str(MAX_ATTEMPS_FAILED_TX) +\
                                            ' times for swap iteration, stop main()!')
                                        logger.info(network + ", session p&l = " + str(session_pl_token1) + " token1" +\
                                                            ", " + "{:1.2f}".format(session_pl_bp) + " bp")
                                        logger.info(network + ", session borrow p&l: i) w/o hedge RL = " + str(session_borrow_pl_token1) + " token1" +\
                                                            ", ii) " + "{:1.2f}".format(session_borrow_pl_bp) + " bp" +\
                                                            ", iii) slippage & pool fee=" + "{:1.2f}".format(session_slippage_and_pool_fee_pl_bp) + " bp"  +\
                                                            ", iv) hedge RL = " + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
                                        logger.info(network + ", session: res num token0 = " + str(session_res_num_token0) +\
                                                            ", res num token1 = " + str(session_res_num_token1) )
                                        logger.info(network + ', session: count LP=' + str(session_count_LP) +\
                                        ', count swaps=' + str(session_count_swaps) +\
                                        ', count unwind distance=' + str(session_count_unwind_distance) +\
                                        ', count unwind signed q=' + str(session_count_unwind_signed_quantity) +\
                                        ', count unwind stop=' + str(session_count_unwind_stop) +\
                                        ', count unwind pool liq=' + str(session_count_unwind_pool_liq) +\
                                        ', count unwind price_mad=' + str(session_count_unwind_max_price_mad) +\
                                        ', count hedge RL = ' + str(session_count_hedge_RL) )
                                        logger.info(network + ", session: time = " + "{:1.1f}".format((time.time() - start_time) / 3600) + " h" +\
                                                            ", max price_mad = " + "{:1.5f}".format(max_price_mad) +\
                                                            ", LP fees = " + "{:1.2f}".format(session_LP_fees_bp) + " bp" +\
                                                            ", RL = " + "{:1.2f}".format(session_RL_bp) + " bp" )
                                        logger.info('network, END session')
                                        return False
                

        if i == int(RUNTIME_SEC / DELAY_LOOP_SEC):
            logger.info(network + ", session p&l = " + str(session_pl_token1) + " token1" +\
                            ", " + "{:1.2f}".format(session_pl_bp) + " bp")
            logger.info(network + ", session borrow p&l: i) w/o hedge RL=" + str(session_borrow_pl_token1) + " token1" +\
                            ", ii) " + "{:1.2f}".format(session_borrow_pl_bp) + " bp" +\
                            ", iii) slippage & pool fee=" + "{:1.2f}".format(session_slippage_and_pool_fee_pl_bp) + " bp"  +\
                            ", iv) hedge RL = " + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
            logger.info(network + ", session: res num token0 = " + str(session_res_num_token0) +\
                                                        ", res num token1 = " + str(session_res_num_token1) )
            logger.info(network + ', session: count LP=' + str(session_count_LP) +\
                                ', count swaps=' + str(session_count_swaps) +\
                                ', count unwind distance=' + str(session_count_unwind_distance) +\
                                ', count unwind signed q=' + str(session_count_unwind_signed_quantity) +\
                                ', count unwind stop=' + str(session_count_unwind_stop) +\
                                ', count unwind pool liq=' + str(session_count_unwind_pool_liq) +\
                                ', count unwind price_mad=' + str(session_count_unwind_max_price_mad) +\
                                ', count hedge RL = ' + str(session_count_hedge_RL) )
            logger.info(network + ", session: time = " + "{:1.1f}".format((time.time() - start_time) / 3600) + " h" +\
                                                    ", max price_mad = " + "{:1.5f}".format(max_price_mad) +\
                                                    ", LP fees = " + "{:1.2f}".format(session_LP_fees_bp) + " bp" +\
                                                    ", RL = " + "{:1.2f}".format(session_RL_bp) + " bp" )
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




