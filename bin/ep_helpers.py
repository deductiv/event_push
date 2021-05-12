
import random
import sys, os, platform
import re
import socket
from datetime import datetime, timezone
from deductiv_helpers import setup_logger, str2bool, decrypt_with_secret

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))

# pylint: disable=import-error
# AWS libraries
import boto3
from botocore.config import Config
# PySMB
from smb.SMBConnection import SMBConnection


# Enumerate proxy settings
http_proxy = os.environ.get('HTTP_PROXY')
https_proxy = os.environ.get('HTTPS_PROXY')
proxy_exceptions = os.environ.get('NO_PROXY')

logger = setup_logger('DEBUG', 'event_push.log', 'ep_helpers')

def get_aws_connection(aws_config):

	# Apply proxy settings to AWS config
	proxy_definitions = {
		'http': http_proxy,
		'https': https_proxy
	}
	boto_config = Config(
		signature_version='s3v4',
		proxies=proxy_definitions
	)

	# Apply non-null setting to boto config
	if 'region' in list(aws_config.keys()):
		region_config = Config(region_name=aws_config['region'])
		boto_config.merge(region_config)
	
	# Set endpoint URL
	if 'endpoint_url' in list(aws_config.keys()):
		endpoint_url = aws_config['endpoint_url']
	else:
		endpoint_url = None

	use_arn = str2bool(aws_config['use_arn'])

	# Check for secret_key encryption
	if not use_arn and aws_config['secret_key'][:1] == '$':
		aws_config['secret_key'] = decrypt_with_secret(aws_config['secret_key'])

	random_number = str(random.randint(10000, 100000))
	if use_arn:
		# Use the current/caller identity ARN from the EC2 instance to connect to S3
		#logger.debug("Using ARN to connect")
		try:
			account_arn_current = boto3.client('sts').get_caller_identity().get('Arn')
			# arn:aws:sts::800000000000:assumed-role/SplunkInstance_ReadOnly/...
			m = re.search(r'arn:aws:sts::(\d+):[^\/]+\/([^\/]+)', account_arn_current)
			aws_account = m.group(1)
			aws_role = m.group(2)

			sts_client = boto3.client('sts')
			role_arn = "arn:aws:iam::" + aws_account + ":role/" + aws_role
			assumed_role_object = sts_client.assume_role(
				RoleArn=role_arn,
				RoleSessionName="AssumeRoleSession" + random_number
			)

			credentials = assumed_role_object['Credentials']
			return boto3.client(
				's3',
				aws_access_key_id=credentials['AccessKeyId'],
				aws_secret_access_key=credentials['SecretAccessKey'],
				aws_session_token=credentials['SessionToken'],
			)
			#logger.debug("Connected using assumed role %s", role_arn)
		except BaseException as e:
			raise Exception("Could not connect to S3. Failed to assume role: " + repr(e))

	elif aws_config['access_key_id'] is not None and aws_config['secret_key'] is not None:
		# Use the credential to connect to S3
		try:
			return boto3.client(
				's3',
				aws_access_key_id=aws_config['access_key_id'],
				aws_secret_access_key=aws_config['secret_key'],
				config=boto_config,
				endpoint_url=endpoint_url)
			#logger.debug("Connected using OAuth credential")
		except BaseException as e:
			raise Exception("Could not connect to S3 using OAuth keys: " + repr(e))
	else:
		raise Exception("ARN not configured and credential not specified.")


def s3_folder_contents(client, bucket, prefix=''):
	# Can't use list_objects_v2 - no owner returned
	logger.debug("Folder contents")
	paginator = client.get_paginator('list_objects')
	for result in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter='/'):
		# Submit a separate request for each folder to get its attributes. 
		# head_object doesn't work here, not specific enough.
		for cp in result.get('CommonPrefixes', []):
			folder_name = cp.get('Prefix')
			folder_result = client.list_objects(Bucket=bucket, Prefix=folder_name, MaxKeys=1)
			for content in folder_result.get('Contents'):
				yield yield_s3_object(content, is_directory=True)

		for content in result.get('Contents', []):
			yield yield_s3_object(content)
		
