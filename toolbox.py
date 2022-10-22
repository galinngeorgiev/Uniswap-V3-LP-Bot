__author__ = "Galin Georgiev"
__copyright__ = "Copyright 2022, GammaDynamics, LLC"
__version__ = "1.1.0.0"


import json
import os
import sys
import numpy as np
import time
import requests
import traceback

import time
from time import gmtime
import datetime
import statistics

#N.B. For converting numbers < 0 to hex: https://math.stackexchange.com/questions/408761/hexadecimal-value-of-a-negative-number
negative_numbers_dict = {'0':'f', '1':'e', '2':'d', '3':'c', '4':'b', '5':'a', '6':'9', '7':'8', '8':'7', '9':'6', 'a':'5', 'b':'4', 'c':'3', 'd':'2', 'e':'1', 'f':'0'}

from web3 import Web3, HTTPProvider
from web3.logs import DISCARD
from web3.exceptions import TimeExhausted
from web3.gas_strategies.time_based import medium_gas_price_strategy, fast_gas_price_strategy
from web3.middleware import geth_poa_middleware #N.B. Need this for Polygon Mumbai only (Alchemy node_url does not work with the inject below?)

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
#formatter = logging.Formatter('%(asctime)s - %(name)s - %(process)d - %(processName)s - %(module)s - %(levelname)s - %(message)s')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)20.20s - %(message)s')
handler.setFormatter(formatter)
# add the handlers to the logger
if not len(logger.handlers):
	logger.addHandler(handler)

##############################################################


class Initialization():
	def __init__(self, network='mumbai'):
		super(Initialization, self).__init__()

		if network == 'ethereum':
			if NODE_INFURA:
				node_url = 'https://mainnet.infura.io/v3/' + INFURA_ID
				websocket = 'wss://mainnet.infura.io/ws/v3/' + INFURA_ID
			elif NODE_ALCHEMY:
				node_url = 'https://eth-mainnet.g.alchemy.com/v2/' + ALCHEMY_ID_MAINNET
				websocket = 'wss://eth-mainnet.g.alchemy.com/v2/' + ALCHEMY_ID_MAINNET
			self.networkId = 1 #, self.unwind_dist_price_mad_mult =  UNWIND_DISTANCE_PRICE_MAD_MULT_MAINNET
			self.token0_symbol, self.token0_address, self.token0_decimal = TOKEN0_SYMBOL_MAINNET, TOKEN0_ADDRESS_MAINNET, TOKEN0_DECIMAL_MAINNET
			self.token1_symbol, self.token1_address, self.token1_decimal = TOKEN1_SYMBOL_MAINNET, TOKEN1_ADDRESS_MAINNET, TOKEN1_DECIMAL_MAINNET
			self.pool_fee = POOL_FEE_MAINNET
		#N.B. Alchemy (used for current_LP_position()) does not support Kovan anymore
		#elif network == 'kovan':
		#	node_url = 'https://kovan.infura.io/v3/' + INFURA_ID
		#	self.networkId = 42 #, self.unwind_dist_price_mad_mult = UNWIND_DISTANCE_PRICE_MAD_MULT_KOVAN
		#	self.token0_symbol, self.token0_address, self.token0_decimal = TOKEN0_SYMBOL_KOVAN, TOKEN0_ADDRESS_KOVAN, TOKEN0_DECIMAL_KOVAN
		#	self.token1_symbol, self.token1_address, self.token1_decimal = TOKEN1_SYMBOL_KOVAN, TOKEN1_ADDRESS_KOVAN, TOKEN1_DECIMAL_KOVAN
		#	self.pool_fee = POOL_FEE_KOVAN
		elif network == 'goerli':
			if NODE_INFURA:
				node_url = 'https://goerli.infura.io/v3/' + INFURA_ID
			elif NODE_ALCHEMY:
				node_url = 'https://eth-goerli.g.alchemy.com/v2/' + ALCHEMY_ID_GOERLI
				websocket = 'wss://eth-goerli.g.alchemy.com/v2/' + ALCHEMY_ID_GOERLI 
			self.networkId = 5 #, self.unwind_dist_price_mad_mult = UNWIND_DISTANCE_PRICE_MAD_MULT_GOERLI
			self.token0_symbol, self.token0_address, self.token0_decimal = TOKEN0_SYMBOL_GOERLI, TOKEN0_ADDRESS_GOERLI, TOKEN0_DECIMAL_GOERLI
			self.token1_symbol, self.token1_address, self.token1_decimal = TOKEN1_SYMBOL_GOERLI, TOKEN1_ADDRESS_GOERLI, TOKEN1_DECIMAL_GOERLI
			self.pool_fee = POOL_FEE_GOERLI
		elif network == 'polygon':
			if NODE_INFURA:
				node_url = 'https://polygon-mainnet.infura.io/v3/' + INFURA_ID
				#N.B. Does not have currently websocket connection for Polygon
			elif NODE_ALCHEMY:
				node_url = 'https://polygon-mainnet.g.alchemy.com/v2/' + ALCHEMY_ID_POLYGON
				websocket = 'wss://polygon-mainnet.g.alchemy.com/v2/'  + ALCHEMY_ID_POLYGON
			self.networkId = 137 #, self.unwind_dist_price_mad_mult = UNWIND_DISTANCE_PRICE_MAD_MULT_POLYGON
			self.token0_symbol, self.token0_address, self.token0_decimal = TOKEN0_SYMBOL_POLYGON, TOKEN0_ADDRESS_POLYGON, TOKEN0_DECIMAL_POLYGON
			self.token1_symbol, self.token1_address, self.token1_decimal = TOKEN1_SYMBOL_POLYGON, TOKEN1_ADDRESS_POLYGON, TOKEN1_DECIMAL_POLYGON
			self.pool_fee = POOL_FEE_POLYGON
		elif network == 'mumbai':
			if NODE_INFURA:
				node_url = 'https://polygon-mumbai.infura.io/v3/' + INFURA_ID
				#N.B. Does not have currently websocket connection for Polygon
			elif NODE_ALCHEMY:
				node_url = 'https://polygon-mumbai.g.alchemy.com/v2/' + ALCHEMY_ID_MUMBAI
				websocket = 'wss://polygon-mumbai.g.alchemy.com/v2/'  + ALCHEMY_ID_MUMBAI
			self.networkId = 80001 #, self.unwind_dist_price_mad_mult = UNWIND_DISTANCE_PRICE_MAD_MULT_MUMBAI
			self.token0_symbol, self.token0_address, self.token0_decimal = TOKEN0_SYMBOL_MUMBAI, TOKEN0_ADDRESS_MUMBAI, TOKEN0_DECIMAL_MUMBAI
			self.token1_symbol, self.token1_address, self.token1_decimal = TOKEN1_SYMBOL_MUMBAI, TOKEN1_ADDRESS_MUMBAI, TOKEN1_DECIMAL_MUMBAI
			self.pool_fee = POOL_FEE_MUMBAI

		if NODE_HTTPS:
			self.w3 = Web3(HTTPProvider(node_url))
		elif NODE_WEBSOCKET:
			self.w3 = Web3(Web3.WebsocketProvider(websocket))
		
		#N.B. Need this for Polygon Mumbai only: 
		#N.B. https://stackoverflow.com/questions/70812529/the-field-extradata-is-97-bytes-but-should-be-32-it-is-quite-likely-that-you-a
		#N.B. Alchemy node_url does not work even with inject?
		self.w3.middleware_onion.inject(geth_poa_middleware, layer=0) 


