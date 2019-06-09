// pull in express, sqlite, http, socketio
var express = require('express');
var app = express();
app.use(express.static('public'));

const sqlite3 = require('sqlite3').verbose();


var http = require('http').Server(app);
var io = require('socket.io')(http);
var port = process.env.PORT || 3000;


app.get('/', function(req, res){
  res.sendFile(__dirname + '/index.html');
});

io.on('connection', function(socket){
  socket.on('chat message', function(msg){
    io.emit('chat message', msg);
  });
});

http.listen(port, function(){
  console.log('listening on *:' + port);
});

// open database connection
let db = new sqlite3.Database('/home/root/grasp/shapes/objects2.db', sqlite3.OPEN_READONLY, (err) => {
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