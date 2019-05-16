const http = require('http');




//To fetch IPv4 address of server
var getIpAddress = function()
{
  var ifaces = os.networkInterfaces();
    var ips = 0;

    for(var dev in ifaces)
    {
        ifaces[dev].forEach(function(details){
            //console.log(details);
           if(details.family == 'IPv4' && details.internal == false)
           {
               //ips[dev+(alias?':'+alias:'')] = details.address;
               ips = details.address;
           }
        });
    }
  return ips;
};

const hostname = getIpAddress();



const port = 3000;

const server = http.createServer((req, res) => {
  res.statusCode = 200;
  res.setHeader('Content-Type', 'text/plain');
  res.end('Hello World\n');
});

server.listen(port, hostname, () => {
  console.log(`Server running at http://${hostname}:${port}/`);
});