class Contract():
	def __init__(self, network, w3, type='LT'):
		super(Contract, self).__init__()
		
		if type == 'LT':
			#N.B. Using SwapRouter02.sol requires commenting out 'deadline' in params
			contract_address = ROUTER_ADDRESS  #SwapRouter02.sol
			#ABI file is copied/pasted from Etherscan.io > address > Contract (the list after result:)
			with open(os.path.join(DATA_PATH,'abi', 'SwapRouter02.abi'), 'r', encoding='utf-8') as file:
				contract_abi = json.load(file)
			contract_address = w3.toChecksumAddress(contract_address)
			self.contract = w3.eth.contract(address=contract_address, abi=contract_abi)
		elif type == 'LP':
			contract_address = NPM_ADDRESS #NonfungiblePositionManager.sol
			contract_address = w3.toChecksumAddress(contract_address)
			#ABI file is copied/pasted from Etherscan.io > address > Contract (the list after result:)
			with open(os.path.join(DATA_PATH,'abi', 'NonfungiblePositionManager.abi'), 'r', encoding='utf-8') as file:
				contract_abi = json.load(file)
			self.contract = w3.eth.contract(address=contract_address, abi=contract_abi)
		elif type == 'Pool':
			if network == 'ethereum':
				contract_address = POOL_ADDRESS_MAINNET
			elif network == 'kovan':
				contract_address = POOL_ADDRESS_KOVAN
			elif network == 'goerli':
				contract_address = POOL_ADDRESS_GOERLI
			elif network == 'polygon':
				contract_address = POOL_ADDRESS_POLYGON
			elif network == 'mumbai':
				contract_address = POOL_ADDRESS_MUMBAI
			
			contract_address = w3.toChecksumAddress(contract_address)
			#ABI file is copied/pasted from Etherscan.io > address > Contract (the list after result:)
			with open(os.path.join(DATA_PATH,'abi', 'Pool.abi'), 'r', encoding='utf-8') as file:
				contract_abi = json.load(file)
			self.contract = w3.eth.contract(address=contract_address, abi=contract_abi)
		#print(self.contract.all_functions())


##N.B. Use Selenium because requests() sometime fails and it fails main()!
#from selenium import webdriver
#from selenium.webdriver.chrome.service import Service
#from selenium.webdriver.firefox.options import Options as FirefoxOptions

