H = cacode.h gps_offline.h
C = search_offline.cpp test_search_offline.cpp
F = -lfftw3f -lm 
all:	$(H) $(C)
	g++ /usr/lib/libfftw.a $(C) $(F) -o gps_test
