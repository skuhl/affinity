// Split fib() function into two functions.
#include <stdio.h>
#include <stdlib.h>

void fib_moreThan1(int n)
{
	int first = 0;
	int second = 1;

	for(int i=2; i<=n; i++)
	{
		int this=first+second;
		if(i==n)
		{
			printf("%d\n", this);
			return;
		}
		else
		{
			first=second;
			second = this;
		}
	}
}

void fib(int n)
{
	if(n < 0)
	{
		printf("huh?\n");
		return;
	}
	if(n == 0)
	{
		printf("0\n");
		return;
	}
	if(n == 1)
	{
		printf("1\n");
		return;
	}
	fib_moreThan1(n);
}


int main(void)
{
	for(int i=0; i<13; i++)
		fib(i);

}
