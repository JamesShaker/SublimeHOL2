#include <unistd.h>
#include <signal.h>

int echo_out = 0;

void handle_sigint(int sig)
{ echo_out = 0; }

int main (){
	signal(SIGINT, handle_sigint); 
	char buf[1];
	while(read(0, buf, sizeof(buf))>0) {
   		if (buf[0] == 0x00) {
   			echo_out = !echo_out;
   		}
   		else if (echo_out) {
   			write(1, buf,sizeof(buf));
   		}
	}
}