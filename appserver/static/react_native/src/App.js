/* Copyright 2021 Deductiv Inc.
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
# Version: 2.0.0 (2021-04-26)
*/
 
import React, { forwardRef, Suspense } from 'react';
import { Tab, Tabs, TabList, TabPanel } from 'react-tabs';
import { FormControl, TextField, Select, InputLabel, MenuItem } from '@material-ui/core';
import MaterialTable from '@material-table/core';
// Snackbar notifications
import { withSnackbar } from 'notistack';
// UUID for stanza name generation
import uuid from 'react-native-uuid';
import validator from 'validator';
import moment from 'moment';
import 'moment-timezone';

// Lazy load controls for the file browser UI
const FadeIn = React.lazy(() => import('react-fade-in'));
const FileBrowserModal = React.lazy(() => import('./FileBrowserModal'));

// Stylesheets
import 'react-tabs/style/react-tabs.css';

import Search from "@material-ui/icons/Search";
import FirstPage from "@material-ui/icons/FirstPage";
import LastPage from "@material-ui/icons/LastPage";
import ChevronRight from "@material-ui/icons/ChevronRight";
import ChevronLeft from "@material-ui/icons/ChevronLeft";
import Clear from "@material-ui/icons/Clear";
import ArrowDownward from "@material-ui/icons/ArrowDownward";
import Info from "@material-ui/icons/Info";
import Check from "@material-ui/icons/Check";
import Delete from "@material-ui/icons/Delete";
import Edit from "@material-ui/icons/Edit";
import Add from "@material-ui/icons/Add";
import Remove from '@material-ui/icons/Remove';
import SaveAlt from '@material-ui/icons/SaveAlt';
import FolderIcon from '@material-ui/icons/Folder';
const tableIcons = {
	Search: forwardRef((props, ref) => <Search {...props} ref={ref}/>),
	FirstPage: forwardRef((props, ref) => <FirstPage {...props} ref={ref}/>),
	LastPage: forwardRef((props, ref) => <LastPage {...props} ref={ref}/>),
	NextPage: forwardRef((props, ref) => <ChevronRight {...props} ref={ref}/>),
	PreviousPage: forwardRef((props, ref) => <ChevronLeft {...props} ref={ref}/>),
	Clear: forwardRef((props, ref) => <Clear {...props} ref={ref}/>),
	ResetSearch: forwardRef((props, ref) => <Clear {...props} ref={ref}/>),
	SortArrow: forwardRef((props, ref) => <ArrowDownward {...props} ref={ref}/>),
	Info: forwardRef((props, ref) => <Info {...props} ref={ref}/>),
	DetailPanel: forwardRef((props, ref) => <Info {...props} ref={ref}/>),
	Check: forwardRef((props, ref) => <Check {...props} ref={ref}/>),
	Delete: forwardRef((props, ref) => <Delete {...props} ref={ref}/>),
	Edit: forwardRef((props, ref) => <Edit {...props} ref={ref}/>),
	Add: forwardRef((props, ref) => <Add {...props} ref={ref}/>),
	ThirdStateCheck: forwardRef((props, ref) => <Remove {...props} ref={ref}/>),
	Export: forwardRef((props, ref) => <SaveAlt {...props} ref={ref}/>),
	Open: forwardRef((props, ref) => <FolderIcon {...props} ref={ref}/>)
};

const validators = {
	number: (value) => {
		if (value === undefined || !validator.isFloat(value) || !validator.isInt(value)) {
			return {isValid: false};
		}
		return {isValid: true}
	},
	bool: (value) => {
		if (value === undefined || (value !== true && value !== false)) {
			return {isValid: false};
		}
		return {isValid: true}
	},
	string: (value) => {
		if (value === undefined || validator.isEmpty(value) || !validator.isAscii(value)) {
			return {isValid: false};
		}
		return {isValid: true}
	},
	time: (value) => {
		if (value === undefined || !validator.isDate(value)) {
			return {isValid: false};
		}
		return true
	},
	uuid: (value) => {
		if (value === undefined || !validator.isUUID(value, 4)) {
			return {isValid: false};
		}
		return {isValid: true}
	}
}

// Options for notistack - Event notification/alerting library - Success/fail on table operations
const notistack_options = (variant) => {
	return {
		variant: variant,
		autoHideDuration: 3000
	}
}

