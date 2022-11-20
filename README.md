Run (from console): python "C:\...\UniswapV3_LP\main.py" polygon

1. ETH is a p&l benchmark. Bot trading is on Uniswap v3 liquid pool token0/WETH (token0 is typically a stable coin) on Polygon network (MATIC ~ 1/1000 ETH & gas is proportional to the network coin, so gas fee on Polygon network  ~ 1/1000 of gas fees on Ethereum network). Addresses of tokens and pools are set up in global_params.py. Token0 is borrowed on Aave (that is why 'borrow p&l' is used), using ETH as a collateral. Borrow p&l of an LP position has 3 summands: i) LP fees >= 0; ii) Rebalancing Loss (RL, a.k.a. Impermanent Loss) <= 0, and < 0 only when the LP position is within the price range (in-the-money or ITM); iii) out-of-the-money (OTM) Loss <= 0, and < 0 only when the LP position is out of the price range (out-of-the-money or OTM) and when any rebalancing took place when the LP position was ITM!


   1.1) When current ETH price < LP price, the borrowed token0 rebalances into WETH (if the LP position is ITM) i.e. the borrowed token0 rebalances back into the ETH (borrow) collateral. In this case, the rebalancing of borrowed token0 into ETH is a sole cause of the RL (if the LP position is ITM) and the OTM Loss (if the LP position is OTM; the latter is ETH loss, if there was rebalancing). So when the benchmark is ETH, both RL & OTM Loss = 0 in a 'borrow p&l', on a relative to ETH scale! 
  
   1.2) When current ETH price > LP price, WETH rebalances into token0 (if the LP position is ITM). Because the benchmark is not token0 (typically, cash) or ETH is not borrowed (collaterilized e.g. by token0), both RL < 0 (if the LP position is ITM) and OTM Loss < 0 (if the LP position is OTM; the latter is token0 loss, if there was rebalancing). So when the benchmark is ETH, both RL & OTM Loss <= 0 on an absolute or relative (to ETH) scale.  


The bot LP positions are stacked to the 'left' of the current ETH price, so they are OTM and have as LP price the upper price bound. When ETH price < LP price (scenario 1.1), both RL & OTM Loss = 0 on a relative (to ETH) scale. When ETH price > LP price (scenario 1.2), the bot LP positions are OTM & there is no rebalancing, so both RL & OTM loss = 0 in any (absolute or relative) scale.
  
2. Need approval: contrary to claims of non-expiry, approval seems to expire once a month - without approval the tx-s receive error (seen on polygonscan.com) 'STF': 'safeTransfer can not be completed'! Under polygonscan.com > WETH ('0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619') & USDC ('0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'), under Contract > Write > Approve (connect to my wallet), approve manually both (ROUTER_ADDRESS, for swaps): 0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45 & (NPM_ADDRESS, for LP tx-s): 0xC36442b4a4522E871399CD717aBDD847Ab11FE88 for an infinite amount: 115792089237316195423570985008687907853269984665640564039457584007913129639935
  
2. The account address has to be specified in global_params.py & the private key to the address is encrypted in a file (in the subdir /accounts) with encrypt_file() in encryption.py. The encryption/decryption requires /accounts/salt.txt. When the bot is run, a password to access the private key is required via decrypt_file(), run at the beginning of main() in main.py. If manual tx-s are executed in the account while the bot is running, decreaseLiquidity(), collect() or burn() will fail with "nonce too low" because they rely on the nonce increment from the previous bot tx. The tx-s should in theory succeed on the next iteration, because nonce = None is passed after failure and therefore w3.eth.get_transaction_count(address) is run!
  
3. The account has to have no NFT-s, in order for the bot to run. NFT-s are burned with burn() - see manual commands below. If all tokens are not collected first (after decreaseLiquidity() on the full liquidity), burn() tx produces error on Polygonscan "Fail with error 'Not cleared'". The ABI-s of the contracts used (all of them on the blockchain, made by Uniswap) are in the subdir /abi.

 
4. A session lasts for RUNTIME_SEC (=72000 iterations currently i.e. when  ~ 24 hours when DELAY_LOOP_SEC = 1).  

