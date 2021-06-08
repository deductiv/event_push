# Common cross-app functions to simplify code

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

# Author: J.R. Murray <jr.murray@deductiv.net>
# Version: 2.0.0

from __future__ import print_function
from builtins import str
from future import standard_library
standard_library.install_aliases()
import sys, os
import urllib.request, urllib.parse, urllib.error
import re
import logging
from logging import handlers
import configparser
import time
import datetime
import socket
import json

# Add lib folders to import path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))

# https://github.com/HurricaneLabs/splunksecrets/blob/master/splunksecrets.py
from splunksecrets import decrypt	# pylint: disable=import-error

# pylint: disable=import-error
import splunk.entity as en 
from splunk.rest import simpleRequest

def get_credentials(app, session_key):
	try:
		# list all credentials
		entities = en.getEntities(['admin', 'passwords'], namespace=app,
									owner='nobody', sessionKey=session_key)
	except Exception as e:
		raise Exception("Could not get %s credentials from Splunk. Error: %s" % (app, str(e)))

	credentials = []
	
	for id, c in list(entities.items()):		# pylint: disable=unused-variable
		# c.keys() = ['clear_password', 'password', 'username', 'realm', 'eai:acl', 'encr_password']
		if c['eai:acl']['app'] == app:
			credentials.append( {'realm': c["realm"], 'username': c["username"], "password": c["clear_password"] } )
	
	if len(credentials) > 0:
		return credentials
	else:
		raise Exception("No credentials have been found")

# HTTP request wrapper
def request(method, url, data, headers):
	"""Helper function to fetch data from the given URL"""
	# See if this is utf-8 encoded already
	try:
	    string.decode('utf-8')
	except:
		try:
			data = urllib.parse.urlencode(data).encode("utf-8")
		except:
			data = data.encode("utf-8")
	req = urllib.request.Request(url, data, headers)
	req.get_method = lambda: method
	res_txt = ""
	res_code = "0"
	try: 
		res = urllib.request.urlopen(req)
		res_txt = res.read()
		res_code = res.getcode()
	except urllib.error.HTTPError as e:
		res_code = e.code
		res_txt = e.read()
		eprint("HTTP Error: " + str(res_txt))
	except BaseException as e:
		eprint("URL Request Error: " + str(e))
		sys.exit(1)
	return res_txt, res_code

def setup_logging(logger_name):
	logger = logging.getLogger(logger_name)
	return logger

# For alert actions
def setup_logger(level, filename, facility):
	logger = logging.getLogger(filename)
	# Prevent the log messages from being duplicated in the python.log file
	logger.propagate = False 
	logger.setLevel(level)
	
	log_file = os.path.join( os.environ['SPLUNK_HOME'], 'var', 'log', 'splunk', filename )
	file_handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=25000000, backupCount=2)
	formatter = logging.Formatter('%(asctime)s [{0}] %(levelname)s %(message)s'.format(facility))
	file_handler.setFormatter(formatter)
	logger.addHandler(file_handler)
	
	return logger

def read_config(filename):
	config = configparser.ConfigParser()
	app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
	app_child_dirs = ['default', 'local']
	for cdir in app_child_dirs:
		try:
			config_file = os.path.join( app_dir, cdir, filename )
			config.read(config_file)
		except:
			pass
	return config

# Merge two dictionary objects (x,y) into one (z)
def merge_two_dicts(x, y):
	z = x.copy()	# start with x's keys and values
	z.update(y)	# modifies z with y's keys and values & returns None
	return z

def hex_convert(s):
	return ":".join("{:02x}".format(ord(c)) for c in s)

def str2bool(v):
	if isinstance(v, bool):
		return v
	else:
		return str(v).lower() in ("yes", "y", "true", "t", "1")

# STDERR printing for python 3
def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def escape_quotes(string):
	string = re.sub(r'(?<=\\)"', r'\\\"', string)
	string = re.sub(r'(?<!\\)"', r'\"', string)
	return string

def get_config_from_alias(config_data, stanza_guid_alias = None):
	# Parse and merge the configuration
	try:
		# Delete blank configuration values (in case setup process wrote them)
		for guid in list(config_data.keys()):
			for setting in list(config_data[guid].keys()):
				if config_data[guid][setting] is not None and len(config_data[guid][setting]) == 0:
					del config_data[guid][setting]

		# Set the default configuration
		if 'default' in list(config_data.keys()):
			default_target_config = config_data['default']
		else:
			default_target_config = {}

		# See if a GUID was provided explicitly (used by alert actions)
		# 8-4-4-4-12 format 
		logger = setup_logging('event_push')
		try:
			if stanza_guid_alias is not None:
				logger.debug(type(stanza_guid_alias))
				if re.match(r'[({]?[a-f0-9]{8}[-]?([a-f0-9]{4}[-]?){3}[a-f0-9]{12}[})]?', stanza_guid_alias, flags=re.IGNORECASE):
					logger.debug("Using guid " + stanza_guid_alias)
					return merge_two_dicts(default_target_config, config_data[stanza_guid_alias])
		except BaseException as e:
			logger.exception("Exception caught: " + repr(e))

		# Loop through all GUID stanzas for the specified alias
		for guid in list(config_data.keys()):
			if guid != 'default':
				# Merge the configuration with the default config to fill in null values
				config_stanza = merge_two_dicts(default_target_config, config_data[guid])
				guid_is_default = str2bool(config_stanza['default'])
				# Check to see if this is the configuration we want to use
				if 'alias' in list(config_stanza.keys()):
					if config_stanza['alias'] == stanza_guid_alias or (stanza_guid_alias is None and guid_is_default):
						# Return the specified target configuration, or default if target not specified
						return config_stanza
		return None
	except BaseException as e:
		raise Exception("Unable to find target configuration: " + repr(e))