def current_LP_positions(network='mumbai',address=ADDRESS_TESTNET, init=None):
	#N,B. Use Alchemy API because Etherscan API requires Pro acct for the 721 balance call: https://api.etherscan.io/api?module=account&action=addresstokennftbalance
	if network == 'ethereum':
		url = "https://eth-mainnet.g.alchemy.com/nft/v2/" + ALCHEMY_ID_MAINNET + "/getNFTs?owner=" + address + "&withMetadata=false"
	#N.B. Alchemy does not support Kovan anymore
	#elif network == 'kovan':
	#	url = "https://eth-kovan.g.alchemy.com/nft/v2/" + ALCHEMY_ID + "/getNFTs?owner=" + address + "&withMetadata=false"
	elif network == 'goerli':
		url = "https://eth-goerli.g.alchemy.com/nft/v2/" + ALCHEMY_ID_GOERLI + "/getNFTs?owner=" + address + "&withMetadata=false"
	elif network == 'polygon':
		url = "https://polygon-mainnet.g.alchemy.com/nft/v2/" + ALCHEMY_ID_POLYGON + "/getNFTs?owner=" + address+ "&withMetadata=false"
	elif network == 'mumbai':
		url = "https://polygon-mumbai.g.alchemy.com/nft/v2/" + ALCHEMY_ID_MUMBAI + "/getNFTs?owner=" + address + "&withMetadata=false"

	user_agent = 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:78.0) Gecko/20100101 Firefox/78.0'
	#headers = {"Accept": "application/json"}
	try:
		req = requests.get(url, headers = {'User-agent': user_agent})
	except Exception:
		logger.error('requests.get() in current_LP_positions() failed for url ' + url + ' with error ' + traceback.format_exc(limit=0) + ', stop main()!')
		return False

	#options = FirefoxOptions()
	#options.set_preference('devtools.jsonview.enabled', False) #N.B. Allows for viweing json: https://blog.francium.tech/firefox-selenium-disable-json-formatting-cfaf466fd20f
	##options.headless = True #N.B. No browser is seen

	#try:
	#	s = Service(r'C:/Program Files/geckodriver')
	#	browser = webdriver.Firefox(service=s, options=options)
	#	browser.get(url)
	#except Exception:
	#	logger.error('Selenium / browser in current_LP_positions() failed for url ' + url + ' with error ' + traceback.format_exc(limit=0) + ', next iteration!')
	#	browser.close()
	#	return False

	#time.sleep(DELAY_REQUEST_SEC) #N.B. Sometimes json.loads() fails
	try:
		dict = json.loads(req.text)
		#dict = json.loads(browser.find_element('tag name', 'pre').text)
	except Exception:
		logger.error(network + ', json.loads() in current_LP_positions() failed for url ' + url + ' with error ' + traceback.format_exc(limit=0) + ', next iteration!')
		return False
	
	##N.B. If browser is not closed on every page, get "Access denied"!
	#browser.close()
	#NFT-s
	try:
		NFT = dict['ownedNfts']
	except:
		logger.error(network + ', NFT in current_LP_positions() failed for url ' + url + ' with error ' + traceback.format_exc(limit=0) + ', next iteration!')
		return False

	if init is None:
		init = Initialization(network)
	#N.B. The 'if' condition ensures that the NFT-s are sent from the NPM address
	if len(NFT) > 0:
		tokenIds = [init.w3.toInt(hexstr=NFT[i]['id']['tokenId']) for i in range(len(NFT)) if NFT[i]['contract']['address'] == NPM_ADDRESS.lower()]
		#n.b. Sort the list in ascending order
		tokenIds.sort()
	else:
		tokenIds = []

	logger.info(network + ', LP tokenIds = ' + str(tokenIds) + ', in current_LP_positions()')

	return tokenIds

#N.B. The lib uniswap-python does not work yet on Mumbai
#from uniswap import Uniswap
#uniswap = Uniswap(address=ADDRESS_TESTNET, private_key=PRIVATE_KEY, version=3, provider=node_url)
#current_price_kovan = uniswap.get_price_input(TOKEN1_ADDRESS_POLYGON, TOKEN0_ADDRESS_POLYGON, 10**18) / 10**18

#N.B. Compute liquidity of a mint() event from tokenId
def mint_liquidity_from_tokenId(tokenId, network='mumbai', init=None):

	mint_event='0x3067048beee31b25b2f1681f88dac838c8bba36af25bfb2b7cf7473a5847e35f'

	if init is None:
		init = Initialization(network)
	#N.B. Turn tokenId into hex
	tokenId = init.w3.toHex(tokenId)
	#N.B. Turn tokenId into 64 character hex
	tokenId = '0x' + tokenId[2:].zfill(64)

	headers = {"Accept": "application/json"}
	if network == 'polygon':
		url = "https://api.polygonscan.com/api?module=logs&action=getlogs&topic0=" + mint_event + "&topic0_1_opr=and&topic1=" + str(tokenId) + "&page=1&offset=1000&apikey=" + API_KEY_POLYGONSCAN

	try:
		req = requests.get(url, headers)
	except Exception:
		logger.error(network + ', requests.get() in mint_liquidity_from_tokenId() failed for url ' + url + ' with error ' + traceback.format_exc(limit=0) + ', price unchanged!')
		return False
	#logger.info(network + ', req.text =' + req.text)
	try:
		dict = req.json() #json.loads(req.text)
	except Exception:
		logger.error(network + ', req.json() in mint_liquidity_from_tokenId() failed for url ' + url + ' with error ' + traceback.format_exc(limit=0) + ', price unchanged!')
		return False

	blockNumber = init.w3.toInt(hexstr=dict['result'][0]['blockNumber'])
	txIx = init.w3.toInt(hexstr=dict['result'][0]['transactionIndex'])
	log_data = dict['result'][0]["data"][2:]
	liquidity = init.w3.toInt(hexstr=log_data[:64])
	amount0 = init.w3.toInt(hexstr=log_data[64:128])
	amount1 = init.w3.toInt(hexstr=log_data[128:192])

	return liquidity

