#include <unistd.h>
int main (){
	char buf[1];
	int echo_out = 0;
	while(read(0, buf, sizeof(buf))>0) {
   		if (buf[0] == 0x01) {
   			echo_out = !echo_out;
   		}
   		else if (echo_out) {
   			write(1, buf,sizeof(buf));
   		}
	}
}