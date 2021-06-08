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

# Python 2 and 3 compatible
# search_ep_aws_s3.py
# Push Splunk search results to AWS S3 - Search Command
#
# Author: J.R. Murray <jr.murray@deductiv.net>
# Version: 2.0.0 (2021-04-26)

from __future__ import print_function
from builtins import str
from future import standard_library
standard_library.install_aliases()
import logging
import sys, os, platform
import random
import re
from deductiv_helpers import setup_logger, get_config_from_alias, replace_keywords, exit_error, replace_object_tokens, str2bool

# Add lib folders to import path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
# pylint: disable=import-error
from splunk.clilib import cli_common as cli
import splunk.entity as entity
import splunklib.client as client
import splunklib.results as results
from splunklib.searchcommands import ReportingCommand, dispatch, Configuration, Option, validators
import event_file
from ep_helpers import get_aws_connection
#import boto3
#from botocore.config import Config

# Define class and type for Splunk command
@Configuration()
class epawss3(ReportingCommand):
	doc='''
	**Syntax:**
	search | epawss3 target=<target alias> bucket=<bucket> outputfile=<output path/filename> outputformat=[json|raw|kv|csv|tsv|pipe]

	**Description**
	Push Splunk events to AWS S3 (or compatible) over JSON or raw text.
	'''

	#Define Parameters
	target = Option(
		doc='''
		**Syntax:** **target=***<target alias>*
		**Description:** The name of the AWS target alias provided on the configuration dashboard
		**Default:** The target configured as "Default" within the AWS S3 Setup page (if any)''',
		require=False)

	bucket = Option(
		doc='''
		**Syntax:** **bucket=***<bucket name>*
		**Description:** The name of the destination S3 bucket
		**Default:** The bucket name from the AWS S3 Setup page (if any)''',
		require=False)

	outputfile = Option(
		doc='''
		**Syntax:** **outputfile=***<output path/filename>*
		**Description:** The path and filename to be written to the S3 bucket
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
		**Description:** Limit the fields to be written to the S3 file
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
			cmd_config = cli.getConfStanzas('ep_aws_s3')
		except BaseException as e:
			raise Exception("Could not read configuration: " + repr(e))

		# Facility info - prepended to log lines
		facility = os.path.basename(__file__)
		facility = os.path.splitext(facility)[0]
		try:
			logger = setup_logger(app_config["log_level"], 'event_push.log', facility)
		except BaseException as e:
			raise Exception("Could not create logger: " + repr(e))

		logger.info('AWS S3 Event Push search command initiated')
		logger.debug("Configuration: " + str(cmd_config))
		logger.debug('search_ep_hec command: %s', self)  # logs command line

		# Enumerate settings
		app = self._metadata.searchinfo.app
		user = self._metadata.searchinfo.username
		dispatch = self._metadata.searchinfo.dispatch_dir

		# Replace all tokenized parameter strings
		replace_object_tokens(self)

		# Build the configuration
		aws_config = get_config_from_alias(cmd_config, self.target)

		'''
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
		'''

		if self.bucket is None:
			if 'default_s3_bucket' in list(aws_config.keys()):
				t = aws_config['default_s3_bucket']
				if t is not None and len(t) > 0:
					self.bucket = t
				else:
					exit_error(logger, "No bucket specified", 4)
			else:
				exit_error(logger, "No bucket specified", 5)
		
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

		if self.outputfile is None:
			# Boto is special. We need repr to give it the encoding it expects to match the hashing.
			self.outputfile = repr(app + '_' + user + '___now__' + file_extensions[self.outputformat]).strip("'")
		
		# Replace keywords from output filename
		self.outputfile = replace_keywords(self.outputfile)

		if self.compress is not None:
			logger.debug('Compression: %s', self.compress)
		else:
			try:
				self.compress = str2bool(aws_config['compress'])
			except:
				self.compress = False
		
		# Use the random number to support running multiple outputs in a single search
		random_number = str(random.randint(10000, 100000))
		staging_filename = 'eventpush_staging_' + random_number + '.txt'
		local_output_file = os.path.join(dispatch, staging_filename)

		# Append .gz to the output file if compress=true
		if not self.compress and len(self.outputfile) > 3:
			# We have a .gz extension when compression was not specified. Enable compression.
			if self.outputfile[-3:] == '.gz':
				self.compress = True
		elif self.compress and len(self.outputfile) > 3:
			if self.outputfile[-3:] != '.gz':
				self.outputfile = self.outputfile + '.gz'

		if self.compress:
			local_output_file = local_output_file + '.gz'
		
		logger.debug("Staging file: %s" % local_output_file)
		try:
			s3 = get_aws_connection(aws_config)
		except BaseException as e:
			exit_error(logger, "Could not connect to AWS: " + repr(e), 741423)
			
		'''
		if use_arn:
			# Use the current/caller identity ARN from the EC2 instance to connect to S3
			logger.debug("Using ARN to connect")
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
				s3 = boto3.client(
					's3',
					aws_access_key_id=credentials['AccessKeyId'],
					aws_secret_access_key=credentials['SecretAccessKey'],
					aws_session_token=credentials['SessionToken'],
				)
				logger.debug("Connected using assumed role %s", role_arn)
			except BaseException as e:

				exit_error(logger, "Could not connect to S3. Failed to assume role: " + repr(e), 7)

		elif aws_config['access_key_id'] is not None and aws_config['secret_key'] is not None:
			# Use the credential to connect to S3
			try:
				s3 = boto3.client(
					's3',
					aws_access_key_id=aws_config['access_key_id'],
					aws_secret_access_key=aws_config['secret_key'],
					config=boto_config,
					endpoint_url=endpoint_url)
				logger.debug("Connected using OAuth credential")
			except BaseException as e:
				exit_error(logger, "Could not connect to S3 using OAuth keys: " + repr(e), 6)
		else:
			exit_error(logger, "ARN not configured and credential not specified.", 8)
		'''

		event_counter = 0
		# Write the output file to disk in the dispatch folder
		logger.debug("Writing events to file %s in %s format. Compress=%s\n\tfields=%s", local_output_file, self.outputformat, self.compress, self.fields)
		for event in event_file.write_events_to_file(events, self.fields, local_output_file, self.outputformat, self.compress):
			yield event
			event_counter += 1

		# Upload file to s3
		try:
			with open(local_output_file, "rb") as f:
				s3.upload_fileobj(f, self.bucket, self.outputfile)
			s3 = None
			sts_client = None
			logger.info("Successfully pushed events to s3. app=%s count=%s bucket=%s file=%s user=%s" % (app, event_counter, self.bucket, self.outputfile, user))
			os.remove(local_output_file)
		except s3.exceptions.NoSuchBucket as e:
			exit_error(logger, "Error: No such bucket", 123833)
		except BaseException as e:
			exit_error(logger, "Could not upload file to S3: " + repr(e), 9)

dispatch(epawss3, sys.argv, sys.stdin, sys.stdout, __name__)