#N.B. Compute the latest pool price of token1 w.r.t. token0
def current_pool_price(network='mumbai', block_num=None, price_list=[], price_median=0., pool_liquidity_list=[], pool_liquidity_median=0.,\
						price_mad=0., max_price_mad=0.,	priceLower=[], priceUpper=[], swap_volume_token1=[], rel_swap_volume_token1=[], swap_flow_token1=[], init=None):
	#logger.info(pool_liquidity_list)
	signed_token1_quantity = 0.
	headers = {"Accept": "application/json"}
	if init is None:
		init = Initialization(network)

	if block_num is None:

		#get the latest block with the API
		if network == 'ethereum':
			url = 'https://api.etherscan.io/api?module=proxy&action=eth_blockNumber&apikey=' + API_KEY_ETHERSCAN
		elif network == 'kovan':
			url = 'https://api-kovan.etherscan.io/api?module=proxy&action=eth_blockNumber&apikey=' + API_KEY_ETHERSCAN
		elif network == 'goerli':
			url = 'https://api-goerli.etherscan.io/api?module=proxy&action=eth_blockNumber&apikey=' + API_KEY_ETHERSCAN
		elif network == 'polygon':
			url = 'https://api.polygonscan.com/api?module=proxy&action=eth_blockNumber&apikey=' + API_KEY_POLYGONSCAN
		elif network == 'mumbai':
			url = 'https://api-testnet.polygonscan.com/api?module=proxy&action=eth_blockNumber&apikey=' + API_KEY_POLYGONSCAN
	

		try:
			req = requests.get(url, headers)
		except Exception:
			logger.error('requests.get() for the latest block in current_pool_price() failed for url ' + url + ' with error ' + traceback.format_exc(limit=0) + ', price unchanged!')
			return False

		#time.sleep(DELAY_REQUEST_SEC) #N.B. Sometimes json.loads() fails
		try:
			dict = json.loads(req.text)
		except Exception:
			logger.error(network + ', json.loads() for the latest block in current_pool_price() failed for url ' + url + ' with error ' + traceback.format_exc(limit=0) + ', price unchanged!')
			return False
	
		#time.sleep(DELAY_REQUEST_SEC) #N.B. Sometimes json.loads() fails
		try:
			latest_block_num = init.w3.toInt(hexstr=dict['result'])
		except Exception:
			logger.error(network + ', dict["result"] for the latest block in current_pool_price() failed for url ' + url + ' with error ' + traceback.format_exc(limit=0) + ', price unchanged!')
			return False
		logger.info(network + ', latest block number = ' + str(latest_block_num))

	####################################################
	swap_event='0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67'
	#N.B. Get the latest tx-s in the pool: API is limited to 10,000 tx-s, starting  from startblock (if startblock is not specified, it is assumed to be 0)!
	#N.B. Define differently startblock for testnets!
	#N.B. Use "&endblock='latest' in url because latest_block_num can be staled!
	if network == 'ethereum':
		if block_num is None:
			block_num = latest_block_num - 1000
		url = "https://api.etherscan.io/api?module=account&action=tokentx&address=" + POOL_ADDRESS_MAINNET  + "&startblock=" + str(int(block_num)+1) + "&endblock='latest'&page=1&offset=10000&sort=asc&apikey=" + API_KEY_ETHERSCAN
		pool_address = POOL_ADDRESS_MAINNET
	if network == 'kovan':
		if block_num is None:
			block_num = latest_block_num - 1000000
		url = "https://api-kovan.etherscan.io/api?module=account&action=tokentx&address=" + POOL_ADDRESS_KOVAN + "&startblock=" + str(int(block_num)+1) + "&endblock='latest'&page=1&offset=10000&sort=asc&apikey=" + API_KEY_ETHERSCAN
		pool_address = POOL_ADDRESS_KOVAN
	if network == 'goerli':
		if block_num is None:
			block_num = latest_block_num - 1000000
		url = "https://api-goerli.etherscan.io/api?module=account&action=tokentx&address=" + POOL_ADDRESS_GOERLI + "&startblock=" + str(int(block_num)+1) + "&endblock='latest'&page=1&offset=10000&sort=asc&apikey=" + API_KEY_ETHERSCAN
		pool_address = POOL_ADDRESS_GOERLI
	if network == 'polygon':
		if block_num is None:
			block_num = latest_block_num - 1000
		if EVENT_LOGS:
			if PRICE_ALCHEMY:
				url = "https://polygon-mainnet.g.alchemyapi.io/v2/"  + ALCHEMY_ID_POLYGON
				#N.B. There is no "withMetadata"
				payload = {"id": 1,\
				"jsonrpc": "2.0",\
				"method": "eth_getLogs",
				"params": [{"fromBlock": str(init.w3.toHex(int(block_num)+1)),\
						"toBlock": "latest",\
						"address": POOL_ADDRESS_POLYGON,\
						"topics": [swap_event]}]}
			else:
				#N.B. log API is limited to 1,000/page: https://docs.etherscan.io/api-endpoints/logs
				url = "https://api.polygonscan.com/api?module=logs&action=getlogs&address=" + POOL_ADDRESS_POLYGON + "&topic0=" + str(swap_event) + "&fromBlock=" + str(int(block_num)+1) + "&toBlock='latest'&page=1&offset=1000&apikey=" + API_KEY_POLYGONSCAN
		else:
			if PRICE_ALCHEMY:
				#Alchemy API: https://docs.alchemy.com/reference/alchemy-getassettransfers
				url = "https://polygon-mainnet.g.alchemyapi.io/v2/"  + ALCHEMY_ID_POLYGON
				payload = {"id": 1,\
				"jsonrpc": "2.0",\
				"method": "alchemy_getAssetTransfers",
				"params": [{"fromBlock": str(init.w3.toHex(int(block_num)+1)),\
						"toBlock": "latest",\
						"category": ["erc20"],\
						"withMetadata": True,\
						"excludeZeroValue": True,\
						"order": "asc",\
						"fromAddress": POOL_ADDRESS_POLYGON,\
						#N.B. max=1,000
						"maxCount": "0x3e8" }]}
				payload1 = {"id": 1,\
				"jsonrpc": "2.0",\
				"method": "alchemy_getAssetTransfers",\
				"params": [{"fromBlock": str(init.w3.toHex(int(block_num)+1)),\
						"toBlock": "latest",\
						"category": ["erc20"],\
						"withMetadata": True,\
						"excludeZeroValue": True,\
						"order": "asc",\
						"toAddress": POOL_ADDRESS_POLYGON,\
						#N.B. max=1,000
						"maxCount": "0x3e8" }]}
		
			else:
				#N.B. token transfer tx-s API is limited to 10,000/page: https://docs.etherscan.io/api-endpoints/accounts
				url = "https://api.polygonscan.com/api?module=account&action=tokentx&address=" + POOL_ADDRESS_POLYGON + "&startblock=" + str(int(block_num)+1) + "&endblock='latest'&page=1&offset=10000&sort=asc&apikey=" + API_KEY_POLYGONSCAN
			pool_address = POOL_ADDRESS_POLYGON
	if network == 'mumbai':
		if block_num is None:
			block_num = latest_block_num - 10000000
		url = "https://api-testnet.polygonscan.com/api?module=account&action=tokentx&address=" + POOL_ADDRESS_MUMBAI + "&startblock=" + str(int(block_num)) + "&endblock='latest'&page=1&offset=10000&sort=asc&apikey=" + API_KEY_POLYGONSCAN
		pool_address = POOL_ADDRESS_MUMBAI
		

	#time.sleep(DELAY_REQUEST_SEC) #N.B. Sometimes json.loads() fails
	
	if PRICE_ALCHEMY:
		try:
			req = requests.post(url, json=payload, headers=headers)
			if not EVENT_LOGS:
				req1 = requests.post(url, json=payload1, headers=headers)
		except Exception:
			logger.error(network + ', requests.post() in current_LP_positions() failed for url ' + url + ' with error ' + traceback.format_exc(limit=0) + ', price unchanged!')
			return False
		try:
			dict = req.json()
			if not EVENT_LOGS:
				dict1 = req1.json()
		except Exception:
			logger.error(network + ', req.json() in current_LP_positions() failed for url ' + url + ' with error ' + traceback.format_exc(limit=0) + ', price unchanged!')
			return False
	else:
		try:
			req = requests.get(url, headers)
		except Exception:
			logger.error(network + ', requests.get() in current_LP_positions() failed for url ' + url + ' with error ' + traceback.format_exc(limit=0) + ', price unchanged!')
			return False
		#logger.info(network + ', req.text =' + req.text)
		try:
			dict = req.json() #json.loads(req.text)
		except Exception:
			logger.error(network + ', req.json() in current_LP_positions() failed for url ' + url + ' with error ' + traceback.format_exc(limit=0) + ', price unchanged!')
			return False

