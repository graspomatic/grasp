var zmq = require('zeromq')
  , sock = zmq.socket('sub');

sock.connect('tcp://127.0.0.1:5681');
sock.subscribe('sensor:');
console.log('Subscriber connected to port 5681');

sock.on('message', function(topic, message) {
    console.log('received a message related to:', topic, 'containing message:', message);
    console.log(typeof topic)
    console.log(topic.length)



  var output = Buffer.from(topic);
  console.log(output);  // Result: 32343630 -> 2460
});