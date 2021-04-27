#!/usr/bin/env python

# Copyright 2020 Deductiv Inc.
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
import logging
import sys, os, platform
import time, datetime
import random
import re
import json
from deductiv_helpers import setup_logger, eprint, decrypt_with_secret, get_config_from_alias, replace_keywords, exit_error

# Add lib subfolders to import path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
# pylint: disable=import-error
from splunk.clilib import cli_common as cli
import splunk.entity as entity
import splunklib.client as client
import splunklib.results as results
from splunklib.searchcommands import ReportingCommand, dispatch, Configuration, Option, validators
import event_file

# Import the correct version of cryptography
# https://pypi.org/project/cryptography/
os_platform = platform.system()
py_major_ver = sys.version_info[0]

# Import the correct version of platform-specific libraries
if os_platform == 'Linux':
	if py_major_ver == 3:
		path_prepend = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib', 'py3_linux_x86_64')
	elif py_major_ver == 2:
		path_prepend = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib', 'py2_linux_x86_64')
elif os_platform == 'Darwin': # Does not work with Splunk Python3 build. It requires code signing for libs.
	if py_major_ver == 3:
		path_prepend = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib', 'py3_darwin_x86_64')
	elif py_major_ver == 2:
		path_prepend = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib', 'py2_darwin_x86_64')
elif os_platform == 'Windows':
	if py_major_ver == 3:
		path_prepend = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib', 'py3_win_amd64')
	elif py_major_ver == 2:
		path_prepend = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib', 'py2_win_amd64')

sys.path.append(path_prepend)

import pysftp

