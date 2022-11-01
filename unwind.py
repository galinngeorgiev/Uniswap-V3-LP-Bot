__author__ = "Galin Georgiev"
__copyright__ = "Copyright 2022, GammaDynamics, LLC"
__version__ = "1.1.0.0"


from toolbox import *
from global_params import *
from decreaseLiquidity import decreaseLiquidity
from collect import collect
from burn import burn
from encryption import decrypt_file

def unwind_wrapped(network, tokenId, liquidity, max_fee_per_gas=MAX_FEE_PER_GAS, max_priority_fee_per_gas=MAX_PRIORITY_FEE_PER_GAS):

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

    result = decreaseLiquidity(network, tokenId, liquidity, max_fee_per_gas, max_priority_fee_per_gas, address=Address, private_key=privateKey)
    if isinstance(result, tuple):
        time.sleep(10)
        result = collect(tokenId, network, max_fee_per_gas, max_priority_fee_per_gas, address=Address, private_key=privateKey)
        if isinstance(result, tuple):
            time.sleep(10)
            burn(tokenId, network, max_fee_per_gas, max_priority_fee_per_gas, address=Address, private_key=privateKey)

if __name__ == '__main__':
    #print(len(sys.argv), sys.argv)
    if len(sys.argv) == 3:  #tokenId, liquidity
        unwind_wrapped('mumbai', tokenId=eval(sys.argv[1]), liquidity=eval(sys.argv[2]))
    elif len(sys.argv) == 4:  # network, tokenId, liquidity
        unwind_wrapped(network=str(sys.argv[1]), tokenId=eval(sys.argv[2]), liquidity=eval(sys.argv[3]))
    elif len(sys.argv) == 6:  # network, tokenId, liquidity, max_fee_per_gas, max_priority_fee_per_gas
        unwind_wrapped(network=str(sys.argv[1]), tokenId=eval(sys.argv[2]), liquidity=eval(sys.argv[3]), max_fee_per_gas=eval(sys.argv[4]), max_priority_fee_per_gas=eval(sys.argv[5]))
    else:
        print("Wrong number of inputs!")
