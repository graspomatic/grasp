var redis = require("redis");
var pub = redis.createClient();

var zmq = require('zeromq')
  , sock = zmq.socket('sub');

sock.connect('tcp://127.0.0.1:5681');
sock.subscribe('sensor:');
console.log('Subscriber connected to port 5681');

sock.on('message', function(topic, message) {
    //console.log('received a message related to:', topic, 'containing message:', message);

    full = topic.toString('ascii');

    console.log(full);
    console.log(typeof full);


    var ss = full.split();
    console.log(typeof ss);


    console.log(ss[0])
    console.log(ss[7])

    pub.publish("WebClient", "rightSensor=10,10,10,10,10,10");
});