const booleanize = (value) => {
	if (value === undefined){
		return false;
	} else if (typeof(value) == 'string'){
		value = value.toLowerCase();
	}
	switch(value){
		case true:
		case "true":
		case 1:
		case "1":
		case "on":
		case "yes":
			return true;
		default: 
			return false;
	}
}

const cell_format = { 
	wordBreak: 'break-all', 
	padding: '0 3px'
}

const left_table_header_styles = {
	width: '100%',
	textAlign: 'left',
	verticalAlign: 'bottom',
	paddingBottom: '5px',
	whiteSpace: 'pre-wrap'
}

const center_table_header_styles = {
	width: '100%',
	textAlign: 'center',
	verticalAlign: 'bottom',
	paddingBottom: '5px'
}

const table_options = {
	grouping: false,
	search: false,
	exportButton: false,
	toolbar: true,
	paging: false,
	draggable: false,
	headerStyle: {}, 
	rowStyle: { 
		padding: '0',
		fontSize: '12px', 
		wordBreak: 'break-all' },
	headerStyle: left_table_header_styles,
	actionsCellStyle: {
		padding: '0'}
};

const config_descriptions = {
	'ep_hec': 'HTTP Event Collector',
	'ep_aws_s3': 'AWS S3-Compatible Object Store',
	'ep_box': 'Box.com',
	'ep_sftp': 'SFTP',
	'ep_smb': 'SMB',
}

const LoadingOverlay = (props) => { 
	return (
		<div id="loading_overlay"
			style={{
				position: "fixed",
				top: 0,
				zIndex: 9999,
				width: "100%",
				height: "100%",
				display: "block",
				background: "rgba(0,0,0,0.6)"}}
		> 
			<div style={{
				height: "100%",
				display: "flex",
				justifyContent: "center",
				alignItems: "center"
			}}>
				<span className="spinner" ></span>
			</div>
		</div>
	)
}

class App extends React.Component {
	constructor(props) {
		super(props);

		this.state = {
			show_file_browser: false,		
			file_list: [],					// begin chonky
			folder_chain: [],				// 
			current_folder: '',				// 
			current_config_container: '',				// 
			current_config: '', 			// 
			current_config_alias: '',		// end chonky,
			loading: false,					// FadeIn control for chonky modal
			ep_general: {},
			// table lists
			ep_hec: [], 
			ep_aws: [],
			ep_box: [],
			ep_sftp: [],
			ep_smb: []
		}

		this.get_config_stanza("ep_general", "settings").then((d) => {
			console.log("Setting state from get_config_stanza");
			this.setState({"ep_general": d});
		})
		this.refresh_tables();
		
		//this.validate_field = this.validate_field.bind(this);
		this.refresh_tables = this.refresh_tables.bind(this);
		this.dict_to_querystring = this.dict_to_querystring.bind(this);
		this.rest_to_rows = this.rest_to_rows.bind(this);
		this.list_table_fields = this.list_table_fields.bind(this);
		this.unset_default_entry = this.unset_default_entry.bind(this);
		this.get_config_stanza = this.get_config_stanza.bind(this);
		this.get_config = this.get_config.bind(this);
		this.put_config_item = this.put_config_item.bind(this);
		this.add_row_data = this.add_row_data.bind(this);
		this.update_config_item = this.update_config_item.bind(this);
		this.update_row_data = this.update_row_data.bind(this);
		this.delete_config_item = this.delete_config_item.bind(this);
		this.delete_row_data = this.delete_row_data.bind(this);
		this.handleFileAction = this.handleFileAction.bind(this);
		this.show_folder_contents = this.show_folder_contents.bind(this);
		this.updateParentState = this.updateParentState.bind(this);

		// Tags
		//this.FileBrowserModal = this.FileBrowserModal.bind(this);
		this.EPTabContent = this.EPTabContent.bind(this);
	}

