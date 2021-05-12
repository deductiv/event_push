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
	search | epsftp target=<target host alias> outputfile=<output path/filename> outputformat=[json|raw|kv|csv|tsv|pipe] fields="field1, field2, field3" compress=[true|false]

	**Description**
	Push (export) Splunk events to an SFTP server in any format.
	'''

	# Define Parameters
	target = Option(
		doc='''
		**Syntax:** **target=***<target_host_alias>*
		**Description:** Reference to a target SFTP server within the configuration
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
			#logger.debug("Target configuration: " + str(target_config))
		except BaseException as e:
			exit_error(logger, "Error reading target server configuration: " + repr(e), 124812)

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
					key_file = os.path.join(dispatch, 'epsftp_private_key_' + random_number)
					private_key = target_config['private_key'].replace('\\n', '\n')
					with open(key_file, "w") as f:
						f.write(private_key)
						f.close()
					try:
						if 'passphrase' in valid_settings:
							sftp = pysftp.Connection(host=target_config['host'], private_key=key_file, private_key_pass=target_config['passphrase'], cnopts=cnopts)
						else:
							sftp = pysftp.Connection(host=target_config['host'], username=target_config['username'], private_key=key_file, cnopts=cnopts)
					except BaseException as e:
						exit_error(logger, "Unable to setup SFTP connection with private key: " + repr(e), 921982)
				else:
					exit_error(logger, "Required settings not found", 101926)
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
		
		if sftp is not None:
			# Use the credential to connect to the SFTP server
			try:
				sftp.makedirs(folder)
				sftp.chdir(folder)
			except BaseException as e:
				exit_error(logger, "Could not load remote SFTP directory: " + repr(e), 6)

			contents = sftp.listdir()
			if filename in contents:
				file_exists = True
			else:
				file_exists = False
			
			try:
				event_counter = 0
				# Write the output file to disk in the dispatch folder
				logger.debug("Writing events to file %s in %s format. Compress=%s\n\tfields=%s", local_output_file, self.outputformat, self.compress, self.fields)
				for event in event_file.write_events_to_file(events, self.fields, local_output_file, self.outputformat, self.compress):
					yield event
					event_counter += 1
			except BaseException as e:
				exit_error(logger, "Error writing file to upload", 296733)
		
			try:
				# Upload the file
				sftp.put(local_output_file)
			except BaseException as e:
				exit_error(logger, "Error uploading file to SFTP server: " + repr(e), 109693)

			try:
				# Rename the file
				if file_exists:
					sftp.remove(filename)
				remote_staging_filename = folder + '/' + local_output_file.split('/')[-1]
				remote_target_filename = folder + '/' + filename
				sftp.rename(remote_staging_filename, remote_target_filename)

				if filename in sftp.listdir():
					message = "SFTP Push Status: Success. File name: %s" % (folder + '/' + filename)
					eprint(message)
					logger.info(message)
				else:
					exit_error(logger, "Could not verify uploaded file exists", 771293)
			except BaseException as e:
				exit_error(logger, "Error renaming or replacing file on SFTP server. Does the file already exist?" + repr(e), 109693)
		else:
			exit_error(logger, "Credential not configured.", 8)
		

dispatch(epsftp, sys.argv, sys.stdin, sys.stdout, __name__)


