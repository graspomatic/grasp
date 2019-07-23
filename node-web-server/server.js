// pull in express, sqlite, http, socketio, zeromq
var express = require('express');
var app = express();
app.use(express.static('public'));

const sqlite3 = require('sqlite3').verbose();

var http = require('http').createServer(app);
var io = require('socket.io')(http);        // used to simplify websockets

var path = require('path');
var net = require('net');
//var pattern = 'sensor:0:vals';

// Create a "server" to receive updates from dserv_send
var dserv_rx = net.createServer(function (socket) {
    // Identify this client
    socket.name = socket.remoteAddress + ":" + socket.remotePort;
//    console.log("server " + socket.remoteAddress + ":" + socket.remotePort + " started");

    // Handle incoming messages from clients - this just prints but would likely dispatch
    socket.on('data', function (data) {
        var result = Buffer.from(data);
        var resultString = result.toString('utf8',0,Buffer.byteLength(result)-1);
        var linesSeparated = resultString.split(/\n/g);

        console.log(resultString);

        for (var i=0; i<linesSeparated.length; i++) {
            var singleLine = linesSeparated[i].split(' ');
            var touchVals = singleLine[4];
            console.log(singleLine);
            console.log(touchVals);
            console.log(touchVals.substr(1,touchVals.length - 2));


        }


        //console.log(result.toString('utf8',0,Buffer.byteLength(result)-1));
        //console.log(linesSeparated);
        //console.log(linesSeparated.length);



        //var utf8encoded = Buffer.from(result, 'base64').toString('utf8');



        //io.emit('chat message', result.toString('utf8',0,Buffer.byteLength(result)-1));
    });
}).listen(0);

// When the server is ready, this callback is run
//  It gets the address information, registers, and adds the match for the pattern
dserv_rx.on('listening', function() {

    var client = new net.Socket();
    var host = '127.0.0.1';
    var port = 4620;
    var registered = false;

    // Get the port and address of the server
    //  For the address, we wait until the client socket is opened and get localAddress from it
    var dserv_rx_port = dserv_rx.address().port;
    var dserv_rx_addr;

    client.connect(port, host, function() {
        dserv_rx_addr = client.localAddress;
        client.emit('register');
    });

    client.on('register', function() {
    //    console.log('Registering with dserv_send (' + server_addr + ":" + server_port + ")");
        client.write('%reg ' + dserv_rx_addr + ' ' + dserv_rx_port);
    });

    client.on('addmatch', function() {
    //        console.log('Adding match for pattern ' + pattern);
        var every = 1
        client.write("%match " + dserv_rx_addr + ' ' + dserv_rx_port + ' sensor:0:vals ' + every);
        client.write("%match " + dserv_rx_addr + ' ' + dserv_rx_port + ' sensor:1:vals ' + every);
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

//var zmq = require('zeromq')
//  , sock = zmq.socket('sub');

//sock.connect('ipc:///tmp/dserv-pub');
//sock.subscribe('sensor:');
//console.log('receiving "sensor:" messages from zeromq')


//app.get('/', function(req, res){
//  res.sendFile(__dirname + '/public/index.html');
//});

// socket.io
io.on('connection', function(socket){
  socket.on('chat message', function(msg){
    console.log('received chat message');
    io.emit('chat message', msg);
  });
});

//sock.on('message', function(topic, message) {
//    full = topic.toString('ascii');
//    console.log(full);
//
//    mes = message.toString('ascii');
//    console.log(mes);
//    io.emit('chat message', full);
//    var ss = full.split(' ');
//    var label = ss[0].split(':');
//    var sensor = label[1];
//    console.log(label);
//    console.log(ss[6].slice(1));
//
//    if (sensor == 0) {
//        pub.publish("WebClient", "rightSensor=" +
//        ss[6].slice(1) + "," + ss[7] + "," +
//        ss[8] + "," + ss[9] + "," + ss[10] + "," +
//        ss[11]);
//    }


//    console.log(typeof ss);
//    console.log(ss);
////    console.log(Object.keys(ss));
//
////
//    console.log(ss[0]);
//    console.log(ss[7])

//    pub.publish("WebClient", "rightSensor=10,10,10,10,10,10");
//});

// this is used for socket.io communication
http.listen(3000, function(){
  console.log('listening on *:3000');
});

// open database connection
let db = new sqlite3.Database('/shared/lab/stimuli/grasp/objects2.db', sqlite3.OPEN_READONLY, (err) => {
  if (err) {
    return console.error(err.message);
  }
  console.log('Connected to the objects database.');
});

//example of retrieving stuff from sqlite
//db.serialize(() => {
//  db.each('SELECT objectID as objectID, blobName as blobName, SVG as SVG FROM objectsTable', (err, row) => {
//    if (err) {
//      console.error(err.message);
//    }
//    console.log(row.objectID + "\t" + row.blobName + "\t" + row.SVG);
//  });
//});

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
//
//// modify this function to get whatever we need from the database
//app.get('/dbgetformfills', function(req, res) {
//
//    // Get the list of categories the client is requesting and comma-separate them
//    let cats=Object.keys(req.query);
//    let catsString=cats.join(", ");
//
//    console.log(catsString);
//
//    // Connect to the DB
//    let database = 'formFills.db';
//    let formdb = connectDB(database);
//
//    console.log(database);
//
//    // Get the data from the database and send it to the client
//    formdb.all("SELECT " + catsString + " FROM FormOptions",[], (err, rows) => {
//        if (err) {
//            throw err;
//        }
//        res.setHeader('Content-Type', 'application/json');
//        res.send(JSON.stringify(rows));
//    });
//});
//
// close the sqlite database connection
db.close((err) => {
  if (err) {
    return console.error(err.message);
  }
  console.log('Close the database connection.');
});