	columns = {
		ep_hec: [ 
			{ title: "Stanza", field: "stanza", hidden: true },
			// actions = 10%
			{ title: "Default", field: "default", type: "boolean", width: "5%", headerStyle: center_table_header_styles },
			{ title: "Name/Alias", field: "alias", width: "20%", 
				validate: rowData => validators.string(rowData.alias).isValid }, 
			{ title: "Hostname", field: "host", width: "25%", 
				validate: rowData => validators.string(rowData.host).isValid },
			{ title: "TCP Port", field: "port", width: "10%", 
				validate: rowData => (validators.number(rowData.port).isValid || rowData.port == null || rowData.port == "") },
			{ title: "HEC Token", field: "token", width: "20%", 
				validate: rowData => validators.uuid(rowData.token).isValid },
			{ title: "SSL", field: "ssl", type: "boolean", width: "5%", initialEditValue: 1, headerStyle: center_table_header_styles }
		],
		ep_aws_s3: [
			{ title: "Stanza", field: "stanza", hidden: true },
			// actions = 10%
			{ title: "Default", field: "default", type: "boolean", width: "5%", headerStyle: center_table_header_styles },
			{ title: "Name/Alias", field: "alias", width: "12%", 
				validate: rowData => validators.string(rowData.alias) }, 
			{ title: "Use ARN", field: "use_arn", type: "boolean", width: "5%", headerStyle: center_table_header_styles },
			{ title: "Access Key ID", field: "access_key_id", width: "12%", 
				validate: rowData => ((validators.bool(rowData.use_arn).isValid && rowData.use_arn) || validators.string(rowData.access_key_id).isValid)
			},
			{ title: "Secret Access Key", field: "secret_key", width: "12%", cellStyle: cell_format,
				render: rowData => <span className="password_field">{ ((rowData.secret_key === undefined || rowData.secret_key == '') ? '' : '*'.repeat(8))}</span>,
				editComponent: props => (
					<TextField
						type="password"
						value={props.value}
						error={ (props.value == null || !validators.string(props.value).isValid) && !(validators.bool(props.rowData.use_arn).isValid && props.rowData.use_arn) }
						inputProps={{ "placeholder": "Secret Access Key" }}
						onChange={e => {props.onChange(e.target.value)}}
					/>), 
					validate: rowData => (validators.string(rowData.secret_key).isValid ||  (validators.bool(rowData.use_arn).isValid && rowData.use_arn))
			},
			{ title: "Region", field: "region", width: "10%", 
				validate: rowData => validators.string(rowData.region).isValid }, 
			{ title: "Endpoint URL\n(Blank for AWS S3)", field: "endpoint_url", width: "12%" },
			{ title: "Default Bucket ID", field: "default_s3_bucket", width: "12%" },
			{ title: "Compress Output", field: "compress", type: "boolean", width: "5%", headerStyle: center_table_header_styles }
		],
		ep_box: [
			{ title: "Stanza", field: "stanza", hidden: true },
			// actions = 10%
			{ title: "Default", field: "default", type: "boolean", width: "5%", headerStyle: center_table_header_styles },
			{ title: "Name/Alias", field: "alias", width: "14%", 
				validate: rowData => validators.string(rowData.alias).isValid }, 
			{ title: "Enterprise ID", field: "enterprise_id", width: "10%", 
				validate: rowData => validators.string(rowData.enterprise_id).isValid },
			{ title: "Client ID", field: "client_id", width: "9%", 
				validate: rowData => validators.string(rowData.client_id).isValid },
			{ title: "Client Secret", field: "client_secret", width: "9%", 
				validate: rowData => validators.string(rowData.client_secret).isValid,
				render: rowData => <span className="password_field">{((rowData.client_secret === undefined || rowData.client_secret == '') ? '' : '*'.repeat(8))}</span>,
				editComponent: props => (
					<TextField
						error={ (props.value == null || !validators.string(props.value).isValid) }
						type="password"
						value={props.value}
						inputProps={{"placeholder": "Client Secret"}}
						onChange={e => {props.onChange(e.target.value)}}
					/>) },
			{ title: "Public Key ID", field: "public_key_id", width: "9%", 
				validate: rowData => validators.string(rowData.public_key_id) },
			{ title: "Private Key", field: "private_key", width: "36%", cellStyle: { wordBreak: 'keep-all'}, 
				validate: rowData => validators.string(rowData.private_key).isValid,
				render: rowData => <span className="password_field">{((rowData.private_key === undefined || rowData.private_key == '') ? '' : '[encrypted]')}</span>,
				editComponent: ({ value, onChange }) => (
					<TextField
						error={ (value == null || !validators.string(value).isValid) }
						onChange={e => {onChange(e.target.value)}}
						value={value}
						placeholder="Private Key"
						multiline
						rows={1}
						rowsMax={4}
						/>) },
			{ title: "Passphrase", field: "passphrase", width: "8%", 
				validate: rowData => validators.string(rowData.passphrase).isValid,
				render: rowData => <span className="password_field">{((rowData.passphrase === undefined || rowData.passphrase == '') ? '' : '*'.repeat(8))}</span>,
				editComponent: props => (
					<TextField
						error={ (props.value == null || !validators.string(props.value).isValid) }
						type="password"
						value={props.value}
						inputProps={{"placeholder": "Passphrase"}}
						onChange={e => {props.onChange(e.target.value)}}
					/>) },
			{ title: "Default Folder", field: "default_folder", width: "20%" }, 
			{ title: "Compress Output", field: "compress", type: "boolean", width: "5%", headerStyle: center_table_header_styles }
		],
		ep_sftp: [
			{ title: "Stanza", field: "stanza", hidden: true },
			// actions = 10%
			{ title: "Default", field: "default", type: "boolean", width: "5%", headerStyle: center_table_header_styles },
			{ title: "Name/Alias", field: "alias", width: "14%", 
				validate: rowData => validators.string(rowData.alias).isValid }, 
			{ title: "Hostname", field: "host", width: "35%", 
				validate: rowData => validators.string(rowData.host).isValid },
			{ title: "TCP Port", field: "port", width: "10%",
				validate: rowData => (validators.number(rowData.port).isValid || rowData.port == null || rowData.port == "") },
			{ title: "Username", field: "username", width: "15%", 
				validate: rowData => validators.string(rowData.username).isValid },
			{ title: "Password", field: "password", width: "15%", 
				validate: rowData => (validators.string(rowData.private_key).isValid || validators.string(rowData.password).isValid),
				render: rowData => <span className="password_field">{((rowData.password === undefined || rowData.password == '') ? '' : '*'.repeat(8))}</span>,
				editComponent: props => (
					<TextField
						error={ (props.value == null || !validators.string(props.value).isValid) && !(validators.string(props.rowData.private_key).isValid) }
						type="password"
						value={props.value}
						inputProps={{"placeholder": "Password"}}
						onChange={e => {props.onChange(e.target.value)}}
					/>) },
			{ title: "Private Key", field: "private_key", width: "36%", cellStyle: { wordBreak: 'keep-all'}, 
				validate: rowData => (validators.string(rowData.private_key).isValid || validators.string(rowData.password).isValid),
				render: rowData => <span className="password_field">{((rowData.private_key === undefined || rowData.private_key == '') ? '' : '[encrypted]')}</span>,
				editComponent: props => (
					<TextField
						error={ (props.value == null || !validators.string(props.value).isValid) && !(validators.string(props.rowData.password).isValid) }
						onChange={e => {props.onChange(e.target.value)}}
						value={props.value}
						placeholder="Private Key"
						multiline
						rows={1}
						rowsMax={4}
						/>) },
			{ title: "Passphrase", field: "passphrase", width: "8%", 
				render: rowData => <span className="password_field">{((rowData.passphrase === undefined || rowData.passphrase == '') ? '' : '*'.repeat(8))}</span>,
				editComponent: props => (
					<TextField
						type="password"
						value={props.value}
						inputProps={{"placeholder": "Passphrase"}}
						onChange={e => {props.onChange(e.target.value)}}
					/>) },
			{ title: "Default Folder", field: "default_folder", width: "20%" }, 
			{ title: "Compress Output", field: "compress", type: "boolean", width: "5%", headerStyle: center_table_header_styles }
		],
		ep_smb: [
			{ title: "Stanza", field: "stanza", hidden: true },
			// actions = 10%
			{ title: "Default", field: "default", type: "boolean", width: "5%", headerStyle: center_table_header_styles },
			{ title: "Name/Alias", field: "alias", width: "14%", 
				validate: rowData => validators.string(rowData.alias) }, 
			{ title: "Hostname", field: "host", width: "35%", 
				validate: rowData => validators.string(rowData.host) },
			{ title: "Domain", field: "domain", width: "15%", 
				validate: rowData => validators.string(rowData.domain) },
			{ title: "Username", field: "username", width: "15%", 
				validate: rowData => validators.string(rowData.username) },
			{ title: "Password", field: "password", width: "15%", 
				validate: rowData => validators.string(rowData.password).isValid,
				render: rowData => <span className="password_field">{((rowData.password === undefined || rowData.password == '') ? '' : '*'.repeat(8))}</span>,
				editComponent: props => (
					<TextField
						error={ (props.value == null || !validators.string(props.value).isValid) }
						type="password"
						value={props.value}
						inputProps={{"placeholder": "Password"}}
						onChange={e => {props.onChange(e.target.value)}}
					/>) },
			{ title: "Share Name", field: "share_name", width: "15%", 
				validate: rowData => validators.string(rowData.share_name).isValid },
			{ title: "Default Folder", field: "default_folder", width: "20%" }, 
			{ title: "Compress Output", field: "compress", type: "boolean", width: "5%", headerStyle: center_table_header_styles }
		]
	};
	
