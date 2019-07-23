// pull in express, http, socketio
var express = require('express');
var app = express();
app.use(express.static('public'));

var http = require('http').createServer(app);
var io = require('socket.io')(http);        // used to simplify websockets


var net = require('net');

global.atob = require("atob"); // only necessary if im using atob to convert the utf16 base64 to a string

// Create a "server" to receive updates from dserv_send
var dserv_rx = net.createServer(function (socket) {
    socket.name = socket.remoteAddress + ":" + socket.remotePort;   // Identify this client

    // Handle incoming messages from clients - this just prints but would likely dispatch
    socket.on('data', function (data) {
        var result = Buffer.from(data); // this is hex
        var resultString = result.toString('utf8',0,Buffer.byteLength(result)-1); // this is a string

        io.emit('chat message', resultString);


        var linesSeparated = resultString.split(/\n/g);  //this is an array of one or more strings, one for each line

        for (var i=0; i<linesSeparated.length; i++) {
            var singleLine = linesSeparated[i].split(' '); // split it up by spaces
            var touchVals = singleLine[4];  // vals array with {}
            var touchVals = touchVals.substr(1,touchVals.length - 2);   // this is the vals array without {}, base64 encoded
            //var utf16encoded = Buffer.from(touchVals, 'base64').toString('utf16le'); // string utf16le encoded

            var sBinaryString = atob(touchVals), aBinaryView = new Uint8Array(sBinaryString.length);
	        Array.prototype.forEach.call(aBinaryView, function (el, idx, arr) { arr[idx] = sBinaryString.charCodeAt(idx); });
	        var utf16encoded = String.fromCharCode.apply(null, new Uint16Array(aBinaryView.buffer));

	        console.log(utf16encoded);

            console.log(utf16encoded.charCodeAt(0))
        }
    });
}).listen(0);

// Tell the dserv server what we're interested in
dserv_rx.on('listening', function() {
    var client = new net.Socket();
    var host = '127.0.0.1';
    var port = 4620;
    var registered = false;

    // Get the port and address of the server
    var dserv_rx_port = dserv_rx.address().port;
    var dserv_rx_addr;
    client.connect(port, host, function() {
        dserv_rx_addr = client.localAddress;
        client.emit('register');
    });

    // register with dserv
    client.on('register', function() {
        client.write('%reg ' + dserv_rx_addr + ' ' + dserv_rx_port);
    });

    // tell dserv what patterns we're interested in
    client.on('addmatch', function() {
        var every = 1
        client.write("%match " + dserv_rx_addr + ' ' + dserv_rx_port + ' sensor:0:vals ' + every);
        client.write("%match " + dserv_rx_addr + ' ' + dserv_rx_port + ' sensor:1:vals ' + every);
        registered = true;
    });

    // run the addmatch function if we haven't done it. if so, we're done. kill the client.
    client.on('data', function(data) {
        if (!registered) {
            client.emit('addmatch');
        }
        else {
            client.destroy(); // kill client after server's response
        }
    });


});


// socket.io
io.on('connection', function(socket){
  socket.on('chat message', function(msg){
    console.log('received chat message');
    io.emit('chat message', msg);
  });
});

// this is used for socket.io communication
http.listen(3000, function(){
  console.log('listening on *:3000');
});

app.use('/SVGs', express.static('/home/root/grasp/shapes/SVGs'));

// find my ip address
var os = require('os');
var ifaces = os.networkInterfaces();
hostname = ifaces['eth0'][0]['address'];

//start up server on port 8081
var server = app.listen(8081, hostname, function(){
    var port = server.address().port;
    console.log('Server running at http://${hostname}:${port}/');
});



