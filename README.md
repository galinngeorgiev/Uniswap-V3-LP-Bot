Run (from console): python "C:\...\UniswapV3_LP\main.py" polygon

1. ETH is a p&l benchmark. Bot trading is on Uniswap v3 liquid pool token0/WETH (token0 is usually stable coin) on Polygon network (MATIC ~ 1/1000 ETH & gas is proportional to the network coin, so gas fee on Polygon network  ~ 1/1000 of gas fees on Ethereum network). Addresses of tokens and pools are set up in global_params.py. Token0 is borrowed on Aave (that is why 'borrow p&l' is used), using ETH as a collateral. Borrow p&l of an LP position has 3 summands: i) LP fees >= 0; ii) Rebalancing Loss (RL, a.k.a. Impermanent Loss) <= 0, and < 0 only when the LP position is within the price range (in-the-money or ITM); iii) out-of-the-money (OTM) Loss <= 0, and < 0 only when the LP position is out of the price range (out-of-the-money or OTM) and when any rebalancing took place when the LP position was ITM!


   1.1) When current ETH price < LP price, the borrowed token0 rebalances into WETH i.e. the borrowed token0 gets back into the ETH collateral (for the borrow). The rebalancing of token0 into ETH is a sole cause of the RL & OTM Loss (the latter is ETH loss), so when the benchmark is ETH, both RL & OTM Loss = 0 on this relative scale! 
  
   1.2) When current ETH price > LP price, WETH rebalances into token0. Because the benchmark is not token0 (cash) or ETH is not borrowed (collaterilized by token0), both RL < 0 for ITM LP position & OTM Loss < 0 for rebalanced into token0 LP position, which is OTM.  


The bot LP positions are stacked to the 'left' of the current ETH price, so they are OTM and have as LP price the upper price bound. When ETH price < LP price (scenario 1.1), both RL & OTM Loss = 0 on a relative scale (when ETH is benchmark). When ETH price > LP price (scenario 1.2), the bot LP positions are OTM & there is no rebalancing, so both RL & OTM loss = 0 in any (absolute or relative) scale.
  
2. Need approval: contrary to claims of non-expiry, approval seems to expire once a month - without approval the tx-s receive error (seen on polygonscan.com) 'STF': 'safeTransfer can not be completed'! Under polygonscan.com > WETH ('0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619') & USDC ('0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'), under Contract > Write > Approve (connect to my wallet), approve manually both (ROUTER_ADDRESS, for swaps): 0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45 & (NPM_ADDRESS, for LP tx-s): 0xC36442b4a4522E871399CD717aBDD847Ab11FE88 for an infinite amount: 115792089237316195423570985008687907853269984665640564039457584007913129639935
  
2. The address has to be specified in global_params.py & the private key to the address is encrypted in a file (in the subdir /accounts) with encrypt_file() in encryption.py. It requires /accounts/salt.txt. When the bot is run, a password to access the private key is required via decrypt_file(),run at the beginning of main() in main.py.
  
3. The account has to have no NFT-s, in order for the bot to run. NFT-s are burned with burn() - see manual commands below. If all tokens are not collected first (after decreaseLiquidity() on the full liquidity), burn() tx produces error on Polygonscan "Fail with error 'Not cleared'". The ABI-s of the contracts used (all of them on the blockchain, made by Uniswap) are in the subdir /abi.

 
4. A session lasts for RUNTIME_SEC=72000 i.e. ~ 24 hours.  

Parameters in global_params.py (if use, rename to global_params.py): the bot initiates NUM_LP = 5 LP positions ~$10 each = min(MAX_NUM_TOKEN0_LP, MAX_NUM_TOKEN1_LP * ETH price), each with price range 2 * LP_DISTANCE_TO_BOUND_PER wide, stacked adjacently to the left of the initiation (current) price. The bot liquidates them at the end of the session or when they are UNWIND_DISTANCE_TO_BOUND_PER  OTM. In the latter case, the bot replacesthe old LP position with a new LP position, but only when all LP positions are liquidated. Also, the bot swaps back to the original amounts when the extra amounts exceed MIN_SESSION_SWAP_PER of the total invested. If LP_SWAP = True, bot attempts to swap using LP (no slippage & and pool fee costs).

Parameters in global_params0.py (if use, rename to global_params.py): the bot initiates NUM_LP = 1 LP positions ~$10 each = min(MAX_NUM_TOKEN0_LP, MAX_NUM_TOKEN1_LP * ETH price), with price range 2 * LP_DISTANCE_TO_BOUND_PER[0]  wide, with initiation (current) price immediately above its right price bound. But the bot liquidates/initiates frequently (every ~ 1-20 minutes). Unwinding happens typically because abs(signed WETH) / pool_liquidity in the last DELAY_LOOP_SEC (= 1) second exceeds MAX_UNWIND_TOKEN1_QUANTITY_TO_TVL_BP. Also, the bot swaps back to the original amounts when the extra amounts exceed MIN_SESSION_SWAP_PER of the total invested. If LP_SWAP = True, bot attempts to swap using LP (no slippage & and pool fee costs).
    
5. The updates of the pool price (and therefore all tx-s) happen on every 'main iteration', currently run every DELAY_LOOP_SEC (= 1) seconds. Pool price, p&l and numerous other metrics can be found in the date-of-running log, in the subdir /logs.
 
6. Manual commands to unwind the LP positions (tokenID & liquidity are required - can be found under polygonscan.com > mint tx > logs > increaseLiquidity):
  - to completely unwind i.e run all 3 separate functions shown below: python “C:\...\UniswapV3_LP\unwind.py" polygon tokenId liquidity
  - to only decrease liquidity: python “C:\...\UniswapV3_LP\decreaseLiquidity.py" polygon tokenId liquidity
  - to only collect the funds (after decreaseLiquidity() is run): python "C:\...\UniswapV3_LP\collect.py" tokenId polygon
  - to only burn an NFT with a given tokenId: python "C:\...\UniswapV3_LP\burn.py" tokenId polygon;

  To get the current NFT-s in the account, run: python "C:\...\UniswapV3_LP\toolbox.py" polygon address.
