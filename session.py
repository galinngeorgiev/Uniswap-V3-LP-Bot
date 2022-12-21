__author__ = "Galin Georgiev"
__copyright__ = "Copyright 2022, GammaDynamics, LLC"
__version__ = "1.1.0.0"


from global_params import *
from toolbox import *

class Session():
    def __init__(self, network, address, init):
        super(Session, self).__init__()

        self.network, self.address, self.init = network, address, init
        self.count_LP, self.count_unwind_signed_quantity, self.count_unwind_distance_rebal, self.count_unwind_distance_nonrebal =\
		        (NUM_LP + 1) * [0], (NUM_LP + 1) * [0], (NUM_LP + 1) * [0], (NUM_LP + 1) * [0]
        self.count_LP_swap, self.count_LP_swap_failed, self.count_unwind_stop_profit, self.count_unwind_stop_loss, \
		        self.count_unwind_pool_liq, self.count_unwind_max_price_mad,\
		        self.count_hedge_RL, self.count_non_LP_swaps, self.count_unwind_flow, self.count_success_tx, self.count_failed_tx =\
		        0, 0, 0, 0, 0, 0, 0, 0, 0, (NUM_LP + 1) * [(0, 0, 0, 0)] + [(0,)], (NUM_LP + 1) * [(0, 0, 0, 0)] + [(0,)]
        self.LP_fees_bp, self.RL_bp, self.OTM_loss_bp =\
		        (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.]
        self.token0_rf_pl_token1, self.token0_rf_pl_bp, self.token1_rf_pl_token1, self.token1_rf_pl_bp =\
		        (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.], (NUM_LP + 1) * [0.]
        self.success_tx_gas_fees, self.failed_tx_gas_fees = (NUM_LP + 1) * [(0., 0., 0., 0.)] + [(0.,)], (NUM_LP + 1) * [(0., 0., 0., 0.)] + [(0.,)]
        self.invested, self.collected = (NUM_LP + 1) * [(0., 0.)], (NUM_LP + 1) * [(0., 0)]
        self.token0_price_invested, self.token1_price_invested, self.token0_price_collected, self.token1_price_collected,\
	        self.token0_pl_token1_rf_token1, self.amount_to_swap_token0 = [], [], [], [], 0., 0.
        self.swap_cost_bp, self.conventional_swapped = 0., (0., 0.)
        self.avg_LP_duration, self.avg_ITM_duration, self.avg_OTM_duration =\
		        (NUM_LP + 1) * [0], (NUM_LP + 1) * [0], (NUM_LP + 1) * [0]

    def report(self, address, startBlockNumber, start_time, max_price_mad):
		 
        logger.info('')                                
        logger.info(self.network + ", session: " + self.init.token1_symbol + "-ref-frame p&l w/o swaps = " +\
            "{:1.4f}".format(sum(self.token1_rf_pl_token1)) + ' ' + self.init.token1_symbol +\
            " or " + "{:1.1f}".format(sum(self.token1_rf_pl_bp)) + " bp" +\
            " = " + str(["{:1.1f}".format(s) for s in self.token1_rf_pl_bp]) + " bp" +\
                        ", swap cost=" + "{:1.2f}".format(self.swap_cost_bp) + " bp" +\
            ", token0 (collected - invested) in " + self.init.token1_symbol + "-ref-frame p&l = " +\
                    "{:1.4f}".format(self.token0_pl_token1_rf_token1) + ' ' + self.init.token1_symbol + ' or '+\
                    "{:1.2f}".format(self.token0_pl_token1_rf_token1 / NUM_INVESTED_TOKEN1_LP * 10000) + ' bp')
        logger.info(self.network + ", session: count success tx-s = " + "{:d}".format(sum([sum(s) for s in self.count_success_tx])) +\
            " = [" + str(["{:d}".format(s[0]) for s in self.count_success_tx[:-1]]) +\
            ", " + str(["{:d}".format(s[1]) for s in self.count_success_tx[:-1]]) +\
            ", " + str(["{:d}".format(s[2]) for s in self.count_success_tx[:-1]]) +\
            ", " + str(["{:d}".format(s[3]) for s in self.count_success_tx[:-1]]) +\
            ", " + "{:d}".format(self.count_success_tx[-1][0]) + '] ')
        logger.info(self.network + ", session: count failed  tx-s = " + "{:d}".format(sum([sum(s) for s in self.count_failed_tx])) +\
            " = [" + str(["{:d}".format(s[0]) for s in self.count_failed_tx[:-1]]) +\
            ", " + str(["{:d}".format(s[1]) for s in self.count_failed_tx[:-1]]) +\
            ", " + str(["{:d}".format(s[2]) for s in self.count_failed_tx[:-1]]) +\
            ", " + str(["{:d}".format(s[3]) for s in self.count_failed_tx[:-1]]) +\
            ", " + "{:d}".format(self.count_failed_tx[-1][0]) + '] ')
        logger.info(self.network + ", session: gas fees on success tx-s = " +\
            "{:1.2f}".format(sum([sum(s) for s in self.success_tx_gas_fees])) + ' ' + self.init.network_coin_symbol +\
            " = [" + str(["{:1.2f}".format(s[0]) for s in self.success_tx_gas_fees[:-1]]) +\
            ", " + str(["{:1.2f}".format(s[1]) for s in self.success_tx_gas_fees[:-1]]) +\
            ", " + str(["{:1.2f}".format(s[2]) for s in self.success_tx_gas_fees[:-1]]) +\
            ", " + str(["{:1.2f}".format(s[3]) for s in self.success_tx_gas_fees[:-1]]) +\
            ", " + "{:1.2f}".format(self.success_tx_gas_fees[-1][0]) + '] ' + self.init.network_coin_symbol)
        logger.info(self.network + ", session: gas fees on failed  tx-s = " +\
            "{:1.2f}".format(sum([sum(s) for s in self.failed_tx_gas_fees])) + ' ' + self.init.network_coin_symbol +\
            " = [" + str(["{:1.2f}".format(s[0]) for s in self.failed_tx_gas_fees[:-1]]) +\
            ", " + str(["{:1.2f}".format(s[1]) for s in self.failed_tx_gas_fees[:-1]]) +\
            ", " + str(["{:1.2f}".format(s[2]) for s in self.failed_tx_gas_fees[:-1]]) +\
            ", " + str(["{:1.2f}".format(s[3]) for s in self.failed_tx_gas_fees[:-1]]) +\
            ", " + "{:1.2f}".format(self.failed_tx_gas_fees[-1][0]) + '] ' + self.init.network_coin_symbol)
        logger.info(self.network + ", session" +\
            ": LP fees = " + str(["{:1.1f}".format(s) for s in self.LP_fees_bp]) + " bp" +\
            ", RL = " + str(["{:1.1f}".format(s) for s in self.RL_bp]) + " bp" +\
            ", OTM loss = " + str(["{:1.1f}".format(s) for s in self.OTM_loss_bp]) + " bp" )
            #", iv) hedge RL=" + "{:1.2f}".format(self.hedge_RL_pl_bp) + " bp")
        logger.info(self.network + ", session" +  ": invested " + "{:1.1f}".format(sum(s[0] for s in self.invested)) +\
           " = " + str(["{:1.1f}".format(s[0]) for s in self.invested]) + ' ' + self.init.token0_symbol +\
                                ", collected " + "{:1.1f}".format(sum(s[0] for s in self.collected)) +\
                               " = "  + str(["{:1.1f}".format(s[0]) for s in self.collected]) + ' ' + self.init.token0_symbol )
        logger.info(self.network + ", session" +  ": invested " + "{:1.4f}".format(sum(s[1] for s in self.invested)) +\
           " = "  + str(["{:1.4f}".format(s[1]) for s in self.invested]) + ' ' + self.init.token1_symbol +\
                                ", collected " + "{:1.4f}".format(sum(s[1] for s in self.collected)) +\
                               " = "  + str(["{:1.4f}".format(s[1]) for s in self.collected]) + ' ' + self.init.token1_symbol )
        logger.info(self.network + ", session" +  ": conventionally swapped = " + "{:1.1f}".format(self.conventional_swapped[0]) +\
                ' ' + self.init.token0_symbol + ", " + "{:1.4f}".format(self.conventional_swapped[1]) + ' ' + self.init.token1_symbol)
        logger.info(self.network + ', session' +\
        ': count non-swap LP=' + str(sum(self.count_LP[:NUM_LP])) +\
        ', count swap LP=' + str(self.count_LP[NUM_LP]) +\
        ', count swap LP failed=' + str(self.count_LP_swap_failed) +\
        ', count conventional swaps=' + str(self.count_non_LP_swaps) +\
        ', count unwind flow=' + str(self.count_unwind_flow) +\
        ', count unwind stop profit=' + str(self.count_unwind_stop_profit) +\
        ', count unwind stop loss=' + str(self.count_unwind_stop_loss) +\
        ', count unwind pool liq=' + str(self.count_unwind_pool_liq) +\
        ', count unwind price_mad=' + str(self.count_unwind_max_price_mad) ) #+\
        #', count hedge RL = ' + str(self.count_hedge_RL) )
        logger.info(self.network + ', session' +\
        ': count unwind distance rebalance=' + str(sum(self.count_unwind_distance_rebal)) + "=" + str(self.count_unwind_distance_rebal) +\
        ', count unwind distance non-rebalance=' + str(sum(self.count_unwind_distance_nonrebal)) + "=" + str(self.count_unwind_distance_nonrebal) +\
        ', count unwind signed q=' + str(sum(self.count_unwind_signed_quantity)) + "=" + str(self.count_unwind_signed_quantity) )
        logger.info(self.network + ", session: dur=" + "{:1.1f}".format((time.time() - start_time) / 3600) + " h" +\
            #"; avg LP dur=" + str(["{:1.1f}".format(s / 60) for s in self.avg_LP_duration]) + " min" +\
            "; avg LP ITM dur=" + str(["{:1.1f}".format(s / 60) for s in self.avg_ITM_duration]) + " min" +\
            "; avg LP OTM dur=" + str(["{:1.1f}".format(s / 60) for s in self.avg_OTM_duration]) + " min" +\
            ", max price_mad = " + "{:1.5f}".format(max_price_mad) )
        




 