	// Download the data and push it into the corresponding state entry
	refresh_tables = () => {
		let tables = Object.keys(this.columns);
		//let state_updates = {};
		for (let table of tables) {
			this.get_config(table).then((d) => {
				// Convert the REST response data into a usable row format
				d = this.rest_to_rows(table, d);
				this.setState({[table]: d});
			})
		}
	}

	// Convert an object to an HTTP query string (for Splunk configuration POST requests)
	dict_to_querystring = (d) => {
		let query_list = [];
		let item_list = Object.entries(d);
		for ( var item of item_list ) {
			let name = item[0];
			let val = encodeURIComponent(item[1]);
			query_list.push(name + '=' + val);		
		};
		//console.log("Query list: " + query_list.toString());
		// Join list with & for query string
		return query_list.join('&');
	}

	// Convert REST API responses to a list of objects that translate to table rows
	rest_to_rows = (config_file, d) => {
		let rows = [];
		// Get the names of fields from the columns definition
		let valid_fields = this.list_table_fields(this.columns[config_file])
		//console.log(`Valid fields for ${config_file}: ${JSON.stringify(valid_fields)}`);
		for ( var rest_entry of d ) {
			let row = rest_entry.content;
			row.stanza = rest_entry.name;
			for (var key of Object.keys(row)) {
				// Sanitize the output from the API to only include our defined columns
				if (!valid_fields.includes(key)) {
					delete row[key];
				} else {
					// Find boolean fields and convert the values from strings
					for ( var field of this.columns[config_file] ){
						if ( field.field == key && field.type == "boolean" ) {
							row[key] = booleanize(row[key]);
						}
					}
				}
			}
			rows.push(row);
		}
		return rows;
	}

