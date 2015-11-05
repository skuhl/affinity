#INCLUDE <STDIO.H>
#INCLUDE <STDLIB.H>

VOID FIB(INT N)
{
	IF(N < 0)
	{
		PRINTF("HUH?\N");
		RETURN;
	}
	IF(N == 0)
	{
		PRINTF("0\N");
		RETURN;
	}
	IF(N == 1)
	{
		PRINTF("1\N");
		RETURN;
	}

	INT FIRST = 0;
	INT SECOND = 1;

	FOR(INT I=2; I<=N; I++)
	{
		INT THIS=FIRST+SECOND;
		IF(I==N)
		{
			PRINTF("%D\N", THIS);
			RETURN;
		}
		ELSE
		{
			FIRST=SECOND;
			SECOND = THIS;
		}
	}

}


INT MAIN(VOID)
{
	FOR(INT I=0; I<13; I++)
		FIB(I);

}
