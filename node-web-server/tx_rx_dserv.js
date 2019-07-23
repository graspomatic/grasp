/*
 * basic TCP interaction with dserv_tcp using node
 */

/* Or use this example tcp client written in node.js.  (Originated with
example code from
http://www.hacksparrow.com/tcp-socket-programming-in-node-js.html.) */
'use strict';
var path = require('path');
var net = require('net');

if (process.argv.length < 3) {
    console.log('usage: ' +  path.basename(process.argv[0]) + ' ' +
        path.basename(process.argv[1]) + ' varname [value]');
    process.exit(0);
}

var varname = process.argv[2];
var op = 'get';
var val = '';

if (process.argv.length > 3) {
    val = process.argv[3];
    op = 'set';
}

var client = new net.Socket();
var varname = process.argv[2];
var host = '127.0.0.1';
var port = 4620;

client.connect(port, host, function() {
//    console.log('Connected');
    if (op == 'get') {
        client.write('%get ' + varname);
    }
    else {
        client.write('%set ' + varname + '=' + val);
    }
});

client.on('data', function(data) {
    if (op == 'get') {
        var result = Buffer.from(data);
        console.log(result.toString('utf8',0,Buffer.byteLength(result)-1));
    }
    //client.destroy(); // kill client after server's response
});

client.on('close', function() {
//    console.log('Connection closed');
});


function getFunc() {
    client.write('%get boom');
}

function setFunc() {
    client.write('%set boom ' + Math.random());
}

setInterval(setFunc, 1500);
setInterval(getFunc, 1500);