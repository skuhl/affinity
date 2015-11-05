#include <stdio.h>

int main(int argc, char *argv[])
{
	printf("0\n1\n");
	int first=0, second=1;
	for(int i=0; i<11; i++)
	{
		int now = first+second;
		printf("%d\n", now);
		first = second;
		second = now;
	}
}
