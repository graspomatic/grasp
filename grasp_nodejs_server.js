var redis = require("redis"),
    client_6379 = redis.createClient();
    client_6380 = redis.createClient(port=6380)

// if you'd like to select database 3, instead of 0 (default), call
// client.select(3, function() { /* ... */ });

client_6379.on("error", function (err) {
    console.log("Error " + err);
});

client_6380.on("error", function (err) {
    console.log("Error " + err);
});

const {promisify} = require('util');
const getAsync_6379 = promisify(client_6379.get).bind(client);
const setAsync_6379 = promisify(client_6379.set).bind(client);
const getAsync_6380 = promisify(client_6380.get).bind(client);
const setAsync_6380 = promisify(client_6380.set).bind(client);

// We expect a value 'foo': 'bar' to be present
// So instead of writing client.get('foo', cb); you have to write:



//key = 'foo';
//
//
//getAsync(key).then(function(res) {
//    console.log(res); // => 'bar'
//});
//
//setAsync(key,'barz').then(function(res) {
//    console.log(res); // => 'bar'
//});
//
//getAsync(key).then(function(res) {
//    console.log(res); // => 'bar'
//});

const http = require('http');
var path = require('path');
var fs = require('fs');

var os = require('os');
var ifaces = os.networkInterfaces();
hostname = ifaces['eth0'][0]['address'];
const port = 8080;

//const server = http.createServer((req, res) => {
//  res.statusCode = 200;
//  res.setHeader('Content-Type', 'text/plain');
//  res.end('Hello World\n');
//});


var dir = path.join(__dirname, 'public');

var mime = {
    html: 'text/html',
    txt: 'text/plain',
    css: 'text/css',
    gif: 'image/gif',
    jpg: 'image/jpeg',
    png: 'image/png',
    svg: 'image/svg+xml',
    js: 'application/javascript'
};

var server = http.createServer(function (req, res) {
    var reqpath = req.url.toString().split('?')[0];
    if (req.method !== 'GET') {
        res.statusCode = 501;
        res.setHeader('Content-Type', 'text/plain');
        return res.end('Method not implemented');
    }
    var file = path.join(dir, reqpath.replace(/\/$/, '/index.html'));
    if (file.indexOf(dir + path.sep) !== 0) {
        res.statusCode = 403;
        res.setHeader('Content-Type', 'text/plain');
        return res.end('Forbidden');
    }
    var type = mime[path.extname(file).slice(1)] || 'text/plain';
    var s = fs.createReadStream(file);
    s.on('open', function () {
        res.setHeader('Content-Type', type);
        s.pipe(res);
    });
    s.on('error', function () {
        getAsync_6379('foo').then(function(result) {
            console.log(result); // => 'bar'
            res.setHeader('Content-Type', 'text/plain');
            res.statusCode = 404;
            res.end(result);
        });


    });
});

server.listen(port, hostname, () => {
  console.log(`Server running at http://${hostname}:${port}/`);
});