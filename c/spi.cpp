///////////////////////////////////////////////////////////////////////////////////////////////
// Homemade GPS Receiver
// Copyright (c) Andrew Holme 2011-2013
// http://www.holmea.demon.co.uk/GPS/Main.htm
///////////////////////////////////////////////////////////////////////////////////////////////

#include <unistd.h>

#include "gps.h"
#include "spi.h"

#define BUSY 0x90 // previous request not yet serviced by embedded CPU

///////////////////////////////////////////////////////////////////////////////////////////////

static SPI_MISO junk, *prev = &junk;

///////////////////////////////////////////////////////////////////////////////////////////////
// Critical section "first come, first served"

static int enter, leave;

static void spi_enter() {
    int token=enter++;
    while (token>leave) NextTask();
}

static void spi_leave() {
    leave++;
}

///////////////////////////////////////////////////////////////////////////////////////////////

static void spi_scan(SPI_MOSI *mosi, SPI_MISO *miso=&junk, int bytes=0) {

    int txlen = sizeof(SPI_MOSI);
    int rxlen = sizeof(miso->status) + bytes;

    miso->len = rxlen;
    rxlen = MAX(txlen, prev->len);

    for (;;) {
        peri_spi(SPI_CS1,
            mosi->msg, txlen,   // mosi: new request
            prev->msg, rxlen);  // miso: response to previous caller's request

        usleep(10);
        if (prev->status!=BUSY) break; // new request accepted?
        NextTask(); // wait and try again
    }

    prev = miso; // next caller collects this for us
}

///////////////////////////////////////////////////////////////////////////////////////////////

void spi_set(SPI_CMD cmd, uint16_t wparam, uint32_t lparam) {
    SPI_MOSI tx(cmd, wparam, lparam);
    spi_enter();
    spi_scan(&tx);
    spi_leave();
}

void spi_get(SPI_CMD cmd, SPI_MISO *rx, int bytes, uint16_t wparam) {
    SPI_MOSI tx(cmd, wparam);
    spi_enter();
    spi_scan(&tx, rx, bytes);
    spi_leave();
    rx->status=BUSY;
    while(rx->status==BUSY) NextTask(); // wait for response
}

void spi_hog(SPI_CMD cmd, SPI_MISO *rx, int bytes) { // for atomic clock snapshot
    SPI_MOSI tx(cmd);
    spi_enter();                // block other threads
    spi_scan(&tx, rx, bytes);   // Send request
    tx.cmd=CmdGetJoy;           // Dummy command
    spi_scan(&tx);              // Collect response to our own request
    spi_leave();                // release block
}
