/*
 * subscribe to dserv events from node
 */

var express = require('express');
var app = express();
app.use(express.static('public'));

var http = require('http').Server(app);
var io = require('socket.io')(http);        // used to simplify websockets

'use strict';
var path = require('path');
var net = require('net');

if (process.argv.length < 3) {
    console.log('usage: ' +  path.basename(process.argv[0]) + ' ' +
        path.basename(process.argv[1]) + ' pattern');
    process.exit(0);
}

// Specifiy a pattern to subscribe to as the second argument
var pattern = process.argv[2];

// Create a "server" to receive updates from dserv_send
var server = net.createServer(function (socket) {
    // Identify this client
    socket.name = socket.remoteAddress + ":" + socket.remotePort;
//    console.log("server " + socket.remoteAddress + ":" + socket.remotePort + " started");

    // Handle incoming messages from clients - this just prints but would likely dispatch
    socket.on('data', function (data) {
        var result = Buffer.from(data);
        console.log(result.toString('utf8',0,Buffer.byteLength(result)-1));
        io.emit('chat message', result.toString('utf8',0,Buffer.byteLength(result)-1));
    });
}).listen(0);

// When the server is ready, this callback is run
//  It gets the address information, registers, and adds the match for the pattern
server.on('listening', function() {

    var client = new net.Socket();
    var host = '127.0.0.1';
    var port = 4620;
    var registered = false;

    // Get the port and address of the server
    //  For the address, we wait until the client socket is opened and get localAddress from it
    var server_port = server.address().port;
    var server_addr;

    client.connect(port, host, function() {
        server_addr = client.localAddress;
        client.emit('register');
    });

    client.on('register', function() {
    //    console.log('Registering with dserv_send (' + server_addr + ":" + server_port + ")");
        client.write('%reg ' + server_addr + ' ' + server_port);
    });

    client.on('addmatch', function() {
    //        console.log('Adding match for pattern ' + pattern);
        var every = 1
        client.write("%match " + server_addr + ' ' + server_port + ' ' + pattern + ' ' + every);
        registered = true;
    });

    client.on('data', function(data) {
        if (!registered) {
            client.emit('addmatch');
        }
        else {
    //        console.log('Match added');
            client.destroy(); // kill client after server's response
        }
    });

    client.on('close', function() {
//    console.log('Connection to dserv_tcp closed');
    });
});