# ![App icon](static/appIcon.png) Event Push - Splunk Add-On by [Deductiv](https://www.deductiv.net/)  

This app exports your Splunk search results to remote destinations, so you can do more with your Splunk data. It provides search commands and alert actions to export/push/upload/share your data to multiple destinations of each type. The app must be configured via the Setup dashboard before using it. The setup dashboard includes a connection test feature in the form of a "**Browse**" action for all file-based destinations.

## Supported Export Formats
- JSON
- Raw Text
- KV Pairs
- Comma-Delimited (CSV)
- Tab-Delimited (TSV)
- Pipe-Delimited

## File-Based Destinations  
- Amazon Web Services (AWS) S3-Compatible Object Storage  
- Box.com Cloud Storage  
- SMB File Shares  
- SFTP Servers  

## Streaming Destinations  
- Splunk HTTP Event Collector  

___
## AWS S3-Compatible Object Storage (epawss3)

Export Splunk search results to AWS S3-compatible object storage. Connections can be configured to authenticate using OAuth credentials or the assumed role of the search head EC2 instance.  

### Capabilities  
- configure_ep_aws_s3_read  
- configure_ep_aws_s3_write  

### Search Command Syntax  
```
<search> | epawss3  
        target=<target name/alias>  
        bucket=<bucket>  
        outputfile=<output path/filename>  
        outputformat=[json|raw|kv|csv|tsv|pipe]  
        fields="<comma-delimited fields list>"  
        compress=[true|false]  
```
### Arguments  
- #### Target  
    **Syntax:** target=&lt;target name/alias&gt;  
    **Description:** The name/alias of the destination connection  
    **Default:** The target specified as the default within the setup dashboard  
- #### Bucket  
    **Syntax:** bucket=&lt;bucket name&gt;  
    **Description:** The name of the destination S3 bucket  
    **Default:** Specified within the target configuration  
- #### Output File
    **Syntax:** outputfile=&lt;[folder/]file name&gt;  
    **Description:** The name of the file to be written to the destination. If compression=true, a .gz extension will be appended. If compression is not specified and the filename ends in .gz, compression will automatically be applied.  
    **Default:** `app_username_epoch.ext` (e.g. `search_admin_1588000000.log`).  json=.json, csv=.csv, tsv=.tsv, pipe=.log, kv=.log, raw=.log  
    **Keywords:** `__now__`=epoch, `__today__`=date in yyyy-mm-dd format, `__nowft__`=timestamp in yyyy-mm-dd_hhmmss format.  
- #### Output Format
    **Syntax:** outputformat=[json|raw|kv|csv|tsv|pipe]  
    **Description:** The format for the exported search results  
    **Default:** *csv*  
- #### Fields
    **Syntax:** fields="field1, field2, field3"  
    **Description:** Limit the fields to be written to the exported file. Wildcards are supported.  
    **Default:** All (*)  
- #### Compression
    **Syntax:** compress=[true|false]  
    **Description:** Create the file as a .gz compressed archive  
    **Default:** Specified within the target configuration  

___
## Box Event Push (epbox)  

Export Splunk search results to Box cloud storage. Box must be configured with a Custom App using Server Authentication (with JWT) and a certificate generated. Then, the app must be submitted for approval by the administrator. The administrator should create a folder within the app's account and share it with the appropriate users.  

### Capabilities  
- configure_ep_box_read  
- configure_ep_box_write  

### Search Command Syntax  
```
<search> | epbox  
        target=<target name/alias>  
        outputfile=<output path/filename>  
        outputformat=[json|raw|kv|csv|tsv|pipe]  
        fields="<comma-delimited fields list>"  
        compress=[true|false]  
```

### Arguments  
- #### Target  
    **Syntax:** target=&lt;target name/alias&gt;  
    **Description:** The name/alias of the destination connection  
    **Default:** The target specified as the default within the setup dashboard  
- #### Output File
    **Syntax:** outputfile=&lt;[folder/]file name&gt;  
    **Description:** The name of the file to be written to the destination. If compression=true, a .gz extension will be appended. If compression is not specified and the filename ends in .gz, compression will automatically be applied.  
    **Default:** `app_username_epoch.ext` (e.g. `search_admin_1588000000.log`).  json=.json, csv=.csv, tsv=.tsv, pipe=.log, kv=.log, raw=.log  
    **Keywords:** `__now__`=epoch, `__today__`=date in yyyy-mm-dd format, `__nowft__`=timestamp in yyyy-mm-dd_hhmmss format.  
- #### Output Format
    **Syntax:** outputformat=[json|raw|kv|csv|tsv|pipe]  
    **Description:** The format for the exported search results  
    **Default:** *csv*  
- #### Fields
    **Syntax:** fields="field1, field2, field3"  
    **Description:** Limit the fields to be written to the exported file. Wildcards are supported.  
    **Default:** All (*)  
- #### Compression
    **Syntax:** compress=[true|false]  
    **Description:** Create the file as a .gz compressed archive  
    **Default:** Specified within the target configuration  

___
## SMB Event Push Search Command (epsmb)  

Export Splunk search results to SMB file shares.  

### Capabilities  
- configure_ep_smb_read  
- configure_ep_smb_write  

