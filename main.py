__author__ = "Galin Georgiev"
__copyright__ = "Copyright 2022, GammaDynamics, LLC"
__version__ = "1.1.0.0"



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
    amount0_LP, amount1_LP, priceLower, tickLower, priceUpper, tickUpper, priceLP, LP_position_to_init_price =\
            (NUM_LP + 1) * [None], (NUM_LP + 1) * [None], (NUM_LP + 1) * [None], (NUM_LP + 1) * [None], (NUM_LP + 1) * [None],\
            (NUM_LP + 1) * [None], (NUM_LP + 1) * [None],  (NUM_LP + 1) * [INIT_LP_POSITION_TO_INIT_PRICE]
    swap_volume_token1, rel_swap_volume_token1, swap_flow_token1 = (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.]
    amount0_invested, amount1_invested, asset_ratio_01_LP, asset_ratio_01, asset0_ratio, asset1_ratio =\
            (NUM_LP + 1) * [None], (NUM_LP + 1) * [None], (NUM_LP + 1) * [None], (NUM_LP + 1) * [None], (NUM_LP + 1) * [None], (NUM_LP + 1) * [None]
    tx_invested_token1, tx_token1_rf_invested_token1, tx_collected_token1 =\
            (NUM_LP + 1) * [0.] , (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.]
    tx_invested, tx_collected = (NUM_LP + 1) * [(0., 0.)], (NUM_LP + 1) * [(None, None)]
    tx_token0_rf_pl_token1, tx_token0_rf_pl_bp, tx_token1_rf_pl_token1, tx_token1_rf_pl_bp, tx_estimated_token1_rf_pl_bp =\
            (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.] , (NUM_LP + 1) * [0.]
    RL_v2_token1, RL_v2_bp, v3_v2_mult_factor, RL_v3_token1, RL_v3_bp, LP_fees_bp, OTM_loss_token1, OTM_loss_bp =\
            (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.],  (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.]
    #tx_count_hedge_RL, tx_hedge_RL_amount, last_RL_bp, tx_hedge_RL_pl_bp, hedge_RL_pl_bp =\
    #    (NUM_LP + 1) * [0], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.]
    tx_batch_amount_to_swap_token0 = 0.
    mint_time, duration, ITM_duration, OTM_duration, decreaseLiquidity_time =\
       (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0], (NUM_LP + 1) * [0], (NUM_LP + 1) * [0], (NUM_LP + 1) * [None]
    mint_condition, unwind_condition = (NUM_LP + 1) * [False], (NUM_LP + 1) * [False]
    count_LP_swap_attempts = 0

    #initialize session
    session_count_LP, session_count_unwind_signed_quantity, session_count_unwind_distance_rebal, session_count_unwind_distance_nonrebal =\
            (NUM_LP + 1) * [0], (NUM_LP + 1) * [0], (NUM_LP + 1) * [0], (NUM_LP + 1) * [0]
    session_count_LP_swap, session_count_LP_swap_failed, session_count_unwind_stop_profit, session_count_unwind_stop_loss, \
            session_count_unwind_pool_liq, session_count_unwind_max_price_mad,\
            session_count_hedge_RL, session_count_non_LP_swaps, session_count_unwind_flow =\
            0, 0, 0, 0, 0, 0, 0, 0, 0
    session_LP_fees_bp, session_RL_bp, session_OTM_loss_bp =\
            (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.]
    session_token0_rf_pl_token1, session_token0_rf_pl_bp, session_token1_rf_pl_token1, session_token1_rf_pl_bp, session_gas_fees =\
            (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [(0., 0., 0., 0.)] + [(0.,)]
    session_invested, session_collected = (NUM_LP + 1) * [(0., 0.)], (NUM_LP + 1) * [(0., 0)]
    session_token0_price_invested, session_token1_price_invested, session_token0_price_collected, session_token1_price_collected,\
       session_token0_pl_token1_rf_token1, amount_to_swap_token0 = [], [], [], [], 0., 0.
    session_swap_cost_bp, session_res_num_token0, session_res_num_token1 =  0., 0., 0.
    session_avg_LP_duration, session_avg_ITM_duration, session_avg_OTM_duration =\
            (NUM_LP + 1) * [0], (NUM_LP + 1) * [0], (NUM_LP + 1) * [0]
    
    #initialize flags
    #N.B. Individual tx-s flags are needed so the wrong tx is not run when tx fails!
    flag_change_tokenIds, flag_mint, flag_increaseLiquidity, flag_hedgeRL, flag_decreaseLiquidity, flag_collect, flag_burn, flag_LP_swap =\
        True, True, True, True, True, True, True, False
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
        #1. N.B. obtain the current LP positions: do not run current_LP_positions() (incurs >= 0.5s delay):
        #N.B. i) if not flag_change_tokenIds (raised only on i=0, mint(), burn()), or
        #n.b. ii) if periodicity of iterations is not satisfied;
        #N.B. tokenIds[j] are assigned by mint() but sometimes wrong,\
        #N.B. so tokenIds[j] is assigned for < NUM_LP anew below (that is why current_LP_positions() is run with some periodicity) ; tokenIds[j] = None after successful burn()

        if (not flag_failed_tx) and (flag_change_tokenIds or i % PERIOD_CURRENT_LP_POSITIONS_ITERATIONS == 0):
            flag_change_tokenIds = False

            result = current_LP_positions(network, address=Address, init=init) 
            if isinstance(result, list):

                #N.B. Stop main(), if NFT-s in the account at start!
                if i == 0 and len(result) > 0:
                    logger.error(network + ', there are NFTs in this account with ID-s ' + str(result) + ', burn them with burn.py! Stop main()!')
                    logger.info('network, END session')
                    return False
                
                #N.B. The list result is sorted in ascending order; assuming that mint-assigned tokenIds[NUM_LP] is correct!
                k, l = 0, 0
                while k <= NUM_LP and l < len(result):
                    #N.B. tokenIds[k] is assigned by mint() but sometimes wrong so re-assigned here!
                    #N.B. Increase tokenIds index by 1 if tokenIds[np.argsort(mint_time)[k]] = None: tokenIds[] = None when initialized or after successful burn()!
                    #N.B. If mint() occured in the meantime on LP[np.argsort(mint_time)[k]], accept mint-assigned tokenId!
                    if tokenIds[np.argsort(mint_time)[k]] is None:
                        k += 1
                        continue
                    #N.B. Increase result index by 1 if result[l] == tokenIds[NUM_LP]
                    if result[l] == tokenIds[NUM_LP]:
                        l += 1
                        continue
                    #N.B. Do not assign tokenIds[NUM_LP]!
                    if np.argsort(mint_time)[k] != NUM_LP:
                        tokenIds[np.argsort(mint_time)[k]] = result[l]

                    k += 1
                    l += 1
               
                #N.B. Sometimes Alchemy API returns already burned tokens, so check for that!
                for tokenId in tokenIds:
                    if tokenId in tokenIds_burned:
                        tokenId = None 

                #N.B. There was at least one instance (block = 35403465, tx hash 0x6eaaac828f5554b00cc864bddd8fdf27fc7c694dc6eab8248a9c789da8c37aca, Polygon),
                #N.B. where current_LP_positions() did not pick up an existing LP position
                #N.B. with tokenId = 466471; the mint of tokenId=466471 is not reflected in the log either: main_20221108_VM.log at 2022-11-09 09:04:53,679
                #N.B. but is on polygonscan.com? That is only possible if mint() was executed outside of the bot, but I was driving at that time?
                #N.B. decreaseLiquidity(), collect(), burn() were executed on the next iteration (after 1s), according to polygonscan.com, but failed with error 'Not appproved'?!

                logger.info(network + ', tokenIds = ' + str(tokenIds) + ', in main')
                #N.B. Stop main(), if there are ever > NUM_LP + 1 simulteneous non-None NFT-s in the account!
                if len([t for t in tokenIds if t is not None]) > NUM_LP + 1:
                    logger.info('')
                    logger.error(network + ', more than ' + str(NUM_LP + 1) + ' simulteneous LP positions are NOT allowed, burn the extra with burn.py! Stop main()!')
                    logger.info(network + ", session: " + init.token1_symbol + "-ref-frame p&l w/o swaps = " +\
                        "{:1.4f}".format(sum(session_token1_rf_pl_token1)) + ' ' + init.token1_symbol +\
                        " or " + "{:1.1f}".format(sum(session_token1_rf_pl_bp))  + " bp" +\
                        " = " + str(["{:1.1f}".format(s) for s in session_token1_rf_pl_bp]) + " bp" +\
                        ", swap cost=" + "{:1.2f}".format(session_swap_cost_bp) + " bp" +\
                        ", token0 collected in " + init.token1_symbol + "-ref-frame p&l = " +\
                                "{:1.4f}".format(session_token0_pl_token1_rf_token1) + ' ' + init.token1_symbol + ' or '+\
                                "{:1.2f}".format(session_token0_pl_token1_rf_token1 / NUM_INVESTED_TOKEN1_LP * 10000) + ' bp')
                    logger.info(network + ", session: gas fees = " + "{:1.2f}".format(sum([sum(s) for s in session_gas_fees])) + ' ' + init.network_coin_symbol +\
                                  " = [" + str(["{:1.2f}".format(s[0]) for s in session_gas_fees[:-1]]) +\
                                  ", " + str(["{:1.2f}".format(s[1]) for s in session_gas_fees[:-1]]) +\
                                  ", " + str(["{:1.2f}".format(s[2]) for s in session_gas_fees[:-1]]) +\
                                  ", " + str(["{:1.2f}".format(s[3]) for s in session_gas_fees[:-1]]) +\
                                  ", " + "{:1.2f}".format(session_gas_fees[-1][0]) + '] ' + init.network_coin_symbol)
                    logger.info(network + ", session" +\
                        ": LP fees = " + str(["{:1.1f}".format(s) for s in session_LP_fees_bp]) + " bp" +\
                        ", RL = " + str(["{:1.1f}".format(s) for s in session_RL_bp]) + " bp" +\
                        ", OTM loss = " + str(["{:1.1f}".format(s) for s in session_OTM_loss_bp]) + " bp"  )
                        #", iv) hedge RL=" + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
                    logger.info(network + ", session" +  ": res num token0 = " + str(session_res_num_token0) + ", res num token1 = " + str(session_res_num_token1) )
                    logger.info(network + ", session" +  ": invested " + "{:1.1f}".format(sum(s[0] for s in session_invested)) + " = " + str(["{:1.1f}".format(s[0]) for s in session_invested]) + ' ' + init.token0_symbol +\
                                          ", collected " + "{:1.1f}".format(sum(s[0] for s in session_collected)) + " = "  + str(["{:1.1f}".format(s[0]) for s in session_collected]) + ' ' + init.token0_symbol )
                    logger.info(network + ", session" +  ": invested " + "{:1.4f}".format(sum(s[1] for s in session_invested)) + " = "  + str(["{:1.4f}".format(s[1]) for s in session_invested]) + ' ' + init.token1_symbol +\
                                          ", collected " + "{:1.4f}".format(sum(s[1] for s in session_collected)) + " = "  + str(["{:1.4f}".format(s[1]) for s in session_collected]) + ' ' + init.token1_symbol )
                    logger.info(network + ', session' +\
                                ': count LP=' + str(sum(session_count_LP[:NUM_LP])) +
                                ', count LP swaps=' + str(session_count_LP[NUM_LP]) +\
                                ', count LP swaps failed=' + str(session_count_LP_swap_failed) +\
                                ', count non-LP swaps=' + str(session_count_non_LP_swaps) +\
                                ', count unwind flow=' + str(session_count_unwind_flow) +\
                                ', count unwind stop profit=' + str(session_count_unwind_stop_profit) +\
                                ', count unwind stop loss=' + str(session_count_unwind_stop_loss) +\
                                ', count unwind pool liq=' + str(session_count_unwind_pool_liq) +\
                                ', count unwind price_mad=' + str(session_count_unwind_max_price_mad) ) #+\
                                #', count hedge RL = ' + str(session_count_hedge_RL) )
                    logger.info(network + ', session' +\
                                ': count unwind distance rebalance=' + str(sum(session_count_unwind_distance_rebal)) + "=" + str(session_count_unwind_distance_rebal) +\
                                ', count unwind distance non-rebalance=' + str(sum(session_count_unwind_distance_nonrebal)) + "=" + str(session_count_unwind_distance_nonrebal) +\
                                ', count unwind signed q=' + str(sum(session_count_unwind_signed_quantity)) + "=" + str(session_count_unwind_signed_quantity) )
                    logger.info(network + ", session: dur=" + "{:1.1f}".format((time.time() - start_time) / 3600) + " h" +\
                        #"; avg LP dur=" + str(["{:1.1f}".format(s / 60) for s in session_avg_LP_duration]) + " min" +\
                        "; avg LP ITM dur=" + str(["{:1.1f}".format(s / 60) for s in session_avg_ITM_duration]) + " min" +\
                        "; avg LP OTM dur=" + str(["{:1.1f}".format(s / 60) for s in session_avg_OTM_duration]) + " min" +\
                        ", max price_mad = " + "{:1.5f}".format(max_price_mad) )
                    logger.info('network, END session')
                    return False
                    
                

            else:
                i += 1
                continue

        #####################################################################
        #2. obtain the current pool price: the fuction returns False if no updates!
        #N.B. sometimes (OTM) mint() fails because the price is not updated!
        if (not flag_failed_tx) or (not flag_mint):
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
                    if len(session_token0_price_collected) > 0:
                        session_token0_pl_token1_rf_token1 = sum(- s[0] * (price / s[1] - 1.) / price for s in session_token0_price_collected)
                    if len(session_token0_price_invested) > 0:
                        session_token0_pl_token1_rf_token1 -= sum(- s[0] * (price / s[1] - 1.) / price for s in session_token0_price_invested)
                        logger.info(network + ", session token0 collected in " + init.token1_symbol + "-ref-frame p&l = " +\
                                "{:1.4f}".format(session_token0_pl_token1_rf_token1) + ' ' + init.token1_symbol + ' or '+\
                                "{:1.2f}".format(session_token0_pl_token1_rf_token1 / NUM_INVESTED_TOKEN1_LP * 10000) + ' bp')
            else:
                if not flag_failed_tx:
                    i += 1
                    continue             
        
        ######################################################################
        #3. mint LP position
        #N.B. if individual flags are not specified here, when unwind tx fails, it triggers infinite mint loop;
        if flag_increaseLiquidity and flag_hedgeRL and flag_decreaseLiquidity and flag_collect and flag_burn:

            #######################
            #N.B. amountX_LP[]
            if not flag_mint:
                mint_condition[j] = True #N.B. Assures that mint() is run again, if it fails!
            else:
                #N.B. swap LP
                #N.B. 'priceLP[NUM_LP] is None' condition prevents 2nd LP swap
                if flag_LP_swap and priceLP[NUM_LP] is None and amount_to_swap_token0 != 0.:
                    #N.B. amountX_LP = 0 assures that LP is OTM, otherwise mint() fails!
                    amount0_LP[NUM_LP] = amount_to_swap_token0 * 10**init.token0_decimal if amount_to_swap_token0 > 0 else 0.
                    amount1_LP[NUM_LP] = - amount_to_swap_token0 / price * 10**init.token1_decimal if amount_to_swap_token0 < 0 else 0.
                        
                #N.B. non-swap LP-s 
                #N.B. LP_distance_to_bound from beginning to end of quiet hours
                if (int(time.strftime('%w', time.localtime())) != 6 and int(time.strftime('%w', time.localtime())) != 0 and\
                        (int(time.strftime('%H', time.localtime())) >= QUIET_HOURS_START[0] and int(time.strftime('%H', time.localtime())) < QUIET_HOURS_END[-1])):
                    LP_distance_to_bound = LP_DISTANCE_TO_BOUND_PER[-1] / 100
                    #logger.info(network + ", LP_distance_to_bound = " +\
                    #    "{:1.2f}".format(LP_distance_to_bound * 100) + "% from beginning to end of quiet hours!")
                else:
                    LP_distance_to_bound = LP_DISTANCE_TO_BOUND_PER[0] / 100

                j = 0
                while j < NUM_LP:
                    if priceLP[j] is None:
                        
                        #N.B. mint only OTM LP positions!
                        if not CHANGE_LP_POSITION_TO_INIT_PRICE:
                            if LP_position_to_init_price[j] == 1:
                                amount0_LP[j], amount1_LP[j] = 0., NUM_INVESTED_TOKEN1_LP / NUM_LP
                            elif LP_position_to_init_price[j] == -1:
                                amount0_LP[j], amount1_LP[j] = price * NUM_INVESTED_TOKEN1_LP / NUM_LP, 0.
                        else:
                            if LP_position_to_init_price[j] == 1:
                                #N.B. When the 1-st trades
                                if tx_collected[j][1] is None:
                                    amount0_LP[j], amount1_LP[j] = 0., NUM_INVESTED_TOKEN1_LP / NUM_LP
                                #N.B. Including the case of the last LP[j] was ITM
                                elif tx_collected[j][1] * price >= tx_collected[j][0]:
                                    amount0_LP[j], amount1_LP[j] = 0., tx_collected[j][1]
                                else:
                                    #N.B. Change LP_position_to_init_price[j] of the OTM LP
                                    LP_position_to_init_price[j] *= -1
                                    amount0_LP[j], amount1_LP[j] = tx_collected[j][0], 0.
                                
                            elif LP_position_to_init_price[j] == -1:
                                #N.B. When the 1-st trades
                                if tx_collected[j][0] is None:
                                    amount0_LP[j], amount1_LP[j] = price * NUM_INVESTED_TOKEN1_LP / NUM_LP, 0.
                                #N.B. Including the case of the last LP[j] was ITM
                                elif tx_collected[j][0] >= tx_collected[j][1] * price:
                                    amount0_LP[j], amount1_LP[j] = tx_collected[j][0], 0.
                                else:
                                    #N.B. Change LP_position_to_init_price[j] of the OTM LP
                                    LP_position_to_init_price[j] *= -1
                                    amount0_LP[j], amount1_LP[j] = 0., tx_collected[j][1]
                                
                        #N.B. rescale amountX_LP[j]
                        amount0_LP[j] *= 10**init.token0_decimal
                        amount1_LP[j] *= 10**init.token1_decimal
                    j += 1

            #########################
            #N.B. priceLower[], priceUpper[]: run even if flag_mint = False (dependence on updated price!)
            #N.B. Can use amount_to_swap_token0 sign because this is immediately after amount_to_swap_token0 was set up!

            #N.B. swap LP
            if flag_LP_swap and priceLP[NUM_LP] is None and amount_to_swap_token0 != 0.:
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

            #N.B. non-swap LP-s
            if flag_mint:
                j = 0
            while j < NUM_LP:
                if priceLP[j] is None:

                    ##N.B. LP positions symmetric around the current price: middle LP is symmetric in-the-money: comment-out minting only OTM LP positions!
                    #priceLower[int((NUM_LP - 1) / 2)] = price_DECIMAL * (1. - LP_distance_to_bound)
                    #priceUpper[int((NUM_LP - 1) / 2)] = price_DECIMAL * (1. + LP_distance_to_bound)
                    ##N.B. Assure the the price ranges are adjacent!
                    #if j < int((NUM_LP - 1) / 2)):
                    #        priceLower[j] = price_DECIMAL * (1. + (2 * j - NUM_LP) * LP_distance_to_bound)
                    #        priceUpper[j] = priceLower[j + 1]
                    #for j > int((NUM_LP - 1) / 2)):
                    #        priceLower[j] = priceUpper[j - 1]
                    #        priceUpper[j] = price_DECIMAL * (1. + (2 * (j + 1) - NUM_LP) * LP_distance_to_bound)

                    #N.B. OTM LP positions
                    if LP_position_to_init_price[j] == 1:
                        if LP_distance_to_bound == 0.:
                            if j == 0:
                                priceLower[j] = price_DECIMAL * (1. + 3 * LP_SWAP_DISTANCE_TO_BOUND_PER / 100)
                                #N.B. Re-compute priceLower, priceUpper: tick spacing >> 1, depending on the pool fee: section 4 in https://uniswap.org/whitepaper-v3.pdf
                                #N.B. tick = log(price) / log(1.0001): (6.1) in https://uniswap.org/whitepaper-v3.pdf
                                tickLower[j] = np.log(priceLower[j]) / np.log(1.0001)
                                if init.pool_fee == 500:
                                    tickUpper[j] = int(tickLower[j] // 10 * 10 + 10)
                                    tickLower[j] = int(tickLower[j] // 10 * 10)
                                elif init.pool_fee == 3000:
                                    tickUpper[j] = int(tickLower[j] // 60 * 60 + 60)
                                    tickLower[j] = int(tickLower[j] // 60 * 60)
                                elif init.pool_fee == 10000:
                                    tickUpper[j] = int(tickLower[j] // 200 * 200 + 200)
                                    tickLower[j] = int(tickLower[j] // 200 * 200)
                            else:
                                tickLower[j] = tickUpper[j - 1]
                                if init.pool_fee == 500:
                                    tickUpper[j] = tickLower[j] + 10
                                elif init.pool_fee == 3000:
                                    tickUpper[j] = tickLower[j] + 60
                                elif init.pool_fee == 10000:
                                    tickUpper[j] = tickLower[j] + 200
                            priceLower[j], priceUpper[j] = 1.0001 ** tickLower[j], 1.0001 ** tickUpper[j]
                        else:
                            priceLower[j] = price_DECIMAL * (1. + (j + 1) * 2 * LP_distance_to_bound + LP_SWAP_DISTANCE_TO_BOUND_PER / 100)
                            priceUpper[j] = price_DECIMAL * (1. + (j + 2) * 2 * LP_distance_to_bound + LP_SWAP_DISTANCE_TO_BOUND_PER / 100)
                    elif LP_position_to_init_price[j] == -1:
                        if LP_distance_to_bound == 0.:
                            if j == 0:
                                priceUpper[j] = price_DECIMAL * (1. - 3 * LP_SWAP_DISTANCE_TO_BOUND_PER / 100)
                                #N.B. Re-compute priceLower, priceUpper: tick spacing >> 1, depending on the pool fee: section 4 in https://uniswap.org/whitepaper-v3.pdf
                                #N.B. tick = log(price) / log(1.0001): (6.1) in https://uniswap.org/whitepaper-v3.pdf
                                tickUpper[j] = np.log(priceUpper[j]) / np.log(1.0001)
                                if init.pool_fee == 500:
                                    tickLower[j] = int(tickUpper[j] // 10 * 10 - 10)
                                    tickUpper[j] = int(tickUpper[j] // 10 * 10)
                                elif init.pool_fee == 3000:
                                    tickLower[j] = int(tickUpper[j] // 60 * 60 - 60)
                                    tickUpper[j] = int(tickUpper[j] // 60 * 60)
                                elif init.pool_fee == 10000:
                                    tickLower[j] = int(tickUpper[j] // 200 * 200 - 200)
                                    tickUpper[j] = int(tickUpper[j] // 200 * 200)
                            else:
                                tickUpper[j] = tickLower[j - 1]
                                if init.pool_fee == 500:
                                    tickLower[j] = tickUpper[j] - 10
                                elif init.pool_fee == 3000:
                                    tickLower[j] = tickUpper[j] - 60
                                elif init.pool_fee == 10000:
                                    tickLower[j] = tickUpper[j] - 200
                            priceLower[j], priceUpper[j] = 1.0001 ** tickLower[j], 1.0001 ** tickUpper[j]
                        else:
                            priceLower[j] = price_DECIMAL * (1. - (j + 2) * 2 * LP_distance_to_bound - LP_SWAP_DISTANCE_TO_BOUND_PER / 100)
                            priceUpper[j] = price_DECIMAL * (1. - (j + 1) * 2 * LP_distance_to_bound - LP_SWAP_DISTANCE_TO_BOUND_PER / 100)
                if flag_mint: #N.B. Otherwise, j increases and mint() is typically not run again, after mint() failure (because mint_condition[j + 1] = False)!        
                    j += 1

            ##########################
            #N.B. mint_condition[]
            if flag_mint:
                #N.B. swap LP
                if flag_LP_swap and priceLP[NUM_LP] is None and amount_to_swap_token0 != 0.:
                    if amount0_LP[NUM_LP] > 0 or amount1_LP[NUM_LP] > 0:
                        mint_condition[NUM_LP] = True

                #N.B. non-swap LP-s
                j = 0
                while j < NUM_LP:
                    if priceLP[j] is None:
                        if i < int(RUNTIME_SEC / DELAY_LOOP_SEC) - NUM_LP * MAX_ATTEMPS_FAILED_TX:
                            mint_condition[j] = True

                        #N.B. Do not initiate non-swap LP with the wrong  LP_position_to_init_price in the last quarter of RUNTIME_SEC / DELAY_LOOP_SEC!
                        if CHANGE_LP_POSITION_TO_INIT_PRICE and i > 0.75 * int(RUNTIME_SEC / DELAY_LOOP_SEC) and\
                                    LP_position_to_init_price[j] == INIT_LP_POSITION_TO_INIT_PRICE:
                            logger.info("NO LP[" + str(j) + "] mint in the last quarter of RUNTIME_SEC / DELAY_LOOP_SEC because LP_position_to_init_price = " +\
                                    str(LP_position_to_init_price[j]) + " == INIT_LP_POSITION_TO_INIT_PRICE = " + str(INIT_LP_POSITION_TO_INIT_PRICE) )
                            mint_condition[j] = False
                    j += 1

                #N.B. Do not initiate non-swap LP-s if abs(signed_token1_quantity) is too small &
                #N.B.  MIN_INIT_AFTER_BLOCKS or MIN_INIT_AFTER_PRICE_RET_BP are not passed!
                if blockNumber_init is None:
                    if i != 0 and abs(signed_token1_quantity) * price / pool_liquidity_list[-1] *\
                        10 ** (0.5 * (init.token0_decimal + init.token1_decimal)) >= MIN_INIT_TOKEN1_VALUE_TO_POOL_LIQUIDITY_BP / 10000:
                        blockNumber_init, price_init = block_num, price #if signed_token1_quantity > 0 else -price
                        logger.info(network + ", blockNumber_init = " + str(blockNumber_init) + ", price_init = " +\
                            "{:1.5f}".format(price_init) + ", scaled abs(signed_token1_quantity) * price / pool_liquidity_list[-1] = " +\
                            "{:1.3f}".format(abs(signed_token1_quantity) * price / pool_liquidity_list[-1] * 10 ** (0.5 * (init.token0_decimal + init.token1_decimal)) * 10000) +\
                            " >=  MIN_INIT_TOKEN1_VALUE_TO_POOL_LIQUIDITY_BP = " + str(MIN_INIT_TOKEN1_VALUE_TO_POOL_LIQUIDITY_BP))
                    else:
                        logger.info(network + ", NO non-swap LP-s mint because blockNumber_init/price_init is not set yet: " +\
                            "scaled abs(signed_token1_quantity) * price / pool_liquidity_list[-1] = " +\
                            "{:1.3f}".format(abs(signed_token1_quantity) * price / pool_liquidity_list[-1] * 10 ** (0.5 * (init.token0_decimal + init.token1_decimal)) * 10000) +\
                            " <  MIN_INIT_TOKEN1_VALUE_TO_POOL_LIQUIDITY_BP = " + str(MIN_INIT_TOKEN1_VALUE_TO_POOL_LIQUIDITY_BP))
                    mint_condition[:NUM_LP] = NUM_LP * [False]
                else:
                    if  block_num >= blockNumber_init + MIN_INIT_AFTER_BLOCKS:
                        if abs(price - price_init) / price_init * 10000 < MIN_INIT_AFTER_PRICE_RET_BP: # and (price - price_init) * price_init > 0:
                            logger.info(network + ", blockNumber_init = " + str(blockNumber_init) + ", price_init = " + "{:1.5f}".format(price_init))
                            logger.info(network + ", NO LP[" + str(j) + "]  mint because abs(price - price_init) / price_init = " +\
                                    "{:1.2f}".format(abs(price - price_init) / price_init * 10000) +\
                                    " bp < MIN_INIT_AFTER_PRICE_RET_BP = " + str(MIN_INIT_AFTER_PRICE_RET_BP) + " bp")
                            mint_condition[:NUM_LP] = NUM_LP * [False]
                        blockNumber_init, price_init = None, None
                    else:
                        logger.info(network + ", blockNumber_init = " + str(blockNumber_init) + ", price_init = " + "{:1.5f}".format(price_init))
                        logger.info(network + ", NO non-swap LP-s mint because current block number = " +\
                                    str(block_num) + " <  blockNumber_init = " + str(blockNumber_init) +\
                                    " + MIN_INIT_AFTER_BLOCKS = " + str(blockNumber_init + MIN_INIT_AFTER_BLOCKS) )
                        mint_condition[:NUM_LP] = NUM_LP * [False]

                #N.B. Do not initiate non-swap LP-s during quiet hours
                if int(time.strftime('%w', time.localtime())) != 6 and int(time.strftime('%w', time.localtime())) != 0 and\
                        ((int(time.strftime('%H', time.localtime())) >= QUIET_HOURS_START[0] and int(time.strftime('%H', time.localtime())) < QUIET_HOURS_END[0]) or\
                        (int(time.strftime('%H', time.localtime())) >= QUIET_HOURS_START[1] and int(time.strftime('%H', time.localtime())) < QUIET_HOURS_END[1])):
                     mint_condition[:NUM_LP] = NUM_LP * [False]
                     logger.info(network + ", NO non-swap LP mint during quiet hours!")

                #N.B. Do not initiate non-swap LP if pool liquidity decreases < threshold * pool lquidity median!
                if EVENT_LOGS and len(pool_liquidity_list) > 0 and\
                    pool_liquidity_list[-1] < np.min([pool_liquidity_median, pool_liquidity_list[-1]]) * MIN_POOL_LIQUIDITY_PER[0] / 100:
                    logger.info('')
                    logger.info("NO non-swap LP mint because EVENT_LOGS=F or pool liq = " +\
                                    "{:1.0f}".format(pool_liquidity_list[-1] / 10 ** (0.5 * (init.token0_decimal + init.token1_decimal))) +\
                                    " < pool liq median * threshold= " + "{:1.0f}".format(pool_liquidity_median  / 10 ** (0.5 * (init.token0_decimal + init.token1_decimal)) * MIN_POOL_LIQUIDITY_PER[0] / 100))
                    mint_condition[:NUM_LP] = NUM_LP * [False]

                #N.B. Do not initiate non-swap LP if price_mad too high!
                if price_mad > PRICE_MAD[0]: # and (time.time() - max_price_mad_time) / 60 >= PRICE_MAD_WAIT_TIME_MIN:
                    logger.info('')
                    logger.info("NO non-swap LP mint because price_mad = " + "{:1.5f}".format(price_mad) + " > " + str(PRICE_MAD[0]) )
                    mint_condition[:NUM_LP] = NUM_LP * [False]

                #N.B. Do not initiate non-swap LP after RUNTIME_SEC / DELAY_LOOP_SEC
                if i >= int(RUNTIME_SEC / DELAY_LOOP_SEC) - NUM_LP * MAX_ATTEMPS_FAILED_TX: #tokenIds[:NUM_LP] == NUM_LP * [None]
                    mint_condition[:NUM_LP] = NUM_LP * [False]
      

            #############################
            #N.B. mint() (only if mint_condition[j])
            if flag_mint:
                j = 0
            while j <= NUM_LP:
                #if j == NUM_LP and not flag_LP_swap: #N.B. When j += 1, this line is hit, but if mint_condition[NUM_LP] == False, nothing will happen!
                #    j = 0
                #    break
                if mint_condition[j]:
                    #N.B. mint() returns sometimes wrong BlockNumber, tokenID, if it is done too fast after another tx
                    #if j > 0:
                    #    time.sleep(3)
                    #N.B.  flag_increaseLiquidity and flag_hedgeRL and flag_decreaseLiquidity and flag_collect and flag_burn on the top of mint_condition loop!
                    if count_failed_tx < MAX_ATTEMPS_FAILED_TX:
                        #N.B. Compute nonce in mint() in order to keep the order of mints()
                        result = mint(network, amount0ToMint=amount0_LP[j], amount1ToMint=amount1_LP[j], tickLower=tickLower[j], tickUpper=tickUpper[j], \
                                        max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas, \
                                        address=Address, private_key=privateKey, init=init)
                        if isinstance(result, tuple):
                            gas_fee, tokenId, liquidity, amount0, amount1, blockNumber, nonce = result

                            tokenIds[j], liquidities[j] = tokenId, liquidity
                            session_gas_fees[j] = tuple(map(sum, zip(session_gas_fees[j], (gas_fee, 0., 0., 0.) )))
                            #N.B. priceLP from line (71) in https://github.com/Uniswap/v3-periphery/blob/main/contracts/libraries/LiquidityAmounts.sol
                            #N.B. When price range is out-of-the-money, priceLP equals one of the price bound!
                            priceLP[j] = (amount0  / liquidities[j] + np.sqrt(priceLower[j])) ** 2
                            pool_liquidity_LP = pool_liquidity_list[-1]
                            swap_volume_token1[j], rel_swap_volume_token1[j], swap_flow_token1[j] = 0., 0., 0.
                            amount0_invested[j], amount1_invested[j] = amount0, amount1
                            blockNumber_init, price_init = None, None
                            amount0_LP[j], amount1_LP[j] = None, None
                            tx_slippage_and_pool_fee_pl_bp = 0. #, tx_count_hedge_RL[j] = 0
                            tx_invested[j] = (amount0 / 10**init.token0_decimal / price, amount1 / 10**init.token1_decimal)
                            tx_invested_token1[j] = amount0 / 10**init.token0_decimal / price + amount1 / 10**init.token1_decimal
                            tx_token1_rf_invested_token1[j] = tx_invested_token1[j]
                            mint_time[j], iteration_time, ITM_duration[j], OTM_duration[j] = time.time(), time.time(), 0, 0
                            mint_condition[j] = False
                            session_invested[j] = tuple(map(sum, zip(session_invested[j], (amount0 / 10**init.token0_decimal, amount1 / 10**init.token1_decimal) )))
                            
                            if j == NUM_LP and flag_LP_swap:
                                logger.info(network  + ", LP[" + str(j) + "]:" +\
                                            ", mint LP swap: priceLP = " + "{:1.5f}".format(priceLP[NUM_LP] / 10**init.token0_decimal * 10**init.token1_decimal) +\
                                            ", priceLower = " + "{:1.5f}".format(priceLower[NUM_LP] / 10**init.token0_decimal * 10**init.token1_decimal) +\
                                            ", priceUpper = " + "{:1.5f}".format(priceUpper[NUM_LP] / 10**init.token0_decimal * 10**init.token1_decimal) +\
                                            ", session count LP swap tx_s = " + str(session_count_LP[NUM_LP]))
                            else:
                                #hedge_RL = HEDGE_RL
                                #tx_hedge_RL_pl_bp[j], hedge_RL_pl_bp[j], last_RL_bp[j], tx_hedge_RL_amount[j], last_hedge_RL_price[j] = 0., 0., 0., 0., None
                                if amount1 != 0:
                                    asset_ratio_01_LP[j] = amount0 / price / amount1
                                else:
                                    asset_ratio_01_LP[j] = np.inf
                                logger.info(network + ", LP[" + str(j) + "]:" +\
                                            " invested " + str(tx_invested_token1[j]) + ' ' + init.token1_symbol +\
                                            ", asset0/asset1 = " +  "{:1.3f}".format(asset_ratio_01_LP[j]) +\
                                            ", priceLP = " + "{:1.5f}".format(priceLP[j] / 10**init.token0_decimal * 10**init.token1_decimal) +\
                                            ", priceLower = " + "{:1.5f}".format(priceLower[j] / 10**init.token0_decimal * 10**init.token1_decimal) +\
                                            ", priceUpper = " + "{:1.5f}".format(priceUpper[j] / 10**init.token0_decimal * 10**init.token1_decimal) )
                                
                            #N.B. run current_pool_price() again only if mint() succeeds (otherwise the price is updated at the beginning of the next iteration
                            #N.B. the fuction returns False if no updates!
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
                            #N.B. nonce=None triggers web3 getting a nonce
                            priceLP[j], nonce = None, None
                            count_failed_tx += 1
                            if j == NUM_LP and flag_LP_swap:
                                count_LP_swap_attempts += 1
                            logger.error(network + ", mint() failed for LP[" + str(j) + "]" +\
                                ", count_failed_tx = " + str(count_failed_tx) + ", count_LP_swap_attempts = " + str(count_LP_swap_attempts))
                            flag_failed_tx, flag_mint = True, False
                            break #N.B. Break the inner loop
                    else:
                        logger.info('')
                        logger.error(network + ', mint() for LP[' + str(j) + '] failed MAX_ATTEMPS_FAILED_TX = ' + str(MAX_ATTEMPS_FAILED_TX) + ' times, stop main()!')
                        current_LP_positions(network, address=Address, init=init) 
                        #logger.info(network + ", session p&l = " + str(session_token0_rf_pl_token1[j]) + ' ' + init.token1_symbol +\
                        #                ", " + "{:1.2f}".format(session_token0_rf_pl_bp[j]) + " bp")
                        logger.info(network + ", session: " + init.token1_symbol + "-ref-frame p&l w/o swaps = " +\
                                "{:1.4f}".format(sum(session_token1_rf_pl_token1)) + ' ' + init.token1_symbol +\
                                " or " + "{:1.1f}".format(sum(session_token1_rf_pl_bp))  + " bp" +\
                                " = " + str(["{:1.1f}".format(s) for s in session_token1_rf_pl_bp]) + " bp" +\
                                ", swap cost=" + "{:1.2f}".format(session_swap_cost_bp) + " bp" +\
                                ", token0 collected in " + init.token1_symbol + "-ref-frame p&l = " +\
                                        "{:1.4f}".format(session_token0_pl_token1_rf_token1) + ' ' + init.token1_symbol + ' or '+\
                                        "{:1.2f}".format(session_token0_pl_token1_rf_token1 / NUM_INVESTED_TOKEN1_LP * 10000) + ' bp')
                        logger.info(network + ", session: gas fees = " + "{:1.2f}".format(sum([sum(s) for s in session_gas_fees])) + ' ' + init.network_coin_symbol +\
                                  " = [" + str(["{:1.2f}".format(s[0]) for s in session_gas_fees[:-1]]) +\
                                  ", " + str(["{:1.2f}".format(s[1]) for s in session_gas_fees[:-1]]) +\
                                  ", " + str(["{:1.2f}".format(s[2]) for s in session_gas_fees[:-1]]) +\
                                  ", " + str(["{:1.2f}".format(s[3]) for s in session_gas_fees[:-1]]) +\
                                  ", " + "{:1.2f}".format(session_gas_fees[-1][0]) + '] ' + init.network_coin_symbol)
                        logger.info(network + ", session" +\
                                ": LP fees = " + str(["{:1.1f}".format(s) for s in session_LP_fees_bp]) + " bp" +\
                                ", RL = " + str(["{:1.1f}".format(s) for s in session_RL_bp]) + " bp" +\
                                ", OTM loss = " + str(["{:1.1f}".format(s) for s in session_OTM_loss_bp]) + " bp"   )
                                #", iv) hedge RL=" + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
                        logger.info(network + ", session" +  ": res num token0 = " + str(session_res_num_token0) + ", res num token1 = " + str(session_res_num_token1) )
                        logger.info(network + ", session" +  ": invested " + "{:1.1f}".format(sum(s[0] for s in session_invested)) + " = " + str(["{:1.1f}".format(s[0]) for s in session_invested]) + ' ' + init.token0_symbol +\
                                              ", collected " + "{:1.1f}".format(sum(s[0] for s in session_collected)) + " = "  + str(["{:1.1f}".format(s[0]) for s in session_collected]) + ' ' + init.token0_symbol )
                        logger.info(network + ", session" +  ": invested " + "{:1.4f}".format(sum(s[1] for s in session_invested)) + " = "  + str(["{:1.4f}".format(s[1]) for s in session_invested]) + ' ' + init.token1_symbol +\
                                              ", collected " + "{:1.4f}".format(sum(s[1] for s in session_collected)) + " = "  + str(["{:1.4f}".format(s[1]) for s in session_collected]) + ' ' + init.token1_symbol )
                        logger.info(network + ', session' +\
                                ': count LP=' + str(sum(session_count_LP[:NUM_LP])) +\
                                ', count LP swaps=' + str(session_count_LP[NUM_LP]) +\
                                ', count LP swaps failed=' + str(session_count_LP_swap_failed) +\
                                ', count non-LP swaps=' + str(session_count_non_LP_swaps) +\
                                ', count unwind flow=' + str(session_count_unwind_flow) +\
                                ', count unwind stop profit=' + str(session_count_unwind_stop_profit) +\
                                ', count unwind stop loss=' + str(session_count_unwind_stop_loss) +\
                                ', count unwind pool liq=' + str(session_count_unwind_pool_liq) +\
                                ', count unwind price_mad=' + str(session_count_unwind_max_price_mad) ) #+\
                                #', count hedge RL = ' + str(session_count_hedge_RL) )
                        logger.info(network + ', session' +\
                                ': count unwind distance rebalance=' + str(sum(session_count_unwind_distance_rebal)) + "=" + str(session_count_unwind_distance_rebal) +\
                                ', count unwind distance non-rebalance=' + str(sum(session_count_unwind_distance_nonrebal)) + "=" + str(session_count_unwind_distance_nonrebal) +\
                                ', count unwind signed q=' + str(sum(session_count_unwind_signed_quantity)) + "=" + str(session_count_unwind_signed_quantity) )
                        logger.info(network + ", session: dur=" + "{:1.1f}".format((time.time() - start_time) / 3600) + " h" +\
                            #"; avg LP dur=" + str(["{:1.1f}".format(s / 60) for s in session_avg_LP_duration]) + " min" +\
                            "; avg LP ITM dur=" + str(["{:1.1f}".format(s / 60) for s in session_avg_ITM_duration]) + " min" +\
                            "; avg LP OTM dur=" + str(["{:1.1f}".format(s / 60) for s in session_avg_OTM_duration]) + " min" +\
                            ", max price_mad = " + "{:1.5f}".format(max_price_mad) )
                        logger.info('network, END session')
                        return False

                #N.B. 'if not flag_failed_tx' is not needed here, because unwind tx are checked to not have failed and if mint() fails, it breaks the NUM_LP-loop!
                #N.B. if not commented-out, 'if not flag_failed_tx' can create infinite j-loop, when flag_failed_tx
                #if not flag_failed_tx:
                j += 1

        ###################################################################################
        #N.B. Reporting in log
        unwind_distance_to_bound = [(UNWIND_DIST_TO_BOUND_PER[k][0] / 100, UNWIND_DIST_TO_BOUND_PER[k][1] / 100) \
                                    if LP_position_to_init_price[k] == 1 else (UNWIND_DIST_TO_BOUND_PER[k][1] / 100, UNWIND_DIST_TO_BOUND_PER[k][0] / 100) \
                                    for k in range(NUM_LP)]                            
        if amount_to_swap_token0 > 0:
            unwind_distance_to_bound = unwind_distance_to_bound + [(0., - LP_SWAP_UNWIND_DISTANCE_PER / 100)]
        elif amount_to_swap_token0 < 0:
            unwind_distance_to_bound = unwind_distance_to_bound + [(- LP_SWAP_UNWIND_DISTANCE_PER / 100, 0.)]

        if tokenIds != (NUM_LP + 1) * [None]:
            if not flag_failed_tx:
                j = 0
                while j <= NUM_LP: # and i < int(RUNTIME_SEC / DELAY_LOOP_SEC) - NUM_LP * MAX_ATTEMPS_FAILED_TX:
                    #N.B. 3a. Estimate quantities to report: RL, asset ratio, LP fees
                    #N.B. Rebalancing Loss (RL)
                    #N.B. see Google docs > Crypto > Defi Swaps > Uniswap > RL > Uniswap V2 & V3 > RL or > Greeks: https://docs.google.com/document/d/1K83HF3-A9NqFKtjF-wcf6Kduz0r-J0yYchiyOCfaKgo/edit
                    if priceLower[j] is not None and priceUpper[j] is not None and priceLP[j] is not None:
                        
                        tx_token1_rf_invested_token1[j] = amount0_invested[j] / 10**init.token0_decimal / price + amount1_invested[j] / 10**init.token1_decimal
                        if price_DECIMAL >= priceLower[j] and price_DECIMAL <= priceUpper[j]:
                            RL_v2_bp[j] = 2 * np.sqrt(price_DECIMAL / priceLP[j]) / (price_DECIMAL / priceLP[j] + 1) - 1
                            RL_v2_token1[j] = RL_v2_bp[j] * tx_token1_rf_invested_token1[j]
                            RL_v2_bp[j] *= 10000

                            #delta_RL_v2[j] = (1 - price_DECIMAL / priceLP[j]) / np.sqrt(price_DECIMAL / priceLP[j]) / (price_DECIMAL / priceLP[j] + 1)**2
                            v3_v2_mult_factor[j] = (price_DECIMAL / priceLP[j] + 1) / \
                                    (price_DECIMAL / priceLP[j] * (1 - np.sqrt(priceLP[j] / priceUpper[j])) + (1 - np.sqrt(priceLower[j] / priceLP[j])))
                            #time
                            ITM_duration[j] += time.time() - iteration_time
                        else:
                            OTM_duration[j] += time.time() - iteration_time
                            #N.B. Price can change dramatically within DELAY_LOOP_SEC and not be reflected in RL_v3!
                            if price_DECIMAL < priceLower[j]:
                                RL_v2_bp[j] = 10000 * (2 * np.sqrt(priceLower[j] / priceLP[j]) / (priceLower[j] / priceLP[j] + 1) - 1)
                                #delta_RL_v2[j] = (1 - priceLower[j] / priceLP[j]) / np.sqrt(priceLower[j] / priceLP[j]) / (priceLower[j] / priceLP[j] + 1)**2
                                v3_v2_mult_factor[j] = (priceLower[j] / priceLP[j] + 1) / \
                                    (priceLower[j] / priceLP[j] * (1 - np.sqrt(priceLP[j] / priceUpper[j])) + (1 - np.sqrt(priceLower[j] / priceLP[j])))
                            elif price_DECIMAL > priceUpper[j]:
                                RL_v2_bp[j] = 10000 * (2 * np.sqrt(priceUpper[j] / priceLP[j]) / (priceUpper[j] / priceLP[j] + 1) - 1)
                                #delta_RL_v2[j] = (1 - priceUpper[j] / priceLP[j]) / np.sqrt(priceUpper[j] / priceLP[j]) / (priceUpper[j] / priceLP[j] + 1)**2
                                v3_v2_mult_factor[j] = (priceUpper[j] / priceLP[j] + 1) / \
                                    (priceUpper[j] / priceLP[j] * (1 - np.sqrt(priceLP[j] / priceUpper[j])) + (1 - np.sqrt(priceLower[j] / priceLP[j])))
                        
                        #N.B. adjust for multiple LP-s
                        #N.B. NUM_INVESTED_TOKEN1_LP  is better used as a denominator, as opposed to sum(tx_token1_fr_invested_token1), because the latter can be smaller
                        RL_v2_bp[j] *= tx_token1_rf_invested_token1[j] / NUM_INVESTED_TOKEN1_LP

                        #N.B. RL_v3
                        RL_v3_token1[j] = RL_v2_token1[j] * v3_v2_mult_factor[j]
                        RL_v3_bp[j] = RL_v2_bp[j] * v3_v2_mult_factor[j]

                        #N.B. delta_RL_v3: formula true only if Price_LP is geometric average of priceUpper & priceLower 
                        #delta_RL_v3[j] = delta_RL_v2[j] * v3_v2_mult_factor[j]
                        
                        ###################
                        #N.B. Asset ratio
                        if price_DECIMAL < priceLower[j] or min([abs(price_DECIMAL - priceLower[j]), abs(priceLP[j] - priceUpper[j])]) <= EPSILON:
                            asset_ratio_01[j] = 0.
                            asset0_ratio[j], asset1_ratio[j] = 0., 1.
                        elif price_DECIMAL > priceUpper[j] or min([abs(price_DECIMAL - priceUpper[j]), abs(priceLP[j] - priceLower[j])]) <= EPSILON:
                            asset_ratio_01[j] = np.inf
                            asset0_ratio[j], asset1_ratio[j] = 1., 0.
                        else:
                            #N.B. see Google docs > Crypto > Defi Swaps > Uniswap > V3 > Balances: https://docs.google.com/document/d/1K83HF3-A9NqFKtjF-wcf6Kduz0r-J0yYchiyOCfaKgo/edit
                            asset_ratio_01[j] = (np.sqrt(price_DECIMAL) - np.sqrt(priceLower[j])) / (np.sqrt(priceLP[j]) - np.sqrt(priceLower[j])) \
                                        / ((1 / np.sqrt(price_DECIMAL) - 1 / np.sqrt(priceUpper[j])) / (1 / np.sqrt(priceLP[j]) - 1 / np.sqrt(priceUpper[j]))) \
                                        / price_DECIMAL * priceLP[j] \
                                        #* asset_ratio_01_LP[j]
                            asset0_ratio[j], asset1_ratio[j] = asset_ratio_01[j] / (asset_ratio_01[j] + 1), 1 / (asset_ratio_01[j] + 1.)
                       
                        ###################
                        #N.B. LP Fees
                        #N.B. Alchemy transfer tx-s API does not report txIx, tx order in the same block is unknown & rel_swap_volume_token1 is wrong!
                        #N.B. If collect() or burn() return False (swap() does not return False), liquidities=[]
                        #N.B. swap_volume_token1[j] & rel_swap_volume_token1[j] are computed in current_pool_price(), using priceLower, priceUpper
                        if PRICE_ALCHEMY and (not EVENT_LOGS):
                            if pool_liquidity_median is not None:
                                LP_fees_bp[j] = liquidities[j] / pool_liquidity_median * swap_volume_token1[j] * init.pool_fee / 1000000 / NUM_INVESTED_TOKEN1_LP * 10000
                            else:
                                #N.B. Triggers STOP_LOSS!
                                LP_fees_bp[j] = 0. #-np.infty
                        else:
                            LP_fees_bp[j] = liquidities[j] * rel_swap_volume_token1[j] * init.pool_fee / 1000000 / NUM_INVESTED_TOKEN1_LP * 10000
                        
                        #N.B. Triggers STOP_LOSS!
                        #else:
                        #    LP_fees_bp = -np.infty

                        ##################
                        #N.B. OTM loss
                        if price_DECIMAL < priceLower[j]:
                            #N.B. Only approximate because amount0_invested token0 is converted to token1
                            #N.B. Using token0 does not generate OTM_loss (corectly!) for up OTM LP positions (they have amount0_invested = 0) when price is down!
                            OTM_loss_token1[j] = amount0_invested[j] / 10**init.token0_decimal * (price_DECIMAL / priceLower[j] - 1.) / price # < 0
                        elif price_DECIMAL > priceUpper[j]:
                            #N.B. Only approximate because amount1_invested token1 is converted to token0
                            #N.B. Using token1 does not generate OTM_loss (correctly!) for down OTM LP positions (they have amount1_invested = 0) when price is up!
                            OTM_loss_token1[j] = - amount1_invested[j] / 10**init.token1_decimal * (price_DECIMAL / priceUpper[j] - 1.) # < 0
                        else:
                            OTM_loss_token1[j] = 0.

                        OTM_loss_bp[j] = OTM_loss_token1[j] * 10000 / NUM_INVESTED_TOKEN1_LP

                        #logger.info('')
                        logger.info(network + ", LP[" + str(j) + "]" +\
                                                ": lower dist-to-bound / unwind per = " + "{:1.2f}".format((1. - priceLower[j] / price_DECIMAL) * 100) + "%" +\
                                                " / " + "{:1.2f}".format(unwind_distance_to_bound[j][0] * 100) + "%" +\
                                                ", upper dist-to-bound / unwind per = " + "{:1.2f}".format((priceUpper[j] / price_DECIMAL - 1.) * 100) + "%" +\
                                                " / " + "{:1.2f}".format(unwind_distance_to_bound[j][1] * 100) + "%" +\
                                                #"; dur = " + "{:1.1f}".format((time.time() - mint_time[j]) / 60) + " min"
                                                "; ITM dur = " + "{:1.1f}".format(ITM_duration[j] / 60) + " min" +\
                                                "; OTM dur = " + "{:1.1f}".format(OTM_duration[j] / 60) + " min" +\
                                                "; LP_position_to_init_price = " + str(LP_position_to_init_price[j]) )
                                                #", initial asset0/asset1 = " +  "{:1.3f}".format(asset_ratio_01_LP[j]) +\
                                                #", current rel asset0/asset1 = " +  "{:1.3f}".format(asset_ratio_01[j]) )
                        
                        tx_estimated_token1_rf_pl_bp[j] = LP_fees_bp[j] + RL_v3_bp[j] + OTM_loss_bp[j] #+ tx_hedge_RL_pl_bp[j] + hedge_RL_pl_bp[j]
                        #if price_DECIMAL >= priceLP[j] and j < NUM_LP:
                        #        tx_estimated_token1_rf_pl_bp[j] += RL_v3_bp[j] + OTM_loss_bp[j]
                        if liquidities[j] is not None:
                            logger.info(network + ", LP[" +str(j) + "]" +\
                                                    ": LP fees = " +  "{:1.2f}".format(LP_fees_bp[j]) + " bp" +\
                                                    ", RL_v2 = " +  "{:1.2f}".format(RL_v2_bp[j]) + " bp" +\
                                                    #", delta_RL_v2 = " +  "{:1.4f}".format(delta_RL_v2[j]) +\
                                                    ", RL_v3 = " +  "{:1.2f}".format(RL_v3_bp[j]) + " bp" +\
                                                    #", delta_RL_v3 = " +  "{:1.4f}".format(delta_RL_v3[j])+\
                                                    #", hedge RL p&l = " +  "{:1.2f}".format(tx_hedge_RL_pl_bp[j] + hedge_RL_pl_bp[j]) + " bp" +\
                                                    ", OTM loss = " +  "{:1.2f}".format(OTM_loss_bp[j]) + " bp" +\
                                                    ", estimated " + init.token1_symbol + "-ref-frame p&l = " +  "{:1.2f}".format(tx_estimated_token1_rf_pl_bp[j]) + "bp")
                    
                    j += 1
                
                logger.info(network + ", session_res_num_token0 = " +  "{:1.2f}".format(session_res_num_token0) + ' ' + init.token0_symbol +\
                                    "; tx batch amount_to_swap_token0 = " + "{:1.5f}".format(tx_batch_amount_to_swap_token0) + ' ' + init.token0_symbol +\
                                    ", amount_to_swap_token0 = " + "{:1.2f}".format(amount_to_swap_token0) + ' ' + init.token0_symbol)
                iteration_time = time.time()
                j = 0
            
                ###########################################################################
                #N.B. Unwind condition (still under 'not flag_failed_tx'; othewise 'unwind_condition' is not touched!)
                unwind_condition = (NUM_LP + 1) * [False]
                if flag_mint:
                    ##N.B. Unwind failed tx-s; use specific flags to avoid failed mint() which will trigger unwind_condition!
                    #if (not flag_increaseLiquidity) or (not flag_hedgeRL) or (not flag_decreaseLiquidity) or (not flag_collect) or (not flag_burn):
                    #    unwind_condition[j] = True

                    #N.B. swap LP
                    if flag_LP_swap:
                        #N.B. unwinding at the end!
                        if i >= main_loop_end - MAX_ATTEMPS_FAILED_TX:
                            logger.info('')
                            logger.info(network + ", UNWIND failing LP swap with tokenId = " + str(tokenIds[NUM_LP]) + " because of the end of main loop!")
                            count_LP_swap_attempts += 1
                            #N.B. If not flag_LP_swap, conventional swap is not triggered!
                            #flag_LP_swap = False
                            unwind_condition[NUM_LP] = True

                        #N.B. Need lower price!
                        #N.B. Can use amount_to_swap_token0 sign despite the fact that this is not immediately after amount_to_swap_token0 was set up:
                        #N.B. because there is only one LP swap and conventional swap & LP swap can not co-exist: amount_to_swap_token0 has not changed!
                        if amount_to_swap_token0 > 0:
                            #N.B. Unwinding successfully LP swap (price is small enough): token0 is converted into token1
                            if priceLower[NUM_LP] is not None and 1. - priceLower[NUM_LP] / price_DECIMAL <= 0.: #- LP_SWAP_DISTANCE_TO_BOUND_PER / 100:
                                logger.info('')
                                logger.info(network + ", UNWIND successful LP swap with tokenId = " + str(tokenIds[NUM_LP]) + " because price = " + str(price) +\
                                    " is LP_SWAP_DISTANCE_TO_BOUND_PER / 100 = " + str(LP_SWAP_DISTANCE_TO_BOUND_PER / 100) + "%" +\
                                    " below priceLower[NUM_LP] = " + str(priceLower[NUM_LP] / 10**init.token0_decimal * 10**init.token1_decimal) + ". flagLP_SWAP = False.")
                                flag_LP_swap, amount_to_swap_token0 = False, 0.
                                unwind_condition[NUM_LP] = True

                            #N.B. unwinding failed LP swap: price is too large!
                            if priceUpper[NUM_LP] is not None and priceUpper[NUM_LP] / price_DECIMAL - 1. <= - LP_SWAP_UNWIND_DISTANCE_PER / 100:
                                count_LP_swap_attempts += 1
                                logger.info('')
                                logger.info(network + ", UNWIND failing LP swap with tokenId = " + str(tokenIds[NUM_LP]) + " because price = " + str(price) +\
                                    " is LP_SWAP_UNWIND_DISTANCE_PER / 100 = " + str(LP_SWAP_UNWIND_DISTANCE_PER / 100) + "%" +\
                                    " above priceUpper[NUM_LP] = " + str(priceUpper[NUM_LP] / 10**init.token0_decimal * 10**init.token1_decimal) +\
                                    "; count_LP_swap_attempts = " + str(count_LP_swap_attempts))
                                unwind_condition[NUM_LP] = True
                              
                        #N.B. Need higher price!
                        #N.B. Can use amount_to_swap_token0 sign despite the fact that this is not immediately after amount_to_swap_token0 was set up:
                        #N.B. because there is only one LP swap and conventional swap & LP swap can not co-exist: amount_to_swap_token0 has not changed!
                        if amount_to_swap_token0 < 0:
                            #N.B. Unwinding successfully LP swap (price is big enough):  token1 is converted into token0
                            if priceUpper[NUM_LP] is not None and priceUpper[NUM_LP] / price_DECIMAL - 1. <= 0.: #- LP_SWAP_DISTANCE_TO_BOUND_PER / 100:
                                logger.info('')
                                logger.info(network + ", UNWIND successful LP swap with tokenId = " + str(tokenIds[NUM_LP]) + " because price = " + str(price) +\
                                    " is LP_SWAP_DISTANCE_TO_BOUND_PER / 100 = " + str(LP_SWAP_DISTANCE_TO_BOUND_PER / 100) + "%" +\
                                    " above priceUpper[NUM_LP] = " + str(priceUpper[NUM_LP] / 10**init.token0_decimal * 10**init.token1_decimal) + ". flagLP_SWAP = False.")
                                flag_LP_swap, amount_to_swap_token0 = False, 0.
                                unwind_condition[NUM_LP] = True

                            #N.B. unwinding failed LP swap: price is too small!
                            if priceLower[NUM_LP] is not None and 1. - priceLower[NUM_LP] / price_DECIMAL <= -LP_SWAP_UNWIND_DISTANCE_PER /100:
                                count_LP_swap_attempts += 1
                                logger.info('')
                                logger.info(network + ", UNWIND failing LP swap with tokenId = " + str(tokenIds[NUM_LP]) + " because price = " + str(price) +\
                                    " is LP_SWAP_UNWIND_DISTANCE_PER / 100 = " + str(LP_SWAP_UNWIND_DISTANCE_PER / 100) + "%" +\
                                    " below priceLower[NUM_LP] = " + str(priceLower[NUM_LP] / 10**init.token0_decimal * 10**init.token1_decimal) +\
                                    "; count_LP_swap_attempts = " + str(count_LP_swap_attempts))
                                unwind_condition[NUM_LP] = True
                                
                    #N.B. non-swap LP-s 
                    #N.B. still under 'not flag_failed_tx'; othewise 'unwind_condition' is not touched!

                    #N.B. Unwind non-swap LP-s during quiet hours
                    if (int(time.strftime('%w', time.localtime())) != 6 and int(time.strftime('%w', time.localtime())) != 0 and\
                        ((int(time.strftime('%H', time.localtime())) >= QUIET_HOURS_START[0] and int(time.strftime('%H', time.localtime())) < QUIET_HOURS_END[0]) or\
                        (int(time.strftime('%H', time.localtime())) >= QUIET_HOURS_START[1] and int(time.strftime('%H', time.localtime())) < QUIET_HOURS_END[1]))):
                        unwind_condition[:NUM_LP] = NUM_LP * [True]
                        logger.info(network + ", UNWIND all non-swap LP positions during quiet hours!")
                    else:
                        j = 0
                        while j < NUM_LP:
                            #N.B. raise unwind_condition only if there is an actual LP j-th position!
                            #N.B. Combining this condition with j < NUM_LP, results in an infinite loop!
                            if tokenIds[j] is not None and priceLower[j] is not None and priceUpper[j] is not None and priceLP[j] is not None:

                                #N.B. If ITM
                                if price_DECIMAL >= priceLower[j] and price_DECIMAL <= priceUpper[j]:
                                    #N.B. Price volatility too large
                                    if price_mad > PRICE_MAD[-1]:
                                        logger.info('')
                                        logger.info(network + ", UNWIND LP[" + str(j) + "] position with tokenId = " + str(tokenIds[j]) +\
                                                    " because price_mad = " + str(price_mad) + " > PRICE_MAD[-1] = " + str(PRICE_MAD[-1]))
                                        unwind_condition[j] = True
                                        session_count_unwind_max_price_mad += 1

                                    #N.B. token1 signed swap quantity too large but only for the LP position before last or before tokenIds = None
                                    if EVENT_LOGS and (j + 1 == NUM_LP or tokenIds[j + 1] == None) and\
                                            LP_position_to_init_price[j] * signed_token1_quantity * price / pool_liquidity_list[-1]  *\
                                            10 ** (0.5 * (init.token0_decimal + init.token1_decimal)) * 10000 > MAX_UNWIND_TOKEN1_VALUE_TO_POOL_LIQUIDITY_BP:
                                        logger.info('')
                                        logger.info(network + ", UNWIND LP[" + str(j) + "] position with tokenId = " + str(tokenIds[j]) +\
                                                            " because LP_position_to_init_price[j] * signed_token1_quantity * price / pool_liquidity * 10000 = " +\
                                                            "{:1.4f}".format(LP_position_to_init_price[j] * signed_token1_quantity * price / pool_liquidity_list[-1] *\
                                                                    10 ** (0.5 * (init.token0_decimal + init.token1_decimal)) * 10000) +\
                                                            " > MAX_UNWIND_TOKEN1_VALUE_TO_POOL_LIQUIDITY_BP = " + str(MAX_UNWIND_TOKEN1_VALUE_TO_POOL_LIQUIDITY_BP))
                                        unwind_condition[j] = True
                                        session_count_unwind_signed_quantity[j] += 1
                        
                                    #N.B. Pool liquidity too small
                                    if EVENT_LOGS and pool_liquidity_list[-1] < pool_liquidity_LP * MIN_POOL_LIQUIDITY_PER[-1] / 100:
                                        logger.info('')
                                        logger.info(network + ", UNWIND LP[" + str(j) + "] position with tokenId = " + str(tokenIds[j]) +\
                                                    " because pool liq = " +\
                                                    "{:1.0f}".format(pool_liquidity_list[-1] / 10 ** (0.5 * (init.token0_decimal + init.token1_decimal))) +\
                                                    " < initiation LP pool liq * threshold = " +\
                                                    "{:1.0f}".format(pool_liquidity_LP  / 10 ** (0.5 * (init.token0_decimal + init.token1_decimal)) * MIN_POOL_LIQUIDITY_PER[-1] / 100))
                                        unwind_condition[j] = True
                                        session_count_unwind_pool_liq += 1
                                
                                ##N.B.  # of active LP-s
                                #if len([t for t in tokenIds[:NUM_LP] if t is not None]) == 1:
                                #    logger.info('')
                                #    logger.info(network + ", UNWIND the remaining LP position with tokenId = " + str(tokenIds[j]) +\
                                #       " because LP[" + str(j) + "] is the only non-swap LP!")
                                #    unwind_condition[j] = True

                                #N.B. Stop-profit / stop-loss
                                if tx_estimated_token1_rf_pl_bp[j]  < - STOP_LOSS_BP: 
                                    #+ tx_hedge_RL_pl_bp[j] + hedge_RL_pl_bp[j] or\
                                    # + tx_hedge_RL_pl_bp[j] + hedge_RL_pl_bp[j]:
                                    #logger.info('')
                                    logger.info(network + ", UNWIND LP[" + str(j) + "] position with tokenId = " + str(tokenIds[j]) +\
                                       " because tx estimated p&l < - " + str(STOP_LOSS_BP) + " bp")
                                    unwind_condition[j] = True
                                    session_count_unwind_stop_loss += 1
                                if tx_estimated_token1_rf_pl_bp[j] > STOP_PROFIT_BP: 
                                    #+ tx_hedge_RL_pl_bp[j] + hedge_RL_pl_bp[j] or\
                                    # + tx_hedge_RL_pl_bp[j] + hedge_RL_pl_bp[j]:
                                    #logger.info('')
                                    logger.info(network + ", UNWIND LP[" + str(j) + "] position with tokenId = " + str(tokenIds[j]) +\
                                       "  because tx estimated p&l bp or > " + str(STOP_PROFIT_BP) + " bp")
                                    unwind_condition[j] = True
                                    session_count_unwind_stop_profit += 1
                                
                                #N.B. Unwind distance to bound reached
                                if 1. - priceLower[j] / price_DECIMAL <= unwind_distance_to_bound[j][0]:
                                    #asset_ratio_01 <= UNWIND_ASSET_RATIO_PER / 100 or asset_ratio_01 >= 1. / (UNWIND_ASSET_RATIO_PER / 100)
                                    logger.info('')
                                    logger.info(network + ", UNWIND LP[" + str(j) + "] position with tokenId = " + str(tokenIds[j]) +\
                                        "  because lower unwind_distance_to_bound[" + str(j) + "] = " + str(unwind_distance_to_bound[j][0]) + " is reached!")
                                    unwind_condition[j] = True
                                    #N.B. Flip the position of LP to price
                                    if amount1_invested[j] == 0.:
                                        session_count_unwind_distance_rebal[j] += 1
                                        if CHANGE_LP_POSITION_TO_INIT_PRICE:
                                            LP_position_to_init_price[j] *= -1
                                        session_count_unwind_distance_nonrebal[j] += 1
                                if priceUpper[j] / price_DECIMAL - 1. <= unwind_distance_to_bound[j][1]:
                                    #asset_ratio_01 <= UNWIND_ASSET_RATIO_PER / 100 or asset_ratio_01 >= 1. / (UNWIND_ASSET_RATIO_PER / 100)
                                    logger.info('')
                                    logger.info(network + ", UNWIND LP[" + str(j) + "] position with tokenId = " + str(tokenIds[j]) +\
                                            "  because upper unwind_distance_to_bound[" + str(j) + "] = " + str(unwind_distance_to_bound[j][1]) + " is reached!")
                                    unwind_condition[j] = True
                                    #N.B. Flip the position of LP to price
                                    if amount0_invested[j] == 0.:
                                        session_count_unwind_distance_rebal[j] += 1
                                        if CHANGE_LP_POSITION_TO_INIT_PRICE:
                                            LP_position_to_init_price[j] *= -1
                                    else:
                                        session_count_unwind_distance_nonrebal[j] += 1
                                                            
                                #N.B. Swap flow threshold reached
                                if swap_volume_token1[j] > MIN_UNWIND_SWAP_VOLUME_TOKEN1 and swap_flow_token1[j] > MIN_UNWIND_SWAP_FLOW_PER / 100 * swap_volume_token1[j]:
                                    logger.info('')
                                    logger.info(network + ", UNWIND LP[" + str(j) + "] position with tokenId = " + str(tokenIds[j]) +\
                                            "  because swap_volume_token1[" + str(j) + "] = " + "{:1.0f}".format(swap_volume_token1[j]) +\
                                                " > MIN_UNWIND_SWAP_VOLUME_TOKEN1 = " + str(MIN_UNWIND_SWAP_VOLUME_TOKEN1) +\
                                                " and swap_flow[" + str(j) + "] / swap_volume[" + str(j) + "]= " +\
                                                "{:1.2f}".format(swap_flow_token1[j] / swap_volume_token1[j] * 100) + "%" +\
                                                " > MIN_UNWIND_SWAP_FLOW_PER = " + str(MIN_UNWIND_SWAP_FLOW_PER) + "%")
                                    logger.info('')
                                    unwind_condition[j] = True
                                    session_count_unwind_flow += 1

                            j += 1

                    #N.B. Last iterations reserved for unwinding non-LP swap tx-s
                    if i >= int(RUNTIME_SEC / DELAY_LOOP_SEC) - NUM_LP * MAX_ATTEMPS_FAILED_TX:
                        logger.info('')
                        logger.info(network + ", UNWIND all non-swap LP positions because end-of-runtime is reached: i = " +\
                                    str(int(RUNTIME_SEC / DELAY_LOOP_SEC) - NUM_LP * MAX_ATTEMPS_FAILED_TX))
                        unwind_condition[:NUM_LP] = NUM_LP * [True]
            
                    if TEST:
                        unwind_condition = [unwind_condition[j] or i % 2 == 1 for j in range(NUM_LP)] + [False]

            ###########################################################################
            #N.B. decreaseLiquidity(), collect(), burn() (only if unwind_condition[j])
            if flag_mint:
                if not flag_failed_tx:
                    j = 0
                while j <= NUM_LP:
                    #if j == NUM_LP and not flag_LP_swap: #N.B. When j += 1, this line is hit but if unwind_condition[NUM_LP] == False, nothing will happen!
                    #    j = 0
                    #    break
                    if unwind_condition[j] and tokenIds[j] is not None:

                        #############################
                        #4. decreaseLiquidity()
                        #N.B. If decreaseLiquidity() tx fails, run only the failed decreaseLiquidity() in the next iteration!
                        #time.sleep(1)
                        if flag_increaseLiquidity and flag_hedgeRL and flag_collect and flag_burn:
                        
                            if count_failed_tx < MAX_ATTEMPS_FAILED_TX:
                                #N.B. If decreaseLiquidity() tx fails, run only the failed decreaseLiquidity() in the next main loop iteration!
                                #N.B. Passing nonce speeds up execution
                                result = decreaseLiquidity(network, tokenIds[j], liquidities[j],\
                                                max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas, \
                                                            address=Address, private_key=privateKey, init=init, nonce=nonce)
                                if isinstance(result, tuple):
                                    gas_fee, amount0, amount1, nonce = result
                                    session_gas_fees[j] = tuple(map(sum, zip(session_gas_fees[j], (0., gas_fee, 0., 0.) )))
                                    flag_failed_tx, flag_decreaseLiquidity = False, True
                                    count_failed_tx = 0
                                    liquidities[j] = None
                                    #unwind_condition[j] = False #N.B. unwind_condition[j] = True is used below in log reporting for all NUM_LP trades!
                                    #hedge_RL = HEDGE_RL
                                    decreaseLiquidity_time[j] = time.time()
                                else:
                                    nonce = None
                                    if not result:
                                        #N.B. nonce=None triggers web3 getting a nonce
                                        flag_failed_tx, flag_decreaseLiquidity, nonce = True, False, None
                                        count_failed_tx += 1
                                        logger.error(network + ", decreaseLiquidity() failed for LP[" + str(j) + "], tokenId " + str(tokenIds[j]) +\
                                                    ", count_failed_tx = " + str(count_failed_tx))
                                        break #N.B. Break the NUM_LP-loop and continue with code
                            else:
                                logger.info('')
                                logger.error(network + ', decreaseLiquidity() for LP[' + str(j) + '] failed MAX_ATTEMPS_FAILED_TX = ' + str(MAX_ATTEMPS_FAILED_TX) + ' times, stop main()!')
                                current_LP_positions(network, address=Address, init=init) 
                                #logger.info(network + ", session p&l = " + str(session_token0_rf_pl_token1[j]) + ' ' + init.token1_symbol +\
                                #                        ", " + "{:1.2f}".format(session_token0_rf_pl_bp[j]) + " bp")
                                logger.info(network + ", session: " + init.token1_symbol + "-ref-frame p&l w/o swaps = " +\
                                    "{:1.4f}".format(sum(session_token1_rf_pl_token1)) + ' ' + init.token1_symbol +\
                                    " or " + "{:1.1f}".format(sum(session_token1_rf_pl_bp)) + " bp" +\
                                    " = " + str(["{:1.1f}".format(s) for s in session_token1_rf_pl_bp]) + " bp" +\
                                                ", swap cost=" + "{:1.2f}".format(session_swap_cost_bp) + " bp" +\
                                    ", token0 collected in " + init.token1_symbol + "-ref-frame p&l = " +\
                                            "{:1.4f}".format(session_token0_pl_token1_rf_token1) + ' ' + init.token1_symbol + ' or '+\
                                            "{:1.2f}".format(session_token0_pl_token1_rf_token1 / NUM_INVESTED_TOKEN1_LP * 10000) + ' bp')
                                logger.info(network + ", session: gas fees = " + "{:1.2f}".format(sum([sum(s) for s in session_gas_fees])) + ' ' + init.network_coin_symbol +\
                                  " = [" + str(["{:1.2f}".format(s[0]) for s in session_gas_fees[:-1]]) +\
                                  ", " + str(["{:1.2f}".format(s[1]) for s in session_gas_fees[:-1]]) +\
                                  ", " + str(["{:1.2f}".format(s[2]) for s in session_gas_fees[:-1]]) +\
                                  ", " + str(["{:1.2f}".format(s[3]) for s in session_gas_fees[:-1]]) +\
                                  ", " + "{:1.2f}".format(session_gas_fees[-1][0]) + '] ' + init.network_coin_symbol)
                                logger.info(network + ", session" +\
                                    ": LP fees = " + str(["{:1.1f}".format(s) for s in session_LP_fees_bp]) + " bp" +\
                                    ", RL = " + str(["{:1.1f}".format(s) for s in session_RL_bp]) + " bp" +\
                                    ", OTM loss = " + str(["{:1.1f}".format(s) for s in session_OTM_loss_bp]) + " bp" )
                                    #", iv) hedge RL=" + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
                                logger.info(network + ", session" +  ": res num token0 = " + str(session_res_num_token0) + ", res num token1 = " + str(session_res_num_token1) )
                                logger.info(network + ", session" +  ": invested " + "{:1.1f}".format(sum(s[0] for s in session_invested)) + " = " + str(["{:1.1f}".format(s[0]) for s in session_invested]) + ' ' + init.token0_symbol +\
                                                      ", collected " + "{:1.1f}".format(sum(s[0] for s in session_collected)) + " = "  + str(["{:1.1f}".format(s[0]) for s in session_collected]) + ' ' + init.token0_symbol )
                                logger.info(network + ", session" +  ": invested " + "{:1.4f}".format(sum(s[1] for s in session_invested)) + " = "  + str(["{:1.4f}".format(s[1]) for s in session_invested]) + ' ' + init.token1_symbol +\
                                                      ", collected " + "{:1.4f}".format(sum(s[1] for s in session_collected)) + " = "  + str(["{:1.4f}".format(s[1]) for s in session_collected]) + ' ' + init.token1_symbol )
                                logger.info(network + ', session' +\
                                ': count LP=' + str(sum(session_count_LP[:NUM_LP])) +\
                                ', count LP swaps=' + str(session_count_LP[NUM_LP]) +\
                                ', count LP swaps failed=' + str(session_count_LP_swap_failed) +\
                                ', count non-LP swaps=' + str(session_count_non_LP_swaps) +\
                                ', count unwind flow=' + str(session_count_unwind_flow) +\
                                ', count unwind stop profit=' + str(session_count_unwind_stop_profit) +\
                                ', count unwind stop loss=' + str(session_count_unwind_stop_loss) +\
                                ', count unwind pool liq=' + str(session_count_unwind_pool_liq) +\
                                ', count unwind price_mad=' + str(session_count_unwind_max_price_mad) ) #+\
                                #', count hedge RL = ' + str(session_count_hedge_RL) )
                                logger.info(network + ', session' +\
                                ': count unwind distance rebalance=' + str(sum(session_count_unwind_distance_rebal)) + "=" + str(session_count_unwind_distance_rebal) +\
                                ', count unwind distance non-rebalance=' + str(sum(session_count_unwind_distance_nonrebal)) + "=" + str(session_count_unwind_distance_nonrebal) +\
                                ', count unwind signed q=' + str(sum(session_count_unwind_signed_quantity)) + "=" + str(session_count_unwind_signed_quantity) )
                                logger.info(network + ", session: dur=" + "{:1.1f}".format((time.time() - start_time) / 3600) + " h" +\
                                    #"; avg LP dur=" + str(["{:1.1f}".format(s / 60) for s in session_avg_LP_duration]) + " min" +\
                                    "; avg LP ITM dur=" + str(["{:1.1f}".format(s / 60) for s in session_avg_ITM_duration]) + " min" +\
                                    "; avg LP OTM dur=" + str(["{:1.1f}".format(s / 60) for s in session_avg_OTM_duration]) + " min" +\
                                    ", max price_mad = " + "{:1.5f}".format(max_price_mad) )
                                logger.info('network, END session')
                                return False

                        #####################################################################
                        #5. collect()
                        #N.B. If collect() tx fails, run only the failed collect() in the next iteration!
                        #time.sleep(1)
                        if flag_increaseLiquidity and flag_hedgeRL and flag_decreaseLiquidity and flag_burn:
                            if count_failed_tx < MAX_ATTEMPS_FAILED_TX:
                                #N.B. If collect() tx fails, run only the failed collect() in the next main loop iteration!
                                #N.B. Passing nonce speeds up execution                 
                                result = collect(tokenIds[j], network, max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas, \
                                                    address=Address, private_key=privateKey, init=init, nonce=nonce)
                                if isinstance(result, tuple):
                                    gas_fee, amount0, amount1, nonce = result
                                    blockNumber_init, price_init = block_num, price #if signed_token1_quantity > 0 else -price
                                    session_gas_fees[j] = tuple(map(sum, zip(session_gas_fees[j], (0., 0., gas_fee, 0.) )))
                            
                                    #N.B. tx
                                    session_count_LP[j] += 1
                                    tx_collected[j] = (amount0 / 10**init.token0_decimal, amount1 / 10**init.token1_decimal)
                                    
                                    tx_collected_token1[j] = amount0 / 10**init.token0_decimal / price + amount1 / 10**init.token1_decimal
                                    tx_token0_rf_pl_token1[j] = tx_collected_token1[j] - tx_invested_token1[j]
                                    tx_token0_rf_pl_bp[j] = (tx_collected_token1[j] - tx_invested_token1[j]) / sum(tx_invested_token1) * 10000
                                    tx_token1_rf_invested_token1[j] = amount0_invested[j] / 10**init.token0_decimal / price + amount1_invested[j] / 10**init.token1_decimal
                                    tx_token1_rf_pl_token1[j] = tx_collected_token1[j] - tx_token1_rf_invested_token1[j]
                                    tx_token1_rf_pl_bp[j] = tx_token1_rf_pl_token1[j] / NUM_INVESTED_TOKEN1_LP * 10000
                                    #N.B. tx hedge RL P&L is a sum tx_hedge_RL_pl_bp + hedge_RL_pl_bp:  hedge_RL_pl_bp measures hedge RL  P&L only from the last hedge!
                                    #tx_token1_rf_pl_bp[j] += tx_hedge_RL_pl_bp[j] + hedge_RL_pl_bp[j]
                                    duration[j] = decreaseLiquidity_time[j] - mint_time[j]
                                    
                                    #N.B. session
                                    session_token0_rf_pl_token1[j] += tx_token0_rf_pl_token1[j]
                                    session_token0_rf_pl_bp[j] +=  tx_token0_rf_pl_bp[j]
                                    session_token1_rf_pl_token1[j] += tx_token1_rf_pl_token1[j]
                                    session_token1_rf_pl_bp[j] += tx_token1_rf_pl_bp[j]
                                    #session_hedge_RL_pl_bp += tx_hedge_RL_pl_bp[j] + hedge_RL_pl_bp[j]
                                    session_collected[j] = tuple(map(sum, zip(session_collected[j], (amount0 / 10**init.token0_decimal, amount1 / 10**init.token1_decimal) )))
                                    session_LP_fees_bp[j] += LP_fees_bp[j]
                                    session_RL_bp[j] += RL_v3_bp[j]
                                    session_OTM_loss_bp[j] += OTM_loss_bp[j]
                                    session_avg_LP_duration[j] = (session_avg_LP_duration[j] * (session_count_LP[j] - 1) +\
                                                                            (decreaseLiquidity_time[j] - mint_time[j]) ) / session_count_LP[j]
                                    session_avg_ITM_duration[j] = (session_avg_ITM_duration[j] * (session_count_LP[j] - 1) +\
                                                                ITM_duration[j]) / session_count_LP[j]
                                    session_avg_OTM_duration[j] = (session_avg_OTM_duration[j] * (session_count_LP[j] - 1) +\
                                                                OTM_duration[j]) / session_count_LP[j]
                                    
                                    if j < NUM_LP:
                                        #N.B. tx_batch_amount_to_swap_token0: swap tx_batch_amount_to_swap_token0 token0 into token1 if > 0 or -tx_batch_amount_to_swap_token0 / price token1 into token0 if < 0
                                        #N.B. Use tx_batch_amount_to_swap_token0 instead of tx_batch_amount_to_swap_token1 because price can change!
                                        tx_batch_amount_to_swap_token0 += (amount0 - amount0_invested[j]) / 10**init.token0_decimal
                                        tx_res_num_token0,  tx_res_num_token1 = (amount0 - amount0_invested[j]) / 10**init.token0_decimal, (amount1 - amount1_invested[j]) / 10**init.token1_decimal
                                        session_token0_price_collected.append((amount0 / 10**init.token0_decimal, price))
                                        session_token1_price_collected.append((amount1 / 10**init.token1_decimal, price))
   
                                        #N.B. tx P&L log report
                                        #logger.info('')
                                        #logger.info(network + ", LP[" + str(j) + "] tx w/o possible swap: p&l = " +\
                                        #                str(tx_token0_rf_pl_token1[j]) + ' ' + init.token1_symbol +\
                                        #                ", " + "{:1.2f}".format(tx_token0_rf_pl_bp[j]) + " bp" +\
                                        #                ", invested = " + str(tx_invested[j]) +\
                                        #                ", collected = " + str(tx_collected[j]))
                                        logger.info(network + ", LP[" + str(j) + "] tx w/o a possible swap: " + init.token1_symbol + "-ref-frame p&l = " +\
                                                        "{:1.4f}".format(tx_token1_rf_pl_token1[j]) + ' ' + init.token1_symbol +\
                                                        " or " + "{:1.2f}".format(tx_token1_rf_pl_bp[j]) + " bp" +\
                                                        #", iii) hedge RL=" + "{:1.2f}".format(tx_hedge_RL_pl_bp[j] + hedge_RL_pl_bp[j]) + " bp" +\
                                                        #"; num hedge RL=" + str(tx_count_hedge_RL[j]) +\
                                                        #"; dur=" + "{:1.1f}".format(duration[j] / 60) + " min" +\
                                                        "; ITM dur=" + "{:1.1f}".format(ITM_duration[j] / 60) + " min" +\
                                                        "; OTM dur=" + "{:1.1f}".format(OTM_duration[j] / 60) + " min" +\
                                                        "; tx batch amount_to_swap_token0=" + "{:1.5f}".format(tx_batch_amount_to_swap_token0) + ' ' + init.token0_symbol )
                                                        #"; tx swap flow token1 = " + "{:1.1f}".format(swap_flow_token1))

                                        #N.B. session
                                        session_res_num_token0 += tx_res_num_token0
                                        session_res_num_token1 += tx_res_num_token1

                                    elif j == NUM_LP: #N.B. flag_LP_swap = False above!
                                        #N.B. amount0 > 0, amount1 ~ 0 or vice versa!
                                        session_token0_price_collected.append(((amount0 - amount0_invested[j]) / 10**init.token0_decimal, price))
                                        session_token1_price_collected.append(((amount1 - amount1_invested[j]) / 10**init.token1_decimal, price))

                                        logger.info(network + ", LP swap tx for LP[" + str(j) + "]: " + init.token1_symbol + "-ref-frame p&l = " +\
                                                "{:1.4f}".format(session_token1_rf_pl_token1[j]) + ' ' + init.token1_symbol +\
                                                " or " + "{:1.2f}".format(tx_token1_rf_pl_bp[j]) + " bp" +\
                                                #"; dur=" + "{:1.1f}".format(duration[j] / 60) + " min" +\
                                                "; ITM dur=" + "{:1.1f}".format(ITM_duration[j] / 60) + " min" +\
                                                "; OTM dur=" + "{:1.1f}".format(OTM_duration[j] / 60) + " min" +\
                                                ", session swap cost=" + "{:1.2f}".format(session_swap_cost_bp) + " bp" )
               
                                    #N.B. session P&L report
                                    #logger.info(network + ", session (w/o possible) swap p&l= " + str(session_token0_rf_pl_token1[j]) + ' ' + init.token1_symbol +\
                                    #                       ", " + "{:1.2f}".format(session_token0_rf_pl_bp[j]) + " bp")
                                    logger.info(network + ", session for LP[" + str(j) + "]: " + init.token1_symbol + "-ref-frame p&l = " +\
                                            "{:1.4f}".format(session_token1_rf_pl_token1[j]) + ' ' + init.token1_symbol +\
                                            " or " + "{:1.2f}".format(session_token1_rf_pl_bp[j]) + " bp"  )
                                    logger.info(network + ", session" +\
                                            ": LP fees = " + "{:1.2f}".format(session_LP_fees_bp[j]) + " bp" +\
                                            ", RL = " + "{:1.2f}".format(session_RL_bp[j]) + " bp" +\
                                            ", OTM loss = " + "{:1.2f}".format(session_OTM_loss_bp[j]) + " bp"  +\
                                            #"; avg LP dur=" + "{:1.1f}".format(session_avg_LP_duration[j] / 60) + " min" +\
                                            "; avg LP ITM dur=" + "{:1.1f}".format(session_avg_ITM_duration[j] / 60) + " min" +\
                                            "; avg LP OTM dur=" + "{:1.1f}".format(session_avg_OTM_duration[j] / 60) + " min" )
                                            #", iv) hedge RL=" + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
                                
                                    #logger.info(network + ", session" +\
                                    #                ": LP fees  for LP[" + str(j) + "] = " + "{:1.2f}".format(session_LP_fees_bp[j]) + " bp" +\
                                    #                ", RL  for LP[" + str(j) + "] = " + "{:1.2f}".format(session_RL_bp[j]) + " bp")
                                    tickLower[j], priceLower[j], tickUpper[j], priceUpper[j], priceLP[j] = None, None, None, None, None
                                    amount0_invested[j], amount1_invested[j] = None, None
                                    flag_failed_tx, flag_collect = False, True
                                    count_failed_tx = 0
                                else:
                                    if not result:
                                        nonce = None
                                    #N.B. nonce=None triggers web3 getting a nonce
                                    flag_failed_tx, flag_collect, nonce = True, False, None
                                    count_failed_tx += 1
                                    logger.error(network + ", collect() failed for LP[" + str(j) + "], tokenId " + str(tokenIds[j]) +\
                                                    ", count_failed_tx = " + str(count_failed_tx))
                                    break #N.B. Break the NUM_LP-loop and continue with code
                            else:
                                logger.info('')
                                logger.error(network + ', collect() for LP[' + str(j) + '] failed MAX_ATTEMPS_FAILED_TX = ' + str(MAX_ATTEMPS_FAILED_TX) +  ' times, stop main()!')
                                current_LP_positions(network, address=Address, init=init) 
                                #logger.info(network + ", session p&l = " + str(session_token0_rf_pl_token1[j]) + ' ' + init.token1_symbol +\
                                #                    ", " + "{:1.2f}".format(session_token0_rf_pl_bp[j]) + " bp")
                                logger.info(network + ", session: " + init.token1_symbol + "-ref-frame p&l w/o swaps = " +\
                                    "{:1.4f}".format(sum(session_token1_rf_pl_token1)) + ' ' + init.token1_symbol +\
                                    " or " + "{:1.1f}".format(sum(session_token1_rf_pl_bp)) + " bp" +\
                                    " = " + str(["{:1.1f}".format(s) for s in session_token1_rf_pl_bp])+ " bp" +\
                                    ", swap cost=" + "{:1.2f}".format(session_swap_cost_bp) + " bp" +\
                                    ", token0 collected in " + init.token1_symbol + "-ref-frame p&l = " +\
                                            "{:1.4f}".format(session_token0_pl_token1_rf_token1) + ' ' + init.token1_symbol + ' or '+\
                                            "{:1.2f}".format(session_token0_pl_token1_rf_token1 / NUM_INVESTED_TOKEN1_LP * 10000) + ' bp')
                                logger.info(network + ", session: gas fees = " + "{:1.2f}".format(sum([sum(s) for s in session_gas_fees])) + ' ' + init.network_coin_symbol +\
                                  " = [" + str(["{:1.2f}".format(s[0]) for s in session_gas_fees[:-1]]) +\
                                  ", " + str(["{:1.2f}".format(s[1]) for s in session_gas_fees[:-1]]) +\
                                  ", " + str(["{:1.2f}".format(s[2]) for s in session_gas_fees[:-1]]) +\
                                  ", " + str(["{:1.2f}".format(s[3]) for s in session_gas_fees[:-1]]) +\
                                  ", " + "{:1.2f}".format(session_gas_fees[-1][0]) + '] ' + init.network_coin_symbol)
                                logger.info(network + ", session" +\
                                    ": LP fees = " + str(["{:1.1f}".format(s) for s in session_LP_fees_bp]) + " bp" +\
                                    ", RL = " + str(["{:1.1f}".format(s) for s in session_RL_bp]) + " bp" +\
                                    ", OTM loss = " + str(["{:1.1f}".format(s) for s in session_OTM_loss_bp]) + " bp"  )
                                    #", iv) hedge RL=" + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
                                logger.info(network + ", session" +  ": res num token0 = " + str(session_res_num_token0) + ", res num token1 = " + str(session_res_num_token1) )
                                logger.info(network + ", session" +  ": invested " + "{:1.1f}".format(sum(s[0] for s in session_invested)) + " = " + str(["{:1.1f}".format(s[0]) for s in session_invested]) + ' ' + init.token0_symbol +\
                                                      ", collected " + "{:1.1f}".format(sum(s[0] for s in session_collected)) + " = "  + str(["{:1.1f}".format(s[0]) for s in session_collected]) + ' ' + init.token0_symbol )
                                logger.info(network + ", session" +  ": invested " + "{:1.4f}".format(sum(s[1] for s in session_invested)) + " = "  + str(["{:1.4f}".format(s[1]) for s in session_invested]) + ' ' + init.token1_symbol +\
                                                      ", collected " + "{:1.4f}".format(sum(s[1] for s in session_collected)) + " = "  + str(["{:1.4f}".format(s[1]) for s in session_collected]) + ' ' + init.token1_symbol )
                                logger.info(network + ', session' +\
                                ': count LP=' + str(sum(session_count_LP[:NUM_LP])) +\
                                ', count LP swaps=' + str(session_count_LP[NUM_LP]) +\
                                ', count LP swaps failed=' + str(session_count_LP_swap_failed) +\
                                ', count non-LP swaps=' + str(session_count_non_LP_swaps) +\
                                ', count unwind flow=' + str(session_count_unwind_flow) +\
                                ', count unwind stop profit=' + str(session_count_unwind_stop_profit) +\
                                ', count unwind stop loss=' + str(session_count_unwind_stop_loss) +\
                                ', count unwind pool liq=' + str(session_count_unwind_pool_liq) +\
                                ', count unwind price_mad=' + str(session_count_unwind_max_price_mad) ) #+\
                                #', count hedge RL = ' + str(session_count_hedge_RL) )
                                logger.info(network + ', session' +\
                                ': count unwind distance rebalance=' + str(sum(session_count_unwind_distance_rebal)) + "=" + str(session_count_unwind_distance_rebal) +\
                                ', count unwind distance non-rebalance=' + str(sum(session_count_unwind_distance_nonrebal)) + "=" + str(session_count_unwind_distance_nonrebal) +\
                                ', count unwind signed q=' + str(sum(session_count_unwind_signed_quantity)) + "=" + str(session_count_unwind_signed_quantity) )
                                logger.info(network + ", session: dur=" + "{:1.1f}".format((time.time() - start_time) / 3600) + " h" +\
                                   #"; avg LP dur=" + str(["{:1.1f}".format(s / 60) for s in session_avg_LP_duration]) + " min" +\
                                   "; avg LP ITM dur=" + str(["{:1.1f}".format(s / 60) for s in session_avg_ITM_duration]) + " min" +\
                                   "; avg LP OTM dur=" + str(["{:1.1f}".format(s / 60) for s in session_avg_OTM_duration]) + " min" +\
                                   "; max price_mad = " + "{:1.5f}".format(max_price_mad)  )
                                logger.info('network, END session')
                                return False
             
                        ###################################################
                        #6. burn(): otherwise the NFT (corresponding to the LP) stays in the wallet & can be seen running current_LP_positions()
                        #N.B. From the docs: "The token must have 0 liquidity and all tokens must be collected first.": https://docs.uniswap.org/protocol/reference/periphery/NonfungiblePositionManager
                        #N.B. If tokens not collected first, burn() tx produces error on Etherscan "Fail with error 'Not cleared'"
                        #N.B. If burn() tx fails, run only burn() in the next iteration!
                        #N.B. swap() is after burn() (if burn() fails, swap() is delayed!) because swap() does not depend on unwind_condition
                        #time.sleep(1)
                        if flag_increaseLiquidity and flag_hedgeRL and flag_decreaseLiquidity and flag_collect:
                            #N.B. If burn() tx fails, run only the failed burn() in the next main loop iteration!
                            #N.B. Passing nonce speeds up execution
                            if count_failed_tx < MAX_ATTEMPS_FAILED_TX:                        
                                result = burn(tokenIds[j], network, max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas, \
                                                address=Address, private_key=privateKey, init=init, nonce=nonce)
                                if isinstance(result, tuple):
                                    gas_fee, nonce = result
                                    session_gas_fees[j] = tuple(map(sum, zip(session_gas_fees[j], (0., 0., 0., gas_fee) )))
                                    tokenIds_burned += [tokenIds[j]]
                                    nonce += 1
                                    flag_change_tokenIds = True
                                    tokenIds[j], mint_time[j] = None, 0.
                                    flag_failed_tx, flag_burn = False, True
                                    count_failed_tx = 0
                                else:
                                    #N.B. nonce=None triggers web3 getting a nonce
                                    flag_failed_tx, flag_burn, nonce = True, False, None
                                    count_failed_tx += 1
                                    logger.error(network + ", burn() failed for LP[" + str(j) + "], tokenId " + str(tokenIds[j]) +\
                                                    ", count_failed_tx = " + str(count_failed_tx))
                                    break #N.B. Break the NUM_LP-loop and continue with code
                            else:
                                logger.info('')
                                logger.error(network + ', burn() for LP[' + str(j) + '] failed MAX_ATTEMPS_FAILED_TX = ' + str(MAX_ATTEMPS_FAILED_TX) + ' times, stop main()!')
                                current_LP_positions(network, address=Address, init=init) 
                                #logger.info(network + ", session p&l = " + str(session_token0_rf_pl_token1[j]) + ' ' + init.token1_symbol +\
                                #                    ", " + "{:1.2f}".format(session_token0_rf_pl_bp[j]) + " bp")
                                logger.info(network + ", session: " + init.token1_symbol + "-ref-frame p&l w/o swaps = " +\
                                    "{:1.4f}".format(sum(session_token1_rf_pl_token1)) + ' ' + init.token1_symbol +\
                                    " or " + "{:1.1f}".format(sum(session_token1_rf_pl_bp)) + " bp" +\
                                    " = " + str(["{:1.1f}".format(s) for s in session_token1_rf_pl_bp]) + " bp" +\
                                    ", swap cost=" + "{:1.2f}".format(session_swap_cost_bp) + " bp" +\
                                    ", token0 collected in " + init.token1_symbol + "-ref-frame p&l = " +\
                                            "{:1.4f}".format(session_token0_pl_token1_rf_token1) + ' ' + init.token1_symbol + ' or '+\
                                            "{:1.2f}".format(session_token0_pl_token1_rf_token1 / NUM_INVESTED_TOKEN1_LP * 10000) + ' bp')
                                logger.info(network + ", session: gas fees = " + "{:1.2f}".format(sum([sum(s) for s in session_gas_fees])) + ' ' + init.network_coin_symbol +\
                                  " = [" + str(["{:1.2f}".format(s[0]) for s in session_gas_fees[:-1]]) +\
                                  ", " + str(["{:1.2f}".format(s[1]) for s in session_gas_fees[:-1]]) +\
                                  ", " + str(["{:1.2f}".format(s[2]) for s in session_gas_fees[:-1]]) +\
                                  ", " + str(["{:1.2f}".format(s[3]) for s in session_gas_fees[:-1]]) +\
                                  ", " + "{:1.2f}".format(session_gas_fees[-1][0]) + '] ' + init.network_coin_symbol)
                                logger.info(network + ", session" +\
                                    ": LP fees = " + str(["{:1.1f}".format(s) for s in session_LP_fees_bp]) + " bp" +\
                                    ", RL = " + str(["{:1.1f}".format(s) for s in session_RL_bp]) + " bp" +\
                                    ", OTM loss = " + str(["{:1.1f}".format(s) for s in session_OTM_loss_bp]) + " bp" )
                                    #", iv) hedge RL=" + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
                                logger.info(network + ", session" +  ": res num token0 = " + str(session_res_num_token0) + ", res num token1 = " + str(session_res_num_token1) )
                                logger.info(network + ", session" +  ": invested " + "{:1.1f}".format(sum(s[0] for s in session_invested)) + " = " + str(["{:1.1f}".format(s[0]) for s in session_invested]) + ' ' + init.token0_symbol +\
                                                      ", collected " + "{:1.1f}".format(sum(s[0] for s in session_collected)) + " = "  + str(["{:1.1f}".format(s[0]) for s in session_collected]) + ' ' + init.token0_symbol )
                                logger.info(network + ", session" +  ": invested " + "{:1.4f}".format(sum(s[1] for s in session_invested)) + " = "  + str(["{:1.4f}".format(s[1]) for s in session_invested]) + ' ' + init.token1_symbol +\
                                                      ", collected " + "{:1.4f}".format(sum(s[1] for s in session_collected)) + " = "  + str(["{:1.4f}".format(s[1]) for s in session_collected]) + ' ' + init.token1_symbol )
                                logger.info(network + ', session' +\
                                ': count LP=' + str(sum(session_count_LP[:NUM_LP])) +\
                                ', count LP swaps=' + str(session_count_LP[NUM_LP]) +\
                                ', count LP swaps failed=' + str(session_count_LP_swap_failed) +\
                                ', count non-LP swaps=' + str(session_count_non_LP_swaps) +\
                                ', count unwind flow=' + str(session_count_unwind_flow) +\
                                ', count unwind stop profit=' + str(session_count_unwind_stop_profit) +\
                                ', count unwind stop loss=' + str(session_count_unwind_stop_loss) +\
                                ', count unwind pool liq=' + str(session_count_unwind_pool_liq) +\
                                ', count unwind price_mad=' + str(session_count_unwind_max_price_mad) ) #+\
                                #', count hedge RL = ' + str(session_count_hedge_RL) )
                                logger.info(network + ', session' +\
                                ': count unwind distance rebalance=' + str(sum(session_count_unwind_distance_rebal)) + "=" + str(session_count_unwind_distance_rebal) +\
                                ', count unwind distance non-rebalance=' + str(sum(session_count_unwind_distance_nonrebal)) + "=" + str(session_count_unwind_distance_nonrebal) +\
                                ', count unwind signed q=' + str(sum(session_count_unwind_signed_quantity)) + "=" + str(session_count_unwind_signed_quantity) )
                                logger.info(network + ", session: dur=" + "{:1.1f}".format((time.time() - start_time) / 3600) + " h" +\
                                    #"; avg LP dur=" + str(["{:1.1f}".format(s / 60) for s in session_avg_LP_duration]) + " min" +\
                                    "; avg LP ITM dur=" + str(["{:1.1f}".format(s / 60) for s in session_avg_ITM_duration]) + " min" +\
                                    "; avg LP OTM dur=" + str(["{:1.1f}".format(s / 60) for s in session_avg_OTM_duration]) + " min" +\
                                    ", max price_mad = " + "{:1.5f}".format(max_price_mad) )
                                logger.info('network, END session')
                                return False

                    #N.B. 'if not flag_failed_tx' is not needed here because mint() is checked to not have failed and if the uwind tx-s fail, they break the NUM_LP-loop!
                    #N.B. if not commented-out, 'if not flag_failed_tx' can create infinite j-loop, if flag_failed_tx
                    #if not flag_failed_tx:         
                    j += 1

                if (not flag_failed_tx):
                    
                    if unwind_condition != (NUM_LP + 1) * [False] and i <= int(RUNTIME_SEC / DELAY_LOOP_SEC):
                        logger.info('')
                        logger.info(network + ", session  for all LP-s: " + init.token1_symbol + "-ref-frame p&l w/o swaps = " +\
                                "{:1.4f}".format(sum(session_token1_rf_pl_token1)) + ' ' + init.token1_symbol +\
                                " or " + "{:1.1f}".format(sum(session_token1_rf_pl_bp)) + " bp" +\
                                " = " + str(["{:1.1f}".format(s) for s in session_token1_rf_pl_bp]) + " bp" +\
                                ", swap cost=" + "{:1.2f}".format(session_swap_cost_bp) + " bp" +\
                                ", token0 collected in " + init.token1_symbol + "-ref-frame p&l = " +\
                                        "{:1.4f}".format(session_token0_pl_token1_rf_token1) + ' ' + init.token1_symbol + ' or '+\
                                        "{:1.2f}".format(session_token0_pl_token1_rf_token1 / NUM_INVESTED_TOKEN1_LP * 10000) + ' bp')
                        logger.info(network + ", session: gas fees = " + "{:1.2f}".format(sum([sum(s) for s in session_gas_fees])) + ' ' + init.network_coin_symbol +\
                                  " = [" + str(["{:1.2f}".format(s[0]) for s in session_gas_fees[:-1]]) +\
                                  ", " + str(["{:1.2f}".format(s[1]) for s in session_gas_fees[:-1]]) +\
                                  ", " + str(["{:1.2f}".format(s[2]) for s in session_gas_fees[:-1]]) +\
                                  ", " + str(["{:1.2f}".format(s[3]) for s in session_gas_fees[:-1]]) +\
                                  ", " + "{:1.2f}".format(session_gas_fees[-1][0]) + '] ' + init.network_coin_symbol)
                        logger.info(network + ", session" +\
                               ": LP fees = " + str(["{:1.1f}".format(s) for s in session_LP_fees_bp]) + " bp" +\
                                ", RL = " + str(["{:1.1f}".format(s) for s in session_RL_bp]) + " bp" +\
                                ", OTM loss = " + str(["{:1.1f}".format(s) for s in session_OTM_loss_bp]) + " bp" )
                        logger.info(network + ", session" +  ": res num token0 = " + str(session_res_num_token0) + ", res num token1 = " + str(session_res_num_token1) )
                        logger.info(network + ", session" +  ": invested " + "{:1.1f}".format(sum(s[0] for s in session_invested)) + " = " + str(["{:1.1f}".format(s[0]) for s in session_invested]) + ' ' + init.token0_symbol +\
                                              ", collected " + "{:1.1f}".format(sum(s[0] for s in session_collected)) + " = "  + str(["{:1.1f}".format(s[0]) for s in session_collected]) + ' ' + init.token0_symbol )
                        logger.info(network + ", session" +  ": invested " + "{:1.4f}".format(sum(s[1] for s in session_invested)) + " = "  + str(["{:1.4f}".format(s[1]) for s in session_invested]) + ' ' + init.token1_symbol +\
                                              ", collected " + "{:1.4f}".format(sum(s[1] for s in session_collected)) + " = "  + str(["{:1.4f}".format(s[1]) for s in session_collected]) + ' ' + init.token1_symbol )
                        logger.info(network + ', session' +\
                                ': count LP=' + str(sum(session_count_LP[:NUM_LP])) +\
                                ', count LP swaps=' + str(session_count_LP[NUM_LP]) +\
                                ', count LP swaps failed=' + str(session_count_LP_swap_failed) +\
                                ', count non-LP swaps=' + str(session_count_non_LP_swaps) +\
                                ', count unwind flow=' + str(session_count_unwind_flow) +\
                                ', count unwind stop profit=' + str(session_count_unwind_stop_profit) +\
                                ', count unwind stop loss=' + str(session_count_unwind_stop_loss) +\
                                ', count unwind pool liq=' + str(session_count_unwind_pool_liq) +\
                                ', count unwind price_mad=' + str(session_count_unwind_max_price_mad) ) #+\
                                #', count hedge RL = ' + str(session_count_hedge_RL) )
                        logger.info(network + ', session' +\
                                ': count unwind distance rebalance=' + str(sum(session_count_unwind_distance_rebal)) + "=" + str(session_count_unwind_distance_rebal) +\
                                ', count unwind distance non-rebalance=' + str(sum(session_count_unwind_distance_nonrebal)) + "=" + str(session_count_unwind_distance_nonrebal) +\
                                ', count unwind signed q=' + str(sum(session_count_unwind_signed_quantity)) + "=" + str(session_count_unwind_signed_quantity) )
                        logger.info(network + ", session for all LP-s:, dur=" + "{:1.1f}".format((time.time() - start_time) / 3600) + " h" +\
                                #"; avg LP dur=" + str(["{:1.1f}".format(s / 60) for s in session_avg_LP_duration]) + " min" +\
                                "; avg LP ITM dur=" + str(["{:1.1f}".format(s / 60) for s in session_avg_ITM_duration]) + " min" +\
                                "; avg LP OTM dur=" + str(["{:1.1f}".format(s / 60) for s in session_avg_OTM_duration]) + " min" )
            
                 
        ######################################################################
        #7. Swap the collected amounts difference to achieve the original amounts
        #N.B. If slippage is too low, conventional swap fails with error 'Too little received'
        if flag_mint and flag_increaseLiquidity and flag_hedgeRL and flag_decreaseLiquidity and flag_collect and flag_burn:
            
            #swap_condition
            swap_condition = False
            #N.B. If a failed LP swap or the end of main loop, conventional swap is executed!
            if flag_LP_swap and (count_LP_swap_attempts >= LP_SWAP_MAX_ATTEMPTS_FAILED_TX or i >= main_loop_end - MAX_ATTEMPS_FAILED_TX):
                if count_LP_swap_attempts >= LP_SWAP_MAX_ATTEMPTS_FAILED_TX:
                    logger.info(network + ", LP swap tx failed " +\
                            str(count_LP_swap_attempts) + " times, conventional swap is executed with amount_to_swap_token0 = " + str(amount_to_swap_token0))
                if i == main_loop_end - MAX_ATTEMPS_FAILED_TX:
                    logger.info(network + ", LP swap tx with tokenId = " + str(tokenIds_burned[-1]) + " failed because iterations reached main_loop_end" +\
                            ", conventional swap is executed with amount_to_swap_token0 = " + str(amount_to_swap_token0)  + ' ' + init.token0_symbol)
                #N.B. Can use amount_to_swap_token0 despite the fact that this is not immediately after amount_to_swap_token0 was set up:
                #N.B. because there is only one LP swap and conventional swap & LP swap can not co-exist: amount_to_swap_token0 has not changed!
               
                session_count_LP_swap_failed += 1
                flag_LP_swap, j = False, 0 #N.B. Affects the end of the loop
                flag_mint, mint_condition[NUM_LP] = True, False
                swap_condition = True
            else:
                #N.B. session swap: overwrites tx batch swap because session_res_num_token0 includes tx_batch_amount_to_swap_token0
                if abs(session_res_num_token1) >= MIN_SESSION_SWAP_PER / 100 * NUM_INVESTED_TOKEN1_LP or\
                        i >= int(RUNTIME_SEC / DELAY_LOOP_SEC):
                    if session_res_num_token0 > 0:
                        amount_to_swap_token0 = session_res_num_token0
                    elif session_res_num_token1 > 0:
                        amount_to_swap_token0 = -session_res_num_token1 * price
                    session_res_num_token0, session_res_num_token1, tx_batch_amount_to_swap_token0  = 0., 0., 0.
                    if i >= int(RUNTIME_SEC / DELAY_LOOP_SEC):
                        logger.info(network + ", swap_condition = True at the end of session: session swap because i = " + str(i) + " >= " +\
                            str(int(RUNTIME_SEC / DELAY_LOOP_SEC)) + "; amount_to_swap_token0 = " + str(amount_to_swap_token0)  + ' ' + init.token0_symbol)
                    else:
                        logger.info(network + ", swap_condition = True for session swap: amount_to_swap_token0 = " + str(amount_to_swap_token0)  + ' ' + init.token0_symbol)
                    swap_condition = True
                else:
                    logger.info(network + ", no session swap: abs(session_res_num_token1) = " + "{:1.4f}".format(abs(session_res_num_token1)) +\
                            " <= min session swap token1 = " + str(MIN_SESSION_SWAP_PER / 100 * NUM_INVESTED_TOKEN1_LP)  + ' ' + init.token1_symbol)
                    #N.B. tx batch swap
                    #N.B. swap tx_batch_amount_to_swap_token0  token0 into token1 if > 0 or -tx_batch_amount_to_swap_token0 / price token1 into token0 if < 0
                    if abs(tx_batch_amount_to_swap_token0) >= MIN_TX_BATCH_SWAP_PER / 100 * NUM_INVESTED_TOKEN1_LP * price:
                        amount_to_swap_token0 = tx_batch_amount_to_swap_token0
                        session_res_num_token0 -= tx_batch_amount_to_swap_token0
                        session_res_num_token1 += tx_batch_amount_to_swap_token0 / price
                        tx_batch_amount_to_swap_token0 = 0.
                        logger.info(network + ", tx batch swap: amount_to_swap_token0 = " + str(amount_to_swap_token0)  + ' ' + init.token0_symbol)
                        swap_condition = True
                    else:
                        logger.info(network + ", no tx batch swap either: abs(tx_batch_amount_to_swap_token0) = " +\
                                        "{:1.2f}".format(abs(tx_batch_amount_to_swap_token0))  +\
                                    ' ' + init.token0_symbol + " <= min tx swap threshold = " +\
                                   "{:1.2f}".format(MIN_TX_BATCH_SWAP_PER / 100 * NUM_INVESTED_TOKEN1_LP * price) + ' ' + init.token0_symbol)
                        swap_condition = False
                    
            #N.B. if CHANGE_LP_POSITION_TO_INIT_PRICE, LP_position_to_init_price[j] changes sign and hence swaps maybe needed only at the end
            if CHANGE_LP_POSITION_TO_INIT_PRICE:
                swap_condition = swap_condition and i >= int(RUNTIME_SEC / DELAY_LOOP_SEC)

            #swap
            if swap_condition and abs(amount_to_swap_token0) >= SWAP_EPSILON_PER / 100  * NUM_INVESTED_TOKEN1_LP * price:
                logger.info(network + ", swap because swap_condition is raised and amount_to_swap_token0 = " +\
                        str(amount_to_swap_token0) + " with abs(amount_to_swap_token0) >= epsilon = " +\
                        str(SWAP_EPSILON_PER / 100  * NUM_INVESTED_TOKEN1_LP * price) )

                #LP swap
                if LP_SWAP and count_LP_swap_attempts < LP_SWAP_MAX_ATTEMPTS_FAILED_TX and i < main_loop_end - MAX_ATTEMPS_FAILED_TX:
                    flag_LP_swap = True
                    logger.info(network + ", flag_LP_swap is raised! count_LP_swap_attempts = " + str(count_LP_swap_attempts))
                    #N.B. Get fresh price before LP swap
                    i += 1
                    continue

                #conventional swap
                else:
                    flag_LP_swap, mint_condition[NUM_LP], count_LP_swap_attempts = False, False, 0
                    #N.B. Size-split swap: if amount_to_swap_token0 > 0, swap amount_to_swap_token0 token0 to token1; if < 0, swap -amount_to_swap_token0 token1 to token0;
                    #N.B. Passing nonce speeds up execution
                    result = size_split_swap(network, price, amount_to_swap_token0,\
                        max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas,\
                        address=Address, private_key=privateKey, init=init, nonce=nonce)
                    if isinstance(result, tuple):
                        gas_fee, pool_liquidity, pool_price, swap_price, slippage_and_pool_fee_token1, nonce = result
                        session_collected[NUM_LP] = tuple(map(sum, zip(session_collected[NUM_LP], (-amount_to_swap_token0, amount_to_swap_token0 / price))))
                        session_token0_price_collected.append((-amount_to_swap_token0, price))
                        session_token1_price_collected.append((amount_to_swap_token0 / price, price))
                        amount_to_swap_token0 = 0.
                        session_count_non_LP_swaps += 1

                        #N.B. tx
                        tx_slippage_and_pool_fee_pl_bp = slippage_and_pool_fee_token1 / NUM_INVESTED_TOKEN1_LP * 10000 
                        logger.info(network + ", conventional swap slippage & pool fee cost = " +\
                                        "{:1.4f}".format(slippage_and_pool_fee_token1) + ' ' + init.token1_symbol + ' or ' +\
                                        "{:1.2f}".format(tx_slippage_and_pool_fee_pl_bp) + " bp" )#+\
                                        #"; tx swap flow token1 = " + "{:1.1f}".format(swap_flow_token1))
                        #N.B. session
                        session_swap_cost_bp += tx_slippage_and_pool_fee_pl_bp
                        session_gas_fees[-1] = tuple(map(sum, zip(session_gas_fees[-1], (gas_fee, ) )))
                        #session_token1_rf_pl_bp[j] += tx_slippage_and_pool_fee_pl_bp
                        logger.info(network + ', session: count conventional swaps=' + str(session_count_non_LP_swaps) +\
                                    #" i) " + "{:1.2f}".format(session_token1_rf_pl_bp[j]) + " bp"  +\
                                    ", swap cost=" + "{:1.2f}".format(session_swap_cost_bp) + " bp")
                    else:
                        nonce = None
                        if result:
                            break #N.B. continue with code!
                        else:
                            if flag_increaseLiquidity and flag_hedgeRL and flag_decreaseLiquidity and flag_collect and flag_burn:
                                logger.info('')
                                logger.error(network + ', size_split_swap() failed MAX_ATTEMPS_FAILED_TX = ' + str(MAX_ATTEMPS_FAILED_TX) +\
                                    ' times for swap iteration, stop main()!')
                                current_LP_positions(network, address=Address, init=init) 
                                #logger.info(network + ", session p&l = " + str(session_token0_rf_pl_token1[j]) + ' ' + init.token1_symbol +\
                                #                    ", " + "{:1.2f}".format(session_token0_rf_pl_bp[j]) + " bp")
                                logger.info(network + ", session: " + init.token1_symbol + "-ref-frame p&l w/o swaps = " +\
                                    "{:1.4f}".format(sum(session_token1_rf_pl_token1)) + ' ' + init.token1_symbol +\
                                    " or " + "{:1.1f}".format(sum(session_token1_rf_pl_bp)) + " bp" +\
                                    " = " + str(["{:1.1f}".format(s) for s in session_token1_rf_pl_bp]) + " bp" +\
                                    ", swap cost=" + "{:1.2f}".format(session_swap_cost_bp) + " bp" +\
                                    ", token0 collected in " + init.token1_symbol + "-ref-frame p&l = " +\
                                            "{:1.4f}".format(session_token0_pl_token1_rf_token1) + ' ' + init.token1_symbol + ' or '+\
                                            "{:1.2f}".format(session_token0_pl_token1_rf_token1 / NUM_INVESTED_TOKEN1_LP * 10000) + ' bp')
                                logger.info(network + ", session: gas fees = " + "{:1.2f}".format(sum([sum(s) for s in session_gas_fees])) + ' ' + init.network_coin_symbol +\
                                    " = [" + str(["{:1.2f}".format(s[0]) for s in session_gas_fees[:-1]]) +\
                                    ", " + str(["{:1.2f}".format(s[1]) for s in session_gas_fees[:-1]]) +\
                                    ", " + str(["{:1.2f}".format(s[2]) for s in session_gas_fees[:-1]]) +\
                                    ", " + str(["{:1.2f}".format(s[3]) for s in session_gas_fees[:-1]]) +\
                                    ", " + "{:1.2f}".format(session_gas_fees[-1][0]) + '] ' + init.network_coin_symbol)
                                logger.info(network + ", session" +\
                                    ": LP fees = " + str(["{:1.1f}".format(s) for s in session_LP_fees_bp]) + " bp" +\
                                    ", RL = " + str(["{:1.1f}".format(s) for s in session_RL_bp]) + " bp" +\
                                    ", OTM loss = " + str(["{:1.1f}".format(s) for s in session_OTM_loss_bp]) + " bp"  )
                                    #", iv) hedge RL=" + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
                                logger.info(network + ", session" +  ": res num token0 = " + str(session_res_num_token0) + ", res num token1 = " + str(session_res_num_token1) )
                                logger.info(network + ", session" +  ": invested " + "{:1.1f}".format(sum(s[0] for s in session_invested)) + " = " + str(["{:1.1f}".format(s[0]) for s in session_invested]) + ' ' + init.token0_symbol +\
                                                        ", collected " + "{:1.1f}".format(sum(s[0] for s in session_collected)) + " = "  + str(["{:1.1f}".format(s[0]) for s in session_collected]) + ' ' + init.token0_symbol )
                                logger.info(network + ", session" +  ": invested " + "{:1.4f}".format(sum(s[1] for s in session_invested)) + " = "  + str(["{:1.4f}".format(s[1]) for s in session_invested]) + ' ' + init.token1_symbol +\
                                                        ", collected " + "{:1.4f}".format(sum(s[1] for s in session_collected)) + " = "  + str(["{:1.4f}".format(s[1]) for s in session_collected]) + ' ' + init.token1_symbol )
                                logger.info(network + ', session' +\
                                ': count LP=' + str(sum(session_count_LP[:NUM_LP])) +\
                                ', count LP swaps=' + str(session_count_LP[NUM_LP]) +\
                                ', count LP swaps failed=' + str(session_count_LP_swap_failed) +\
                                ', count non-LP swaps=' + str(session_count_non_LP_swaps) +\
                                ', count unwind flow=' + str(session_count_unwind_flow) +\
                                ', count unwind stop profit=' + str(session_count_unwind_stop_profit) +\
                                ', count unwind stop loss=' + str(session_count_unwind_stop_loss) +\
                                ', count unwind pool liq=' + str(session_count_unwind_pool_liq) +\
                                ', count unwind price_mad=' + str(session_count_unwind_max_price_mad) ) #+\
                                #', count hedge RL = ' + str(session_count_hedge_RL) )
                                logger.info(network + ', session' +\
                                ': count unwind distance rebalance=' + str(sum(session_count_unwind_distance_rebal)) + "=" + str(session_count_unwind_distance_rebal) +\
                                ', count unwind distance non-rebalance=' + str(sum(session_count_unwind_distance_nonrebal)) + "=" + str(session_count_unwind_distance_nonrebal) +\
                                ', count unwind signed q=' + str(sum(session_count_unwind_signed_quantity)) + "=" + str(session_count_unwind_signed_quantity) )
                                logger.info(network + ", session: dur=" + "{:1.1f}".format((time.time() - start_time) / 3600) + " h" +\
                                        #"; avg LP dur=" + str(["{:1.1f}".format(s / 60) for s in session_avg_LP_duration]) + " min" +\
                                        "; avg LP ITM dur=" + str(["{:1.1f}".format(s / 60) for s in session_avg_ITM_duration]) + " min" +\
                                        "; avg LP OTM dur=" + str(["{:1.1f}".format(s / 60) for s in session_avg_OTM_duration]) + " min" +\
                                        ", max price_mad = " + "{:1.5f}".format(max_price_mad) )
                                logger.info('network, END session')
                                return False
            elif abs(amount_to_swap_token0) < SWAP_EPSILON_PER / 100  * NUM_INVESTED_TOKEN1_LP * price:
                logger.info(network + ", no conventional swap because swap_condition is raised but amount_to_swap_token0 = " +\
                        "{:1.2f}".format(amount_to_swap_token0) + " with abs(amount_to_swap_token0) < epsilon = " +\
                        "{:1.2f}".format(SWAP_EPSILON_PER / 100  * NUM_INVESTED_TOKEN1_LP * price)  + ' ' + init.token0_symbol)
                
        #N.B. End
        if i >= int(RUNTIME_SEC / DELAY_LOOP_SEC) and i % PERIOD_CURRENT_LP_POSITIONS_ITERATIONS == 0:
            
            current_LP_positions(network, address=Address, init=init)
            logger.info('')
            #logger.info(network + ", session p&l = " + str(sum(session_token0_rf_pl_token1)) + ' ' + init.token1_symbol +\
            #                ", " + "{:1.2f}".format(sum(session_token0_rf_pl_bp)) + " bp")
            logger.info(network + ", session: " + init.token1_symbol + "-ref-frame p&l w/o swaps = " +\
                            "{:1.4f}".format(sum(session_token1_rf_pl_token1)) + ' ' + init.token1_symbol +\
                            " or " + "{:1.1f}".format(sum(session_token1_rf_pl_bp)) + " bp" +\
                            " = " + str(["{:1.1f}".format(s) for s in session_token1_rf_pl_bp]) + " bp" +\
                            ", swap cost=" + "{:1.2f}".format(session_swap_cost_bp) + " bp" +\
                            ", token0 collected in " + init.token1_symbol + "-ref-frame p&l = " +\
                                    "{:1.4f}".format(session_token0_pl_token1_rf_token1) + ' ' + init.token1_symbol + ' or '+\
                                    "{:1.2f}".format(session_token0_pl_token1_rf_token1 / NUM_INVESTED_TOKEN1_LP * 10000) + ' bp')
            logger.info(network + ", session: gas fees = " + "{:1.2f}".format(sum([sum(s) for s in session_gas_fees])) + ' ' + init.network_coin_symbol +\
                                  " = [" + str(["{:1.2f}".format(s[0]) for s in session_gas_fees[:-1]]) +\
                                  ", " + str(["{:1.2f}".format(s[1]) for s in session_gas_fees[:-1]]) +\
                                  ", " + str(["{:1.2f}".format(s[2]) for s in session_gas_fees[:-1]]) +\
                                  ", " + str(["{:1.2f}".format(s[3]) for s in session_gas_fees[:-1]]) +\
                                  ", " + "{:1.2f}".format(session_gas_fees[-1][0]) + '] ' + init.network_coin_symbol)
            logger.info(network + ", session" +\
                            ": LP fees = " + str(["{:1.1f}".format(s) for s in session_LP_fees_bp]) + " bp" +\
                            ", RL = " + str(["{:1.1f}".format(s) for s in session_RL_bp]) + " bp" +\
                            ", OTM loss = " + str(["{:1.1f}".format(s) for s in session_OTM_loss_bp]) + " bp"   )
                            #", iv) hedge RL = " + "{:1.2f}".format(session_hedge_RL_pl_bp) + " bp")
            logger.info(network + ", session" +  ": res num token0 = " + str(session_res_num_token0) + ", res num token1 = " + str(session_res_num_token1) )
            logger.info(network + ", session" +  ": invested " + "{:1.1f}".format(sum(s[0] for s in session_invested)) + " = " + str(["{:1.1f}".format(s[0]) for s in session_invested]) + ' ' + init.token0_symbol +\
                                  ", collected " + "{:1.1f}".format(sum(s[0] for s in session_collected)) + " = "  + str(["{:1.1f}".format(s[0]) for s in session_collected]) + ' ' + init.token0_symbol )
            logger.info(network + ", session" +  ": invested " + "{:1.4f}".format(sum(s[1] for s in session_invested)) + " = "  + str(["{:1.4f}".format(s[1]) for s in session_invested]) + ' ' + init.token1_symbol +\
                                  ", collected " + "{:1.4f}".format(sum(s[1] for s in session_collected)) + " = "  + str(["{:1.4f}".format(s[1]) for s in session_collected]) + ' ' + init.token1_symbol )
            logger.info(network + ', session' +\
                                ': count LP=' + str(sum(session_count_LP[:NUM_LP])) +\
                                ', count LP swaps=' + str(session_count_LP[NUM_LP]) +\
                                ', count LP swaps failed=' + str(session_count_LP_swap_failed) +\
                                ', count non-LP swaps=' + str(session_count_non_LP_swaps) +\
                                ', count unwind flow=' + str(session_count_unwind_flow) +\
                                ', count unwind stop profit=' + str(session_count_unwind_stop_profit) +\
                                ', count unwind stop loss=' + str(session_count_unwind_stop_loss) +\
                                ', count unwind pool liq=' + str(session_count_unwind_pool_liq) +\
                                ', count unwind price_mad=' + str(session_count_unwind_max_price_mad) ) #+\
                                #', count hedge RL = ' + str(session_count_hedge_RL) )
            logger.info(network + ', session' +\
                                ': count unwind distance rebalance=' + str(sum(session_count_unwind_distance_rebal)) + "=" + str(session_count_unwind_distance_rebal) +\
                                ', count unwind distance non-rebalance=' + str(sum(session_count_unwind_distance_nonrebal)) + "=" + str(session_count_unwind_distance_nonrebal) +\
                                ', count unwind signed q=' + str(sum(session_count_unwind_signed_quantity)) + "=" + str(session_count_unwind_signed_quantity) )
            logger.info(network + ", session: dur=" + "{:1.1f}".format((time.time() - start_time) / 3600) + " h" +\
                                        #"; avg LP dur=" + str(["{:1.1f}".format(s / 60) for s in session_avg_LP_duration]) + " min" +\
                                        "; avg LP ITM dur=" + str(["{:1.1f}".format(s / 60) for s in session_avg_ITM_duration]) + " min" +\
                                        "; avg OTM dur=" + str(["{:1.1f}".format(s / 60) for s in session_avg_OTM_duration]) + " min" +\
                                        ", max price_mad = " + "{:1.5f}".format(max_price_mad))

            #N.B. If flag_LP_swap, loop continues
            if not flag_LP_swap:
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