# Define class and type for Splunk command
@Configuration()
class epsftp(ReportingCommand):
	doc='''
	**Syntax:**
	search | epsftp target=<target host> outputfile=<output path/filename> outputformat=[json|raw|kv|csv|tsv|pipe] fields="field1, field2, field3" compress=[true|false]

	**Description**
	Push Splunk events to an SFTP server in any format.
	'''

	# Define Parameters
	target = Option(
		doc='''
		**Syntax:** **target=***<target_alias>*
		**Description:** Reference to a target Box app within the configuration
		**Default:** The target configured as "Default" within the setup page (if any)''',
		require=False)

	outputfile = Option(
		doc='''
		**Syntax:** **outputfile=***<file path/file name>*
		**Description:** The name of the file to be written to Box
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
			cmd_config = cli.getConfStanzas('ep_sftp')
		except BaseException as e:
			raise Exception("Could not read configuration: " + repr(e))
		
		# Facility info - prepended to log lines
		facility = os.path.basename(__file__)
		facility = os.path.splitext(facility)[0]
		try:
			logger = setup_logger(app_config["log_level"], 'event_push.log', facility)
		except BaseException as e:
			raise Exception("Could not create logger: " + repr(e))

		logger.info('SFTP Event Push search command initiated')

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

		# Use the random number to support running multiple outputs in a single search
		random_number = str(random.randint(10000, 100000))

		try:
			target_config = get_config_from_alias(cmd_config, self.target)
			if target_config is None:
				exit_error(logger, "Unable to find target configuration.", 100937)
			logger.debug("Target configuration: " + str(target_config))
		except BaseException as e:
			exit_error(logger, "Error reading target server configuration: " + repr(e), 124812)

		# Check to see if we have credentials
		valid_settings = []
		for l in list(target_config.keys()):
			if len(target_config[l]) > 0:
				valid_settings.append(l) 
		if 'host' in valid_settings and 'port' in valid_settings:
			# A target has been configured. Check for credentials.
			try:
				if ('username' in valid_settings and 'password' in valid_settings):
					sftp = pysftp.Connection(host=target_config['host'], username=target_config['username'], password=decrypt_with_secret(target_config['client_secret']))
				elif ('private_key' in valid_settings and 'passphrase' in valid_settings):
					# Write the decrypted private key to a temporary file
					key_file = os.path.join(dispatch, 'epsftp_private_key_' + random_number)
					with open(key_file, "w") as f:
						f.write(decrypt_with_secret(target_config['private_key']).replace('\\n', '\n'))
						f.close()
					sftp = pysftp.Connection(host=target_config['host'], private_key=key_file, private_key_pass=decrypt_with_secret(target_config['passphrase']).strip())

				if sftp is None:
					exit_error(logger, "Unable to setup SFTP connection", 921982)
			except BaseException as e: 
				exit_error(logger, "Could not find or decrypt the specified credential: " + repr(e), 230494)
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
		now = str(int(time.time()))
		default_filename = (app + '_' + user + '___now__' + file_extensions[self.outputformat]).strip("'")

		folder, filename = event_file.parse_outputfile(self.outputfile, default_filename, target_config)
		'''
		# Split the output into folder and filename
		if self.outputfile is not None:
			folder_list = self.outputfile.split('/')
			if len(folder_list) == 1:
				# No folder specified, use the default
				use_default_folder = True
				filename = folder_list[0]
			elif folder_list[0] == '':
				# Length > 1, outputfile points to the root folder (leading /)
				use_default_folder = False
			else:
				# Length > 1 and outputfile points to a relative path (no leading /)
				use_default_folder = True

			if len(folder_list) > 1 and folder_list[-1] == '':
				# No filename provided, trailing /
				filename = default_filename
				folder_list.pop()
			elif len(folder_list) > 1 and len(folder_list[-1]) > 0:
				filename = folder_list[-1]
				folder_list.pop()
		else:
			use_default_folder = True
			filename = default_filename
			folder_list = []
		
		if use_default_folder:
			if 'default_folder' in list(target_config.keys()):
				# Use the configured default folder
				folder_list = target_config['default_folder'].strip('/').split('/') + folder_list
			else:
				# Use the root folder
				folder_list = ['']
		
		# Replace keywords from output filename and folder
		folder = replace_keywords('/'.join(folder_list))
		filename = replace_keywords(filename)
		logger.debug("Folder = " + folder)
		logger.debug("Filename = " + filename)
		'''

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
		logger.debug("Staging file: %s" % local_output_file)

		# Append .gz to the output file if compress=true
		if not self.compress and len(filename) > 3:
			if filename[-3:] == '.gz':
				# We have a .gz extension when compression was not specified. Enable compression.
				self.compress = True
		elif self.compress and len(filename) > 3:
			if filename[-3:] != '.gz':
				filename = filename + '.gz'
		
		if sftp is not None:
			
			# Use the credential to connect to the SFTP server
			try:
				# Create the folders required to store the file
				subfolders = folder.strip('/').split('/')
				if '' in subfolders:
					subfolders.remove('')
				logger.debug("Folders: %s" % str(subfolders))
				with sftp.cd('/'):
					x = sftp.listdir()
					logger.debug(x)
				'''
				# Prepend the list with the root element
				box_folder_object = client.root_folder().get()
				# Walk the folder path until we find the target directory
				for subfolder_name in subfolders:
					logger.debug("Looking for folder: %s" % subfolder_name)
					# Get the folder ID for the string specified from the list of child subfolders
					# folder object is from the previous iteration
					folder_contents = box_folder_object.get_items()
					folder_found = False
					for item in folder_contents:
						if item.type == 'folder':
							#logger.debug('{0} {1} is named "{2}"'.format(item.type.capitalize(), item.id, item.name))
							if subfolder_name == item.name:
								logger.debug("Found a target folder ID: %s" % str(item.id))
								box_folder_object = client.folder(folder_id=item.id)
								folder_found = True
					if not folder_found:
						# Create the required subfolder
						box_folder_object = box_folder_object.create_subfolder(subfolder_name)
				'''

				try:
					event_counter = 0
					# Write the output file to disk in the dispatch folder
					logger.debug("Writing events to file %s in %s format. Compress=%s\n\tfields=%s", local_output_file, self.outputformat, self.compress, self.fields)
					for event in event_file.write_events_to_file(events, self.fields, local_output_file, self.outputformat, self.compress):
						yield event
						event_counter += 1
				except BaseException as e:
					exit_error(logger, "Error writing file to upload", 296733)
			except BaseException as e:
				exit_error(logger, "Could not load remote SFTP directory: " + repr(e), 6)
		
			try:
				#new_file = box_folder_object.upload(local_output_file, file_name=filename)
				#message = "Box Event Push Status: Success. File name: %s, File ID: %s" % (new_file.name, new_file.id)
				#eprint(message)
				#logger.info(message)
				pass
			except BaseException as e:
				exit_error(logger, "Error uploading file to SFTP server: " + repr(e), 109693)
		else:
			exit_error(logger, "Credential not configured.", 8)
		

dispatch(epsftp, sys.argv, sys.stdin, sys.stdout, __name__)


