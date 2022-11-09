TEST = False
############################################
#Model

if TEST:
	NUM_LP, RUNTIME_SEC = 1, 60
	NUM_TOKEN0_LP, NUM_TOKEN1_LP  = 1, 0.001
	LP_DISTANCE_TO_BOUND_PER = [50, 70]
	UNWIND_DIST_TO_BOUND_PER = [(10, 10)]
	#INCREASE_LIQUIDITY = False
	#HEDGE_RL, HEDGE_RL_THRESHOLD_BP = False, 1
	STOP_LOSS_BP, STOP_PROFIT_BP = 10000, 10000
	#UNWIND_ASSET_RATIO_PER = 10
	MIN_UNWIND_SWAP_VOLUME_TOKEN1, MIN_UNWIND_SWAP_FLOW_PER = 50, 50
	PRICE_MAD = [100, 1000]
	MIN_INIT_TOKEN1_QUANTITY_TO_TVL_BP, MAX_UNWIND_TOKEN1_QUANTITY_TO_TVL_BP = 10000, 10000
	MIN_INIT_AFTER_BLOCKS, MIN_INIT_AFTER_PRICE_RET_BP = 0, 0
	MIN_POOL_LIQUIDITY_PER = [1000, 0]
	LP_SWAP, LP_SWAP_MULT_RUNTIME, LP_SWAP_DISTANCE_TO_BOUND_PER, LP_SWAP_UNWIND_DISTANCE_PER, LP_SWAP_MAX_ATTEMPTS_FAILED_TX = False, 2, 0.05, 0.25, 5
	MIN_SESSION_SWAP_PER, MIN_TX_BATCH_SWAP_PER, SWAP_EPSILON_PER = 10000, 0, 0.
	#DECREASE_ONLY_UNWIND_DIST_TIME_MIN = 0
	#SWAP_FLOW_THRESHOLD_PER = 30
	MAX_ATTEMPS_FAILED_TX = 3
	MULT_GAS_FACTOR_REPLACE, MAX_MULT_FACTOR_GAS_REPLACE = 5, 20
	SLIPPAGE_PER, MAX_SLIPPAGE_PER = 5, 50
	DELAY_LOOP_SEC = 10
	EXPIRY_SEC, TIMEOUT_SEC = 60, 1800
	MAX_QUANTITY0_SWAP_ITERATION, DELAY_SWAP_ITERATION_SEC = 1000, 10 #NUM_TOKEN0_LP / 3, 10
	MAX_TX_IX, MIN_TOKEN1_QUANTITY = 10000, 0
	MAX_PRICE_RETURN_PER = 10000000
	#PRICE_MAD_WAIT_TIME_MIN = 0
