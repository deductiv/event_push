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

# Python 2 and 3 compatible
# search_ep_hec.py
# Push Splunk events to Splunk HEC over JSON - Search Command
#
# Author: J.R. Murray <jr.murray@deductiv.net>
# Version: 2.0.0 (2021-04-26)

from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
import logging
import sys, os
import time
import socket
import json

# Add lib folders to import path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
# pylint: disable=import-error
from splunk.clilib import cli_common as cli
import splunklib.client as client
import splunklib.results as results
from splunklib.searchcommands import StreamingCommand, dispatch, Configuration, Option, validators
from CsvResultParser import *
from deductiv_helpers import setup_logger, eprint, str2bool, get_config_from_alias, exit_error, port_is_open, replace_object_tokens

# Use the library from George Starcher for HTTP Event Collector
# Updated to support Python3
from splunk_http_event_collector.http_event_collector import http_event_collector   # https://github.com/georgestarcher/Splunk-Class-httpevent
	  
# Define class and type for Splunk command
@Configuration(local=True)
class ephec(StreamingCommand):
	doc='''
	**Syntax:**
	search | ephec target=<target_host_alias>
			host=[host_value|$host_field$]
			source=[source_value|$source_field$]
			sourcetype=[sourcetype_value|$sourcetype_field$]
			index=[index_value|$index_field$] 

	**Description**
	Push Splunk events to an HTTP listener (such as Splunk HEC) over JSON.
	'''

	#Define Parameters
	target = Option(
		doc='''
		**Syntax:** **target=***<target_host_alias>*
		**Description:** Reference to a target HEC endpoint within the configuration
		**Default:** The target configured as "Default" within the HEC Setup page (if any)''',
		require=False)

	host = Option(
		doc='''
		**Syntax:** **host=***[host_value|$host_field$]*
		**Description:** Field or string to be assigned to the host field on the pushed event
		**Default:** $host$, or if not defined, the hostname of the sending host (from inputs.conf)''',
		require=False)

	source = Option(
		doc='''
		**Syntax:** **source=***[source_value|$source_field$]*
		**Description:** Field or string to be assigned to the source field on the pushed event
		**Default:** $source$, or if not defined, it is omitted''',
		require=False)

	sourcetype = Option(
		doc='''
		**Syntax:** **sourcetype=***[sourcetype_value|$sourcetype_field$]*
		**Description:** Field or string to be assigned to the sourcetype field on the pushed event
		**Default:** $sourcetype$, or if not defined, json''',
		require=False)

	index = Option(
		doc='''
		**Syntax:** **index=***[index_value|$index_field$]*
		**Description:** The remote index in which to store the pushed event
		**Default:** $index$, or if not defined, the remote endpoint's default.''',
		require=False) 

	# Validators found @ https://github.com/splunk/splunk-sdk-python/blob/master/splunklib/searchcommands/validators.py

	def __getitem__(self, key):
		return getattr(self,key)

	#define main function
	def stream(self, events):
		try:
			app_config = cli.getConfStanza('ep_general','settings')
			cmd_config = cli.getConfStanzas('ep_hec')
		except BaseException as e:
			raise Exception("Could not read configuration: " + repr(e))
		
		# Facility info - prepended to log lines
		facility = os.path.basename(__file__)
		facility = os.path.splitext(facility)[0]
		try:
			logger = setup_logger(app_config["log_level"], 'event_push.log', facility)
		except BaseException as e:
			raise Exception("Could not create logger: " + repr(e))

		logger.info('HEC Event Push search command initiated')

		# Set defaults
		if self.host is None:
			self.host = "$host$"
		# Get the default values used for data originating from this machine
		inputs_host = cli.getConfStanza('inputs','splunktcp')["host"]

		logger.debug('search_ep_hec command: %s', self)  # logs command line

		if self.source is None:
			self.source = "$source$"

		if self.sourcetype is None:
			self.sourcetype = "$sourcetype$"

		if self.index is None:
			self.index = "$index$"

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
		searchinfo = self._metadata.searchinfo
		app = searchinfo.app
		user = searchinfo.username
		
		# Replace all tokenized parameter strings
		replace_object_tokens(self)
		
		try:
			target_config = get_config_from_alias(cmd_config, self.target)
			if target_config is None:
				exit_error(logger, "Unable to find target configuration.", 100937)

			logger.debug("Target configuration: " + str(target_config))
			hec_token = target_config['token']
			hec_host = target_config['host']
			hec_port = target_config['port']
			hec_ssl = str2bool(target_config['ssl'])
		except BaseException as e:
			exit_error(logger, "Error reading target server configuration: " + repr(e), 124812)

		if len(hec_host) == 0:
			exit_error(logger, "No host specified", 119371)

		# Create HEC object
		hec = http_event_collector(hec_token, hec_host, http_event_port=hec_port, http_event_server_ssl=hec_ssl)
		if port_is_open(hec_host, hec_port):
			logger.debug("Port connectivity check passed")
			if hec.check_connectivity():

				# Special event key fields that can be specified/overridden in the alert action
				meta_keys = ['source', 'sourcetype', 'host', 'index']
				event_count = 0
				for event in events:
					# Get the fields list for the event
					event_keys = list(event.keys())

					payload = {}
					payload_event_src = {}
					# Copy event to new event, so we can change it
					for f in event_keys:
						payload_event_src[f] = event[f]

					if '_time' in event_keys:
						payload.update({ "time": payload_event_src['_time'] })
						del(payload_event_src['_time'])
					else:
						payload.update({ "time": time.time() })

					for k in meta_keys:
						# Loop through the metadata keys: host/source/sourcetype/index
						if getattr(self, k)[0] == getattr(self, k)[-1] and getattr(self, k)[-1] == "$":
							if k in event_keys:
								# If the key field is in the event and its output argument is set to a variable
								payload.update({ k: payload_event_src[getattr(self, k)[1:-1]] })
								# Delete it from the payload event source so it's not included when we dump the rest of the fields later.
								del(payload_event_src[getattr(self, k)[1:-1]])
							elif k == "host" and self.host == "$host$":
								# "host" field not found in event, but has the default value. Use the one from inputs.conf.
								payload.update({ k: inputs_host })
						else:
							# Plaintext entry
							payload.update({ k: self[k] })

					# Only send _raw (no other fields) if the _raw field was included in the search result.
					# (Don't include other fields/values)
					if '_raw' in list(payload_event_src.keys()):
						#logger.debug("Using _raw from search result")
						payload.update({ "event": payload_event_src['_raw'] })
					else:
						payload.update({ "event": payload_event_src })

					event_count += 1
					logger.debug("Payload = " + str(payload))
					hec.batchEvent(payload)
					yield(event)

				hec.flushBatch()
				logger.info("Successfully pushed events. count=%s target=%s app=%s user=%s" % (event_count, hec_host, app, user))
			else: # Connectivity check failed
				exit_error(logger, "HEC endpoint port open but connection test failed.", 104893)
		else:
			if str2bool(hec_ssl):
				protocol = 'https'
			else:
				protocol = 'http'
			exit_error(logger, "Unable to connect to the HEC endpoint: %s" % protocol+'://'+hec_host+':'+hec_port, 100253)
dispatch(ephec, sys.argv, sys.stdin, sys.stdout, __name__)
