__author__ = "Galin Georgiev"
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

##############################################################

#N.B. Does not reqiure building a tx: https://web3py.readthedocs.io/en/v5/contracts.html
def positions(network, tokenId, init=None):
	
	if init is None:
		init = Initialization(network)
	c = Contract(network, init.w3, 'LP')

	#N.B. See the return of the function in file 1 of https://polygonscan.com/address/0xC36442b4a4522E871399CD717aBDD847Ab11FE88#code > Contract > Code
	try:
		[nonce, operator, token0, token1, fee, tickLower, tickUpper, liquidity, feeGrowthInside0LastX128, feeGrowthInside1LastX128, tokensOwed0, tokensOwed1] =\
			c.contract.functions.positions(tokenId).call()
	except Exception as e:
		logger.error(network + ', c.contract.functions.positions(' + str(tokenId) + ').call() failed with error ' +\
			traceback.format_exc(limit=0) )
		return False
	
	return tickLower, tickUpper, liquidity

if __name__ == '__main__':
	if len(sys.argv) == 3:  # network, tokenId
		positions(network=str(sys.argv[1]), tokenId=eval(sys.argv[2]))
	else:
		print("Wrong number of inputs!")