	list_table_fields = (l) => {
		// l = List of dicts passed
		let fields = [];
		
		for (var d of l) {
			fields.push(d.field);
		}
		return fields;
	}

	// If "Default" attribute is set, unset it for all other entries in the configuration
	unset_default_entry = (config_file, new_default_stanza) => {
		let config_entries = [...this.state[config_file]];
		for (let old_entry of config_entries) {
			if ( old_entry.stanza != new_default_stanza && old_entry.default ) {
				let new_entry = {...old_entry};
				delete new_entry.tableData;
				new_entry.default = false;
				this.update_row_data(config_file, new_entry, old_entry);
			}
		}
	}

	get_config_stanza = (config_file, stanza) => {
		return new Promise((resolve, reject) => {
			this.props.splunk.get(`event_push/${config_file}/${stanza}`).then((d) => {
				let clear = JSON.parse(d);
				//resolve(clear);
				resolve(clear["entry"][0]["content"]);
			})
		});
	}
	get_config = (config_file) => {
		return new Promise((resolve, reject) => {
			this.props.splunk.get(`event_push/${config_file}`)
				.then((d) => {
					let clear = JSON.parse(d);
					resolve(clear["entry"]);
					//resolve(clear["entry"][0]["content"]);
				});
		});
	}
	
	put_config_item = (config_file, items) => {
		
		return new Promise((resolve, reject) => {
			if ( 'stanza' in items ) {
				var rest_endpoint = `event_push/${config_file}/${items.stanza}`;
			} else {
				var rest_endpoint = `event_push/${config_file}`;
			};

			this.props.splunk.request(rest_endpoint,
				"POST",
				{"output_mode": "json"},
				null,
				this.dict_to_querystring(items),
				{"Content-Type": "application/x-www-form-urlencoded"},
				 null
				)
			.error(data => {
				this.props.enqueueSnackbar('Error creating record', notistack_options('error'));
				reject(data)
			})
			.done(data => {
				this.refresh_tables();
				this.props.enqueueSnackbar('Record created successfully', notistack_options('success'));
				resolve(JSON.parse(data))
			});
		});
	}
	// Set the state data when adding a configuration item using the table view
	add_row_data = (config_file, new_data) => {
		return new Promise((resolve, reject) => {
			setTimeout(async () => {
				new_data.stanza = uuid.v4();
				const dataNew = [...this.state[config_file]];
				// If "default" is set for this new record, unset it for any other records that might have it
				if ( (new_data.default === undefined) ? false : new_data.default ) {
					this.unset_default_entry(config_file, new_data.stanza);
				}
				await this.put_config_item(config_file, new_data);
				dataNew.push(new_data);
				console.log("Setting state from add_row_data");
				this.setState({[config_file]: dataNew});
				resolve();
			}, 1000);
		});
	}

