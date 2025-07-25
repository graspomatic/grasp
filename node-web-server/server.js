// pull in express, http, socketio
var express = require('express');
var app = express();
app.use(express.static('public'));
var http = require('http').createServer(app);
var io = require('socket.io')(http);        // used to simplify websockets

var net = require('net');

// Create a "server" to receive updates from dserv_send
var dserv_rx = net.createServer(function (socket) {
    socket.name = socket.remoteAddress + ":" + socket.remotePort;   // Identify this client

    // Forward incoming messages to the web client
    socket.on('data', function (data) {
        var result = Buffer.from(data); // this is hex
        var resultString = result.toString('utf8',0,Buffer.byteLength(result)-1); // this is a string
        io.emit('chat message', resultString);
    });
}).listen(0);

// Tell the dserv server what we're interested in
dserv_rx.on('listening', function() {
    dservclient = new net.Socket();
    var host = '192.168.88.40';
    var port = 4620;
    var registered = false;

    // Get the port and address of the server
    var dserv_rx_port = dserv_rx.address().port;
    var dserv_rx_addr;
    dservclient.connect(port, host, function() {
        dserv_rx_addr = dservclient.localAddress;
        dservclient.emit('register');
    });

    // register with dserv
    dservclient.on('register', function() {
        dservclient.write('%reg ' + dserv_rx_addr + ' ' + dserv_rx_port);
    });

    // tell dserv what patterns we're interested in
    dservclient.on('addmatch', function() {
        var every = 1
        dservclient.write("%match " + dserv_rx_addr + ' ' + dserv_rx_port + ' grasp/sensor0/vals ' + every);
        dservclient.write("%match " + dserv_rx_addr + ' ' + dserv_rx_port + ' grasp/sensor1/vals ' + every);
        registered = true;
    });

    // run the addmatch function if we haven't done it. if so, we're done. kill the client.
    dservclient.on('data', function(data) {
        if (!registered) {
            dservclient.emit('addmatch');
        } else {
            var result = Buffer.from(data);
            console.log(result.toString('utf8',0,Buffer.byteLength(result)-1));
        }
    });
});



function getFunc() {
    dservclient.write('%get boom');
}

function setFunc() {
    var thisInt = Math.floor(Math.random() * 100);
    dservclient.write('%set boom=' + thisInt.toString());
}

setInterval(setFunc, 1500);
setInterval(getFunc, 1500);

// this is necessary for socket.io communication
http.listen(3000, function(){
  console.log('listening on *:3000');
});

app.use('/SVGs', express.static('/home/root/grasp/shapes/SVGs'));

// find my ip address
var os = require('os');
var ifaces = os.networkInterfaces();
hostname = ifaces['eth1'][0]['address'];

//start up server on port 8081
var server = app.listen(8081, hostname, function(){
    var port = server.address().port;
    console.log(`Server running at http://${hostname}:${port}/`);
});



