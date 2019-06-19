var redis = require("redis");
var pub = redis.createClient();

var zmq = require('zeromq')
  , sock = zmq.socket('sub');

sock.connect('tcp://127.0.0.1:5689');
//sock.connect('ipc:///tmp/dserv-pub');
sock.subscribe('sensor:');
console.log('Subscriber connected to port 5681');

sock.on('message', function(topic, message) {
    //console.log('received a message related to:', topic, 'containing message:', message);

    full = topic.toString('ascii');

    console.log(full);
//    console.log(typeof full);  // its a string


    var ss = full.split(' ');
    var label = ss[0].split(':');
    var sensor = label[1];
    console.log(label);
    console.log(ss[6].slice(1));


    if (sensor == 0) {
        pub.publish("WebClient", "rightSensor=" +
        ss[6].slice(1) + "," + ss[7] + "," +
        ss[8] + "," + ss[9] + "," + ss[10] + "," +
        ss[11]);
    }


//    console.log(typeof ss);
//    console.log(ss);
////    console.log(Object.keys(ss));
//
////
//    console.log(ss[0]);
//    console.log(ss[7])

//    pub.publish("WebClient", "rightSensor=10,10,10,10,10,10");
});