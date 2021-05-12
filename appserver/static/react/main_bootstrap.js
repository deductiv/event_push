require.config({"paths":{"main":"/static/app/event_push/react/main.js?v=4487e4620e915d525400","react":"/static/app/event_push/react/react.js?v=66d5549ca9cc11f6a70d","react-dom":"/static/app/event_push/react/react-dom.js?v=5bbcc7c7f5ecf54ff8cb"},"shim":{"main":{"exports":["main"]},"react":{"exports":"react"},"react-dom":{"exports":"react-dom"}}});
                require([
                        "splunkjs/ready!",
                        "splunkjs/mvc/simplexml/ready!",
                        "splunkjs/mvc/utils",
                        "main", "react", "react-dom", "backbone", "jquery"
                    ], function (mvc,
                                 ignored,
                                 splunkjsUtils,
                                 main, react, reactdom, backbone, $
                    ) {
                    
                    let myObjects = $(".eventpush_setup").each((k, v)=>{
                        reactdom.render(
                        react.createElement(main.default, {
                            splunk: mvc,
                            utils: splunkjsUtils,
                            splunk_components: { backbone: backbone,  $: $, } ,
                            data: {...$(v).data()}
                            }),
                         v
                        );
                    });
                    });
                