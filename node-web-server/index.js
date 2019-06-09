var app = require('express')();
var http = require('http').Server(app);
var io = require('socket.io')(http);

app.get('/', function (req, res) {
    res.sendfile('index.html');
});

io.on('connection', function (socket) {
    console.log('a user connected');
    socket.emit('server-message', 'hello socket.io server');
    socket.on('message', function(message) {
      console.log(message);
    });
});
