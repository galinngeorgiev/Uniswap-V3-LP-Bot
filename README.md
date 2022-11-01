Run (from console): python "C:\...\UniswapV3_LP\main.py" polygon

0. ETH is a p&l benchmark. Bot trading is on Uniswap v3 liquid pools token0/WETH (token0 usually stable coin). Addresses of tokens and pools are set up in global_params.py. Token0 is borrowed on Aave (that is why 'borrow p&l' is used), using ETH as a collateral. Borrow p&l of an LP position has 3 summands: i) LP fees >= 0; ii) Rebalancing Loss (RL, a.k.a. Impermanent Loss) <= 0; iii) out-of-the-money (OTM) Loss <= 0.

        i) When current ETH price < LP price, the borrowed token0 rebalances into WETH i.e. the 'borrow' gets back into the collateral. This rebalancing causes RL & OTM Loss, so when the benchmark is ETH, the latter are both zero. That is why the bot LP positions are stacked to the 'left' of the current ETH price.
  
        ii) When current ETH price > LP price, WETH rebalances into token0. Because the benchmark is not token0 (cash) or ETH is not borrowed (collaterilized by token0), both RL & OTM Loss do not disappear & are substancial.
  
2. Need approval: contrary to claims of non-expiry, approval seems to expire once a month - without approval the tx-s receive error (seen on polygonscan.com) 'STF': 'safeTransfer can not be completed'! Under polygonscan.com > WETH ('0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619') & USDC ('0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'), under Contract > Write > Approve (connect to my wallet), approve manually both (ROUTER_ADDRESS, for swaps): 0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45 & (NPM_ADDRESS, for LP tx-s): 0xC36442b4a4522E871399CD717aBDD847Ab11FE88 for an infinite amount: 115792089237316195423570985008687907853269984665640564039457584007913129639935
  
2. The address has to be specified in global_params.py & the private key to the address is encrypted in a file (in the subdir /accounts) with encrypt_file() in encryption.py. It requires /accounts/salt.txt. When the bot is run, a password to access the private key is required via decrypt_file(),run at the beginning of main() in main.py.
  
3. The account has to have no NFT-s, in order for the bot to run. NFT-s are burned with burn() - see manual commands below. If all tokens are not collected first (after decreaseLiquidity() on the full liquidity), burn() tx produces error on Polygonscan "Fail with error 'Not cleared'". The ABI-s of the contracts used (all of them on the blockchain, made by Uniswap) are in the subdir /abi.

 
4. A session lasts for RUNTIME_SEC=72000 i.e. ~ 24 hours.  

Parameters in global_params0.py (if use, rename to global_params.py): the bot initiates NUM_LP = 5 LP positions ~$10 each = min(MAX_NUM_TOKEN0_LP, MAX_NUM_TOKEN1_LP * ETH price), each with price range 2 * LP_DISTANCE_TO_BOUND_PER[0] = 0.5% wide, stacked adjacently, so that the middle LP position has the initiation (current) price at the middle of its price range. The bot liquidates all of them at the end of the session or when the curent price is ~ NUM_LP * 2 * LP_DISTANCE_TO_BOUND_PER[0] ~ 2.5% away from the initiation price. In the latter case, the bot initiates NUM_LP new LP positions, as above. Also, the bot swaps back to the original amounts when the extra amounts exceed MIN_SESSION_SWAP_PER=10% of the total invested.

Parameters in global_params1.py (if use, rename to global_params.py): the bot initiates NUM_LP = 1 LP positions ~$10 each = min(MAX_NUM_TOKEN0_LP, MAX_NUM_TOKEN1_LP * ETH price), with price range 2 * LP_DISTANCE_TO_BOUND_PER[0] = 0.5% wide, with initiation (current) price at the middle of its price range. But the bot liquidates/initiates frequently (every ~ 1-20 minutes). Unwinding happens typically because abs(signed WETH) / pool_liquidity in the last DELAY_LOOP_SEC (= 1) second exceeds MAX_UNWIND_TOKEN1_QUANTITY_TO_TVL_BP. Also, the bot swaps back to the original amounts when the extra amounts exceed MIN_SESSION_SWAP_PER=50% of the total invested.
    
5. The updates of the pool price (and therefore all tx-s) happen on every 'main iteration', currently run every DELAY_LOOP_SEC (= 1) seconds. Pool price, p&l and numerous other metrics can be found in the date-of-running log, in the subdir /logs.
 
6. Manual commands to unwind the LP positions (tokenID & liquidity are required - can be found under polygonscan.com > mint tx > logs > increaseLiquidity):
  - to completely unwind i.e run all 3 separate functions shown below: python “C:\...\UniswapV3_LP\unwind.py" polygon tokenId liquidity
  - to only decrease liquidity: python “C:\...\UniswapV3_LP\decreaseLiquidity.py" polygon tokenId liquidity
  - to only collect the funds (after decreaseLiquidity() is run): python "C:\...\UniswapV3_LP\collect.py" tokenId polygon
  - to only burn an NFT with a given tokenId: python "C:\...\UniswapV3_LP\burn.py" tokenId polygon;

  To get the current NFT-s in the account, run: python "C:\...\UniswapV3_LP\toolbox.py" polygon address.
