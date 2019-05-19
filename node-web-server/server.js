// set up express
var express = require("express");
var app = express();
app.use(express.static('public'));

//make way for some custom css, js and images
app.use('/css', express.static(__dirname + '/public/css'));
app.use('/js', express.static(__dirname + '/public/js'));
//app.use('../shapes/SVGs', express.static('../shapes/SVGs'));

app.use('/SVGs', express.static('/home/root/grasp/shapes'));

var os = require('os');
var ifaces = os.networkInterfaces();
hostname = ifaces['eth0'][0]['address'];

var server = app.listen(8081, hostname, function(){
    var port = server.address().port;
    console.log('Server running at http://${hostname}:${port}/');
