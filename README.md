Change the DATA_PATH string at the bottom of global_params.py to the desired path (using Windows requires double-slash). The path is used for all sub-dirs: ..\accounts (where there is a file with encrypted account private key - currently ..\accounts\MM_account3.txt'), ..\abi (files containing smart contract abi-s), ..\logger. Run the bot from console: python "C:\...\UniswapV3_LP\main.py" polygon

1. ETH is a p&l reference frame (benchmark). Bot trading is on Uniswap v3 liquid pool token0/WETH (token0 is typically a stable coin) on Polygon network (MATIC ~ 1/1000 ETH & gas is proportional to the network coin, so gas fee on Polygon network  ~ 1/1000 of gas fees on Ethereum network). Addresses of tokens and pools are set up in global_params.py. ETH ref frame p&l of an LP position has 3 summands: i) LP fees >= 0; ii) Rebalancing Loss (RL, a.k.a. Impermanent Loss) <= 0, and < 0 only when the LP position is within the price range (in-the-money or ITM); iii) out-of-the-money (OTM) Loss <= 0, and < 0 only when the LP position is out of the price range (out-of-the-money or OTM) and when any rebalancing took place when the LP position was ITM!
 
The bot LP positions are stacked to the 'right' of the current ETH price, so they are OTM.
  
2. Need approval: contrary to claims of non-expiry, approval seems to expire once a month - without approval the tx-s receive error (seen on polygonscan.com) 'STF': 'safeTransfer can not be completed'! Under polygonscan.com > WETH ('0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619') & USDC ('0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'), under Contract > Write > Approve (connect to my wallet), approve manually both (ROUTER_ADDRESS, for swaps): 0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45 & (NPM_ADDRESS, for LP tx-s): 0xC36442b4a4522E871399CD717aBDD847Ab11FE88 for an infinite amount: 115792089237316195423570985008687907853269984665640564039457584007913129639935
  
2. The account address has to be specified in global_params.py & the private key to the address is encrypted in a file (in the subdir ./accounts) with encrypt_file() in encryption.py. The encryption/decryption requires ./accounts/salt.txt. When the bot is run, a password to access the private key is required via decrypt_file(), run at the beginning of main() in main.py. If manual tx-s are executed in the account while the bot is running, decreaseLiquidity(), collect() or burn() will fail with "nonce too low" because they rely on the nonce increment from the previous bot tx. The tx-s should in theory succeed on the next iteration, because nonce = None is passed after failure and therefore w3.eth.get_transaction_count(address) is run!
  
3. The account has to have no NFT-s, in order for the bot to run. NFT-s are burned with burn() - see manual commands below. If all tokens are not collected first (after decreaseLiquidity() on the full liquidity), burn() tx produces error on Polygonscan "Fail with error 'Not cleared'". The ABI-s of the contracts used (all of them on the blockchain, made by Uniswap) are in the subdir /abi.

 
4. A session lasts for RUNTIME_SEC (=72000 iterations currently i.e. when  ~ 24 hours when DELAY_LOOP_SEC = 1).  

Parameters are in global_params.py (all global variables are capitalized): the bot initiates NUM_LP LP positions for a total NUM_INVESTED_TOKEN1_LP ETH, each with price range 2 * LP_DISTANCE_TO_BOUND_PER wide, stacked adjacently to the right of the initiation ETH price (LP_position_to_init_price[:NUM_LP] = 1). The bot liquidates them when they are UNWIND_DISTANCE_TO_BOUND_PER  OTM or at the end of the session or on some other conditions.
    
5. The updates of the pool price (and therefore all tx-s) happen on every 'main iteration', currently run every DELAY_LOOP_SEC (= 1) seconds. Pool price, p&l and numerous other metrics can be found in the date-of-running log, in the subdir /logs.

6. When a blockchain tx fails MAX_ATTEMPTS_FAILED_TX ( 5 currently), the bot stops, so outstading mints have to be unwound manually - see below.

7. A global flag LP_SWAP = True: avoids pool fee & slippage by executing an un-coventional swap via LP position (with the tightest possible price range). When LP_SWAP:
    i) the runtime may increase to max LP_SWAP_MULT_RUNTIME * RUNTIME;
   ii) when LP swap fails LP_SWAP_MAX_ATTEMPTS_FAILED_TX times or the extended end LP_SWAP_MULT_RUNTIME * RUNTIME_SEC is reached, conventional (non-LP) swap is executed.
 
8. Manual commands to unwind the LP positions:

  - NFT-s in the address: python "C:\Users\galin.georgiev\GammaDynamics Net\Dev\Python\UniswapV3_LP\toolbox.py" polygon address (without quotes)
  - to completely unwind (a mint) tx. tokenID & liquidity are required - can be found under polygonscan.com > mint tx > logs > increaseLiquidity. One command runs all 3 separate functions (decreaseLiquidity(), collect() and burn()): python “C:\...\UniswapV3_LP\unwind.py" polygon tokenId liquidity
  - to only decrease liquidity. tokenID & liquidity are required (see above): python “C:\...\UniswapV3_LP\decreaseLiquidity.py" polygon tokenId liquidity
  - to only collect the funds (after decreaseLiquidity() is run). tokenId is required: python "C:\...\UniswapV3_LP\collect.py" tokenId polygon
  - to only burn an NFT with a given tokenId. tokenId is required: python "C:\...\UniswapV3_LP\burn.py" tokenId polygon; when a burn() returns error 'Not cleared', instead of subtracting liquidities (standard Excel does not have the precision!), it is easier to remove the LP position from the Uniswap app and then burn the token with the above command!

  To get the current NFT-s in the account, run: python "C:\...\UniswapV3_LP\toolbox.py" polygon address.
  
  9. Polygonscan  errors:

      i) Fail with error 'STF':
      
            - tx is not approved;
            - 
            - there are not enough tokens in the account, for swap();


      ii) 'Transaction too old' in any tx: when pending tx time > EXPIRY_SEC or EXPIRY_SEC is <= 5;
      
      iii) 'Too little received' in swap(): when slippage is set too low;
      
      iv) 'Not cleared' in burn(): there are more tokens left i.e. the LP position still have some liquidity left;
      
      v) 'insufficient funds for gas * price + value': not enough tokens (typically < 20 MATIC on Polygon), used for gas, to cover gas parameters in global_params.py: MAX_FEE_PER_GAS, MAX_PRIORITY_FEE_PER_GAS, MAX_GAS_UNITS;
      
      vi) 'nonce too low': get it sometimes in swaps if i) nonce is None and DELAY_NONCE_SEC in global_params.py is too small;
