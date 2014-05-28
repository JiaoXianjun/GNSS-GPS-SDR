///////////////////////////////////////////////////////////////////////////////////////////////
// Homemade GPS Receiver
// Copyright (c) Andrew Holme 2011-2013
// http://www.holmea.demon.co.uk/GPS/Main.htm
///////////////////////////////////////////////////////////////////////////////////////////////

#include <stdio.h>

#include "gps.h"
#include "spi.h"

///////////////////////////////////////////////////////////////////////////////////////////////

int fpga_init() {

    char s[2049];
    FILE *fp;
    int n;

    fp = fopen("24.bit", "rb"); // FPGA configuration bitstream
    if (!fp) return -1;

    for (;;) {
        n = fread(s, 1, 2048, fp);
        if (n<=0) break;
        peri_spi(SPI_CS0, s, n, s, n);
    }

    fclose(fp);

    fp = fopen("44.com", "rb"); // Embedded CPU binary
    if (!fp) return -2;

    n = fread(s, 1, 2048, fp);
    peri_spi(SPI_CS0, s, n+1, s, n+1);

    return fclose(fp);
}

///////////////////////////////////////////////////////////////////////////////////////////////

int main(int argc, char *argv[]) {
    SPI_MISO miso;
    int ret;

    ret = peri_init();
    if (ret) {
        printf("peri_init() returned %d\n", ret);
        return ret;
    }

    ret = fpga_init();
    if (ret) {
        printf("fpga_init() returned %d\n", ret);
        return ret;
    }

    ret = SearchInit();
    if (ret) {
        printf("SearchInit() returned %d\n", ret);
        return ret;
    }

    spi_set(CmdSetDAC, 2560); // Put TCVCXO bang on 10.000000 MHz

    CreateTask(SearchTask);
    for(int i=0; i<NUM_CHANS; i++) CreateTask(ChanTask);
    CreateTask(SolveTask);
//    CreateTask(UserTask);

    for (int joy, prev=0; !EventCatch(EVT_EXIT); prev=joy) {
        spi_get(CmdGetJoy, &miso, 1);
        joy = JOY_MASK & ~miso.byte[0];
        if (joy!=0 && prev==0) EventRaise(joy);
    }

    SearchFree();
    peri_free();

    return !EventCatch(EVT_SHUTDOWN);
}
