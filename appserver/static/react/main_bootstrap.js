require.config({"paths":{"main":"/static/app/event_push/react/main.js?v=d365b4f68034b8757049","react":"/static/app/event_push/react/react.js?v=154a92c29ec52a4692dc","react-dom":"/static/app/event_push/react/react-dom.js?v=25fe35808c42c2c5a78c"},"shim":{"main":{"exports":["main"]},"react":{"exports":"react"},"react-dom":{"exports":"react-dom"}}});
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
        