def replace_keywords(s):

	now = str(int(time.time()))
	nowft = datetime.datetime.now().strftime("%F_%H%M%S")
	today = datetime.datetime.now().strftime("%F")

	strings_to_replace = {
		'__now__': now,
		'__nowft__': nowft,
		'__today__': today
	}
	
	for x in list(strings_to_replace.keys()):
		s = s.replace(x, strings_to_replace[x])
	
	return s

def exit_error(logger, message, error_code=1):
	logger.critical(message)
	print(message)
	exit(error_code)

def decrypt_with_secret(encrypted_text):
	# Check for encryption
	if encrypted_text[:1] == '$':
		# Decrypt the text
		# Read the splunk.secret file
		with open(os.path.join(os.getenv('SPLUNK_HOME'), 'etc', 'auth', 'splunk.secret'), 'r') as ssfh:
			splunk_secret = ssfh.readline()
		# Call the decrypt function from splunksecrets.py
		return decrypt(splunk_secret, encrypted_text)
	else:
		# Not encrypted
		return encrypted_text

def port_is_open(ip, port):
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.settimeout(3)
	try:
		s.connect((ip, int(port)))
		s.shutdown(2)
		return True
	except:
		return False

if __name__ == "__main__":
	pass

def get_tokens(searchinfo):
	tokens = {}
	# Get the host of the splunkd service
	splunkd_host = searchinfo.splunkd_uri[searchinfo.splunkd_uri.index("//")+2:searchinfo.splunkd_uri.rindex(":")]
	splunkd_port = searchinfo.splunkd_uri[searchinfo.splunkd_uri.rindex(":")+1:]

	tokens = {
		'splunkd_host': splunkd_host,
		'splunkd_port': splunkd_port
	}

	# Get the search job attributes
	if searchinfo.sid: 
		job_uri = en.buildEndpoint(
			[
				'search', 
				'jobs', 
				searchinfo.sid
			], 
			namespace=searchinfo.app, 
			owner=searchinfo.owner
		)
		job_response = simpleRequest(job_uri, method='GET', getargs={'output_mode':'json'}, sessionKey=searchinfo.session_key)[1]
		search_job         = json.loads(job_response)
		job_content        = search_job['entry'][0]['content']
	else:
		job_content        = {}

	for key, value in list(job_content.items()):
		if value is not None:
			tokens['job.' + key] = json.dumps(value, default=lambda o: o.__dict__)
	#eprint("job_content=" + json.dumps(job_content))

	if 'label' in list(job_content.keys()):
		tokens['name'] = job_content['label']

		# Get the saved search properties
		entityClass = ['saved', 'searches']
		uri = en.buildEndpoint(
			entityClass,
			namespace=searchinfo.app, 
			owner=searchinfo.owner
		)

		responseBody = simpleRequest(uri, method='GET', getargs={'output_mode':'json'}, sessionKey=searchinfo.session_key)[1]

		saved_search = json.loads(responseBody)
		ss_content = saved_search['entry'][0]['content']
		#eprint("SSContent=" + json.dumps(ss_content))

		for key, value in list(ss_content.items()):
			if not key.startswith('display.'):
				if value is not None:
					tokens[key] = json.dumps(value, default=lambda o: o.__dict__)

	tokens['owner'] = searchinfo.owner
	tokens['app'] = searchinfo.app
	#tokens['results_link'] = 'http://127.0.0.1:8000/en-US/app/search/search?sid=1622650709.10799'
	
	# Parse all of the nested objects (recursive function)
	for t, tv in list(tokens.items()):
		tokens = merge_two_dicts(tokens, parse_nested_json(t, tv))
	
	#for t, tv in list(tokens.items()):
	#	if type(tv) == str:
	#		eprint(t + '=' + tv)
	#	else:
	#		eprint(t + "(type " + str(type(tv)) + ") = " + str(tv))
	return tokens

def parse_nested_json(parent_name, j):
	retval = {}
	try:
		if j is not None:
			sub_tokens = json.loads(j)
			if sub_tokens is not None:
				for u, uv in list(sub_tokens.items()):
					if type(uv) == dict:
						retval = merge_two_dicts(retval, parse_nested_json(parent_name + '.' + u, json.dumps(uv)))
					else:
						retval[(parent_name + '.' + u).replace('..', '.')] = uv
						#eprint('added subtoken ' + (parent_name + '.' + u).replace('..', '.') + '=' + str(uv))
		return retval
	except ValueError:
		return {parent_name: j}
	except AttributeError:
		return {parent_name: j}
	except BaseException as e:
		eprint("Exception parsing JSON subtoken: " + repr(e))
	
def replace_object_tokens(o):
	tokens = get_tokens(o._metadata.searchinfo)
	for var in vars(o):
		val = getattr(o, var)
		try:
			if '$' in val:
				try:
					setattr(o, var, replace_string_tokens(tokens, val))
				except BaseException as e:
					eprint("Error replacing token text for variable %s value %s: %s" % (var, val, repr(e)))
		except:
			# Probably an index out of range error
			pass
	#return o

	#for t, v in list(tokens.items()):
	#	param = param.replace('$'+t+'$', v)
	#return param

def replace_string_tokens(tokens, v):
	b = v
	# Replace all tokenized strings
	for t, tv in list(tokens.items()):
		if tv is not None:
			v = v.replace('$'+t+'$', str(tv))
	# Print the result if the value changed
	#if b != v:
	#	eprint(b + ' -> ' + v)
	return v