///////////////////////////////////////////////////////////////////////////////////////////////
// Homemade GPS Receiver
// Copyright (c) Andrew Holme 2011-2013
// http://www.holmea.demon.co.uk/GPS/Main.htm
///////////////////////////////////////////////////////////////////////////////////////////////
// 2014-05-01: Jiao Xianjun (putaoshu@gmail.com)
// to test captured GPS bin here: http://www.jks.com/gps/gps.html

#include <stdio.h>
#include <stdlib.h>

double FC, FS, max_fo;
#include "gps_offline.h"

int main(int argc, char *argv[]) {
    int ret;

    char filename[256];
    sprintf(filename, "%s", "gps.samples.1bit.I.fs5456.if4092.bin");
    FC = 4.092e6;
    FS = 5.456e6;
    max_fo = 5000.0;

    printf("GPS CA code offline search. Extract from http://www.aholme.co.uk/GPS/Main.htm\n");
    printf("Jiao Xianjun (putaoshu@gmail.com). 2014-05.\n");
    printf("usage:\n");
    printf("gps_test   filename_of_1bit_IF_cap   carrier_freq   sampling_rate   max_freq_offset\n");
    printf("or\n");
    printf("gps_test (Make sure gps.samples.1bit.I.fs5456.if4092.bin can be found. Download http://www.jks.com/gps/gps.html)\n");

    if (argc == 5) {
      sprintf(filename, "%s", argv[1]);
      FC = atof(argv[2]);
      FS = atof(argv[3]);
    }else if (argc != 1) {
      printf("Please run with 3 arguments or without argument!\n");
      return(0);
    }

    ret = SearchInit();
    if (ret) {
        printf("SearchInit() returned %d\n", ret);
        return ret;
    }

    SearchTask(filename);

    return(0);
}
