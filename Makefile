CFLAGS =  -I. -Ic

gps_test:
	gcc c/test_search_offline.cpp c/search_offline.cpp /usr/lib/libfftw3.a /usr/lib/libfftw3f.a  -lm -o gps_test