def yield_s3_object(content, is_directory=False):
	timestamp = content.get('LastModified')
	timestamp = timestamp.timestamp() if timestamp is not None else None
	owner = content.get('Owner')
	owner = owner['DisplayName'] if owner is not None and 'DisplayName' in list(owner.keys()) else owner

	return {
		"id": content.get('Key'),
		"name": content.get('Key').strip('/').split('/')[-1],
		"size": content.get('Size'),
		"modDate": timestamp,
		"owner": owner,
		"isDir": is_directory
	}


def get_aws_s3_directory(aws_config, bucket_folder_path):
	logger.debug("Bucket = " + aws_config['default_s3_bucket'])
	logger.debug("Bucket folder path = " + bucket_folder_path)
	folder_path = bucket_folder_path.split('/')
	bucket_name = folder_path[0]
	if bucket_name is None or len(bucket_name) == 0:
		bucket_name = aws_config['default_s3_bucket']
	if len(folder_path) > 1:
		folder = '/'.join(folder_path[1:]).strip('/') + ('/')
	else:
		folder = ''
	logger.debug("Folder = " + folder)

	logger.debug("bucket name = " + str(bucket_name))
	if bucket_name is None:
		if 'default_s3_bucket' in list(aws_config.keys()):
			t = aws_config['default_s3_bucket']
			logger.debug(t)
			if t is not None and len(t) > 0:
				bucket_name = t
			else:
				bucket_name = ''
		else:
			bucket_name = ''
	try:
		conn = get_aws_connection(aws_config)
	except BaseException as e:
		raise Exception("Could not connect to AWS: " + repr(e))

	file_list = []
	if len(bucket_name) > 0:
		# Get the directory listing within the bucket
		# List files and folders
		for e in s3_folder_contents(conn, bucket_name, folder):
			file_list.append( e )
	else:
		# Get the list of buckets
		logger.debug("Getting list of buckets")
		bucket_list = conn.list_buckets()
		bucket_list_props = bucket_list['Buckets']
		for b in bucket_list_props:	
			timestamp = b['CreationDate']
			timestamp = timestamp.timestamp() if timestamp is not None else None
			file_list.append( {
				"id": b['Name'],
				"name": b['Name'],
				"modDate": timestamp,
				"isDir": True
			} )
	return file_list

def get_box_directory(box_config, folder_path):
	return []

def get_sftp_directory(sftp_config, folder_path):
	return []

def get_smb_directory(smb_config, folder_path = '/'):
	# Get the local client hostname
	client_name = socket.gethostname()
	# Delete any domain from the client hostname string
	if '.' in client_name:
		client_name = client_name[0:client_name.index('.')]

	valid_settings = []
	for l in list(smb_config.keys()):
		if smb_config[l][0] == '$':
			smb_config[l] = decrypt_with_secret(smb_config[l]).strip()
		if len(smb_config[l]) > 0:
			valid_settings.append(l) 
	try:
		if all (k in valid_settings for k in ('host', 'username', 'password', 'domain', 'share_name')):
			try:
				conn = SMBConnection(smb_config['username'], smb_config['password'], client_name, 
					smb_config['host'], domain=smb_config['domain'], use_ntlm_v2=True,
					sign_options = SMBConnection.SIGN_WHEN_SUPPORTED) 
				conn.connect(smb_config['host'], 139)

				if smb_config['share_name'] not in (s.name for s in conn.listShares(timeout=10)):
					raise Exception("Unable to find the specified share name on the server")
				
				# List the directory contents
				#logger.debug(folder_path)
				contents = conn.listPath(smb_config['share_name'], folder_path)
				file_list = []
				for content in contents:
					entry = yield_smb_object(content, folder_path)
					if entry is not None:
						file_list.append(entry)
				
				return file_list

			except BaseException as e:
				raise Exception("Unable to setup SMB connection: " + repr(e))
		else:
			raise Exception("Required settings not found")
	except BaseException as e: 
		raise Exception("Error reading the configuration: " + repr(e))

def yield_smb_object(content, folder_path):
	folder_path = folder_path.rstrip('/').rstrip('\\')
	if content.filename not in [u'.', u'..']:
		return {
			"id": folder_path + '/' + content.filename,
			"name": content.filename,
			"isHidden": True if content.file_attributes & 2 > 0 else False,
			"size": content.file_size,
			"modDate": content.last_write_time,
			"parentId": folder_path,
			"isDir": True if content.isDirectory else False
		}
	else:
		return None