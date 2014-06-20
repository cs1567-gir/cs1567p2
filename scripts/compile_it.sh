gcc -c -Wall -O2 -Wall -ansi -pedantic -fPIC -o ../src/mask_array.o ../src/mask_array.c
gcc -o ../lib/libmask_array.so -shared ../src/mask_array.o
