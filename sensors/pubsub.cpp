/*Example code for pub/sub
  run as publisher
  ./pubsub pub <channelName> <message>

  run as subscriber
   ./pubsub sub <channelName>*/


/*----------------------
Publish and Subscribe
------------------------*/

#include <signal.h>
#include <cstring>
#include <iostream>
#include <stdio.h>
#include <stdlib.h>
#include <string>
#include <hiredis/hiredis.h>
#include <hiredis/async.h>
#include <hiredis/adapters/libevent.h>


using namespace std;


void subCallback(redisAsyncContext *c, void *r, void *privdata) {

  redisReply *reply = (redisReply*)r;
  if (reply == NULL){
    cout<<"Response not recev"<<endl;
    return;
  }
  if(reply->type == REDIS_REPLY_ARRAY & reply->elements == 3)
  {
    if(strcmp( reply->element[0]->str,"subscribe") != 0)
    {
      cout<<"Message received -> "<<
        reply->element[2]->str<<"( on channel : "<<reply->element[1]->str<<")"<<endl;
    }
  }
  }

void pubCallback(redisAsyncContext *c, void *r, void *privdata) {

  redisReply *reply = (redisReply*)r;
  if (reply == NULL){
    cout<<"Response not recev"<<endl;
    return;
  }
  cout<<"message published"<<endl;
  redisAsyncDisconnect(c);
}

int main(int argv, char** args)
{
   string processName(args[1]);

   signal(SIGPIPE, SIG_IGN);
   struct event_base*
     base = event_base_new();

   redisAsyncContext*
     _redisContext = redisAsyncConnect("127.0.0.1", 6379);

   if (_redisContext->err) {
     /* Let context leak for now... */
     cout<<"Error: "<< _redisContext->errstr<<endl;
     return 1;
   }

   redisLibeventAttach(_redisContext,base);

   int status;
  //Act as publisher
   if(processName.compare("pub") == 0)
   {
     string command ("publish ");
     command.append(args[2]);
     command.append (" ");
     command.append(args[3]);

     status = redisAsyncCommand(_redisContext,
           pubCallback,
           (char*)"pub", command.c_str());
   }
  //Act as subscriber
   else if(processName.compare("sub") == 0)
   {
     string command ("subscribe ");
     command.append(args[2]);

     status = redisAsyncCommand(_redisContext,
           subCallback,
           (char*)"sub", command.c_str());
   }
   else
     cout<<"Try pub or sub"<<endl;

  event_base_dispatch(base);
  return 0;
}