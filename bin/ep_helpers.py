#!/usr/bin/env python
import random
import sys, os, platform
import re
import socket
import stat
from datetime import datetime
from deductiv_helpers import setup_logger, str2bool, decrypt_with_secret

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))

os_platform = platform.system()
py_major_ver = sys.version_info[0]
# Import the correct version of platform-specific libraries
if os_platform == 'Linux':
	if py_major_ver == 3:
		path_prepend = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib', 'py3_linux_x86_64')
	elif py_major_ver == 2:
		path_prepend = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib', 'py2_linux_x86_64')
elif os_platform == 'Darwin': # Does not work with Splunk Python build. It requires code signing for libs.
	path_prepend = ''
elif os_platform == 'Windows':
	if py_major_ver == 3:
		path_prepend = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib', 'py3_win_amd64')
	elif py_major_ver == 2:
		path_prepend = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib', 'py2_win_amd64')
sys.path.append(path_prepend)

# pylint: disable=import-error
# Splunk
#from splunk.clilib import cli_common as cli
# Box.com
# AWS libraries
# PySMB
#PySFTP
#

# Enumerate proxy settings
http_proxy = os.environ.get('HTTP_PROXY')
https_proxy = os.environ.get('HTTPS_PROXY')
proxy_exceptions = os.environ.get('NO_PROXY')

random_number = str(random.randint(10000, 100000))

#app_config = cli.getConfStanza('ep_general','settings')
facility = os.path.basename(__file__)
facility = os.path.splitext(facility)[0]
#logger = setup_logger(app_config["log_level"], 'event_push.log', facility)
logger = setup_logger('DEBUG', 'event_push.log', facility)

def get_aws_connection(aws_config):
	global boto3, Config
	import boto3
	from botocore.config import Config
	
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

	#random_number = str(random.randint(10000, 100000))
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


def s3_folder_contents(client, bucket, prefix):
	# Can't use list_objects_v2 - no owner returned
	#logger.debug("Folder contents")
	paginator = client.get_paginator('list_objects')
	if len(prefix) > 0:
		prefix = (prefix + '/').replace('//', '/')
	#logger.debug('prefix = ' + prefix)
	for result in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter='/'):
		# Submit a separate request for each folder to get its attributes. 
		# head_object doesn't work here, not specific enough.
		for cp in result.get('CommonPrefixes', []):
			folder_name = cp.get('Prefix')
			folder_result = client.list_objects(Bucket=bucket, Prefix=folder_name, MaxKeys=1)
			for content in folder_result.get('Contents'):
				content = yield_s3_object(content, is_directory=True)
				content["id"] = ('/' + bucket + '/' + content["id"]).replace('//', '/')
				yield content

		for content in result.get('Contents', []):
			content = yield_s3_object(content)
			content["id"] = ('/' + bucket + '/' + content["id"]).replace('//', '/')
			# We already retrieved the folders in the for-loop above.
			#logger.debug(content["id"][-1])
			if not content["isDir"] and not content["id"][-1] == '/':
				yield content
		
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

	#logger.debug("Default bucket = " + aws_config['default_s3_bucket'])
	logger.debug("Bucket folder path = " + bucket_folder_path)
	folder_path = bucket_folder_path.strip('/').split('/')
	bucket_name = folder_path[0]
	if bucket_name is None or len(bucket_name) == 0:
		logger.debug("No bucket specified")
		folder_prefix = '/'
		bucket_name = ''
		#pass #bucket_name = aws_config['default_s3_bucket'] Default bucket code happens in rest_ep_dirlist
	if len(folder_path) >= 1:
		folder_prefix = '/'.join(folder_path[1:]).strip('/')
	#elif len(folder_path) == 1:
	#	folder = '/' + bucket_name
	else:
		folder_prefix = '/'
	logger.debug("Folder Prefix = " + folder_prefix)

	try:
		conn = get_aws_connection(aws_config)
	except BaseException as e:
		raise Exception("Could not connect to AWS: " + repr(e))

	file_list = []
	if len(bucket_name) > 0:
		logger.debug("Getting bucket contents for " + bucket_name)
		# Get the directory listing within the bucket
		# List files and folders
		for e in s3_folder_contents(conn, bucket_name, folder_prefix):
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
				"id": '/' + b['Name'],
				"name": b['Name'],
				"modDate": timestamp,
				"isDir": True
			} )
	return file_list