else:
	NUM_LP, RUNTIME_SEC = 1, 72000 #N.B. Running time of the loop (loop runs longer because tx executions take time)
	assert NUM_LP % 2 == 1
	NUM_TOKEN0_LP, NUM_TOKEN1_LP = 10, 0.01
	#N.B. UNWIND_DIST_TO_BOUND_PER is more robust than UNWIND_ASSET_RATIO_PER because the distance does not depend on price_LP (which could be very different than API pool prices)
	##UNWIND_ASSET_RATIO_PER = 80
	LP_DISTANCE_TO_BOUND_PER = [0.15, 0.15] #2-nd is for begining-to-end of quiet hours, 1-st otherwise!
	UNWIND_DIST_TO_BOUND_PER = [(-0.15, -0.15)] #N.B. Unwind j-th tx if its dist-to-...-bound < dist-to-...-bound; smaller UNWIND_DIST_TO_BOUND_PER do not incure OTM loss!
	assert len(UNWIND_DIST_TO_BOUND_PER) == NUM_LP
	#N.B. Make sure that LP tx does not unwind immediately!
	if NUM_LP > 1:
		assert min([-UNWIND_DIST_TO_BOUND_PER[0][1], -UNWIND_DIST_TO_BOUND_PER[-1][0]]) >= NUM_LP * 2 * max(LP_DISTANCE_TO_BOUND_PER)
	#INCREASE_LIQUIDITY = False #N.B. This flag is for increaseLiquidity() without mint(); not working properly: after execution, has to goes straight to mint(), without decreaseLiquidity() but not otherwise!
	#HEDGE_RL, HEDGE_RL_THRESHOLD_BP = False, 0.05
	STOP_LOSS_BP, STOP_PROFIT_BP = 25, 25
	MIN_UNWIND_SWAP_VOLUME_TOKEN1, MIN_UNWIND_SWAP_FLOW_PER = 10000, 10000
	PRICE_MAD = [10000., 0., 0.001] #[0.0001, 0.00015, 0.0002] #N.B. 1st is max for a new LP position, 2nd is min for hedging RL, last is min for unwinding the LP position
	MIN_INIT_TOKEN1_QUANTITY_TO_TVL_BP, MAX_UNWIND_TOKEN1_QUANTITY_TO_TVL_BP = -10000., 10000. #0.04, 0.04 #N.B. 1st in min for a new LP position; 2nd is max for unwinding LP position;
	MIN_INIT_AFTER_BLOCKS, MIN_INIT_AFTER_PRICE_RET_BP = 0, 0 #150, 5 
	MIN_POOL_LIQUIDITY_PER = [50, 50] #[99, 95] #N.B. 1st is min for a new LP position (w.r.t pool liq median), 2nd is min for unwinding the LP position;
	LP_SWAP, LP_SWAP_MULT_RUNTIME, LP_SWAP_DISTANCE_TO_BOUND_PER, LP_SWAP_UNWIND_DISTANCE_PER, LP_SWAP_MAX_ATTEMPTS_FAILED_TX = False, 2, 0.1, 0.25, 2 #N.B. Execute swaps with LP;
	assert LP_SWAP_UNWIND_DISTANCE_PER /  LP_SWAP_DISTANCE_TO_BOUND_PER >= 5
	MIN_SESSION_SWAP_PER, MIN_TX_BATCH_SWAP_PER, SWAP_EPSILON_PER = 100, 1000000, 10 #N.B. execute swaps only if abs(amount_to_swap_token0) >
	assert MIN_SESSION_SWAP_PER * MIN_TX_BATCH_SWAP_PER > 1000000 #N.B. Only one swap type is allowed: either session or tx batch!
	#DECREASE_ONLY_UNWIND_DIST_TIME_MIN = 30 #N.B.
	#SWAP_FLOW_THRESHOLD_PER = 30
	MAX_ATTEMPS_FAILED_TX = 5
	assert MAX_ATTEMPS_FAILED_TX > LP_SWAP_MAX_ATTEMPTS_FAILED_TX
	MULT_GAS_FACTOR_REPLACE, MAX_MULT_FACTOR_GAS_REPLACE = 2, 10
	SLIPPAGE_PER, MAX_SLIPPAGE_PER = 1, 5 #N.B. If slippage is too low, get error 'Too little received'
	DELAY_LOOP_SEC = 1
	#N.B. If tx-s are pending > 5 mins, they usualy fail with  'Transaction too old'
	EXPIRY_SEC, TIMEOUT_SEC = 300, 300 #N.B. 1st is used for deadline (cancel after) in mint, decreaseLiquidity; 2nd is used in .wait_for_transaction_receipt (if TIMEOUT_SEC=0,  w3.eth.wait_for_transaction_receipt returns error TimeExhausted)
	MAX_QUANTITY0_SWAP_ITERATION, DELAY_SWAP_ITERATION_SEC = 3000, 5 #N.B. Swap size-splitting assumes that token0 price ~ 1
	#N.B. The min of Quantity1 for WMATIC/WETH Uniswap v3 Polygon pools (data from Jan to Jun 2022) is reached at 0.5 WETH!
	MAX_TX_IX, MIN_TOKEN1_QUANTITY = 10000, 0.05 #min block position, min token1 quantity of tx when computing current pool price
	MAX_PRICE_RETURN_PER = 1 #N.B. used in current_pool_price(): larger numbers result is bad prices! 
	#PRICE_MAD_WAIT_TIME_MIN = 10

MAX_FEE_PER_GAS = int(1000e9) #N.B. Set to 1,000 Gwei the max amount of gas/unit (set to 100 Gwei on Ethereum, if I have only 0.1 ETH)
MAX_PRIORITY_FEE_PER_GAS = int(30e9) #on Polygon the minimum that works is 30 Gwei/unit; on Ethereum 5 Gwei/unit works (the fee is gone)
MAX_GAS_UNITS = int(1e6) #N.B. Decreasing this fails even for burn() on ethereum
DELAYED_ERR_NUM_ITERATIONS = 10
NUM_OBSERVATIONS_MEDIAN, MAX_CARDINALITY_LIST = 30, 50
assert MAX_CARDINALITY_LIST > NUM_OBSERVATIONS_MEDIAN
#N.B. US market Open and Close and US macro-economic announcements (8:30 EDT) are quiet hours
#N.B. i) higher LP_distance_to_bound from beginning to end of quiet hours
#N.B. ii) do not initiate & unwind positions during quiet hours: https://docs.python.org/3/library/time.html#functions
QUIET_HOURS_START, QUIET_HOURS_END = [14, 20], [14, 20]
assert len(QUIET_HOURS_START) == len(QUIET_HOURS_END)
DELAY_NONCE_SEC = 3
DELAY_REQUEST_SEC = 10
EPSILON = 0.0001 #N.B. Used in asset_ratio_01