### Search Command Syntax  
```
<search> | epsmb  
        target=<target name/alias>  
        outputfile=<output path/filename>  
        outputformat=[json|raw|kv|csv|tsv|pipe]  
        fields="<comma-delimited fields list>"  
        compress=[true|false]  
```

### Arguments  
- #### Target  
    **Syntax:** target=&lt;target name/alias&gt;  
    **Description:** The name/alias of the destination connection  
    **Default:** The target specified as the default within the setup dashboard  
- #### Output File
    **Syntax:** outputfile=&lt;[folder/]file name&gt;  
    **Description:** The name of the file to be written to the destination. If compression=true, a .gz extension will be appended. If compression is not specified and the filename ends in .gz, compression will automatically be applied.  
    **Default:** `app_username_epoch.ext` (e.g. `search_admin_1588000000.log`).  json=.json, csv=.csv, tsv=.tsv, pipe=.log, kv=.log, raw=.log  
    **Keywords:** `__now__`=epoch, `__today__`=date in yyyy-mm-dd format, `__nowft__`=timestamp in yyyy-mm-dd_hhmmss format.  
- #### Output Format
    **Syntax:** outputformat=[json|raw|kv|csv|tsv|pipe]  
    **Description:** The format for the exported search results  
    **Default:** *csv*  
- #### Fields
    **Syntax:** fields="field1, field2, field3"  
    **Description:** Limit the fields to be written to the exported file. Wildcards are supported.  
    **Default:** All (*)  
- #### Compression
    **Syntax:** compress=[true|false]  
    **Description:** Create the file as a .gz compressed archive  
    **Default:** Specified within the target configuration  

___
## SFTP Event Push Search Command (epsftp)  

Export Splunk search results to SFTP servers.  

### Capabilities  
- configure_ep_sftp_read  
- configure_ep_sftp_write  

### Search Command Syntax  
```
<search> | epsftp  
        target=<target name/alias>  
        outputfile=<output path/filename>  
        outputformat=[json|raw|kv|csv|tsv|pipe]  
        fields="<comma-delimited fields list>"  
        compress=[true|false]  
```

### Arguments  
- #### Target  
    **Syntax:** target=&lt;target name/alias&gt;  
    **Description:** The name/alias of the destination connection  
    **Default:** The target specified as the default within the setup dashboard  
- #### Output File
    **Syntax:** outputfile=&lt;[folder/]file name&gt;  
    **Description:** The name of the file to be written to the destination. If compression=true, a .gz extension will be appended. If compression is not specified and the filename ends in .gz, compression will automatically be applied.  
    **Default:** `app_username_epoch.ext` (e.g. `search_admin_1588000000.log`).  json=.json, csv=.csv, tsv=.tsv, pipe=.log, kv=.log, raw=.log  
    **Keywords:** `__now__`=epoch, `__today__`=date in yyyy-mm-dd format, `__nowft__`=timestamp in yyyy-mm-dd_hhmmss format.  
- #### Output Format
    **Syntax:** outputformat=[json|raw|kv|csv|tsv|pipe]  
    **Description:** The format for the exported search results  
    **Default:** *csv*  
- #### Fields
    **Syntax:** fields="field1, field2, field3"  
    **Description:** Limit the fields to be written to the exported file. Wildcards are supported.  
    **Default:** All (*)  
- #### Compression
    **Syntax:** compress=[true|false]  
    **Description:** Create the file as a .gz compressed archive  
    **Default:** Specified within the target configuration  

___
## Splunk HEC Event Push (ephec)

Push Splunk search results to a Splunk HTTP Event Collector (HEC) listener.

### Capabilities  
- configure_ep_hec_read  
- configure_ep_hec_write  

### Search Command Syntax  
```
<search> | ephec  
        target=<target name/alias>  
        host=[host_value|$host_field$]  
        source=[source_value|$source_field$]  
        sourcetype=[sourcetype_value|$sourcetype_field$]  
        index=[index_value|$index_field$]  
```

#### Arguments  
- #### Host  
    **Syntax:** host=[host_value|$host_field$]  
    **Description:** Field or string to be assigned to the host field on the pushed event  
    **Default:** $host$, or if not defined, the hostname of the sending host (from inputs.conf)  
- #### Source  
    **Syntax:** source=[source_value|$source_field$]  
    **Description:** Field or string to be assigned to the source field on the pushed event  
    **Default:** $source$, or if not defined, it is omitted  
- #### Sourcetype  
    **Syntax:** sourcetype=[sourcetype_value|$sourcetype_field$]  
    **Description:** Field or string to be assigned to the sourcetype field on the pushed event  
    **Default:** $sourcetype$, or if not defined, json  
- #### Index  
    **Syntax:** index=[index_value|$index_field$]  
    **Description:** The remote index in which to store the pushed event  
    **Default:** $index$, or if not defined, the remote endpoint's default.  

___
## Support  
  
Having trouble with the app? Feel free to [email us](mailto:contact@deductiv.net) and we’ll help you sort it out. You can also [reach the author](https://splunk-usergroups.slack.com/team/U30E9LS79) on the Splunk Community Slack.  

## Roadmap  

We welcome your input on our app feature roadmap, which can be found on [Trello](https://trello.com/b/YbFOsuKJ/event-push-add-on-for-splunk-by-deductiv).  