def get_sftp_connection(target_config):
	global pysftp
	import pysftp

	# Check to see if we have credentials
	valid_settings = []
	for l in list(target_config.keys()):
		if target_config[l][0] == '$':
			target_config[l] = decrypt_with_secret(target_config[l]).strip()
		if len(target_config[l]) > 0:
			#logger.debug("l.strip() = [" + target_config[l].strip() + "]")
			valid_settings.append(l) 
	if 'host' in valid_settings and 'port' in valid_settings:
		# A target has been configured. Check for credentials.
		# Disable SSH host checking (fix later - set as an option? !!!)
		cnopts = pysftp.CnOpts()
		cnopts.hostkeys = None
		try:
			if 'username' in valid_settings and 'password' in valid_settings:
				try:
					sftp = pysftp.Connection(host=target_config['host'], username=target_config['username'], password=target_config['password'], cnopts=cnopts)
				except BaseException as e:
					exit_error(logger, "Unable to setup SFTP connection with password: " + repr(e), 921982)
			elif 'username' in valid_settings and 'private_key' in valid_settings:
				# Write the decrypted private key to a temporary file
				temp_dir = os.getcwd()
				key_file = os.path.join(temp_dir, 'epsftp_private_key_' + random_number)
				private_key = target_config['private_key'].replace('\\n', '\n')
				with open(key_file, "w") as f:
					f.write(private_key)
					f.close()
				try:
					if 'passphrase' in valid_settings:
						sftp = pysftp.Connection(host=target_config['host'], private_key=key_file, private_key_pass=target_config['passphrase'], cnopts=cnopts)
					else:
						sftp = pysftp.Connection(host=target_config['host'], username=target_config['username'], private_key=key_file, cnopts=cnopts)
					return sftp
				except BaseException as e:
					raise Exception("Unable to setup SFTP connection with private key: " + repr(e))
			else:
				raise Exception("Required SFTP settings not found")
		except BaseException as e: 
			raise Exception("Could not find or decrypt the specified SFTP credential: " + repr(e))
	else:
		raise Exception("Could not find required SFTP configuration settings")
		
def get_sftp_directory(sftp_config, folder_path):
	sftp = get_sftp_connection(sftp_config)
	dirlist = sftp.listdir_attr(folder_path)
	file_list = []
	for f in dirlist:
		entry = yield_sftp_object(f, folder_path)
		if entry is not None:
			file_list.append(entry)
	# Sort the listing
	# Directories first then filename
	file_list.sort(key=lambda x: (x["isDir"], x["name"]))
	return file_list

def yield_sftp_object(content, folder_path):
	folder_path = folder_path.rstrip('/').rstrip('\\')
	if content.filename not in [u'.', u'..']:
		return {
			"id": folder_path + '/' + content.filename,
			"name": content.filename,
			"isHidden": True if content.filename[0] == '.' else False,
			"size": content.st_size,
			"modDate": content.st_mtime,
			"parentId": folder_path,
			"isDir": True if stat.S_ISDIR(content.st_mode) or (stat.S_ISLNK(content.st_mode) and stat.S_IMODE(content.st_mode) & 1) else False
		}
	else:
		return None

def get_smb_directory(smb_config, folder_path = '/'):
	global SMBConnection
	from smb.SMBConnection import SMBConnection
	
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

def get_box_connection(target_config):
	# Check to see if we have credentials
	valid_settings = []
	for l in list(target_config.keys()):
		if len(target_config[l]) > 0:
			valid_settings.append(l) 
	
	if 'client_id' in valid_settings and 'client_secret' in valid_settings and 'enterprise_id' in valid_settings:
		# A credential has been configured. Check for a cert.
		if 'public_key_id' in valid_settings and 'private_key' in valid_settings and 'passphrase' in valid_settings:
			# Certificate has been configured.

			try:
				enterprise_id = target_config['enterprise_id']
				client_id = target_config['client_id']
				client_secret = decrypt_with_secret(target_config['client_secret'])
				public_key_id = target_config['public_key_id']
				private_key = decrypt_with_secret(target_config['private_key']).replace('\\n', '\n')
				passphrase = decrypt_with_secret(target_config['passphrase'])

				box_authentication = {
					"enterpriseID": enterprise_id,
					"boxAppSettings": {
						"clientID": client_id,
						"clientSecret": client_secret,
						"appAuth": {
							"publicKeyID": public_key_id,
							"privateKey": private_key,
							"passphrase": passphrase
						}
					}
				}
				
				auth = JWTAuth.from_settings_dictionary(box_authentication)

				if auth is not None:
					# Use the credential to connect to Box
					try:
						return Client(auth)
					except BoxAPIException as be:
						raise Exception("Could not connect to Box: " + be.message)
					except BaseException as e:
						raise Exception("Could not connect to Box: " + repr(e))
				else:
					raise Exception("Box credential not configured.")
			except BaseException as e: 
				logger.debug(repr(e))
				raise Exception("Could not find or decrypt the specified credential: " + repr(e))
		else:
			raise Exception("Could not find required certificate settings")
	else:
		raise Exception("Could not find required configuration settings")


