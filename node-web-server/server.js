// set up express
var express = require("express");
var app = express();
app.use(express.static('public'));

const sqlite3 = require('sqlite3').verbose();

// open database in memory
let db = new sqlite3.Database('/home/root/grasp/shapes/objects.db', sqlite3.OPEN_READONLY, (err) => {
  if (err) {
    return console.error(err.message);
  }
  console.log('Connected to the objects database.');
});

db.serialize(() => {
  db.each('SELECT ObjectID as id, blobName as panel FROM objectsTable', (err, row) => {
    if (err) {
      console.error(err.message);
    }
    console.log(row.id + "\t" + row.panel);
  });
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

// modify this function to get whatever we need from the database
app.get('/dbgetformfills', function(req, res) {

    // Get the list of categories the client is requesting and comma-separate them
    let cats=Object.keys(req.query);
    let catsString=cats.join(", ");

    console.log(catsString);

    // Connect to the DB
    let database = 'formFills.db';
    let formdb = connectDB(database);

    console.log(database);

    // Get the data from the database and send it to the client
    formdb.all("SELECT " + catsString + " FROM FormOptions",[], (err, rows) => {
        if (err) {
            throw err;
        }
        res.setHeader('Content-Type', 'application/json');
        res.send(JSON.stringify(rows));
    });
});

// close the database connection
db.close((err) => {
  if (err) {
    return console.error(err.message);
  }
  console.log('Close the database connection.');
});