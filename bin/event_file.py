# Module to create a text file from search results using a Splunk reporting command
# event_file.py
# Write Splunk search results to a custom formatted file
#
# Author: J.R. Murray <jr.murray@deductiv.net>
# Version: 1.1.2 (2020-06-29)

from __future__ import print_function
from builtins import str
from future import standard_library
standard_library.install_aliases()
import sys, os
import time, datetime
import json
import gzip
import logging
from collections import OrderedDict

# Add lib folder to import path
path_prepend = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib')
sys.path.append(path_prepend)
import deductiv_helpers as dhelp

def flush_buffer(string_list, output_file):
	with open(output_file, "ab") as f:
		f.writelines(string_list)

def flush_buffer_gzip(string_list, output_file):
	with gzip.open(output_file, "ab") as f:
		f.writelines(string_list)

def write_events_to_file(events, fields, local_output, outputformat, compression):
	logger = dhelp.setup_logging('event_push')

	# Buffer variables
	output_file_buf = []
	buffer_flush_count = 1000
	event_counter = 0
	first_field = None

	if outputformat == 'json':
		output_file_buf.append('['.encode('utf-8'))
	
	for event in events:
		if first_field is None:
			first_field = list(event.keys())[0]
			#dhelp.eprint('First field = ' + first_field)
		# Get the fields list for the event
		# Filter the fields if fields= is supplied
		if fields is not None:
			event_keys = []
			for k in list(event.keys()):
				if k in fields:
					event_keys.append(k)
		else:
			event_keys = list(event.keys())

		# Pick the output format on the first event if one was not specified
		if event_counter == 0:
			if outputformat is None and '_raw' in event_keys:
				outputformat = 'raw'
			elif outputformat is None:
				outputformat = 'json'

			# Check event format setting and write a header if needed
			if outputformat == "csv" or outputformat == "tsv" or outputformat == "pipe":
				delimiters = {
					'csv': ',',
					'tsv': '\t',
					'pipe': '|'
				}
				delimiter = delimiters[outputformat]
				# Write header
				header = ''
				for field in event_keys:
					# Quote the string if it has a space
					if ' ' in field and outputformat == "csv":
						field = '"' + field + '"'
					# Concatenate the header field names
					header += field + delimiter
				# Strip off the last delimiter
				header = header[:-1] + '\n'
				output_file_buf.append(header.encode('utf-8'))

		output_text = ''
		# Build the row of text
		if outputformat == "raw":
			if '_raw' in event_keys:
				output_text = event["_raw"]
			else:
				logger.warning("No raw field when raw output selected.")
		elif outputformat == "csv" or outputformat == "tsv" or outputformat == "pipe":
			for key, value in list(event.items()):
				logger.debug("Key = %s, Value = %s", key, value)
				if key in event_keys:
					# Convert list to string value
					if isinstance(value, list):
						#value = '"' + delimiter.join(value).replace('"', r'\"') + '"'
						value = '"' + delimiter.join(value).replace('"', r'""') + '"'
					if outputformat == "csv":
						# Escape any double-quotes
						if '"' in value:
							# String has a quotation mark. Quote it and escape those inside.
							value = dhelp.escape_quotes_csv(value)
							value = '"' + value + '"'
						# Quote the string if it has a space or separator
						elif ' ' in value or ',' in value:
							value = '"' + value + '"'
					
					output_text += value + delimiter
			output_text = output_text[:-1]
		elif outputformat == "kv":
			for key, value in list(event.items()):
				if key in event_keys:
					# Escape any double-quotes
					if '"' in value:
						# String has a quotation mark. Quote it and escape those inside.
						value = dhelp.escape_quotes(value)
						value = '"' + value + '"'
					# Quote the string if it has a space or separator
					elif ' ' in value or '=' in value:
						value = '"' + value + '"'

					output_text += key + "=" + value + ' '
		elif outputformat == "json":
			if fields is not None:
				json_event = {}
				for key in event_keys:
					json_event[key] = event[key]
			else:
				json_event = event
			output_text = json.dumps(json_event) + ','

		# Append entry to the lists
		output_file_buf.append((output_text + '\n').encode('utf-8'))
		event_counter += 1
		#event_buf.append(event)

		# Time to flush the buffers
		if len(output_file_buf) == buffer_flush_count:
			if compression:
				flush_buffer_gzip(output_file_buf, local_output)
			else:
				flush_buffer(output_file_buf, local_output)
			output_file_buf = []
			
		yield(event)
	
	if outputformat == 'json':
		if isinstance(output_file_buf[-1], str):
			dhelp.eprint(output_file_buf[-1])
			output_file_buf[-1] = output_file_buf[-1].replace(',\n', '\n').encode('utf-8')
		elif isinstance(output_file_buf[-1], bytes):
			dhelp.eprint(output_file_buf[-1])
			output_file_buf[-1] = output_file_buf[-1].decode('utf-8').replace(',\n', '\n').encode('utf-8')
		output_file_buf.append(']'.encode('utf-8'))

	if compression:
		flush_buffer_gzip(output_file_buf, local_output)
	else:
		flush_buffer(output_file_buf, local_output)
	output_file_buf = None
	logger.debug("Wrote temp output file " + local_output)
	
	#for x in sorted(event_buf, key=lambda k: k[first_field], reverse=True):
	#	yield x
	
def parse_outputfile(outputfile, default_filename, target_config):

	# Split the output into folder and filename
	if outputfile is not None:
		outputfile = outputfile.replace('\\', '/')
		folder_list = outputfile.split('/')
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
			default_folder = target_config['default_folder'].replace('\\', '/')
			folder_list = default_folder.strip('/').split('/') + folder_list
		else:
			# Use the root folder
			folder_list = ['']
	
	# Replace keywords from output filename and folder
	folder = dhelp.replace_keywords('/'.join(folder_list))
	filename = dhelp.replace_keywords(filename)
	return [folder, filename]