	// Update the configuration file using the EAI REST endpoint
	update_config_item = (config_file, item) => {
		//console.log("Item = " + JSON.stringify(item));
		return new Promise((resolve, reject) => {
			this.props.splunk.request(`event_push/${config_file}/${item.stanza}`,
				"POST",
				{"output_mode": "json"},
				null,
				this.dict_to_querystring(item),
				{"Content-Type": "application/x-www-form-urlencoded"},
				null
			)
			.error(data => {
				this.props.enqueueSnackbar('Error updating record', notistack_options('error'));
				reject(data)
			})
			.done(data => {
				this.refresh_tables();
				this.props.enqueueSnackbar('Update successful', notistack_options('success'));
				resolve(JSON.parse(data))
			});
		});
	}
	// Update the UI and state
	update_row_data = (config_file, new_data, old_data) => {
		return new Promise((resolve, reject) => {
			setTimeout(async () => {
				const dataUpdate = [...this.state[config_file]];
				const index = old_data.tableData.id;
				dataUpdate[index] = new_data;
				// If "default" is set for this updated record, unset it for any other records that might have it
				if ( (new_data.default === undefined) ? false : new_data.default ) {
					this.unset_default_entry(config_file, new_data.stanza);
				}
				await this.update_config_item(config_file, new_data);
				console.log("Setting state from update_row_data");
				this.setState({[config_file]: dataUpdate});
				resolve();
			}, 1000)
		})
	}

	delete_config_item = (config_file, stanza) => {
		return new Promise((resolve, reject) => {
			this.props.splunk.request(`event_push/${config_file}/${stanza}`,
				"DELETE",
				{"output_mode": "json"},
				null,
				null,
				{"Content-Type": "application/x-www-form-urlencoded"}, 
				null
			)
			.error(data => {
				reject(data)
				this.props.enqueueSnackbar('Error deleting record', notistack_options('error'));
			})
			.done(data => {
				resolve(data)
				this.props.enqueueSnackbar('Record deleted successfully', notistack_options('success'));
			});
		});
	}
	delete_row_data = (config_file, oldData) => {
		return new Promise((resolve, reject) => {
			setTimeout(async () => {
				const dataDelete = [...this.state[config_file]];
				const index = oldData.tableData.id;
				dataDelete.splice(index, 1);
				await this.delete_config_item(config_file, oldData.stanza);
				console.log("Setting state from delete_row_data");
				this.setState({[config_file]: dataDelete});
				resolve();
			}, 1000)
		})
	}

	handleFileAction = (data) => {
		if (!data.payload.targetFile || !data.payload.targetFile.isDir) return;
		const newPrefix = `${data.payload.targetFile.id.replace(/\/*$/, '')}/`;
		this.show_folder_contents(this.state.current_config, this.state.current_config_alias, this.state.current_config_container, newPrefix)
	}

