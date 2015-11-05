// Add lots of comments to fib.c
#include <stdio.h>
#include <stdlib.h>
// lorem ipsum

// amet
void fib(int n) // consectetur
{
	if(n < 0) // amet viverra
	{
		printf("huh?\n"); // tempus vulputate
		return; /* fusce */
	}
	if(n == 0)  // Morbi volutpat lacus
	{ // Ut
		printf("0\n"); // Nunc
		return;
	}
	if(n == 1) // eget facilisis
	{
		printf("1\n"); // nisi
		return; // non
	}

	int first = 0; // pheratra
	int second = 1;

	// odio vitae
	for(int i=2; i<=n; i++)
	{
		// vestibulum
		int this=first+second;
		if(i==n)
		{ // adipiscing ultricies
			printf("%d\n", this);
			return;
		}
		else
		{ // class aptent tactiti
			first=second; // ut
			second = this;
		}
	}
}

/* This
   is
   a
   multiline
   comment.
*/

int main(void)
{
	for(int i=0; i<13; i++)
		fib(i);

}
