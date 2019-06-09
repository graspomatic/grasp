var app = require('express')();
var http = require('http').Server(app);
var io = require('socket.io')(http);
var port = process.env.PORT || 3000;

app.get('/', function (req, res) {

    res.sendFile(__dirname + '/public/index.html');
});

io.on('connection', function (socket) {
    console.log('a user connected');
    socket.emit('server-message', 'hello socket.io server');
    socket.on('message', function(message) {
      console.log(message);
    });
});

http.listen(port, function(){
  console.log('listening on *:' + port);
});