	// Set the state data when adding a configuration item using the table view
	show_folder_contents = (config_file, alias, container_name, folder) => {
		return new Promise((resolve, reject) => {
//			setTimeout(async () => {
				//console.log("Showing folder data for: " + config_file + "\n" + alias + "\n"  + container_name + "\n"  + folder);
				//console.log("Setting state from show_folder_contents (first)");
				let old_chain = [...this.state.folder_chain];
				let old_files = [...this.state.file_list];
				console.log("Old chain = " + JSON.stringify(old_chain));
				console.log("Old files = " + JSON.stringify(old_files));
				this.setState({loading: true, show_file_browser: true}, 
					() => { // then
						let url='event_push_dirlist';
						let params = {
							"config": config_file,
							"alias": alias
						};
						if (container_name === undefined || container_name === null || container_name.length == 0) {
							container_name = '/' 
						}
						// Start with the root - /
						let chain = [{
							id: '/',
							name: '/',
							isDir: true
						}];
						
						// If the query folder is blank, use the default container name in the chain
						// else, use what's in the folder setting only
						console.log('Container Name = ' + container_name)
						console.log('Folder = ' + folder)

						if (folder !== undefined && folder !== null && folder.length > 0) {
							params["folder"] = folder;
							let chain_path = '';
							if ( folder.match('^[0-9]+\/$')) {
								// Treat the folder like an ID
								chain = [];
								folder = folder.replace('/', '');
								console.log("Using folder argument as ID");
								// Is this ID already in the previously used chain? User opted to go backwards
								console.log("Old chain: " + JSON.stringify(old_chain));
								if ( old_chain.length > 0 ) {
									for ( let chain_entry of old_chain ) {
										chain.push(chain_entry);
										// Break if the just-added ID is the folder specified
										if ( chain_entry.id == folder ) {
											break;
										}
									}
									console.log("New chain 1: " + JSON.stringify(chain));
									if ( old_chain.length == chain.length ) {
										// We made it through our old chain without finding the selection
										// Must have been selected from the list shown
										// Get the object from the file list and append it to the folder chain
										for ( let old_file of old_files ) {
											console.log(folder + " / " + old_file.id);
											if (old_file.id == folder) {
												chain.push(old_file);
												break;
											}
										}
										console.log("New chain 2: " + JSON.stringify(chain));
									}
								}
							} else {
								console.log("Using folder argument as path");
								// Treat the folder argument like a path
								for (let f of folder.replace(/^\/+|\/+$/, "").split('/')) {
									if ( f.length > 0 ) {
										chain_path = chain_path + '/' + f;
										chain.push({
											id: chain_path,
											name: f,
											isDir: true
										})
										console.log("f = " + f);
									}
								}
							}
						} else if ( (folder === undefined || folder === null || folder.length == 0) && container_name != '/' ) {
							// Append the root file (folder) object - container_name = share, bucket, /, etc.
							chain.push({
								id: container_name, // '/',
								name: container_name,
								isDir: true
							});
						}
						//console.log("Setting chain to: " + JSON.stringify(chain));

						this.props.splunk.get(url, params)
						.then((d) => {
							let file_list = JSON.parse(d);
							if (file_list !== null) {
								//console.log("File list = " + JSON.stringify(file_list));
								for (var f=0; f<file_list.length; f++) {
									if ( file_list[f].modDate !== undefined ) {
										file_list[f].modDate = moment.unix(file_list[f].modDate).format('YYYY-MM-DD hh:mm:ss ZZ');
									}
								}
								this.setState({"file_list": file_list}, () => {
									//console.log("Setting state from show_folder_contents (last)");
									this.setState({loading: false,
										folder_chain: chain,
										current_config: config_file,
										current_config_alias: alias,
										current_config_container: container_name});
								});
							}
							resolve(file_list);
						}, reason => {
							alert(`Error retrieving the file listing: ${reason.statusText} (${reason.status})`);
							this.setState({loading: false});
							reject(reason);
						}) ;
					}
				);
				resolve();
//			}, 1000);
		});
	}

	componentDidMount = () => {
		// Future use
	};

	updateParentState = (prop) => {
		this.setState(Object.assign(this.state, prop));
	};


	EPTabContent = (props) => {
		const title = props.title || "";
		const heading = props.heading || "";
		const action_columns = props.action_columns || "2";
		const browsable = booleanize(props.browsable || "false");
		const config = props.config;

		return(
			<div className="form form-horizontal form-complex">
				<h1>{title}</h1>
				{(props.children != null && props.children.length > 0) && (
					<div style={{width: '700px', paddingBottom: '15px'}}>
						<p>{props.children}</p>
					</div>
				)}

				<div className="panel-element-row">
					<MaterialTable
						components={{
							Container: props => (
								<div className={"actionicons-" + action_columns}>
									<div {...props} />
								</div>
							)
						}}
						title={
							<div className="form form-complex">
								<h2>{heading}</h2>
							</div>
						}
						icons={tableIcons}
						columns={this.columns[config]}
						data={this.state[config]}
						editable={{
							onRowAdd: newData => this.add_row_data(config, newData),
							onRowUpdate: (newData, oldData) => this.update_row_data(config, newData, oldData),
							onRowDelete: oldData => this.delete_row_data(config, oldData)
						}}
						actions={ (browsable && [{
							  icon: tableIcons.Open,
							  tooltip: 'Browse',
							  onClick: (event,rowData) => { this.show_folder_contents(config, rowData.alias, rowData.share_name || rowData.default_s3_bucket, rowData.default_folder) }
						}])}
						options={table_options}
						className={"actionicons-" + action_columns}
					/>
				</div>
			</div>
		)
	}

