__author__ = "Galin Georgiev"
__copyright__ = "Copyright 2022, GammaDynamics, LLC"
__version__ = "1.1.0.0"	

import os
import time

import cryptography
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

import secrets
import base64
import getpass

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
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)20.20s - %(message)s')
handler.setFormatter(formatter)
# add the handlers to the logger
if not len(logger.handlers):
	logger.addHandler(handler)

##############################################################


def encrypt_file(file_name):

	#N.B. Generate salt
	#salt = secrets.token_bytes(SALT_SIZE)
	salt_file_name = os.path.join(DATA_PATH,'accounts', 'salt.txt')
	#N.B. If the same salt is not used in decryption, one can not decrypt with the generated key
	#with open(salt_file_name, "wb") as file:
	#	file.write(salt)
	salt = open(salt_file_name, "rb").read()
	password = getpass.getpass(prompt='Password:')

	#N.B. Derive the encryption / decryption key from password; if length != 32, Fernet encryption does not work!
	#N.B. n=2**20 does not have enough memory on VM with 2gb RAM
	kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1) #ref: https://cryptography.io/en/latest/hazmat/primitives/key-derivation-functions/#cryptography.hazmat.primitives.kdf.scrypt.Scrypt
	key = kdf.derive(bytes(password, 'utf-8'))
	key = base64.urlsafe_b64encode(key)

	f = Fernet(key)
	with open(os.path.join(DATA_PATH,'accounts', file_name), "rb") as file:
		file_data = file.read()
	encrypted_data = f.encrypt(file_data)
	with open(os.path.join(DATA_PATH,'accounts', file_name), "wb") as file:
		file.write(encrypted_data)


def decrypt_file(file_name):

	#N.B. #N.B. If the salt used in encryption, is not used in decryption, one can not decrypt with the generated key
	salt_file_name = os.path.join(DATA_PATH,'accounts','salt.txt')
	salt = open(salt_file_name, "rb").read()
	password = getpass.getpass(prompt='Password:')

	#N.B. Derive the encryption / decryption key from password; if length != 32, Fernet encryption does not work!
	kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1) #ref: https://cryptography.io/en/latest/hazmat/primitives/key-derivation-functions/#cryptography.hazmat.primitives.kdf.scrypt.Scrypt
	key = kdf.derive(bytes(password, 'utf-8'))
	key = base64.urlsafe_b64encode(key)

	f = Fernet(key)
	with open(file_name, "rb") as file:
		encrypted_data = file.read()
		
	return f.decrypt(encrypted_data).decode('utf-8')
	