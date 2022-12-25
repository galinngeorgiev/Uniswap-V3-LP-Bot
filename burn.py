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

#N.B. If not collected, burn() tx produces error on Etherscan "Fail with error 'Not cleared'"
def burn(network, tokenId, max_fee_per_gas=MAX_FEE_PER_GAS, max_priority_fee_per_gas=MAX_PRIORITY_FEE_PER_GAS, address=ADDRESS_TESTNET, private_key=PRIVATE_KEY, init=None, nonce=None):
	#burn the NFT correponding to tokenId; otherwise the NFT stays in the wallet
	#N.B. From the docs: "The token must have 0 liquidity and all tokens must be collected first.": https://docs.uniswap.org/protocol/reference/periphery/NonfungiblePositionManager
    
	if init is None:
		init = Initialization(network)
	#N.B. Setting up a gas strategy turns tx-s into 'Legacy'
	#init.w3.eth.set_gas_price_strategy(medium_gas_price_strategy) #N.B. Only used for legacy tx-s: https://web3py.readthedocs.io/en/stable/gas_price.html
	c = Contract(network, init.w3, 'LP')

	if nonce is None:
		#N.B. The nonce does not use 'pending', so the 2nd tx (with higher gas) replaces a pending tx
		try:
			nonce = init.w3.eth.get_transaction_count(address)
		except:
			logger.error(network + ', get_transaction_count() in burn() failed. Next main() iteration (with higher gas)!')
			return False
		time.sleep(DELAY_NONCE_SEC) #N.B. Sometimes get 'nonce too low' error
	else:
		nonce += 1

	burn_tx = c.contract.functions.burn(tokenId).build_transaction({
				"chainId": init.networkId,
				"from": address,
				"maxFeePerGas": init.w3.toHex(max_fee_per_gas),
				"maxPriorityFeePerGas": init.w3.toHex(max_priority_fee_per_gas),
				#"gasPrice": init.w3.toHex(int(5e11)), #N.B. Commenting out gasPrice uses market GasPrice & makes the tx "Type 2: EIP-1559" (as opposed to "Legacy" when un-commented) 
				"gas": init.w3.toHex(MAX_GAS_UNITS), 
				"nonce": nonce
			})
    
	signed_tx = init.w3.eth.account.sign_transaction(burn_tx, private_key)
	try:
		tx_hash = init.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
	except Exception as e:
		#N.B. The error 'connection closed abnormally' delays execution but the tx executes!
		#if 'connection closed abnormally' in traceback.format_exc(limit=0):
		#	logger.error(network + ', send_raw_transaction() in burn() failed with error ' + traceback.format_exc(limit=0))
		#	tx_hash = delay_error(network, init, 'hash', signed_tx.rawTransaction)
		#else:
		logger.error(network + ', send_raw_transaction() in burn() for tokenId ' + str(tokenId) + ' failed with error ' +\
			traceback.format_exc(limit=0) + '. Try again with higher gas! ')
		return False
	  
	#N.B. tx receipt
	tx_receipt = {'status': -1} #N.B. tx_receipt['status'] is not recognised sometimes
	result = wait_for_transaction_receipt(network, tx_hash, timeout=TIMEOUT_SEC, polling=RECEIPT_POLLING_SEC, init=init)
	if isinstance(result, dict):
		tx_receipt = result
		if tx_receipt['status'] == 0:
			logger.error(network + ', burn()  for tokenId ' + str(tokenId) + ' failed with tx_receipt[status] == 0. Try again with higher gas!')
			gas_fee = tx_receipt['effectiveGasPrice'] * tx_receipt['gasUsed'] / 10**init.token1_decimal
			return [gas_fee, False]
		else:
			gas_fee = tx_receipt['effectiveGasPrice'] * tx_receipt['gasUsed'] / 10**init.token1_decimal
			#N.B. Decoding the Transfer() event in the receipt
			event_dict = c.contract.events.Transfer().processReceipt(tx_receipt, errors=DISCARD)
			sender, recipient = event_dict[0]['args']['from'], event_dict[0]['args']['to']
        
			if sender == address and recipient == '0x0000000000000000000000000000000000000000':
				logger.info(network + ', burn() succedeed: block=' + str(tx_receipt["blockNumber"]) + ', tokenId=' + str(tokenId))
			else:
				logger.info(network + ', burn() succedeed: block=' + str(tx_receipt["blockNumber"]) + ', tokenId=' + str(tokenId) + ' but sender=' + str(sender) + ', recipient = ' + recipient)
		return gas_fee, nonce
	else:
		logger.error(network + ', burn() for tokenId ' + str(tokenId) + ' failed because wait_for_transaction_receipt() failed')
		return False
           
	


def burn_wrapped(network, tokenId, max_fee_per_gas=MAX_FEE_PER_GAS, max_priority_fee_per_gas=MAX_PRIORITY_FEE_PER_GAS):

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
		
	burn(network, tokenId, max_fee_per_gas, max_priority_fee_per_gas, address=Address, private_key=privateKey)

if __name__ == '__main__':

	if len(sys.argv) == 3:  # network, tokenId
		burn_wrapped(network=str(sys.argv[1]), tokenId=eval(sys.argv[2]))
	elif len(sys.argv) == 5:  # tokenId, network, max_fee_per_gas, max_priority_fee_per_gas
		burn_wrapped(network=str(sys.argv[1]), tokenId=eval(sys.argv[2]), max_fee_per_gas=eval(sys.argv[3]), max_priority_fee_per_gas=eval(sys.argv[4]))
	else:
		print("Wrong number of inputs!")