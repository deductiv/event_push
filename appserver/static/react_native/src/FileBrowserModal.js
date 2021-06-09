// File browser UI

/*

Props list:

show
onHide
location
instanceId
file_list
folder_chain
onFileAction

*/

import React from 'react';
import Modal from 'react-bootstrap/Modal';
import { setChonkyDefaults, FileBrowser, FileNavbar, FileToolbar, FileList, ChonkyActions } from 'chonky';
import { ChonkyIconFA } from 'chonky-icon-fontawesome';
setChonkyDefaults({ iconComponent: ChonkyIconFA });
ChonkyActions.ToggleHiddenFiles.option.defaultValue = false;

export default function FileBrowserModal(props) {
    return (
        <Modal
            //size="lg"
            id="ep_file_browser_modal"
            show={props.show}
            onHide={props.onHide}
            dialogClassName={"primaryModal"}
            aria-labelledby="file_browser"
            centered={true}
            className="modal-wide in"
            style={{height: '60%', resize: 'vertical'}}
        >
            <Modal.Header closeButton>
                <Modal.Title id="file_browser">
                Browse Location: {props.location}
                </Modal.Title>
            </Modal.Header>
            <Modal.Body
                style={{height: '100%'}}>
                <FileBrowser
                    instanceId={props.instanceId}
                    files={props.file_list}
                    folderChain={props.folder_chain}
                    fillParentContainer={true}
                    onFileAction={props.onFileAction}
                    defaultFileViewActionId={ChonkyActions.EnableListView.id}
                    disableDragAndDrop={true}
                    disableDragAndDropProvider={true}
                    disableSelection={true}
                    disableDefaultFileActions={[
                        ChonkyActions.OpenSelection.id,
                        ChonkyActions.SelectAllFiles.id,
                        ChonkyActions.ClearSelection.id,
                        ChonkyActions.EnableCompactView.id,
                        ChonkyActions.EnableGridView.id
                    ]}
                >
                    <FileNavbar />
                    <FileToolbar />
                    <FileList />
                </FileBrowser>
            </Modal.Body>
        </Modal>
    );
}

//export default FileBrowserModal;

//function FileBrowserModal(props) {
//const FileBrowserModal = props => {
// Original code
/*
    FileBrowserModal = (props) => {		
        const Modal = React.lazy(() => import(Modal from 'react-bootstrap/Modal');

        import moment from 'moment';
        import 'moment-timezone';
        import Modal from 'react-bootstrap/Modal';
        import FadeIn from 'react-fade-in';
        
        // File browser UI
        import { setChonkyDefaults, FileBrowser, FileNavbar, FileToolbar, FileList, ChonkyActions } from 'chonky';
        import { ChonkyIconFA } from 'chonky-icon-fontawesome';
        setChonkyDefaults({ iconComponent: ChonkyIconFA });
        ChonkyActions.ToggleHiddenFiles.option.defaultValue = false;

        return (
            <Modal
                //size="lg"
                id="ep_file_browser_modal"
                show={this.state.show_file_browser}
                onHide={ () => {
                    console.log("Setting state from FileBrowserModal");
                    this.setState({
                        show_file_browser: false,
                        file_list: [],
                        folder_chain: []
                    })}
                }
                dialogClassName={"primaryModal"}
                aria-labelledby="ep_file_browser"
                centered={true}
                className="modal-wide in"
                style={{height: '60%', resize: 'vertical'}}
            >
                <Modal.Header closeButton>
                    <Modal.Title id="ep_file_browser">
                    Browse Location: {config_descriptions[this.state.current_config]} / {this.state.current_config_alias} 
                    </Modal.Title>
                </Modal.Header>
                <Modal.Body
                    style={{height: '100%'}}>
                    <FileBrowser
                        instanceId={props.instanceId}
                        files={this.state.file_list}
                        folderChain={this.state.folder_chain}
                        fillParentContainer={true}
                        onFileAction={this.handleFileAction}
                        defaultFileViewActionId={ChonkyActions.EnableListView.id}
                        disableDragAndDrop={true}
                        disableDragAndDropProvider={true}
                        disableSelection={true}
                        disableDefaultFileActions={[
                            ChonkyActions.OpenSelection.id,
                            ChonkyActions.SelectAllFiles.id,
                            ChonkyActions.ClearSelection.id,
                            ChonkyActions.EnableCompactView.id,
                            ChonkyActions.EnableGridView.id
                        ]}
                    >
                        <FileNavbar />
                        <FileToolbar />
                        <FileList />
                    </FileBrowser>
                </Modal.Body>
            </Modal>
        );
    }
        */