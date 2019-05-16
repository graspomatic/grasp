// Set up redis connections

var redis = require("redis"),
    client_6379 = redis.createClient();
    client_6380 = redis.createClient(6380)

client_6379.on("error", function (err) {
    console.log("Error " + err);
});

client_6380.on("error", function (err) {
    console.log("Error " + err);
});

const {promisify} = require('util');
const getAsync_6379 = promisify(client_6379.get).bind(client_6379);
const setAsync_6379 = promisify(client_6379.set).bind(client_6379);
const getAsync_6380 = promisify(client_6380.get).bind(client_6380);
const setAsync_6380 = promisify(client_6380.set).bind(client_6380);



// Set up nodejs

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
        getAsync_6380('panel').then(function(result) {
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