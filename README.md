1. Need approval: seems to expire once a month - without approval the tx-s receive error (seen on polygonscan.com) 
  'STF': 'safeTransfer can not be completed'!
  Under polygonscan.com > WETH ('0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619') & USDC ('0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'),
  under Contract > Write > Approve (connect to my wallet), approve manually both
  (ROUTER_ADDRESS, for swaps): 0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45 & (NPM_ADDRESS, for LP tx-s): 0xC36442b4a4522E871399CD717aBDD847Ab11FE88
  for an infinite amount: 115792089237316195423570985008687907853269984665640564039457584007913129639935
  
2. The address has to be specified in global_params.py & the private key to the address is encrypted in a file (under subfolder /accounts)
    with encrypt_file() in encryption.py. When the bot is run, a password to access the private key is required via decrypt_file(),
    run at the beginning of main() in main.py.
  
3. The account has to have no NFT-s, in order for the bot to run.


 
4.  With parameters in global_params.py, the bot initiates 5 LP positions ~$10 each = min(MAX_NUM_TOKEN0_LP, MAX_NUM_TOKEN1_LP)
    and liquidates them at the end of the session. Also, swaps back to the original amounts. A session lasts for ~ 24 hours.
    The bot has the ability to initiate/liquidate as frequently as possible.

 
5. Manual commands to unwind the LP positions (tokenID & liquidity are required - can be found under polygonscan.com > mint tx > logs > increaseLiquidity):
  - to completely unwind i.e run all 3 separate functions shown below: python “C:\...\unwind.py" polygon tokenId liquidity
  - to only decrease liquidity: python “C:\...\decreaseLiquidity.py" polygon tokenId liquidity
  - to only collect the funds (after decreaseLiquidity() is run): python "C:\...\collect.py" tokenId polygon
  - to only burn the NFT corresponding to LP position (after collect() for the full amount is run): python "C:\...\burn.py" tokenId polygon;

  To get the current NFT-s in the account, run: python "C:\...\toolbox.py" polygon address.
