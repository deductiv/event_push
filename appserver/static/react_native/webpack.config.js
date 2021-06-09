const path = require('path');
let requirejsPlugin = require('requirejs-webpack-plugin'),
    webpack = require('webpack'),
    LicensePlugin = require('webpack-license-plugin');
const {CleanWebpackPlugin} = require('clean-webpack-plugin');

const csvTransform = (packages) => {
  const keys = ['name', 'version', 'license']

  return [
    keys.join(','),
    ...packages.map(pckg => keys.map(key => `"${pckg[key]}"`).join(',')),
  ].join('\n')
}

new webpack.DefinePlugin({
  'process.env.REACT_APP_SC_ATTR': JSON.stringify('data-styled-event_push'),
  'process.env.SC_ATTR': JSON.stringify('data-styled-event_push')
})

const po = (assets, entry_file, entry_file_object, entry_object) => {
    let exp = {};
    exp[entry_file] = {exports: [`${entry_file}`]};
    let common_paths = ["react", "react-dom", `${entry_file_object}`];
    let ourPaths = {};
    Object.keys(assets.paths).forEach((item, index) => {
        if (common_paths.includes(item)) {
            ourPaths[item] = assets.paths[item];
        }
    });
    delete assets["baseUrl"];
    assets["shim"] = {};
    assets["paths"] = ourPaths;
    let require_named_modules = [],
        require_named_objects = [],
        require_splunk_components = {
            'backbone': 'backbone',
            "jquery": "$"
        },
        require_splunk_components_objects = "{"
    ;
    Object.keys(assets["paths"]).forEach((key) => {
        assets["shim"][key] = exp[key] || {exports: key};
        require_named_modules.push(`${key}`);
        require_named_objects.push(`${key.replace(/[^a-zA-Z]/g, "")}`);
    });
    Object.keys(require_splunk_components).forEach((key) => {
        require_named_modules.push(`${key}`);
        require_named_objects.push(`${require_splunk_components[key]}`);
        require_splunk_components_objects += ` ${require_splunk_components[key]}: ${require_splunk_components[key]}, `;
    });
    require_splunk_components_objects += "}";
    //assets["deps"] = ["runtime", "bootstrap-config"];
    return `require.config(${JSON.stringify(assets)});
        require([
                "splunkjs/ready!",
                "splunkjs/mvc/simplexml/ready!",
                "splunkjs/mvc/utils",
                "${require_named_modules.join('", "')}"
            ], function (mvc,
                            ignored,
                            splunkjsUtils,
                            ${require_named_objects.join(", ").replace(/"/g, "")}
            ) {
            
            let myObjects = $(".${entry_object}").each((k, v)=>{
                reactdom.render(
                react.createElement(${entry_file_object.replace(/[^a-zA-Z]/g, "")}.default, {
                    splunk: mvc,
                    utils: splunkjsUtils,
                    splunk_components: ${require_splunk_components_objects} ,
                    data: {...$(v).data()}
                    }),
                    v
                );
            });
            });
        `;
};

let config_mode = process.env.NODE_ENV || false ? process.env.NODE_ENV : 'development',
    app_name = process.env.APP_NAME || "search",
    mode = process.env.NODE_ENV === "production" ? "production" : 'development';
let path2 = __dirname + `/.env.${config_mode}`;
let dotenv = require('dotenv').config({path: path2});
module.exports = {
    watch: true,
    entry: {
        "main": './src/index.js',
        "react": "./node_modules/react/umd/react.production.min.js",
        "react-dom": "./node_modules/react-dom/umd/react-dom.production.min.js",
        "snackbar_utils": "./src/SnackbarUtils.js"
    },
    externals: [
        "react",
        "react-dom"
    ],
    output: {
        globalObject: 'this',
        filename: '[name].js', // change this to '[name].[contenthash:8].js' if using the asset manifest for better caching
        path: path.join(__dirname, '../react'),
        publicPath: `/static/app/${app_name}/react/`,
        library: 'main',
        libraryTarget: 'umd',
    },
    devtool: 'inline-source-map',
    mode: mode,
    optimization: {
        moduleIds: "named",
        minimize: true,
        chunkIds: 'named' /*,
        runtimeChunk: 'single',
        splitChunks: {
            chunks: 'all',
        }*/
    },
    module: {
        rules: [
            {
                test: /\.(js|mjs|jsx|ts|tsx)$/,
                exclude: /node_modules/,
                use: [
                    {
                        loader: 'babel-loader',
                        options: {
                            plugins: [
                                ["@babel/plugin-proposal-object-rest-spread", {"loose": true, "useBuiltIns": true}],
                                '@babel/plugin-transform-spread',
                                '@babel/plugin-proposal-class-properties',
                                '@babel/plugin-transform-runtime',
                                '@babel/plugin-transform-modules-amd',
                                "@babel/plugin-syntax-dynamic-import"

                            ],
                            presets: ['@babel/preset-env', '@babel/preset-react']
                        }
                    }
                ],
            },
            {test: /\.scss?$/, exclude: /node_modules/, use: ['style-loader', 'css-loader', 'sass-loader']},
            {test: /\.css?$/, use: ['style-loader', 'css-loader']},
        ],
    },
    plugins: [
        new webpack.DefinePlugin({
            "process.env": dotenv.parsed
        }),
        new CleanWebpackPlugin(),
        new requirejsPlugin({
            path: path.join(__dirname, '../react'),
            filename: 'main_bootstrap.js',
            pathUrl: `/static/app/${app_name}/react/`,
            processOutput: (assets) => {
                return po(assets, "main", "main", "eventpush_setup")
            }
        })
    ]
};