############################################
#Encryption
SALT_SIZE =16

############################################
#N.B. Personal
#N.B. Get destination address from wallet
ADDRESS_MAINNET = '0x152D206474a0242cc242011b08d9082103a53E43'
ADDRESS_POLYGON = '0xd12954646A9A468EEC2E331Ad300c7d4dcB01EA4'
ADDRESS_TESTNET = '0x81f991E9d7a2bd2146Cc68F831f806187eA9b5ae'

#N.B. Get the private key string from wallet acct
PRIVATE_KEY = '172e6be936e1151c7d8fc448e0e27007f4a0d93f4cf1ecbc3c926a07d6ab6448' #testnets
 
#################
#N.B. Uniswap v3 networks, tokens, pools
TOKEN0_SYMBOL_MAINNET, TOKEN0_ADDRESS_MAINNET, TOKEN0_DECIMAL_MAINNET = 'CRV','0xD533a949740bb3306d119CC777fa900bA034cd52', 6
TOKEN1_SYMBOL_MAINNET, TOKEN1_ADDRESS_MAINNET, TOKEN1_DECIMAL_MAINNET = 'WETH', '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', 18
#UNWIND_DISTANCE_PRICE_MAD_MULT_MAINNET = 1
POOL_ADDRESS_MAINNET, POOL_FEE_MAINNET = '0x4c83A7f819A5c37D64B4c5A2f8238Ea082fA1f4e', 10000 #CRV / ETH 1% pool

################
TOKEN0_SYMBOL_KOVAN, TOKEN0_ADDRESS_KOVAN, TOKEN0_DECIMAL_KOVAN = 'DAI','0x4F96Fe3b7A6Cf9725f59d353F723c1bDb64CA6Aa', 18 
TOKEN1_SYMBOL_KOVAN, TOKEN1_ADDRESS_KOVAN, TOKEN1_DECIMAL_KOVAN = 'WETH', '0xd0A1E359811322d97991E03f863a0C30C2cF029C', 18
#UNWIND_DISTANCE_PRICE_MAD_MULT_KOVAN = 1
POOL_ADDRESS_KOVAN, POOL_FEE_KOVAN = '0x89007E48d47484245805679Ab37114DB117AfAB2', 3000 #DAI / ETH 0.3% pool

################
#TOKEN0_SYMBOL_GOERLI, TOKEN0_ADDRESS_GOERLI, TOKEN0_DECIMAL_GOERLI = 'DAI','0xdc31Ee1784292379Fbb2964b3B9C4124D8F89C60', 18
TOKEN0_SYMBOL_GOERLI, TOKEN0_ADDRESS_GOERLI, TOKEN0_DECIMAL_GOERLI = 'USDC', '0xD87Ba7A50B2E7E660f678A895E4B72E7CB4CCd9C', 6
TOKEN1_SYMBOL_GOERLI, TOKEN1_ADDRESS_GOERLI, TOKEN1_DECIMAL_GOERLI = 'WETH', '0xB4FBF271143F4FBf7B91A5ded31805e42b2208d6', 18
#UNWIND_DISTANCE_PRICE_MAD_MULT_GOERLI = 1
#POOL_ADDRESS_GOERLI = '0x9A22f5f70D02A83bF91034dBc8028cf7a741375f' #DAI / ETH 0.3% pool
POOL_ADDRESS_GOERLI, POOL_FEE_GOERLI = '0x04B1560f4F58612a24cF13531F4706c817E8A5Fe', 3000 #USDC / ETH 0.3 % POOL