############################################################################################################
	GMTtimeStamp, blockNumber, txIx, token0_quantity, token1_quantity, longShort = None, None, None, None, None, None
	try:
		if EVENT_LOGS:
			data = dict['result'] #list
			#logger.info(network + ', data =' + str(data))
			if len(data) == 0:
				logger.info(network + ', no swaps in this batch, swap logs processed = len(data) = 0' +\
						 ' from blockNumber=' + str(int(block_num) + 1) + ' to latest block, in current_pool_price(), price unchanged!')
				return True
			#N.B. Sorting, if there is > 1 entry!
			elif len(data) > 1:
			#N.B. Counter-intuitively, when there is > 1 criteria to sort, we have to sort first by the 2nd criteria: https://docs.python.org/3/howto/sorting.html#sortinghowto
			#N.B. If I use 'init.w3.toInt(hexstr=', sorting generates ValueError: invalid literal for int() with base 16: '0x'
			#N.B. Tx-s in the same block are naturally ordered by txIx. Sometimes, data[i]["transactionIndex"] = '0x'
			#	data.sort(key=lambda d: d['transactionIndex'])
				data.sort(key=lambda d: d['blockNumber'])
			len_data = len(data) + 1
		else:
			if PRICE_ALCHEMY:
				#N.B. key 'result' is replaced by 'error' (when failure) and returs an error when calling dict['result']
				data = dict['result']['transfers'] #list
				#N.B. Need data1 for a check later
				data1 = dict1['result']['transfers'] #list
				data += data1
				#N.B. Counter-intuitively, when there is > 1 criteria to sort, we have to sort first by the 2nd criteria: https://docs.python.org/3/howto/sorting.html#sortinghowto
				#N.B. My hypothesis is that tx-s are already ordered properly in the same block?
				#data.sort(key=lambda d: d['hash'])
				data.sort(key=lambda d: int(d['blockNum']))
			
			else:
				data = dict['result'] #list
				data.sort(key=lambda d: int(d['transactionIndex']))
				data.sort(key=lambda d: int(d['blockNumber']))
			len_data = len(data)
			if len(data) <= 1:
				logger.info(network + ', no swaps in this batch, tx processed=len(data) <=1' +\
						 ' from blockNumber=' + str(int(block_num) + 1) + ' to latest block, in current_pool_price(), price unchanged!')
				return True

		i = 0
		while i < len_data - 1:
			if EVENT_LOGS:
				#logger.info(network + ', data[i]=' + str(data[i]))
				blockNumber = init.w3.toInt(hexstr=data[i]["blockNumber"])
				#N.B. Sometimes, data[i]["transactionIndex"] = '0x'
				try:
					txIx = init.w3.toInt(hexstr=data[i]["transactionIndex"])
				except:
					txIx = 0
				#N.B. The swap event logs API returns ['data'] has 5 quantities in hex, 64 characters each:
				#N.B. (token0 quantity, token1 quantity, sqrtPriceX96, liquidity, tick)
				#logger.info(str(GMTtimeStamp) + ', ' + str(blockNumber) + ', ' + str(txIx))
				log_data = data[i]["data"][2:]
				#N.B. For converting numbers < 0 to hex: https://math.stackexchange.com/questions/408761/hexadecimal-value-of-a-negative-number
				if init.w3.toInt(hexstr=log_data[0]) < 8: #N.B. identifying negative numbers in hex: https://stackoverflow.com/questions/33629416/how-to-tell-if-hex-value-is-negative
					longShort = 1
					token0_quantity = init.w3.toInt(hexstr=log_data[:64]) #N.B. dec > 0
					token1_quantity = [negative_numbers_dict[i] for i in log_data[64:128]] #N.B. dec < 0
					token1_quantity = init.w3.toInt(hexstr=''.join(token1_quantity)) + 1
				else:
					longShort = -1
					token0_quantity = [negative_numbers_dict[i] for i in log_data[:64]] #N.B. dec < 0
					token0_quantity = init.w3.toInt(hexstr=''.join(token0_quantity)) + 1
					token1_quantity = init.w3.toInt(hexstr=log_data[64:128]) #N.B. dec > 0

				token0_quantity /= 10**init.token0_decimal
				token1_quantity /= 10**init.token1_decimal
				swap_price = token0_quantity / token1_quantity
				#N.B. Get swap price before pool fee!
				if longShort == 1:
					swap_price *= 1. - init.pool_fee / 1000000
				elif longShort == -1:
					swap_price /= 1. - init.pool_fee / 1000000

				sqrtPriceX96 = init.w3.toInt(hexstr=log_data[128:192])
				#N.B. price = (sqrtPriceX96 / 2^96)^2 https://docs.uniswap.org/sdk/guides/fetching-prices
				#N.B. Compute the pool price of token1 w.r.t. token0
				price = 1. / (sqrtPriceX96 / 2**96)**2 / 10**init.token0_decimal * 10**init.token1_decimal
				pool_liquidity =  init.w3.toInt(hexstr=log_data[192:256])
									
				if not PRICE_ALCHEMY:
					GMTtimeStamp = datetime.datetime.utcfromtimestamp(init.w3.toInt(hexstr=data[i]["timeStamp"]))
					GMTtimeStamp = GMTtimeStamp.strftime('%Y-%m-%d %H:%M:%S')
				
				if blockNumber is None:
					logger.warning(network + ', blockNumber is None when reading logs in pool! Next tx...')
					i += 1
					continue
			else:
			#N.B. Take into account only swap tx-s (not LP tx-s!): LP tx-s ratio of tokens does not mean price!
				if data[i]["hash"] == data[i+1]["hash"] and (data[i]["from"] == data[i+1]["to"] or data[i]["to"] == data[i+1]["from"]):
					if PRICE_ALCHEMY:
						GMTtimeStamp = data[i]["metadata"]["blockTimestamp"]
						blockNumber = data[i]["blockNum"]
						blockNumber = init.w3.toInt(hexstr=blockNumber)
						if blockNumber is None:
							logger.warning(network + ', blockNumber is None when reading tx-s in pool! Next tx...')
							i += 1
							continue
						token_symbol = data[i]["asset"]
						next_token_symbol = data[i+1]["asset"]
					else:
						GMTtimeStamp = datetime.datetime.utcfromtimestamp(int(data[i]["timeStamp"]))
						GMTtimeStamp = GMTtimeStamp.strftime('%Y-%m-%d %H:%M:%S')
						blockNumber = data[i]["blockNumber"]
						txIx = data[i]["transactionIndex"]
						if GMTtimeStamp is None or blockNumber is None or txIx is None:
							logger.warning(network + ', GMTtimeStamp or blockNumber or txIx is None when reading tx-s in pool! Next tx...')
							i += 1
							continue
						token_symbol = data[i]["tokenSymbol"]
						next_token_symbol = data[i+1]["tokenSymbol"]
				
					if token_symbol == init.token0_symbol:
						try:
							#print(data[i]["value"], data[i]["tokenDecimal"])
							token0_quantity = float(data[i]["value"])
							if not PRICE_ALCHEMY:
								token0_quantity /= 10. ** float(data[i]["tokenDecimal"])
						except:
							logger.error('Error in tokenQuantity0 (when token0_symbol) in current_pool_price(), next tx!')
							i += 1
							continue
						if token0_quantity is None:
							logger.warning(network + ', token0_quantity is None when reading tx-s in pool, next tx...')
							i += 1
							continue
				
						if next_token_symbol == init.token1_symbol:
							try:
								token1_quantity = float(data[i+1]["value"])
								if not PRICE_ALCHEMY:
									token1_quantity /= 10. ** float(data[i+1]["tokenDecimal"])
							except:
								logger.error(network + ', error in tokenQuantity1 (when token0_symbol) in current_pool_price(), next tx...')
								i += 1
								continue
							if token1_quantity is None:
								logger.warning(network + ', token1_quantity is None  (when token0_symbol)  in current_pool_price(), next tx...')
								i += 1
								continue
					
							if data[i]["from"] == pool_address.lower():
								longShort = -1
							elif str(data[i]["to"]) == pool_address.lower():
								longShort = 1
							else:
								logger.warning(network + ', pool_address is neither data[i]["from"] nor data[i]["to"], next tx...')
								i += 1
								continue
							#print(data[i+1]["value"], data[i+1]["tokenDecimal"])
							i += 1
					elif token_symbol == init.token1_symbol:
						try:
							token1_quantity = float(data[i]["value"])
							if not PRICE_ALCHEMY:
								token1_quantity /= 10. ** float(data[i]["tokenDecimal"])
						except:
							logger.error(network + ', error in tokenQuantity1 (when token1_symbol) in current_pool_price(), next tx...')
							i += 1
							continue
						if token1_quantity is None:
							logger.warning(network + ', token1_quantity is None (when token1_symbol) in current_pool_price(), next tx...')
							i += 1
							continue

						if next_token_symbol == init.token0_symbol:
							try:
								#print(data[i+1]["value"], data[i+1]["tokenDecimal"])
								token0_quantity = float(data[i+1]["value"])
								if not PRICE_ALCHEMY:
									token0_quantity /= 10. ** float(data[i+1]["tokenDecimal"])
							except:
								logger.error(network + ', error in token0_quantity (when token1_symbol) in current_pool_price(), price unchanged!')
								return False
							if token0_quantity is None:
								logger.warning(network + ', token0_quantity is None when reading tx-s in pool! Next tx...')
								i += 1
								continue
							if str(data[i]["from"]) == pool_address.lower():
								longShort = 1
							elif str(data[i]["to"]) == pool_address.lower():
								longShort = -1
							else:
								logger.warning(network + ', pool_address is neither data[i]["from"] nor data[i]["to"], next tx...')
								i += 1
								continue
							#print(data[i]["value"], data[i]["tokenDecimal"])
							i += 1

					#print(GMtimeStamp, blockNumber, txIx, token0_quantity, token1_quantity, longShort)
				else:
					GMTtimeStamp, blockNumber, txIx, token0_quantity, token1_quantity, longShort = None, None, None, None, None, None

			#N.B. Sometimes Quantity1=0 (Price=0) or Quantity0=0 (division by 0)
			if token0_quantity is not None and token0_quantity != 0. and token1_quantity is not None and\
				blockNumber is not None and longShort is not None:

				signed_token1_quantity += longShort * token1_quantity
				if EVENT_LOGS:
					price_DECIMAL = price * 10**init.token0_decimal / 10**init.token1_decimal
					for j in range(NUM_LP):
						if priceLower[j] is not None and price_DECIMAL >= priceLower[j] and priceUpper[j] is not None and price_DECIMAL <= priceUpper[j]:
							rel_swap_volume_token1[j] += token1_quantity / pool_liquidity
				else:
					#N.B. Compute the pool price of token1 w.r.t. token0
					price = token0_quantity / token1_quantity
					#N.B. Get swap price before charging pool fees
					if longShort == 1:
						price *= 1. - init.pool_fee / 1000000
					elif longShort == -1:
						price /= 1. - init.pool_fee / 1000000
					swap_price = price
					price_DECIMAL = price * 10**init.token0_decimal / 10**init.token1_decimal
					if len(price_list) > 0 and price != price_list[-1]:
						pool_liquidity = abs(token1_quantity / (1 / np.sqrt(price) - 1 / np.sqrt(price_list[-1])) )
						#N.B. liquidity decimal is by definition = 0.5 * (init.token0_decimal + init.token1_decimal)
						pool_liquidity *= 10 ** (0.5 * (init.token0_decimal + init.token1_decimal))
						for j in range(NUM_LP):
							if priceLower[j] is not None and price_DECIMAL >= priceLower[j] and priceUpper[j] is not None and price_DECIMAL <= priceUpper[j]:
								rel_swap_volume_token1[j] +=\
								   abs(1 / np.sqrt(price) - 1 / np.sqrt(price_list[-1]) ) / 10 ** (0.5 * (init.token0_decimal + init.token1_decimal))

				for j in range(NUM_LP):
					if priceLower[j] is not None and price_DECIMAL >= priceLower[j] and priceUpper[j] is not None and price_DECIMAL <= priceUpper[j]:
						swap_volume_token1[j] += token1_quantity
						swap_flow_token1[j] += longShort * token1_quantity
				
				#N.B. Can not use '+=' on a list!
				pool_liquidity_list.append(pool_liquidity)
				if len(pool_liquidity_list) > MAX_CARDINALITY_LIST:
					pool_liquidity_list.pop(0)
				#logger.info(swap_volume_token1)
				if PRICE_ALCHEMY:
					price_condition = token1_quantity > MIN_TOKEN1_QUANTITY
				else:
					price_condition = txIx is not None and int(txIx) <= MAX_TX_IX and token1_quantity > MIN_TOKEN1_QUANTITY

				if price_condition:
					#N.B. Can not take into account last price when computing price_median
					if len(price_list) > NUM_OBSERVATIONS_MEDIAN:
						price_median = statistics.median(price_list[-NUM_OBSERVATIONS_MEDIAN:])
						pool_liquidity_median = statistics.median(pool_liquidity_list[-NUM_OBSERVATIONS_MEDIAN:])
						if len(price_list) > 1:
							diff_log_price = np.diff(np.log(price_list[-NUM_OBSERVATIONS_MEDIAN:]))
							price_mad = 1.4826 * statistics.median([abs(p - statistics.median(diff_log_price)) for p in diff_log_price])
							if price_mad > max_price_mad:
								max_price_mad = price_mad

					if (price_median == 0. or abs(price / price_median - 1.) < MAX_PRICE_RETURN_PER / 100):
						#N.B. Can not use '+=' on a list!
						price_list.append(price)
						if len(price_list) > MAX_CARDINALITY_LIST:
							price_list.pop(0)
						#N.B. Only the last lines are printed in the log
						if (len_data - 1 > 0 and len_data - 1 <= 100) or (len_data - 1 > 100 and i > len_data - 100):
							out_line = network + ", tx processed " + str(len(data)) \
								+ ", block=" + str(blockNumber) + ", txIx=" + str(txIx)\
								+ ", p=" + "{:1.5f}".format(price_list[-1]) \
								+ ", swap p=" + "{:1.5f}".format(swap_price) \
								+ ", p med=" + "{:1.5f}".format(price_median)\
								+ ", p_mad=" + "{:1.5f}".format(price_mad)\
								+ ", tok1_q=" + "{:1.2f}".format(token1_quantity)\
								+ ", signed_tok1_q=" + "{:1.2f}".format(signed_token1_quantity)\
								+ ", LS=" + str(longShort)\
								+ ", pool liq=" + "{:1.0f}".format(pool_liquidity_list[-1] / 10 ** (0.5 * (init.token0_decimal + init.token1_decimal)))\
								+ ", pool liq med=" + "{:1.0f}".format(pool_liquidity_median / 10 ** (0.5 * (init.token0_decimal + init.token1_decimal)))\
								#+ ", volume tok1 (since LP)=" + "{:1.1f}".format(swap_volume_token1)\
								#+ ", flow tok1 (since LP)=" + "{:1.1f}".format(swap_flow_token1)
							logger.info(out_line)
						#else:
						#	out_line = network + ', price unchanged!'
						#	logger.info(out_line)
						#	return True
					else:
						logger.warning(network + ', price=' + str(token0_quantity / token1_quantity) +\
							', price_median=' + str(price_median) +\
							', abs(token0_q / token1_q / price_median - 1.) >= MAX_PRICE_RETURN_PER / 100, price:=None (not added to price_list), next tx...')
						price = None
						i += 1
						continue
					
			#else:
			#	logger.warning(network + ', no swap tx-s, next tx...')
			#	i += 1
			#	continue
			
			i += 1
			#N.B. End of data loop


		#N.B. The Alchemy API returns max 1,000 tx-s/page
		if EVENT_LOGS:
			if PRICE_ALCHEMY:
				if len(data) == 10000:
					logger.error(network + ', len(data) == 10,000, need smaller block number difference, price unchanged!')
					price_list += [None]
			else:
				if len(data) == 1000:
					logger.error(network + ', len(data) == 1,000, need smaller block number difference, price unchanged!')
					price_list += [None]

		else:
			if PRICE_ALCHEMY:
				#N.B. The two lists are combined into data
				if len(data) >= 2000 or len(data1) >= 1000:
					logger.error(network + ', len(data)=2,000 or len(data1)=1,000 , need smaller block number difference, price unchanged!')
					price_list += [None]
			else:
				#N.B. The Etherscan API returns max 10,000 tx-s/page. They are at the beginning, not the end, so if pool tx-s are > 10,000, price can be stale!
				if len(data) == 10000:
					logger.error(network + ', len(data) == 10,000, need smaller block number difference, price unchanged!')
					price_list += [None]

		#if blockNumber is None:
		#	logger.info(network + ', there were no swap tx-s in this batch, len(data)=' + str(len(data)) +\
		#	   ', from blockNumber=' + str(int(block_num) + 1) + ' to latest block, in current_pool_price(), price unchanged!')
		#	return False
	except:
		logger.error(network + ", error in data retrieval in current_pool_price() " + traceback.format_exc(limit=0) +", price unchanged!")
		#logger.error('dict["Status"] = 0 in current_pool_price() for url ' + url + ', price unchanged!')
		return False

	
	return [GMTtimeStamp, blockNumber, txIx, price_list, price_median, pool_liquidity_list, pool_liquidity_median, signed_token1_quantity,\
				price_mad, max_price_mad, swap_volume_token1, rel_swap_volume_token1, swap_flow_token1]