def get_box_directory(target_config, folder_path):
	global JWTAuth, Client, BoxAPIException
	from boxsdk import JWTAuth, Client, BoxAPIException
	
	# Let the exception pass through
	client = get_box_connection(target_config)
	if 'default_folder' in list(target_config.keys()) and (folder_path is None or len(folder_path) == 0):
		folder_path = target_config['default_folder']
	
	try:
		if re.match(r'^\d+\/$', folder_path):
			# Folder path is actually a folder ID
			box_folder_object = client.folder(folder_id=folder_path.replace('/', '')).get()
		else:
			# Folder path is actually a folder path
			subfolders = folder_path.strip('/').split('/')
			if '' in subfolders:
				subfolders.remove('')
			logger.debug("Folders: %s" % str(subfolders))
			# Prepend the list with the root element
			box_folder_object = client.root_folder().get()
			# Walk the folder path until we find the target directory
			for i in range(len(subfolders)):
				subfolder_name = subfolders[i]
				logger.debug("Looking for folder: %s" % subfolder_name)
				folder_contents = box_folder_object.get_items()
				# If we are at the last entry, we already have the folder_contents assigned
				if i != len(subfolders):
					# Get the contents of the folder
					# folder object is from the previous iteration
					for item in folder_contents:
						if item.type == 'folder':
							#logger.debug('{0} {1} is named "{2}"'.format(item.type.capitalize(), item.id, item.name))
							if subfolder_name == item.name:
								logger.debug("Found a target folder ID: %s" % str(item.id))
								box_folder_object = client.folder(folder_id=item.id)
								break
		
		fields = ["id", "name", "owner", "content_modified_at", "item_collection", "owner", "size", "parent", "status"]
		folder_data = box_folder_object.get_items(fields=fields)
		logger.debug(folder_data.__dict__)
		file_list = []
		#if hasattr(folder_data.item_collection, "item_collection"):
		#	if hasattr(folder_data.item_collection, "entries"):
		#		logger.debug("Has entries")
		for item in folder_data:
			#logger.debug(item.name)
			#if item.type == 'file':
				#logger.debug(item.status)
			try:
				#if item.item_status == "active":
				entry = {
					#"box_id": item.id,
					"id": ('/' + '/'.join(subfolders) + '/' + item.name).replace('//', '/'),
					#"id": item.id,
					"name": item.name
					#"parentId": ('/' + '/'.join(subfolders)).replace('//', '/')
				}
				if item.type == 'folder':
					entry["isDir"] = True
					#f = client.folder(item.id).get()
				else:
					entry["isDir"] = False
					#f = client.file(item.id).get()
				#entry["link"] = f.url
				if hasattr(item, "owned_by"):
					entry["owner"] = item.owned_by.login
				entry_ts = item.content_modified_at
				# Remove the last colon (e.g. from -04:00)
				entry_ts = entry_ts[0:entry_ts.rindex(':')]+entry_ts[entry_ts.rindex(':')+1:]
				entry["modDate"] = datetime.strptime(entry_ts, '%Y-%m-%dT%H:%M:%S%z').timestamp()
				entry["size"] = item.size
				if hasattr(item, "parent"):
					if hasattr(item.parent, "id"):
						entry["parentId"] = item.parent.id
				# Folder -or- active file
				#if not hasattr(item, "status") or (hasattr(item, "status") and item.status == "active"):
				logger.debug(entry)
				file_list.append(entry)

			except BaseException as e:
				logger.debug("Exception: " + repr(e))

		logger.debug("done")
		return file_list


	except BoxAPIException as be:
		raise Exception("Could not retrieve folder contents: " + be.message)
	except BaseException as e:
		raise Exception("Could not retrieve folder contents: " + repr(e))