#################
TOKEN0_SYMBOL_POLYGON, TOKEN0_ADDRESS_POLYGON, TOKEN0_DECIMAL_POLYGON = 'USDC', '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174', 6
#TOKEN0_SYMBOL_POLYGON, TOKEN0_ADDRESS_POLYGON, TOKEN0_DECIMAL_POLYGON = 'WMATIC', '0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270', 18
TOKEN1_SYMBOL_POLYGON, TOKEN1_ADDRESS_POLYGON, TOKEN1_DECIMAL_POLYGON = 'WETH', '0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619', 18
#UNWIND_DISTANCE_PRICE_MAD_MULT_POLYGON = 10000
#POOL_ADDRESS_POLYGON, POOL_FEE_POLYGON = '0x167384319B41F7094e62f7506409Eb38079AbfF8', 3000 #MATIC / WETH 0.3% pool
#POOL_ADDRESS_POLYGON, POOL_FEE_POLYGON = '0x86f1d8390222A3691C28938eC7404A1661E618e0', 500 #MATIC / WETH 0.05% pool
#POOL_ADDRESS_POLYGON, POOL_FEE_POLYGON = '0x0e44ceb592acfc5d3f09d996302eb4c499ff8c10', 3000 #USDC / WETH 0.3% pool
POOL_ADDRESS_POLYGON, POOL_FEE_POLYGON = '0x45dDa9cb7c25131DF268515131f647d726f50608', 500  #USDC / WETH 0.05% pool

#################
TOKEN0_SYMBOL_MUMBAI, TOKEN0_ADDRESS_MUMBAI, TOKEN0_DECIMAL_MUMBAI = 'WMATIC', '0x9c3C9283D3e44854697Cd22D3Faa240Cfb032889', 18
TOKEN1_SYMBOL_MUMBAI, TOKEN1_ADDRESS_MUMBAI, TOKEN1_DECIMAL_MUMBAI = 'WETH', '0xA6FA4fB5f76172d178d61B04b0ecd319C5d1C0aa', 18
#UNWIND_DISTANCE_PRICE_MAD_MULT_MUMBAI = 10000
POOL_ADDRESS_MUMBAI, POOL_FEE_MUMBAI = '0xc1FF5D622aEBABd51409e01dF4461936b0Eb4E43', 3000 #MATIC / WETH 0.3% pool

############################################
#addresses of Uniswap deployed contracts are listed in https://docs.uniswap.org/protocol/reference/deployments & are the same for all nets
#ROUTER_ADDRESS = '0xE592427A0AEce92De3Edee1F18E0157C05861564' #SwapRouter.sol 
ROUTER_ADDRESS = '0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45' #SwapRouter02.sol: does not have a deadline, which is needed to cancel the swap!
NPM_ADDRESS = '0xC36442b4a4522E871399CD717aBDD847Ab11FE88' #NonfungiblePositionManager.sol


#############################################
#N.B. connecting nodes & pool price
#N.B. websockets are faster than http connection! #https://www.geeksforgeeks.org/what-is-web-socket-and-how-it-is-different-from-the-http/
#N.B. Connecting through websocket is required to watch events!
NODE_HTTPS, NODE_WEBSOCKET = False, True
assert NODE_HTTPS != NODE_WEBSOCKET
#N.B. Infura https node produced an error at init.w3.eth.get_block('latest')["timestamp"]
NODE_INFURA, NODE_ALCHEMY = False, True
assert NODE_INFURA != NODE_ALCHEMY
#N.B. Infura does not currently have websocket connection for Polygon
if NODE_WEBSOCKET:
	assert NODE_ALCHEMY
#N.B. Logs of swap events are needed in order: 
#N.B. i) to get a good pool price (sqrtPriceX96), without slippage, and 
#N.B. ii) to get a good pool liquidity, and therefore good pool fees, therefore good stop-profit, stop-loss;
EVENT_LOGS, PRICE_ALCHEMY = True, True


#Node keys
INFURA_ID ='851d2aaec9c64e0d8eef1a5091c92e11'
ALCHEMY_ID_MAINNET = '1m_hU9tB6kdF5AzeLleH3zTMAFeUbCuE'
ALCHEMY_ID_GOERLI = 'jYc-ph7JoLhzMFW9Z5931DMZZ9Ygn4uT'
ALCHEMY_ID_POLYGON = 'PgquUWUOppPD9DrAFfjtrrZhnWf7-z8U'
ALCHEMY_ID_MUMBAI = 'BTtwYOtlTK_1tsrOFPJnyBk3_ea51bQd'

#API keys
API_KEY_ETHERSCAN = 'TQR47U65YJ3ZUTH7JQCR9HVTNSFP3A7DDB'
API_KEY_POLYGONSCAN = '6MSYSPDNI98ABGVETDTI4QVPZN33DG1674'

##############################################

DATA_PATH = 'C:\\Users\\galin.georgiev\\GammaDynamics Net\\Dev\\Python\\UniswapV3_LP'
