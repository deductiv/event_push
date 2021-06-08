#!/usr/bin/env python

# Copyright 2021 Deductiv Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Python 3 compatible only (Does not work on Mac version of Splunk's Python)
# search_ep_sftp.py
# Push Splunk search results to a remote SFTP server - Search Command
#
# Author: J.R. Murray <jr.murray@deductiv.net>
# Version: 2.0.0 (2021-04-27)

from __future__ import print_function
from builtins import str
from future import standard_library
standard_library.install_aliases()
import sys, os
import random
import socket
from deductiv_helpers import setup_logger, eprint, decrypt_with_secret, get_config_from_alias, exit_error, replace_object_tokens

# Add lib subfolders to import path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
# pylint: disable=import-error
from splunk.clilib import cli_common as cli
from splunklib.searchcommands import ReportingCommand, dispatch, Configuration, Option, validators
import event_file
from smb.SMBConnection import SMBConnection

# Define class and type for Splunk command
@Configuration()
class epsmb(ReportingCommand):
	doc='''
	**Syntax:**
	search | epsmb target=<target host alias> outputfile=<output path/filename> outputformat=[json|raw|kv|csv|tsv|pipe] fields="field1, field2, field3" compress=[true|false]

	**Description**
	Push (export) Splunk events to an SMB server share in any format.
	'''

	# Define Parameters
	target = Option(
		doc='''
		**Syntax:** **target=***<target_host_alias>*
		**Description:** Reference to a target SMB share within the configuration
		**Default:** The target configured as "Default" within the setup page (if any)''',
		require=False)

	outputfile = Option(
		doc='''
		**Syntax:** **outputfile=***<file path/file name>*
		**Description:** The name of the file to be written remotely
		**Default:** The name of the user plus the timestamp and the output format, e.g. admin_1588000000.log
			json=.json, csv=.csv, tsv=.tsv, pipe=.log, kv=.log, raw=.log''',
		require=False)

	outputformat = Option(
		doc='''
		**Syntax:** **outputformat=***[json|raw|kv|csv|tsv|pipe]*
		**Description:** The format written for the output events/search results
		**Default:** *csv*''',
		require=False) 

	fields = Option(
		doc='''
		**Syntax:** **fields=***"field1, field2, field3"*
		**Description:** Limit the fields to be written to the file
		**Default:** All (Unspecified)''',
		require=False, validate=validators.List()) 

	compress = Option(
		doc='''
		**Syntax:** **compress=***[true|false]*
		**Description:** Option to compress the output file into .gz format before uploading
		**Default:** The setting from the target configuration, or True if .gz is in the filename ''',
		require=False, validate=validators.Boolean())

	# Validators found @ https://github.com/splunk/splunk-sdk-python/blob/master/splunklib/searchcommands/validators.py
	
	def __getitem__(self, key):
		return getattr(self,key)
	
	def map(self, events):
		for e in events:
			yield(e)

	#define main function
	def reduce(self, events):

		try:
			app_config = cli.getConfStanza('ep_general','settings')
			cmd_config = cli.getConfStanzas('ep_smb')
		except BaseException as e:
			raise Exception("Could not read configuration: " + repr(e))
		
		# Facility info - prepended to log lines
		facility = os.path.basename(__file__)
		facility = os.path.splitext(facility)[0]
		try:
			logger = setup_logger(app_config["log_level"], 'event_push.log', facility)
		except BaseException as e:
			raise Exception("Could not create logger: " + repr(e))

		logger.info('SMB Event Push search command initiated')

		# Enumerate proxy settings
		http_proxy = os.environ.get('HTTP_PROXY')
		https_proxy = os.environ.get('HTTPS_PROXY')
		proxy_exceptions = os.environ.get('NO_PROXY')

		if http_proxy is not None:
			logger.debug("HTTP proxy: %s" % http_proxy)
		if https_proxy is not None:
			logger.debug("HTTPS proxy: %s" % https_proxy)
		if proxy_exceptions is not None:
			logger.debug("Proxy Exceptions: %s" % proxy_exceptions)
	
		# Enumerate settings
		app = self._metadata.searchinfo.app
		user = self._metadata.searchinfo.username
		dispatch = self._metadata.searchinfo.dispatch_dir
		
		# Replace all tokenized parameter strings
		replace_object_tokens(self)

		# Use the random number to support running multiple outputs in a single search
		random_number = str(random.randint(10000, 100000))

		try:
			target_config = get_config_from_alias(cmd_config, self.target)
			if target_config is None:
				exit_error(logger, "Unable to find target configuration.", 100937)
		except BaseException as e:
			exit_error(logger, "Error reading target server configuration: " + repr(e), 124812)

		# Get the local client hostname
		client_name = socket.gethostname()
		# Delete any domain from the client hostname string
		if '.' in client_name:
			client_name = client_name[0:client_name.index('.')]
		
		# Check to see if we have credentials
		valid_settings = []
		for l in list(target_config.keys()):
			if target_config[l][0] == '$':
				target_config[l] = decrypt_with_secret(target_config[l]).strip()
			if len(target_config[l]) > 0:
				valid_settings.append(l) 
		if 'host' in valid_settings:
			# A target has been configured. Check for credentials.
			try:
				if 'username' in valid_settings and 'password' in valid_settings and 'domain' in valid_settings and 'share_name' in valid_settings:
					try:
						conn = SMBConnection(target_config['username'], target_config['password'], client_name, 
							target_config['host'], domain=target_config['domain'], use_ntlm_v2=True,
							sign_options = SMBConnection.SIGN_WHEN_SUPPORTED) 
						connected = conn.connect(target_config['host'], 139)
						'''
						shares = 
						share_exists = False
						for i in range(len(shares)):
							if shares[i].name == target_config['share_name']:
								share_exists = True
								break
						'''
						if target_config['share_name'] not in (s.name for s in conn.listShares(timeout=10)):
							exit_error(logger, "Unable to find the specified share name on the server", 553952)
					except BaseException as e:
						exit_error(logger, "Unable to setup SMB connection: " + repr(e), 921982)
				else:
					exit_error(logger, "Required settings not found", 101926)
			except BaseException as e: 
				exit_error(logger, "Error reading the configuration: " + repr(e), 230494)
		else:
			exit_error(logger, "Could not find required configuration settings", 2823874)
		
		file_extensions = {
			'raw':  '.log',
			'kv':   '.log',
			'pipe': '.log',
			'csv':  '.csv',
			'tsv':  '.tsv',
			'json': '.json'
		}

		if self.outputformat is None:
			self.outputformat = 'csv'
		# Create the default filename
		default_filename = (app + '_' + user + '___now__' + file_extensions[self.outputformat]).strip("'")

		folder, filename = event_file.parse_outputfile(self.outputfile, default_filename, target_config)

		if self.compress is not None:
			logger.debug('Compression: %s', self.compress)
		else:
			try:
				self.compress = target_config.get('compress')
			except:
				self.compress = False
		
		staging_filename = 'eventpush_staging_' + random_number + '.txt'
		local_output_file = os.path.join(dispatch, staging_filename)
		if self.compress:
			local_output_file = local_output_file + '.gz'

		# Append .gz to the output file if compress=true
		if not self.compress and len(filename) > 3:
			if filename[-3:] == '.gz':
				# We have a .gz extension when compression was not specified. Enable compression.
				self.compress = True
		elif self.compress and len(filename) > 3:
			if filename[-3:] != '.gz':
				filename = filename + '.gz'
		
		if conn is not None:
			# Use the credential to connect to the SFTP server
			try:
				# Check to see if the folder exists
				folder_attrs = conn.getAttributes(target_config['share_name'], folder, timeout=10)
			except BaseException:
				# Remote directory could not be loaded. It must not exist. Create it. 
				# Create the folders required to store the file
				subfolders = ['/'] + folder.strip('/').split('/')
				if '' in subfolders:
					subfolders.remove('')
				logger.debug("Folders list for dir creation: %s" % str(subfolders))
				current_folder = ''
				folder_depth = len(subfolders) - 1
				for i, subfolder_name in enumerate(subfolders):
					current_folder = (current_folder + '/' + subfolder_name).replace('//', '/')
					logger.debug("Current folder = " + current_folder)
					try:
						conn.getAttributes(target_config['share_name'], current_folder, timeout=10)
					except:
						conn.createDirectory(target_config['share_name'], current_folder, timeout=10)
				try:
					folder_attrs = conn.getAttributes(target_config['share_name'], folder, timeout=10)
				except BaseException as e:
					exit_error(logger, "Could not load or create remote directory: " + repr(e), 377890)
			
			# This should always be true
			if folder_attrs is not None:
				if folder_attrs.isReadOnly or not folder_attrs.isDirectory:
					exit_error(logger, "Could not access the remote directory: " + repr(e), 184772)
				else:
					try:
						event_counter = 0
						# Write the output file to disk in the dispatch folder
						logger.debug("Writing events to file %s in %s format. Compress=%s\n\tfields=%s", local_output_file, self.outputformat, self.compress, self.fields)
						for event in event_file.write_events_to_file(events, self.fields, local_output_file, self.outputformat, self.compress):
							yield event
							event_counter += 1
					except BaseException as e:
						exit_error(logger, "Error writing file to upload: " + repr(e), 296733)
					
					# Write the file to the remote location
					try:
						with open(local_output_file, 'rb', buffering=0) as local_file:
							bytes_uploaded = conn.storeFile(target_config['share_name'], folder + '/' + filename, local_file)
					except BaseException as e:
						exit_error(logger, "Error uploading file to SMB server: " + repr(e), 109693)
			
					if bytes_uploaded > 0:
						message = "SMB Push Status: Success. File name: %s" % (folder + '/' + filename)
						eprint(message)
						logger.info(message)
					else:
						exit_error(logger, "Zero bytes uploaded", 771293)
		else:
			exit_error(logger, "Could not connect to server.", 159528)
		
dispatch(epsmb, sys.argv, sys.stdin, sys.stdout, __name__)


