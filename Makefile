.PHONY: all clean

all: main

clean:
	rm *.o main

main: main.c
	gcc main.c -o main -O3 -lm