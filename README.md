1. Need approval: seems to expire once a month - without approval the tx-s receive error (seen on polygonscan.com) 'STF': 'safeTransfer can not be completed'!
  Under polygonscan.com > WETH ('0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619') & USDC ('0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'), under Contract > Write > Approve (connect to my wallet), approve manually both (ROUTER_ADDRESS, for swaps): 0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45 & (NPM_ADDRESS, for LP tx-s): 0xC36442b4a4522E871399CD717aBDD847Ab11FE88 for an infinite amount: 115792089237316195423570985008687907853269984665640564039457584007913129639935
  
2. The address has to be specified in global_params.py & the private key to the address is encrypted in a file (in the subdir /accounts) with encrypt_file() in encryption.py. It requires /accounts/salt.txt. When the bot is run, a password to access the private key is required via decrypt_file(),run at the beginning of main() in main.py.
  
3. The account has to have no NFT-s, in order for the bot to run. NFT-s are burned with burn() - see manual commands below. The ABI-s of the contracts used (all of them on the blockchain, made by Uniswap) are in the subdir /abi.

 
4.  With the current parameters in global_params.py, the bot initiates NUM_LP = 5 LP positions ~$10 each = min(MAX_NUM_TOKEN0_LP, MAX_NUM_TOKEN1_LP * ETH price), each with price range sum(LP_DISTANCE_TO_BOUND_PER)=0.5% wide, stacked adjacently, so that the middle LP position has the initiation (current) price at the middle of its price range. The bot liquidates all of them at the end of the session or when the curent price is (NUM_LP - 1) * 0.5% away from the initiation price. in the latter case, the bot initiates NUM_LP new LP positions, as above. Also, the bot swaps back to the original amounts when the extra amounts         exceed MIN_SESSION_SWAP_PER=10% of the total invested. A session lasts for RUNTIME_SEC=72000 i.e. ~ 24 hours. 
    
5. The updates of the pool price happen on every iteration, currently iteration run every 10 sec (DELAY_LOOP_SEC = 10). Pool price, p&l and numerous other metrics can be found in the date-of-running log, in the subdir /logs.
 
6. Manual commands to unwind the LP positions (tokenID & liquidity are required - can be found under polygonscan.com > mint tx > logs > increaseLiquidity):
  - to completely unwind i.e run all 3 separate functions shown below: python “C:\...\unwind.py" polygon tokenId liquidity
  - to only decrease liquidity: python “C:\...\decreaseLiquidity.py" polygon tokenId liquidity
  - to only collect the funds (after decreaseLiquidity() is run): python "C:\...\collect.py" tokenId polygon
  - to only burn the NFT corresponding to LP position (after collect() for the full amount is run): python "C:\...\burn.py" tokenId polygon;

  To get the current NFT-s in the account, run: python "C:\...\toolbox.py" polygon address.
