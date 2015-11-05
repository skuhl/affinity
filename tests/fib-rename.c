#include <stdio.h>
#include <stdlib.h>

void fibonacci(int val)
{
	if(val < 0)
	{
		printf("huh?\n");
		return;
	}
	if(val == 0)
	{
		printf("0\n");
		return;
	}
	if(val == 1)
	{
		printf("1\n");
		return;
	}

	int one = 0;
	int two = 1;

	for(int i=2; i<=val; i++)
	{
		int this=one+two;
		if(i==val)
		{
			printf("%d\n", this);
			return;
		}
		else
		{
			one=two;
			two = this;
		}
	}

}


int main(void)
{
	for(int i=0; i<13; i++)
		fibonacci(i);

}
