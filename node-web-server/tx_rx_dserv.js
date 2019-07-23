/*
 * basic TCP interaction with dserv_tcp using node
 */

/* Or use this example tcp client written in node.js.  (Originated with
example code from
http://www.hacksparrow.com/tcp-socket-programming-in-node-js.html.) */
'use strict';
var path = require('path');
var net = require('net');

var client = new net.Socket();
var varname = process.argv[2];
var host = '127.0.0.1';
var port = 4620;

//client.connect(port, host, function() {
//});

client.on('data', function(data) {
    var result = Buffer.from(data);
    console.log(result.toString('utf8',0,Buffer.byteLength(result)-1));
});



function getFunc() {
    client.write('%get boom');
}

function setFunc() {
    var thisInt = Math.floor(Math.random() * 100);
    client.write('%set boom=' + thisInt.toString());
}

setInterval(setFunc, 1500);
setInterval(getFunc, 1500);