def delay_error(network, init, tx_hash):
	tx_receipt = {'status': 0}

	#logger.error(network + ', Wait for DELAY_REQUEST_SEC = ' + str(DELAY_REQUEST_SEC) + 's and continue')

	for i in range(DELAYED_ERR_NUM_ITERATIONS):
		#N.B. wait!
		time.sleep(DELAY_REQUEST_SEC)
		try:
			tx_receipt = init.w3.eth.get_transaction_receipt(tx_hash)
			break
		except:
			#N.B. If tx is not mined, return {'status': 0}!
			logger.error(network + ', get_transaction_receipt() in decreaseLiquidity() failed after DELAY_REQUEST_SEC = ' +\
					str(DELAY_REQUEST_SEC) + ' with error ' + traceback.format_exc(limit=0) + '. Attempt' + str(i+1) + ' of ' + str(DELAYED_ERR_NUM_ITERATIONS) )
	
	return tx_receipt



#def current_pool_price(network='mumbai', address=ADDRESS_TESTNET):
#	init = Initialization(network)
#	c_pool = Contract(network, init.w3, 'Pool')
#	#c_pool.contract.all_functions()
    
#	nonce = init.w3.eth.get_transaction_count(address)
#	slot0_tx = c_pool.contract.functions.slot0().build_transaction({
#        "chainId": init.networkId,
#        "from": address,
#        #N.B. Smaller gas price results in slow execution!
#        #"gasPrice": w3.toHex(int(5e9)), #N.B. Commenting out gasPrice uses market GasPrice & makes the tx "Type 2: EIP-1559" (as opposed to "Legacy" when un-commented) 
#        "gas": init.w3.toHex(int(1e6)), #, #500000,
#        "nonce": nonce
#    })

#	signed_tx = init.w3.eth.account.sign_transaction(slot0_tx, private_key=PRIVATE_KEY)
#	tx_hash = init.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
#	try:
#		tx_receipt = init.w3.eth.wait_for_transaction_receipt(tx_hash, timeout = TIMEOUT_SEC)
#	except:
#		logger.error(network + ", error .TimeExhausted in w3.eth.wait_for_transaction_receipt in current_pool_price(). Stop main()!")
#		return False

       
#	if tx_receipt['status'] == 0:
#		logger.error(network + ', tx slot0() failed! Tx receipt %s. Stop main()!', tx_receipt)
#		return False
#	else:
#		slot0_tx.sqrtPriceX96


if __name__ == '__main__':
	if len(sys.argv) == 1: # no inputs
		current_LP_positions('mumbai')
	elif len(sys.argv) == 2: #network
		current_LP_positions(network=str(sys.argv[1]))
	elif len(sys.argv) == 3: #network, address
		current_LP_positions(str(sys.argv[1]), str(sys.argv[2]))
	else:
		print("Wrong number of inputs!")