	render() {
		let self = this;
		console.log("Rendering");
		return (
			<div>
				<Suspense fallback={<div>Loading...</div>}>
					{this.state.loading && (
						<FadeIn transitionDuration="125">
							<LoadingOverlay />
						</FadeIn>
					)}
				</Suspense>
				<Tabs id="tabs_list" className="nav nav-tabs" 
					defaultIndex={0} transition={false} >
					<TabList className="nav nav-tabs">
						<Tab className="nav-item"><a href="#" className="toggle-tab">General</a></Tab>
						<Tab className="nav-item"><a href="#" className="toggle-tab">Splunk HEC</a></Tab>
						<Tab className="nav-item"><a href="#" className="toggle-tab">AWS S3-Compatible</a></Tab>
						<Tab className="nav-item"><a href="#" className="toggle-tab">Box</a></Tab>
						<Tab className="nav-item"><a href="#" className="toggle-tab">SFTP</a></Tab>
						<Tab className="nav-item"><a href="#" className="toggle-tab">SMB</a></Tab>
					</TabList>
					<TabPanel className="tab-pane">
						<div className="form form-horizontal form-complex">
							<h1>General Settings</h1>
							<FormControl id="general_form">
								<InputLabel id="logging_label">Logging Level</InputLabel>
								<Select labelId="logging_label" 
									id="log_level" 
									style={{ width: "150px" }}
									value={(this.state.ep_general.log_level === undefined) ? "" : this.state.ep_general.log_level}
									onChange={(event) => {
										this.update_config_item( 
											"ep_general", 
											{
												stanza: 'settings',
												log_level: event.target.value
											}
										)
										console.log("Setting state from General Settings tab");
										this.setState({"ep_general": {log_level: event.target.value}});
									}}>
									<MenuItem value="DEBUG">Debug</MenuItem>
									<MenuItem value="INFO">Info</MenuItem>
									<MenuItem value="WARNING">Warning</MenuItem>
									<MenuItem value="ERROR">Error</MenuItem>
									<MenuItem value="CRITICAL">Critical</MenuItem>
								</Select>
							</FormControl>
						</div>
					</TabPanel>
					<TabPanel className="tab-pane">
						<this.EPTabContent 
							title="Event Push to Splunk HTTP Event Collector (ephec)" 
							heading="Splunk HTTP Event Collector Connections" 
							action_columns="2" 
							config="ep_hec" />
					</TabPanel>
					<TabPanel className="tab-pane">
						<this.EPTabContent 
							title="Event Push to AWS S3 (epawss3)" 
							heading="AWS S3-Compatible Connections" 
							action_columns="3"
							browsable="true"
							config="ep_aws_s3" />
					</TabPanel>
					<TabPanel className="tab-pane">
						<this.EPTabContent 
							title="Event Push to Box (epbox)" 
							heading="Box Connections" 
							action_columns="3"
							browsable="true"
							config="ep_box">
								In your <a href="https://app.box.com/developers/console/newapp">Box Admin Console</a>, create a new Custom App with Server Authentication (with JWT) and create a new key pair to get this information. Then, submit the new app for authorization.
						</this.EPTabContent>
					</TabPanel>
					<TabPanel className="tab-pane">
						<this.EPTabContent 
							title="Event Push to SFTP (epsftp)" 
							heading="SFTP Connections" 
							action_columns="3"
							browsable="true"
							config="ep_sftp" />
					</TabPanel>
					<TabPanel className="tab-pane">
						<this.EPTabContent 
							title="Event Push to SMB (epsmb)" 
							heading="SMB Connections" 
							action_columns="3"
							browsable="true"
							config="ep_smb" />
					</TabPanel>
				</Tabs>
				<Suspense fallback={<div>Loading...</div>}>
					{this.state.show_file_browser && (
						<FileBrowserModal 
							id="file_browser" 
							instanceId="ep" 
							show={this.state.show_file_browser}
							onHide={ () => {
								console.log("Setting state from FileBrowserModal");
								this.setState({
									show_file_browser: false,
									file_list: [],
									folder_chain: []
								})}
							}
							location={`${config_descriptions[this.state.current_config]} / ${this.state.current_config_alias}`} 
							file_list={this.state.file_list}
							folder_chain={this.state.folder_chain}
							onFileAction={this.handleFileAction} />
					)}
				</Suspense>
			</div>
		);
	}
}


export default withSnackbar(App);
//export default App;