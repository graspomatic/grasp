// set up express
var express = require("express");
var app = express();
app.use(express.static('public'));

const sqlite3 = require('sqlite3').verbose();

// open database in memory
let db = new sqlite3.Database('/home/root/grasp/shapes/objects.db', (err) => {
  if (err) {
    return console.error(err.message);
  }
  console.log('Connected to the objects database.');
});

// close the database connection
db.close((err) => {
  if (err) {
    return console.error(err.message);
  }
  console.log('Close the database connection.');
});

//make way for some custom css, js and images
//app.use('/css', express.static(__dirname + '/public/css'));
//app.use('/js', express.static(__dirname + '/public/js'));
//app.use('../shapes/SVGs', express.static('../shapes/SVGs'));

app.use('/SVGs', express.static('/home/root/grasp/shapes/SVGs'));

var os = require('os');
var ifaces = os.networkInterfaces();
hostname = ifaces['eth0'][0]['address'];

var server = app.listen(8081, hostname, function(){
    var port = server.address().port;
    console.log('Server running at http://${hostname}:${port}/');
});