Parameters in global_params.py (all global variables are capitalized): the bot initiates NUM_LP LP positions for a total 0.1 = NUM_INVESTED_TOKEN1_LP ETH, each with price range 2 * LP_DISTANCE_TO_BOUND_PER wide, stacked adjacently to the right of the initiation ETH price (LP_position_to_init_price[:NUM_LP] = 1). The bot liquidates them when they are UNWIND_DISTANCE_TO_BOUND_PER  OTM or at the end of the session. In the former case, the bot replaces the old LP position with a new LP position, but only when all LP positions are liquidated. 

Parameters in global_params0.py (if use, rename to global_params.py): the bot initiates NUM_LP = 1 LP positions ~$10  = min(MAX_NUM_TOKEN0_LP, MAX_NUM_TOKEN1_LP * ETH price), with price range 2 * LP_DISTANCE_TO_BOUND_PER[0]  wide, with initiation (current) price immediately above its right price bound. But the bot liquidates/initiates frequently (every ~ 1-20 minutes). Unwinding happens typically because signed WETH / pool_liquidity in the last DELAY_LOOP_SEC (= 1) second exceeds MAX_UNWIND_TOKEN1_QUANTITY_TO_TVL_BP. 

After an LP tx is fully roundtripped (after mint(), decreaseLiquidity(), collect(), burn()), the bot swaps back (see flag LP_SWAP below): i) to the session original amounts, if MIN_SESSION_SWAP_PER is small enough; ii) to the NUM_LP LP tx-s total original amounts, if MIN_TX_BATCH_SWAP_PER is small enough; 
    
5. The updates of the pool price (and therefore all tx-s) happen on every 'main iteration', currently run every DELAY_LOOP_SEC (= 1) seconds. Pool price, p&l and numerous other metrics can be found in the date-of-running log, in the subdir /logs.

6. When a blockchain tx fails MAX_ATTEMPTS_FAILED_TX ( 5 currently), the bot stops, so outstading mints have to be unwound manually - see below.

7. A global flag LP_SWAP = True: attempts LP_SWAP_MAX_ATTEMPTS_FAILED_TX times (currently 2) to avoid pool fee & slippage by swapping via LP position (with the tightest possible price range). LP tx-s are positioned so that always WETH rebalances into borrowed token0 (ETH does not rebalance into unborrwoed token0). So, when the benchmark is ETH, for an LP swap, both RL & OTM Loss = 0 in a 'borrow p&l' on a relative to ETH scale: therefore LP swap can remain as an open LP position fo a long time! When LP_SWAP:
    i) the runtime may increase to max LP_SWAP_MULT_RUNTIME * RUNTIME_SEC (currently 2 * RUNTIME_SEC);
   ii) when LP swap fails LP_SWAP_MAX_ATTEMPTS_FAILED_TX times or the extended end LP_SWAP_MULT_RUNTIME * RUNTIME_SEC is reached, conventional (non-LP) swap is executed.
 
8. Manual commands to unwind the LP positions:

  - NFT-s in the address: python "C:\Users\galin.georgiev\GammaDynamics Net\Dev\Python\UniswapV3_LP\toolbox.py" polygon address (without quotes)
  - to completely unwind (a mint) tx. tokenID & liquidity are required - can be found under polygonscan.com > mint tx > logs > increaseLiquidity. One command runs all 3 separate functions (decreaseLiquidity(), collect() and burn()): python “C:\...\UniswapV3_LP\unwind.py" polygon tokenId liquidity
  - to only decrease liquidity. tokenID & liquidity are required (see above): python “C:\...\UniswapV3_LP\decreaseLiquidity.py" polygon tokenId liquidity
  - to only collect the funds (after decreaseLiquidity() is run). tokenId is required: python "C:\...\UniswapV3_LP\collect.py" tokenId polygon
  - to only burn an NFT with a given tokenId. tokenId is required: python "C:\...\UniswapV3_LP\burn.py" tokenId polygon;

  To get the current NFT-s in the account, run: python "C:\...\UniswapV3_LP\toolbox.py" polygon address.
