from __future__ import print_function
from builtins import str
from future import standard_library
standard_library.install_aliases()
import sys, os, platform
import random
import re
import json

# Add lib subfolders to import path
#sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
# pylint: disable=import-error
from splunk.clilib import cli_common as cli
import splunk.entity as entity
import splunklib.client as client
from splunk.persistconn.application import PersistentServerConnectionApplication
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from deductiv_helpers import setup_logger, str2bool, decrypt_with_secret, get_config_from_alias
from ep_helpers import get_aws_s3_directory, get_box_directory, get_sftp_directory, get_smb_directory

config = cli.getConfStanza('ep_general','settings')
# Facility info - prepended to log lines
facility = os.path.basename(__file__)
facility = os.path.splitext(facility)[0]
logger = setup_logger(config["log_level"], 'event_push.log', facility)

def return_error(error_text):
	return {'error': error_text, 
		'status': 500}

def get_directory_contents(config_file, config, query):
	# Use config_file to decide which method to call
	try:
		if config_file == 'ep_aws_s3':
			return get_aws_s3_directory(config, query['folder'])
		elif config_file == 'ep_box':
			return get_box_directory(config, query['folder'])
		elif config_file == 'ep_sftp':
			return get_sftp_directory(config, query['folder'])
		elif config_file == 'ep_smb':
			return get_smb_directory(config, query['folder'])
			
	except BaseException as e:
		#logger.exception("Could not get directory listing: " + repr(e))
		raise Exception("Could not get directory listing: " + repr(e))

class RemoteDirectoryListingHandler(PersistentServerConnectionApplication):
	def __init__(self, command_line, command_arg):
		#super(PersistentServerConnectionApplication, self).__init__()	# pylint: disable=bad-super-call
		PersistentServerConnectionApplication.__init__(self)
	
	# Handle a syncronous from splunkd.
	def handle(self, in_string):
		"""
		Called for a simple synchronous request.
		@param in_string: request data passed in
		@rtype: string or dict
		@return: String to return in response.  If a dict was passed in,
				it will automatically be JSON encoded before being returned.
		"""

		try:
			config = {
				"general": cli.getConfStanza('ep_general','settings'),
				"ep_aws_s3": cli.getConfStanzas('ep_aws_s3'),
				"ep_box": cli.getConfStanzas('ep_box'),
				"ep_sftp": cli.getConfStanzas('ep_sftp'),
				"ep_smb": cli.getConfStanzas('ep_smb'),
			}
		
		except BaseException as e:
			raise Exception("Could not read configuration: " + repr(e))
		
		input = json.loads(in_string)
		logger.debug("Received connection from src_ip=%s user=%s" % (input['connection']['src_ip'], input['session']['user']))
		# Check for permissions

		if "query" in list(input.keys()):
			query = {}
			#logger.debug('input query = ' + str(input['query']))
			if isinstance(input['query'], list):
				for i in input['query']:
					query[i[0]] = i[1]
			logger.debug('query = ' + str(query))

			if "config" in list(query.keys()) and "alias" in list(query.keys()):
				config_file = query['config']
				entry_alias = query['alias']
			else: 
				return_error("Invalid query")

			try:
				datasource_config = get_config_from_alias(config[config_file], entry_alias)
			except BaseException as e:
				logger.exception("Could not get config: " + repr(e))

			logger.debug('datasource_config = ' + str(datasource_config))
			if datasource_config is not None:
				# Set the defaults
				if 'folder' not in list(query.keys()):
					if 'default_bucket' in list(datasource_config.keys()):
						query['folder'] = datasource_config['default_bucket']
					else:
						query['folder'] = ''
					if 'default_folder' in list(datasource_config.keys()):
						query['folder'] = (query['folder'] + '/' + datasource_config['default_folder']).replace('//', '/')
				try:
					payload = get_directory_contents(config_file, datasource_config, query)
					try:
						payload = json.dumps(payload)
					except BaseException as e:
						return_error("Could not convert payload to JSON: " + repr(e))
					return {
						"payload": payload,
						"status": 200
					}
				except BaseException as e:
					return_error("Error getting the directory listing: " + repr(e))
			else:
				return_error("Cannot find the specified configuration")
		else:
			return_error("No query supplied")
		
	def handleStream(self, handle, in_string):
		"""
		For future use
		"""
		raise NotImplementedError(
			"PersistentServerConnectionApplication.handleStream")

	def done(self):
		"""
		Virtual method which can be optionally overridden to receive a
		callback after the request completes.
		"""
		pass

